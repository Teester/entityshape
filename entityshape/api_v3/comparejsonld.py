"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
import re

import requests
from requests import Response

from api_v3.utilities import Utilities
from entityshape.api_v3.compareproperties import CompareProperties
from entityshape.api_v3.comparestatements import CompareStatements


class CompareJSONLD:
    """
    A class to compare a wikidata entity with a JSON-LD representation of an entityschema
    """

    def __init__(self, shape: dict, entity: str, language:str) -> None:
        """
        Compares json from a wikidata entity with the json-ld representation of an entityschema

        :param dict shape: The json-ld representation of the entityschema to be assessed against
        :param str entity: The Q number of the wikidata entity to be assessed
        """
        self._utilities = Utilities()
        self._entity: str = entity
        self._shape: dict = shape
        self._entities: dict = self._get_entity_json(entity)
        self._property_responses: dict = {}
        self._props = self._get_props()
        self._names = self._get_property_names(language)

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        props: CompareProperties = CompareProperties(self._entity, self._entities, self._props, self._shape, self._names)
        return props.compare_properties()

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        statements: CompareStatements = CompareStatements(self._entities, self._entity, self._shape)
        return statements.compare_statements()

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison

        :return: json for general properties of the comparison
        """
        if "shapes" not in self._shape:
            return {}
        if "entities" not in self._entities:
            return {}

        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            data_string: str = json.dumps(self._shape["shapes"])
            if item in data_string and item in self._entities["entities"][self._entity]:
                general[item] = "incorrect"
                expected: list = self._shape["shapes"]
                actual: str = self._entities["entities"][self._entity][item]
                if actual in expected:
                    general[item] = "correct"
        return general

    @staticmethod
    def _get_entity_json(entity: str) -> dict:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{entity}.json"
        response: Response = requests.get(url=url,
                                          headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        if response.status_code == 200:
            return response.json()
        return {}

    def _get_props(self) -> list:
        """
        Gets a list of properties included in the entity and assigns them to self._props

        """
        if "entities" not in self._entities:
            return []
        if self._entity not in self._entities["entities"]:
            return []

        claims = self._entities["entities"][self._entity]['claims']
        props: list = []
        # Get properties from the entity
        for claim in claims:
            if claim not in props:
                props.append(claim)

        if "shapes" not in self._shape:
            return props
        # Get properties from the shape
        for shape in self._shape["shapes"]:
            properties: list = re.findall(r'P\d+', json.dumps(shape))
            for prop in properties:
                if prop not in props and prop.startswith("P") and len(prop) > 1:
                    props.append(prop)
        return props

    def _get_property_names(self, language: str) -> dict:
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :param str language: The language in which to get the property names
        :return: Nothing
        """
        names: dict = {}
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            response: Response = requests.get(url="https://www.wikidata.org/w/api.php",
                                              params={"action": "wbgetentities",
                                                      "ids": required_properties,
                                                      "props": "labels",
                                                      "languages": language,
                                                      "format": "json"},
                                              headers={'User-Agent': 'Entityshape API by User:Teester'})
            json_text: dict = response.json()
            for item in element:
                try:
                    names[item] = json_text["entities"][item]["labels"][language]["value"]
                except KeyError:
                    names[item] = ""
        return names
