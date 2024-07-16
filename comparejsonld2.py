"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
from typing import Tuple, Any

import requests
from requests import Response


class CompareJSONLD2:
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

        self.response = SetupResponse(entity, shape, language)
        self._entities = self.response.get_entities()

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        props: CompareProperties = CompareProperties(self.response)
        return props.compare_properties()

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        statements: CompareStatements = CompareStatements(self.response)
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


class CompareProperties:

    def __init__(self, response) -> None:
        self.results: dict = {}

        self._shapes: dict = response.get_shapes()
        self._entity: str = response.get_entity()
        self._entities: dict = response.get_entities()
        self._responses: dict = response.get_response()
        self._start_shape: dict = response.get_start_shape()
        self._names: dict = response.get_names()

    def compare_properties(self) -> dict:
        """

        :return:
        """
        self._check_props_for_claims()
        return self.results

    def _check_props_for_claims(self):
        self._process_expression(self._start_shape)
        self._process_responses()

    def _process_expression(self, shape: dict):
        expressions = self._get_list_of_expressions(shape)

        for expression in expressions:
            claims: dict = self._entities["entities"][self._entity]["claims"]
            for claim in claims:
                for snak in claims[claim]:
                    self._process_claims(expression, claim, snak)

    def _process_claims(self, expression, claim, snak):
        if expression["type"] == "TripleConstraint":
            if expression["predicate"] in [f"{Constants.Prefixes.wdt}{claim}",
                                           f"{Constants.Prefixes.p}{claim}"]:
                self._process_triple_constraint(expression, snak)
        elif expression["type"] == "EachOf":
            self._process_each_of(expression)
        else:
            self._responses[expression["predicate"]][snak["id"]] = Constants.Responses.correct

    @staticmethod
    def _get_list_of_expressions(shape):
        expressions = []
        if "expressions" in shape:
            for expression in shape["expressions"]:
                expressions.append(expression)
        elif "expression" in shape:
            expressions.append(shape["expression"])
        else:
            expressions.append(shape)
        return expressions

    def _process_each_of(self, shape):
        if "expressions" in shape:
            for expression in shape["expressions"]:
                self._process_expression(expression)
        else:
            self._process_expression(shape["expression"])

    def _process_triple_constraint(self, expression, snak):
        property_id = snak["mainsnak"]["property"]
        if snak["mainsnak"]["datatype"] in ["wikibase-item", "wikibase-entity-id]"]:
            if snak["mainsnak"]["datatype"] == "wikibase-item":
                predicate = f"{Constants.Prefixes.wdt}{property_id}"
            else:
                predicate = f"{Constants.Prefixes.p}{property_id}"
            value = snak["mainsnak"]["datavalue"]["value"]["id"]
            value_id = f"{Constants.Prefixes.wd}{value}"
            response = self._process_wikidata_item(expression, predicate, value_id)
            self._responses[expression["predicate"]][snak["id"]] = response
        elif snak["mainsnak"]["datatype"] in ["time", "quantity", "commonsMedia", "globe-coordinate", "external-id"]:
            self._responses[expression["predicate"]][snak["id"]] = Constants.Responses.present
        else:
            print(f'type = {snak["mainsnak"]["datatype"]}')

    def _process_wikidata_item(self, expression, predicate, value_id):
        if expression["predicate"] not in predicate:
            return Constants.Responses.missing
        if "valueExpr" not in expression:
            # any value is valid
            return Constants.Responses.correct
        elif "type" not in expression["valueExpr"]:
            # must conform to a sub-shape
            for shape in self._shapes["shapes"]:
                if shape["id"] == expression["valueExpr"]:
                    self._process_expression(shape)
        elif expression["valueExpr"]["type"] == "NodeConstraint":
            # must conform to a node constraint
            return self._process_node_constraint(value_id, expression["valueExpr"])
        else:
            print("not a node constraint or value")
            return Constants.Responses.missing

    @staticmethod
    def _process_node_constraint(value, node):
        if value in node["values"]:
            return Constants.Responses.correct
        return Constants.Responses.incorrect

    def _process_responses(self):
        responses = {}
        for expression in self._start_shape["expression"]["expressions"]:
            cardinality = self._process_cardinality(expression)
            if "extra" in self._start_shape:
                if expression["predicate"] in self._start_shape["extra"]:
                    cardinality = Constants.Responses.correct
            necessity = Utilities.get_necessity(expression)
            predicate = expression["predicate"].removeprefix(Constants.Prefixes.wdt)
            predicate = predicate.removeprefix(Constants.Prefixes.p)
            if expression["predicate"] not in responses:
                responses[predicate] = {}
            responses[predicate]["necessity"] = necessity
            responses[predicate]["response"] = cardinality
        for claim in self._entities["entities"][self._entity]["claims"]:
            if claim not in responses:
                responses[claim] = {}
                responses[claim]["necessity"] = Constants.Necessities.absent
        for response in responses:
            responses[response]["name"] = self._names[response]
        self.results = responses

    def _process_cardinality(self, expression: dict) -> str:
        cardinality_result = Constants.Responses.correct
        cardinality = len(self._responses[expression["predicate"]])
        if self._responses[expression["predicate"]]["in_schema"]:
            cardinality = cardinality - 1
        maximum_allowed_cardinality = 1
        minimum_allowed_cardinality = 1
        if "max" in expression:
            maximum_allowed_cardinality = expression["max"]
            if expression["max"] == -1:
                maximum_allowed_cardinality = 1000
        if "min" in expression:
            minimum_allowed_cardinality = expression["min"]
        if cardinality > maximum_allowed_cardinality:
            cardinality_result = Constants.Responses.too_many
        if cardinality < minimum_allowed_cardinality:
            cardinality_result = Constants.Responses.not_enough
        return cardinality_result


class CompareStatements:

    def __init__(self, response) -> None:
        self._entity: str = response.get_entity()
        self._entities: dict = response.get_entities()
        self.start_shape: dict = response.get_start_shape()
        self._statements = response.get_statements()

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
                necessity = self.calculate_necessity(statement["mainsnak"]["property"], self.start_shape)
                if necessity != Constants.Responses.absent:
                    child["necessity"] = necessity
                child, allowed = self._process_shape(statement["mainsnak"], self.start_shape, child)
                statements[statement["id"]] = child
                if allowed.startswith(Constants.Responses.missing):
                    allowed = Constants.Responses.incorrect
                property_statement_results.append(allowed)
        print(statements)
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
        allowed: str = Constants.Responses.not_in_schema
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
                    if extra.endswith(statement["property"]) and allowed == Constants.Responses.incorrect:
                        allowed = Constants.Responses.allowed
        return allowed

    def _process_triple_constraint(self, statement: dict, expression: dict, allowed: str) -> str:
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
            allowed = Constants.Responses.allowed
            self.process_cardinalities(expression, {"mainsnak": statement})
            try:
                if expression["valueExpr"]["type"] == "NodeConstraint":
                    allowed = self.process_node_constraint(statement,
                                                           expression["valueExpr"],
                                                           allowed)
            except (KeyError, TypeError):
                pass
        return allowed

    @staticmethod
    def calculate_necessity(prop: str, shape: dict) -> str:
        """
        Check if a property is required, optional or absent from a shape

        :param str prop: the property to be checked
        :param dict shape: the shape to check against
        :return: necessity
        """
        necessity: str = "absent"
        list_of_expressions: list = []

        if "expression" not in shape:
            return necessity

        if "expressions" in shape["expression"]:
            for expression in shape["expression"]["expressions"]:
                list_of_expressions.append(expression)
        else:
            list_of_expressions.append(shape["expression"])

        for expression in list_of_expressions:
            if "predicate" in expression and expression["predicate"].endswith(prop):
                necessity = Utilities.get_necessity(expression)
        return necessity

    @staticmethod
    def process_cardinalities(expression: dict, claim: dict) -> str:
        """
        Processes cardinalities in expressions

        :return: cardinality
        """
        cardinality: str = Constants.Responses.correct
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
            cardinality = Constants.Responses.too_many
        if max_cardinality and not min_cardinality:
            cardinality = Constants.Responses.not_enough
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
        if statement["snaktype"] == "value" and statement["datavalue"]["type"] == "wikibase-entityid":
            obj = f'{Constants.Prefixes.wd}{statement["datavalue"]["value"]["id"]}'
            if "values" in expression:
                if obj in expression["values"]:
                    allowed = Constants.Responses.correct
                else:
                    allowed = Constants.Responses.incorrect
        return allowed


class Utilities:
    @staticmethod
    def get_necessity(expression: dict) -> str:
        necessity_result = Constants.Necessities.required
        if "min" in expression and expression["min"] == 0:
            necessity_result = Constants.Necessities.optional
            if "max" in expression and expression["max"] == 0:
                necessity_result = Constants.Necessities.not_allowed
        return necessity_result


class Constants:
    class Prefixes:
        wdt: str = "http://www.wikidata.org/prop/direct/"
        wd:  str = "http://www.wikidata.org/entity/"
        p:   str = "http://www.wikidata.org/prop/"

    class Responses:
        absent = "absent"
        allowed = "allowed"
        correct = "correct"
        incorrect = "incorrect"
        missing = "missing"
        not_enough = "not enough statements"
        not_in_schema = "not in schema"
        present = "present"
        too_many = "too many statements"

    class Necessities:
        required = "required"
        optional = "optional"
        not_allowed = "not allowed"
        absent = "absent"


class SetupResponse:
    """
    This class downloads the entity being checked and sets up the structures needed for processing shapes
    """
    def __init__(self, entity, shapes, language):
        self._entity = entity
        self._get_entity_json()
        self._shapes = shapes
        self._language = language
        self._responses = {}
        self._start_shape = {}
        self._names = {}
        self._statements = {}
        self._props = []
        self._get_start_shape()
        self._add_claims_to_response()
        self._get_property_names()
        self._get_statements()

    def get_response(self) -> dict:
        return self._responses

    def get_start_shape(self) -> dict:
        return self._start_shape

    def get_entity(self) -> str:
        return self._entity

    def get_names(self) -> dict:
        return self._names

    def get_entities(self) -> dict:
        return self._entities

    def get_shapes(self) -> dict:
        return self._shapes

    def get_statements(self):
        return self._statements

    def _add_claims_to_response(self) -> None:
        self._add_shape_properties_to_response(self._start_shape)

        claims: dict = self._entities["entities"][self._entity]["claims"]
        for claim in claims:
            self._add_claim_properties_to_response(claim)

    def _add_claim_properties_to_response(self, claim: dict) -> None:
        if f"{Constants.Prefixes.wdt}{claim}" not in self._responses:
            if f"{Constants.Prefixes.p}{claim}" not in self._responses:
                self._add_expressions_to_response(f"{Constants.Prefixes.wdt}{claim}")

    def _add_shape_properties_to_response(self, shape: dict) -> None:
        if "expressions" in shape:
            for expression in shape["expressions"]:
                self._add_expressions_from_shape(expression)
        elif "expression" in shape:
            self._add_expressions_from_shape(shape['expression'])
        else:
            self._add_expressions_from_shape(shape)

    def _add_expressions_from_shape(self, expression: dict) -> None:
        if "predicate" in expression:
            if expression["predicate"] not in self._responses:
                self._add_expressions_to_response(expression["predicate"])
            self._responses[expression["predicate"]]["in_schema"] = True
        elif "expressions" in expression:
            for expression1 in expression["expressions"]:
                self._add_shape_properties_to_response(expression1)

    def _add_expressions_to_response(self, property_id: str) -> None:
        self._responses[property_id] = {}
        prop = property_id.removeprefix(Constants.Prefixes.wdt)
        prop = prop.removeprefix(Constants.Prefixes.p)
        self._props.append(prop)

    def _get_start_shape(self) -> None:
        if "start" not in self._shapes:
            self._start_shape = {}
        if "shapes" not in self._shapes:
            self._start_shape = {}

        start: dict = self._shapes['start']
        for shape in self._shapes['shapes']:
            if shape["id"] == start:
                self._start_shape = shape

    def _get_property_names(self) -> None:
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :return: Nothing
        """
        self._names: dict = {}

        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            url: str = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids=" \
                       f"{required_properties}&props=labels&languages={self._language}&format=json"
            response: Response = requests.get(url)
            json_text: dict = response.json()
            for item in element:
                entity = json_text["entities"][item]
                if "labels" in entity and self._language in entity["labels"]:
                    self._names[entity["id"]] = entity["labels"][self._language]["value"]
                else:
                    self._names[entity["id"]] = ""

    def _get_entity_json(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url)
        self._entities = response.json()

    def _get_statements(self):
        for claim in self._entities:
            property_id = self._entities[claim][self._entity]["claims"]
            for prop in property_id:
                for snak in property_id[prop]:
                    self._statements[snak["id"]] = {}
