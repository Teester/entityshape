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

    def _get_start_shape(self) -> dict:
        """
        Gets the shape associated with the start parameter of the entityschema

        :return: the start shape
        """
        if "start" in self._shape:
            start: dict = self._shape['start']
            start_shape: dict = {}
            if "shapes" in self._shape:
                for shape in self._shape['shapes']:
                    if shape["id"] == start:
                        start_shape = shape
            return start_shape
        else:
            return {}

    def _process_one_of(self) -> None:
        """
        Processes one of expression types in the shape

        :return:
        """
        pass

    def _process_each_of(self) -> None:
        """
       Processes each of expression types in the shape

       :return:
       """
        pass


class CompareProperties:

    def __init__(self, entity: str, entities: dict, props: list, names: dict, start_shape: dict) -> None:
        self._entities: dict = entities
        self._names: dict = names
        self._entity: str = entity
        self._props: list = props
        self._start_shape: dict = start_shape

    def compare_properties(self) -> dict:
        """

        :return:
        """
        claims: dict = self._entities["entities"][self._entity]["claims"]
        properties: dict = {}
        if self._start_shape is None:
            return properties
        utilities: Utilities = Utilities()
        for prop in self._props:
            child: dict = {"name": self._names[prop],
                           "necessity": utilities.calculate_necessity(prop, self._start_shape)}
            if prop in claims:
                response: str = self.check_claims_for_props(claims, prop)
            else:
                response: str = "missing"
            if child["necessity"] != "absent":
                if response != "":
                    child["response"] = response
            properties[prop] = child
        return properties

    def check_claims_for_props(self, claims: dict, prop: str) -> str:
        """"

        :return:
        """
        cardinality = "correct"
        allowed: str = "present"
        if "expression" in self._start_shape and "expressions" in self._start_shape["expression"]:
            for expression in self._start_shape["expression"]["expressions"]:
                allowed_list = []
                for property2 in claims[prop]:
                    is_it_allowed = self._process_triple_constraint(property2["mainsnak"],
                                                                    expression,
                                                                    allowed)
                    if "extra" in self._start_shape:
                        for extra in self._start_shape["extra"]:
                            if extra.endswith(property2["mainsnak"]["property"]) and allowed == "incorrect":
                                is_it_allowed = "allowed"
                    allowed_list.append(is_it_allowed)
                    cardinality = self._process_cardinalities2(allowed_list, self._start_shape,
                                                               property2["mainsnak"]["property"])
                if "correct" in allowed_list:
                    allowed = "correct"
        if cardinality == "correct":
            response = allowed
        else:
            response = cardinality
        return response

    def _process_cardinalities2(self, allowed_list, shape, prop):
        if "predicate" not in shape["expression"]["expressions"][0]:
            return "correct"
        if not shape["expression"]["expressions"][0]["predicate"].endswith(prop):
            return "correct"
        occurrences: dict = allowed_list.count("correct")
        for expression in shape["expression"]["expressions"]:
            if expression["predicate"].endswith(prop):
                cardinality = self._process_cardinalities3(occurrences, expression)
                predicate: str = f'http://www.wikidata.org/prop/direct/{prop}'
                if "extra" in shape and predicate in shape["extra"] and cardinality == "too many statements":
                    cardinality = "correct"
                return cardinality

    @staticmethod
    def _process_cardinalities3(occurrences, expression) -> str:
        cardinality: str = "correct"
        min_cardinality: bool = True
        max_cardinality: bool = True
        max_card: int = 1
        min_card: int = 1
        if "max" in expression:
            max_card = expression["max"]
        if "min" in expression:
            min_card = expression["min"]
        if max_card < occurrences:
            max_cardinality = False
        if min_card > occurrences:
            min_cardinality = False
        if max_card == -1:
            max_cardinality = True
        if min_card == -1:
            min_cardinality = True
        if min_cardinality and not max_cardinality:
            cardinality = "too many statements"
        if max_cardinality and not min_cardinality:
            cardinality = "not enough correct statements"
        return cardinality

    @staticmethod
    def _process_cardinalities(claims: dict, shape: dict) -> str:
        """
        Processes cardinalities of claims to see if the number of claims on a property match
        the requirements of the shape

        :param claims: The claims to be checked
        :param shape: The shape to be checked against
        :return: the status of the cardinality
        """
        cardinality: str = ""
        if "expression" in shape and "expressions" in shape["expression"]:
            for expression in shape["expression"]["expressions"]:
                snak_property: str = claims[0]["mainsnak"]["property"]
                if "predicate" in expression and (expression["predicate"].endswith(snak_property)):
                    cardinality = Utilities.process_cardinalities(expression, claims)
                    predicate: str = f'http://www.wikidata.org/prop/direct/{snak_property}'
                    if "extra" in shape and predicate in shape["extra"] and cardinality == "too many statements":
                        cardinality = "correct"
        return cardinality

    @staticmethod
    def _process_triple_constraint(statement: dict, expression: dict, allowed: str) -> str:
        """
        Processes triple constraint expression types in the shape

        :param dict statement: The entity's statement to be assessed
        :param dict expression: The expression from the shape to be assessed against
        :param str allowed: Whether the statement is allowed by the expression or not currently
        :return: allowed
        """
        statement_property: str = statement["property"]
        if "predicate" in expression and \
                expression["predicate"].endswith(statement_property):
            allowed = "present"
            try:
                if expression["valueExpr"]["type"] == "NodeConstraint":
                    allowed = Utilities.process_node_constraint(statement,
                                                                expression["valueExpr"],
                                                                allowed)
            except (KeyError, TypeError):
                pass
        return allowed


class CompareStatements:

    def __init__(self, entities: dict, entity: str, start_shape: dict) -> None:
        self._entities: dict = entities
        self._entity: str = entity
        self.start_shape: dict = start_shape

    def compare_statements(self) -> dict:
        """
        Compares the statements with the shape

        :return: statements
        """
        statements: dict = {}
        claims: dict = self._entities["entities"][self._entity]['claims']
        for claim in claims:
            property_statement_results: list = []
            for statement in claims[claim]:
                child: dict = {"property": claim}
                utilities: Utilities = Utilities()
                necessity = utilities.calculate_necessity(statement["mainsnak"]["property"], self.start_shape)
                if necessity != "absent":
                    child["necessity"] = necessity
                child, allowed = self._process_shape(statement["mainsnak"], self.start_shape, child)
                statements[statement["id"]] = child
                if allowed.startswith("missing"):
                    allowed = "incorrect"
                property_statement_results.append(allowed)
        return statements

    def _process_shape(self, statement: dict, shape: dict, child: dict) -> Tuple[Any, str]:
        """
        Processes a full shape

        :param statement: The entity's statement to be assessed
        :param shape: The shape to be assessed against
        :param child: The current response from the assessment
        :return: child and allowed
        """
        expressions: dict = {}
        if "expression" in shape and "expressions" in shape["expression"]:
            expressions = shape["expression"]["expressions"]
        allowed: str = "not in schema"
        for expression in expressions:
            allowed = self.process_expressions(expression, shape, statement, allowed)
        if allowed != "":
            child["response"] = allowed
        return child, allowed

    def process_expressions(self, expression: dict, shape: dict, statement: dict, allowed: str) -> str:
        if expression["type"] == "TripleConstraint" and expression["predicate"].endswith(statement["property"]):
            allowed = self._process_triple_constraint(statement,
                                                      expression,
                                                      allowed)
            if "extra" in shape:
                for extra in shape["extra"]:
                    if extra.endswith(statement["property"]) and allowed == "incorrect":
                        allowed = "allowed"
        return allowed

    @staticmethod
    def _process_triple_constraint(statement: dict, expression: dict, allowed: str) -> str:
        """
        Processes triple constraint expression types in the shape

        :param statement: The entity's statement to be assessed
        :param expression: The expression from the shape to be assessed against
        :param allowed: Whether the statement is allowed by the expression or not currently
        :return: allowed
        """
        statement_property: str = statement["property"]
        if "predicate" in expression and \
                expression["predicate"].endswith(statement_property):
            allowed = "allowed"
            Utilities.process_cardinalities(expression, {"mainsnak": statement})
            try:
                if expression["valueExpr"]["type"] == "NodeConstraint":
                    allowed = Utilities.process_node_constraint(statement,
                                                                expression["valueExpr"],
                                                                allowed)
            except (KeyError, TypeError):
                pass
        return allowed


class Utilities:

    def calculate_necessity(self, prop: str, shape: dict) -> str:
        """
        Check if a property is required, optional or absent from a shape

        :param str prop: the property to be checked
        :param dict shape: the shape to check against
        :return: necessity
        """
        necessity: str = "absent"
        if "expression" in shape and "expressions" in shape["expression"]:
            for expression in shape["expression"]["expressions"]:
                if "predicate" in expression and expression["predicate"].endswith(prop):
                    necessity = self.required_or_absent(expression)
        return necessity

    @staticmethod
    def required_or_absent(expression: dict) -> str:
        necessity: str = "optional"
        if ("min" in expression and expression["min"] > 0) or ("min" not in expression and "max" not in expression):
            necessity = "required"
        if "min" in expression and "max" in expression and expression["min"] == 0 and expression["max"] == 0:
            necessity = "absent"
        return necessity

    @staticmethod
    def process_cardinalities(expression: dict, claim: dict) -> str:
        """
        Processes cardinalities in expressions

        :return: cardinality
        """
        cardinality: str = "correct"
        min_cardinality: bool = True
        max_cardinality: bool = True
        max_card: int = 1
        min_card: int = 1
        if "max" in expression:
            max_card = expression["max"]
        if "min" in expression:
            min_card = expression["min"]
        if max_card < len(claim):
            max_cardinality = False
        if min_card > len(claim):
            min_cardinality = False
        if max_card == -1:
            max_cardinality = True
        if min_card == -1:
            min_cardinality = True
        if min_cardinality and not max_cardinality:
            cardinality = "too many statements"
        if max_cardinality and not min_cardinality:
            cardinality = "not enough correct statements"
        return cardinality

    @staticmethod
    def process_node_constraint(statement: dict, expression: dict, allowed: str) -> str:
        """
        Processes node constraint expression types in the shape

        :param dict statement: The entity's statement to be assessed
        :param dict expression: The expression from the shape to be assessed against
        :param str allowed: Whether the statement is allowed by the expression or not currently
        :return: allowed
        """
        if statement["snaktype"] == "value" and \
                statement["datavalue"]["type"] == "wikibase-entityid":
            obj = f'http://www.wikidata.org/entity/{statement["datavalue"]["value"]["id"]}'
            if "values" in expression:
                if obj in expression["values"]:
                    allowed = "correct"
                else:
                    allowed = "incorrect"
        return allowed
