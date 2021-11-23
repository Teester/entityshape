import json
import re

import requests
from requests import Response


class CompareJSONLD:
    def __init__(self, shape: dict, entity: str, language: str):
        self._entity: str = entity
        self._shape: dict = shape
        self._property_responses: dict = {}

        self._get_entity_json()
        if self._entities["entities"][self._entity]:
            self._get_props(self._entities["entities"][self._entity]['claims'])
        self._get_property_names(language)
        self._compare_statements()
        self._compare_properties()

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        return self._compare_properties()

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        return self._compare_statements()

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison
        :return: json for general properties of the comparison
        """
        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            if item in self._shape and item in self._entities["entities"][self._entity]:
                expected: list = self._shape[item]["allowed"]
                actual: str = self._entities["entities"][self._entity][item]
                general[item] = "incorrect"
                if actual in expected:
                    general[item] = "correct"
        return general

    def _get_entity_json(self):
        """
        Downloads the entity from wikidata
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url)
        self._entities = response.json()

    def _get_props(self, claims: dict):
        """
        Gets a list of properties included in the entity
        :param claims: The claims in the entity
        """
        self._props: list = []
        # Get properties from the entity
        for claim in claims:
            if claim not in self._props:
                self._props.append(claim)
        # Get properties from the shape
        for shape in self._shape["shapes"]:
            shape_text = json.dumps(shape)
            properties = re.findall(r'P\d+', shape_text)
            for prop in properties:
                if prop not in self._props and prop.startswith("P") and len(prop) > 1:
                    self._props.append(prop)

    def _get_property_names(self, language: str):
        """
        Gets the names of properties from wikidata
        """
        self._names: dict = {}
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            url: str = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids=" \
                       f"{required_properties}&props=labels&languages={language}&format=json"
            response: Response = requests.get(url)
            json_text: dict = response.json()
            for item in element:
                try:
                    self._names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][language]["value"]
                except KeyError:
                    self._names[json_text["entities"][item]["id"]] = ""

    def _compare_properties(self):
        return {}

    def _compare_statements(self):
        start_shape = self._get_start_shape()
        statements: dict = {}
        claims: dict = self._entities["entities"][self._entity]['claims']
        expressions = start_shape["expression"]["expressions"]
        for claim in claims:
            statement_results: list = []
            property_statement_results: list = []
            for statement in claims[claim]:
                child: dict = {"property": claim}
                allowed = "not in schema"
                prop = statement["mainsnak"]["property"]
                for expression in expressions:
                    if expression["predicate"].endswith(prop):
                        allowed = "present"
                if allowed != "":
                    child["response"] = allowed
                statements[statement["id"]] = child
                statement_results.append(allowed)
                if allowed.startswith("missing"):
                    allowed = "incorrect"
                property_statement_results.append(allowed)
            self._property_responses[claim] = property_statement_results
        return statements

    def _get_start_shape(self):
        start = self._shape['start']
        start_shape = {}
        for shape in self._shape['shapes']:
            if shape["id"] == start:
                start_shape = shape
        return start_shape