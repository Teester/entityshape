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

    def __init__(self, shape: dict, entity: str) -> None:
        """
        Compares json from a wikidata entity with the json-ld representation of an entityschema

        :param dict shape: The json-ld representation of the entityschema to be assessed against
        :param str entity: The Q number of the wikidata entity to be assessed
        """
        self._utilities = Utilities()
        self._entity: str = entity
        self._shape: dict = shape
        self._entities: dict = {}
        self._props: list = []
        self._property_responses: dict = {}

        self._get_entity_json()
        if "entities" in self._entities and self._entities["entities"][self._entity]:
            self._get_props(self._entities["entities"][self._entity]['claims'])
        self.start_shape: dict = self._utilities.get_start_shape(shape)

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        props: CompareProperties = CompareProperties(self._entity, self._entities, self._props, self._shape)
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

    def _get_entity_json(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url=url,
                                          headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        if response.status_code == 200:
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
