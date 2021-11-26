"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
import re
from typing import Tuple, Any

import requests
from requests import Response


class CompareJSONLD:
    """
    A class to compare a wikidata entity with a JSON-LD representation of an entityschema
    """
    def __init__(self, shape: dict, entity: str, language: str):
        """
        Compares json from a wikidata entity with the json-ld representation of an entityschema

        :param shape: The json-ld representation of the entityschema to be assessed against
        :param entity: The Q number of the wikidata entity to be assessed
        :param language: The language to return the results in as a 2 letter code
        """
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

    def _get_entity_json(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url)
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
        for shape in self._shape["shapes"]:
            properties = re.findall(r'P\d+', json.dumps(shape))
            for prop in properties:
                if prop not in self._props and prop.startswith("P") and len(prop) > 1:
                    self._props.append(prop)

    def _get_property_names(self, language: str):
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :param language The language in which to get the property names
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
        """

        :return:
        """
        claims = self._entities["entities"][self._entity]["claims"]
        properties: dict = {}
        response = "missing"
        allowed = "not allowed"
        for prop in self._props:
            child: dict = {"name": self._names[prop],
                           "necessity": self._calculate_necessity(prop, self._get_start_shape())}
            if prop in claims:
                cardinality = self._process_cardinalities_for_properties(claims[prop],
                                                                         self._get_start_shape())
                if cardinality == "correct":
                    response = allowed
                else:
                    response = cardinality
            if response != "":
                child["response"] = response
            properties[prop] = child
        return properties

    def _compare_statements(self):
        start_shape = self._get_start_shape()
        statements: dict = {}
        claims: dict = self._entities["entities"][self._entity]['claims']
        for claim in claims:
            property_statement_results: list = []
            for statement in claims[claim]:
                child: dict = {"property": claim}
                child, allowed = self._process_shape(statement["mainsnak"], start_shape, child)
                statements[statement["id"]] = child
                if allowed.startswith("missing"):
                    allowed = "incorrect"
                property_statement_results.append(allowed)
            self._property_responses[claim] = property_statement_results
        return statements

    def _get_start_shape(self):
        """
        Gets the shape associated with the start parameter of the entityschema

        :return: the start shape
        """
        start = self._shape['start']
        start_shape = {}
        for shape in self._shape['shapes']:
            if shape["id"] == start:
                start_shape = shape
        return start_shape

    def _process_shape(self, statement, shape, child) -> Tuple[Any, str]:
        """
        Processes a full shape

        :param statement: The entity's statement to be assessed
        :param shape: The shape to be assessed against
        :param child: The current response from the assessment
        :return: child and allowed
        """
        expressions: dict = shape["expression"]["expressions"]
        allowed: str = "not in schema"
        for expression in expressions:
            if expression["type"] == "TripleConstraint":
                child, allowed = self._process_triple_constraint(statement,
                                                                 expression,
                                                                 child,
                                                                 allowed)
        if allowed != "":
            child["response"] = allowed
        return child, allowed

    def _process_triple_constraint(self, statement, expression, child, allowed):
        """
        Processes triple constraint expression types in the shape

        :param statement: The entity's statement to be assessed
        :param expression: The expression from the shape to be assessed against
        :param child: The current response from the assessment
        :param allowed: Whether the statement is allowed by the expression or not currently
        :return: child and allowed
        """
        if expression["predicate"].endswith(statement["property"]):
            allowed = "present"
        self._process_cardinalities(expression, statement)
        if "valueExpr" in expression and \
                expression["valueExpr"]["type"] == "NodeConstraint":
            child, allowed = self._process_node_constraint(statement,
                                                           expression["valueExpr"],
                                                           child,
                                                           allowed)
        return child, allowed

    @staticmethod
    def _process_node_constraint(statement, expression, child, allowed):
        """
        Processes node constraint expression types in the shape

        :param statement: The entity's statement to be assessed
        :param expression: The expression from the shape to be assessed against
        :param child: The current response from the assessment
        :param allowed: Whether the statement is allowed by the expression or not currently
        :return: child and allowed
        """
        if statement["snaktype"] == "value" and \
                statement["datavalue"]["type"] == "wikibase-entityid":
            obj = f'http://www.wikidata.org/entity/{statement["datavalue"]["value"]["id"]}'
            if obj in expression["values"]:
                allowed = "correct"
        return child, allowed

    def _process_one_of(self):
        """
        Processes one of expression types in the shape

        :return:
        """
        pass

    def _process_each_of(self):
        """
       Processes each of expression types in the shape

       :return:
       """
        pass

    @staticmethod
    def _process_cardinalities(expression, claim):
        """
       Processes cardinalities in expressions

       :return:
       """
        cardinality: str = "correct"
        min_cardinality: bool = False
        max_cardinality: bool = False
        if "max" in expression and expression['max'] < len(claim):
            max_cardinality = False
        if "min" in expression and expression['min'] > len(claim):
            min_cardinality = False
        if min_cardinality and not max_cardinality:
            cardinality = "too many statements"
        if max_cardinality and not min_cardinality:
            cardinality = "not enough correct statements"
        return cardinality

    def _process_cardinalities_for_properties(self, claims, shape):
        cardinality = ""
        for expression in shape["expression"]["expressions"]:
            if expression["predicate"].endswith(claims[0]["mainsnak"]["property"]):
                cardinality = self._process_cardinalities(expression, claims)
        return cardinality

    @staticmethod
    def _calculate_necessity(prop, shape):
        """
        Check if a property is required, optional or absent from a shape

        :param prop: the property to be checked
        :param shape: the shape to check against
        :return: necessity
        """
        necessity = "absent"
        for expression in shape["expression"]["expressions"]:
            if expression["predicate"].endswith(prop):
                necessity = "optional"
                if "min" in expression and expression["min"] > 0:
                    necessity = "required"
                if "min" not in expression and "max" not in expression:
                    necessity = "required"
        return necessity