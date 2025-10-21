"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
import re

import requests
from requests import Response

from entityshape.api_v2.compareproperties import CompareProperties
from entityshape.api_v2.comparestatements import CompareStatements


class CompareJSONLD:
    """
    A class to compare a wikidata entity with a JSON-LD representation of an entityschema
    """

    def __init__(self, shape: dict, entity: str, language: str) -> None:
        """
        Compares json from a wikidata entity with the json-ld representation of an entityschema

        :param dict shape: The json-ld representation of the entityschema to be assessed against
        :param str entity: The Q number of the wikidata entity to be assessed
        :param str language: The language to return the results in as a 2-letter code
        """
        self._entity: str = entity
        self._shape: dict = shape

        self._property_responses: dict = {}

        self._get_entity_json()
        if self._entities["entities"][self._entity]:
            self._get_props(self._entities["entities"][self._entity]['claims'])
        self._get_property_names(language)
        self.start_shape: dict = self._get_start_shape()

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        props: CompareProperties = CompareProperties(self._entity, self._entities,
                                                     self._props, self._names, self.start_shape)
        return props.compare_properties()

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        statements: CompareStatements = CompareStatements(self._entities, self._entity, self.start_shape)
        return statements.compare_statements()

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison

        :return: json for general properties of the comparison
        """
        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            if "shapes" in self._shape:
                data_string: str = json.dumps(self._shape["shapes"])
                if item in data_string and item in self._entities["entities"][self._entity]:
                    general[item] = "incorrect"
                    expected: list = self._shape["shapes"]
                    actual: str = self._entities["entities"][self._entity][item]
                    if actual in expected:
                        general[item] = "correct"
        return general

    def _get_entity_json(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url=url,
                                          headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        self._entities = response.json()

    def _get_props(self, claims: dict) -> None:
        """
        Gets a list of properties included in the entity and assigns them to self._props

        :param claims: The claims in the entity
        """
        self._props: list = []
        # Get properties from the entity
        for claim in claims:
            if claim not in self._props:
                self._props.append(claim)
        # Get properties from the shape
        if "shapes" in self._shape:
            for shape in self._shape["shapes"]:
                properties: list = re.findall(r'P\d+', json.dumps(shape))
                for prop in properties:
                    if prop not in self._props and prop.startswith("P") and len(prop) > 1:
                        self._props.append(prop)

    def _get_property_names(self, language: str) -> None:
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :param str language: The language in which to get the property names
        :return: Nothing
        """
        self._names: dict = {}
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
                    self._names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][language]["value"]
                except KeyError:
                    self._names[json_text["entities"][item]["id"]] = ""

    def _get_start_shape(self) -> dict:
        """
        Gets the shape associated with the start parameter of the entityschema

        :return: the start shape
        """
        if "start" not in self._shape:
            return {}
        if "shapes" not in self._shape:
            return {}

        for shape in self._shape['shapes']:
            if shape["id"] == self._shape["start"]:
                return shape
        return {}
