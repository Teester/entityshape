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
        props: CompareProperties = CompareProperties(self._entities, self._props, self._names, self._shape)
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

    def __init__(self, entities: dict, props: list, names: dict, shapes: dict) -> None:
        self._entities: dict = entities
        self._names: dict = names
        self._props: list = props
        self._shapes: dict = shapes

        response = SetupResponse(self._entities, self._shapes)
        self.responses: dict = response.get_response()
        self._start_shape: dict = response.get_start_shape()
        self._entity: str = response.get_entity()

    def compare_properties(self) -> dict:
        """

        :return:
        """
        claims: dict = self._entities["entities"][self._entity]["claims"]
        properties: dict = {}
        if self._start_shape is None:
            return properties
        utilities: Utilities = Utilities()

        self.check_props_for_claims()

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
            elif response != "present":
                child["response"] = response
            properties[prop] = child
        print(json.dumps(properties, sort_keys=True, indent=2))
        return properties

    def check_props_for_claims(self):
        self.process_expression(self._start_shape)
        print(json.dumps(self.responses, sort_keys=True, indent=2))
        self._process_responses()

    def process_expression(self, shape: dict):
        expressions = self.get_list_of_expressions(shape)

        for expression in expressions:
            claims: dict = self._entities["entities"][self._entity]["claims"]
            for claim in claims:
                for snak in claims[claim]:
                    if expression["type"] == "TripleConstraint":
                        if expression["predicate"] in [f"{Constants.Prefixes.wdt}{claim}",
                                                       f"{Constants.Prefixes.p}{claim}"]:
                            self.process_triple_constraint(expression, snak)
                    elif expression["type"] == "EachOf":
                        self.process_each_of(expression)
                    else:
                        self.responses[expression["predicate"]][snak["id"]] = Constants.Responses.correct

    @staticmethod
    def get_list_of_expressions(shape):
        expressions = []
        if "expressions" in shape:
            for expression in shape["expressions"]:
                expressions.append(expression)
        elif "expression" in shape:
            expressions.append(shape["expression"])
        else:
            expressions.append(shape)
        return expressions

    def process_each_of(self, shape):
        if "expressions" in shape:
            for expression in shape["expressions"]:
                self.process_expression(expression)
        else:
            self.process_expression(shape["expression"])

    def process_triple_constraint(self, expression, snak):
        property_id = snak["mainsnak"]["property"]
        predicate = [f"{Constants.Prefixes.wdt}{property_id}", f"{Constants.Prefixes.p}{property_id}"]
        if snak["mainsnak"]["datatype"] in ["wikibase-item", "wikibase-entity-id]"]:
            value = snak["mainsnak"]["datavalue"]["value"]["id"]
            value_id = f"{Constants.Prefixes.wd}{value}"
            if expression["predicate"] in predicate:
                response = Constants.Responses.correct
                if "valueExpr" not in expression:
                    # any value is valid
                    response = Constants.Responses.correct
                elif "type" not in expression["valueExpr"]:
                    # must conform to a sub-shape
                    for shape in self._shapes["shapes"]:
                        if shape["id"] == expression["valueExpr"]:
                            self.process_expression(shape)
                elif expression["valueExpr"]["type"] == "NodeConstraint":
                    # must conform to a node constraint
                    response = self.process_node_constraint(value_id, expression["valueExpr"])
                else:
                    response = Constants.Responses.missing
                    print("not a node constraint or value")
                self.responses[expression["predicate"]][snak["id"]] = response
        elif snak["mainsnak"]["datatype"] in ["time", "quantity", "commonsMedia", "globe-coordinate", "external-id"]:
            self.responses[expression["predicate"]][snak["id"]] = Constants.Responses.correct
        else:
            print(f'type = {snak["mainsnak"]["datatype"]}')

    @staticmethod
    def process_node_constraint(value, node):
        if value in node["values"]:
            return Constants.Responses.correct
        return Constants.Responses.incorrect

    def _process_responses(self):
        responses = {}
        for expression in self._start_shape["expression"]["expressions"]:
            cardinality = self.process_cardinality(expression)
            if "extra" in self._start_shape:
                if expression["predicate"] in self._start_shape["extra"]:
                    cardinality = Constants.Responses.correct
            necessity = self.process_necessity(expression)
            print(f"{expression['predicate']} - {cardinality} - {necessity}")
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
        print(json.dumps(responses, sort_keys=True, indent=2))


    def process_cardinality(self, expression: dict) -> str:
        cardinality_result = Constants.Responses.correct
        cardinality = len(self.responses[expression["predicate"]])
        if self.responses[expression["predicate"]]["in_schema"]:
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

    @staticmethod
    def process_necessity(expression):
        necessity_result = Constants.Necessities.required
        if "min" in expression and expression["min"] == 0:
            necessity_result = Constants.Necessities.optional
            if "max" in expression and expression["max"] == 0:
                necessity_result = Constants.Necessities.not_allowed
        return necessity_result

    def check_claims_for_props(self, claims: dict, prop: str) -> str:
        """"

        :return:
        """
        cardinality: str = "correct"
        allowed: str = "present"
        if "expression" not in self._start_shape:
            return "present"
        if "expressions" not in self._start_shape["expression"]:
            return "present"
        for expression in self._start_shape["expression"]["expressions"]:
            if "predicate" in expression and expression["predicate"].endswith(prop):
                allowed_list = self._get_allowed_list(claims, prop, expression)
                cardinality2 = self._process_cardinalities(expression, allowed_list, self._start_shape, prop)
                if cardinality2 not in ["", "correct"]:
                    cardinality = cardinality2
                if "correct" in allowed_list:
                    allowed = "correct"
        if cardinality == "correct":
            response: str = allowed
        else:
            response: str = cardinality
        return response

    def _get_allowed_list(self, claims: dict, prop: str, expression: dict) -> list:
        allowed_list: list = []
        for statement in claims[prop]:
            is_it_allowed: str = ""
            if statement["mainsnak"]["property"] == prop:
                is_it_allowed = self._process_triple_constraint(statement["mainsnak"],
                                                                expression,
                                                                "")
            if "extra" in self._start_shape:
                for extra in self._start_shape["extra"]:
                    if extra.endswith(prop) and is_it_allowed == "incorrect":
                        is_it_allowed = "allowed"
            allowed_list.append(is_it_allowed)
        return allowed_list

    def _process_cardinalities(self, expression: dict, allowed_list: list, shape: dict, prop: str) -> str:
        if "predicate" not in expression:
            return ""
        if not expression["predicate"].endswith(prop):
            return ""
        occurrences: int = allowed_list.count("correct")
        occurrences += allowed_list.count("present")
        cardinality: str = "correct"
        for expression in shape["expression"]["expressions"]:
            if "predicate" in expression and expression["predicate"].endswith(prop):
                cardinality = self._get_cardinalities(occurrences, expression)
                predicate: str = f'{Constants.Prefixes.wdt}{prop}'
                if "extra" in shape and predicate in shape["extra"] and cardinality == Constants.Responses.too_many:
                    cardinality = "correct"
        return cardinality

    @staticmethod
    def _get_cardinalities(occurrences: int, expression: dict) -> str:
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
            cardinality = Constants.Responses.too_many
        if max_cardinality and not min_cardinality:
            cardinality = "not enough correct statements"
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
            obj = f'{Constants.Prefixes.wd}{statement["datavalue"]["value"]["id"]}'
            if "values" in expression:
                if obj in expression["values"]:
                    allowed = "correct"
                else:
                    allowed = "incorrect"
        return allowed


class Constants:
    class Prefixes:
        wdt: str = "http://www.wikidata.org/prop/direct/"
        wd:  str = "http://www.wikidata.org/entity/"
        p:   str = "http://www.wikidata.org/prop/"

    class Responses:
        correct = "correct"
        incorrect = "incorrect"
        missing = "missing"
        too_many = "too many statements"
        not_enough = "not enough statements"

    class Necessities:
        required = "required"
        optional = "optional"
        not_allowed = "not allowed"
        absent = "absent"


class SetupResponse:
    def __init__ (self, entities, shapes):
        self._entities = entities
        self._shapes = shapes
        self._responses = {}
        self._start_shape = self._get_start_shape()
        self._entity = list(self._entities["entities"].keys())[0]

        self._add_claims_to_response()

    def get_response(self) -> dict:
        return self._responses

    def get_start_shape(self) -> dict:
        return self._start_shape

    def get_entity(self):
        return self._entity

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

    def _get_start_shape(self) -> dict:
        if "start" not in self._shapes:
            return {}
        if "shapes" not in self._shapes:
            return {}

        start: dict = self._shapes['start']
        for shape in self._shapes['shapes']:
            if shape["id"] == start:
                return shape
