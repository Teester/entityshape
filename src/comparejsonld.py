"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
import re
from typing import Any

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
        response: Response = requests.get(url=f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json",
                                          headers={'User-Agent': 'Entityshape API by User:Teester'})
        self._entities = response.json()

    def _get_props(self, claims: dict) -> None:
        """
        Gets a list of properties included in the entity and assigns them to self._props

        :param claims: The claims in the entity
        """
        props: set = set()

        # Get properties from the entity
        for claim in claims:
            props.add(claim)

        # Get properties from the start shape
        # TODO: there must be a more elegant way to do this than just grabbing any Pxx string from the json
        properties: list = re.findall(r'P\d+', json.dumps(self._get_start_shape()))
        for prop in properties:
            props.add(prop)

        self._props: list = list(props)

    def _get_property_names(self, language: str) -> None:
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :param str language: The language in which to get the property names
        :return: Nothing
        """
        self._names: dict = {}
        # Max number of properties to query in a wikidata api query is 50, so split the list of properties up into
        # chunks of no more than 50 each
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        # process each chunk separately
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            response: Response = requests.get(url='https://www.wikidata.org/w/api.php',
                                              params={'action': 'wbgetentities',
                                                      'ids': required_properties,
                                                      'props': 'labels',
                                                      'languages': language,
                                                      'format': 'json'},
                                              headers={'User-Agent': 'Entityshape API by User:Teester'})
            json_text: dict = response.json()

            for item in element:
                item_id: dict = json_text["entities"][item]
                try:
                    self._names[item_id['id']] = item_id["labels"][language]["value"]
                except KeyError:
                    self._names[item_id['id']] = ""

    def _get_start_shape(self) -> dict[Any, Any] | None | Any:
        """
        Gets the shape associated with the start parameter of the entityschema

        :return: the start shape
        """
        if "start" not in self._shape:
            return {}

        if "shapes" not in self._shape:
            return {}

        for shape in self._shape['shapes']:
            if shape["id"] == self._shape['start']:
                return shape


class CompareProperties:

    def __init__(self, entity: str, entities: dict, props: list, names: dict, start_shape: dict) -> None:
        self._entities: dict = entities
        self._names: dict = names
        self._entity: str = entity
        self._props: list = props
        self._start_shape: dict = start_shape

    def compare_properties(self) -> dict:
        """
        Compares the properties in the start shape with the properties in the entity
        :return: a dict containing the responses for each property mentioned in the start shape
        """
        # if there's no start shape, return an empty dict
        if self._start_shape is None:
            return {}
        if "entities" not in self._entities:
            return {}
        if self._entity not in self._entities["entities"]:
            return {}
        if "claims" not in self._entities["entities"][self._entity]:
            return {}

        claims: dict = self._entities["entities"][self._entity]["claims"]
        properties: dict = {}
        utilities: Utilities = Utilities()

        for prop in self._props:
            name: str = self._names[prop]
            necessity: str = utilities.calculate_necessity(prop, self._start_shape)
            response: str = "missing"
            if prop in claims:
                response = self.check_claims_for_props(claims, prop)

            child: dict = {"name": name,
                           "necessity": necessity,
                           "response": response}
            properties[prop] = child
        return properties

    def check_claims_for_props(self, claims: dict, prop: str) -> str:
        """"

        :return:
        """
        if "expression" not in self._start_shape:
            return "present"
        if "expressions" not in self._start_shape["expression"]:
            return "present"

        cardinality: str = "correct"
        allowed: str = "present"
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
        if prop not in claims:
            return []

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

        occurrences: int = allowed_list.count(["correct", "present"])
        cardinality: str = "correct"
        for expression in shape["expression"]["expressions"]:
            if "predicate" in expression and expression["predicate"].endswith(prop):
                cardinality = self._get_cardinalities(occurrences, expression)
                predicate: str = f'http://www.wikidata.org/prop/direct/{prop}'
                if "extra" in shape and predicate in shape["extra"] and cardinality == "too many statements":
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
            cardinality = "too many statements"
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
        if "property" not in statement:
            return allowed
        if "predicate" not in expression:
            return allowed

        statement_property: str = statement["property"]
        if expression["predicate"].endswith(statement_property):
            allowed = "present"
            try:
                if expression["valueExpr"]["type"] == "NodeConstraint":
                    allowed = Utilities.process_node_constraint(statement,
                                                                expression["valueExpr"],
                                                                allowed)
            except (KeyError, TypeError):
                pass
        return allowed

    def _process_each_of(self):
        return

    def _process_one_of(self):
        return


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
        if "entities" not in self._entities:
            return {}
        if self._entity not in self._entities["entities"]:
            return {}
        if "claims" not in self._entities["entities"][self._entity]:
            return {}

        statements: dict = {}
        utilities: Utilities = Utilities()

        claims: dict = self._entities["entities"][self._entity]['claims']
        for claim in claims:
            for statement in claims[claim]:
                child: dict = {"property": claim}
                necessity = utilities.calculate_necessity(statement["mainsnak"]["property"], self.start_shape)
                if necessity != "absent":
                    child["necessity"] = necessity
                child["response"] = self._process_shape(statement["mainsnak"])
                statements[statement["id"]] = child
        return statements

    def _process_shape(self, statement: dict) -> str:
        """
        Processes a statement against a shape

        :param statement: The entity's statement to be assessed
        :return: child
        """
        allowed: str = "not in schema"

        if "expression" not in self.start_shape:
            return allowed
        if "expressions" not in self.start_shape["expression"]:
            return allowed

        expressions: dict = self.start_shape["expression"]["expressions"]
        for expression in expressions:
            allowed = self.process_expressions(expression, statement)
        return allowed

    def process_expressions(self, expression: dict, statement: dict) -> str:
        allowed: str = ""
        if "type" not in expression:
            return allowed
        if "predicate" not in expression:
            return allowed
        if "property" not in statement:
            return allowed

        if expression["type"] == "TripleConstraint" and expression["predicate"].endswith(statement["property"]):
            allowed = self._process_triple_constraint(statement, expression)
            if "extra" in self.start_shape:
                for extra in self.start_shape["extra"]:
                    if extra.endswith(statement["property"]) and allowed == "incorrect":
                        allowed = "allowed"
        return allowed

    @staticmethod
    def _process_triple_constraint(statement: dict, expression: dict) -> str:
        """
        Processes triple constraint expression types in the shape

        :param statement: The entity's statement to be assessed
        :param expression: The expression from the shape to be assessed against
        :return: allowed
        """
        allowed: str = ""
        if "property" not in statement:
            return allowed
        if "predicate" not in expression:
            return allowed

        statement_property: str = statement["property"]
        if expression["predicate"].endswith(statement_property):
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
        if "snaktype" in statement:
            if statement["snaktype"] == "value" and statement["datavalue"]["type"] == "wikibase-entityid":
                obj = f'http://www.wikidata.org/entity/{statement["datavalue"]["value"]["id"]}'
                if "values" in expression:
                    if obj in expression["values"]:
                        allowed = "correct"
                    else:
                        allowed = "incorrect"
        return allowed
