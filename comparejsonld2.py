"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
from operator import countOf

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

        self.response: SetupResponse = SetupResponse(entity, shape, language)

        self._entity: str = self.response.get_entity()
        self._entities: dict = self.response.get_entities()
        self._names: dict = self.response.get_names()
        self._responses: dict = self.response.get_response()
        self._shapes: dict = self.response.get_shapes()
        self._start_shape: dict = self.response.get_start_shape()
        self._statements: dict = self.response.get_statements()

        self._check_props_for_claims()

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        return self._properties

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        return self._statements

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison

        :return: json for general properties of the comparison
        """
        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            if "shapes" in self._shape:
                data_string: str = self._shape["shapes"]
                if item in data_string and item in self._entities["entities"][self._entity]:
                    general[item] = "incorrect"
                    expected: list = self._shape["shapes"]
                    actual: str = self._entities["entities"][self._entity][item]
                    if actual in expected:
                        general[item] = "correct"
        return general

    def _check_props_for_claims(self) -> None:
        self._process_expression(self._start_shape)
        self._process_responses()

    def _process_expression(self, shape: dict) -> None:
        expressions = self._get_list_of_expressions(shape)

        for expression in expressions:
            claims: dict = self._entities["entities"][self._entity]["claims"]
            for claim in claims:
                for snak in claims[claim]:
                    self._process_claims(expression, claim, snak)

    def _process_claims(self, expression: dict, claim: str, snak: dict) -> None:
        if expression["type"] == "TripleConstraint":
            if expression["predicate"] in [f"{Constants.Prefixes.wdt}{claim}",
                                           f"{Constants.Prefixes.p}{claim}"]:
                self._process_triple_constraint(expression, snak)
        elif expression["type"] == "EachOf":
            self._process_each_of(expression)
        else:
            self._update_results(expression["predicate"], snak["id"], Constants.Responses.correct)

    @staticmethod
    def _get_list_of_expressions(shape: dict) -> list:
        expressions: list = []
        if "expressions" in shape:
            for expression in shape["expressions"]:
                expressions.append(expression)
        elif "expression" in shape:
            expressions.append(shape["expression"])
        else:
            expressions.append(shape)
        return expressions

    def _process_each_of(self, shape: dict) -> None:
        if "expressions" in shape:
            for expression in shape["expressions"]:
                self._process_expression(expression)
        else:
            self._process_expression(shape["expression"])

    def _process_triple_constraint(self, expression: dict, snak: dict) -> None:
        property_id: str = snak["mainsnak"]["property"]
        if snak["mainsnak"]["datatype"] in ["wikibase-item", "wikibase-entity-id]"]:
            if snak["mainsnak"]["datatype"] == "wikibase-item":
                predicate: str = f"{Constants.Prefixes.wdt}{property_id}"
            else:
                predicate: str = f"{Constants.Prefixes.p}{property_id}"
            value: str = snak["mainsnak"]["datavalue"]["value"]["id"]
            value_id: str = f"{Constants.Prefixes.wd}{value}"
            response: str = self._process_wikidata_item(expression, predicate, value_id)
            self._update_results(expression["predicate"], snak["id"], response)
        elif snak["mainsnak"]["datatype"] in ["time", "quantity", "commonsMedia", "globe-coordinate", "external-id"]:
            self._update_results(expression["predicate"], snak["id"], Constants.Responses.present)
        else:
            print(f'type = {snak["mainsnak"]["datatype"]}')

    def _update_results(self, predicate: dict, snak: dict, response: str) -> None:
        self._responses[predicate][snak] = response
        self._statements[snak]["response"] = response

    def _process_wikidata_item(self, expression: dict, predicate: str, value_id: str) -> str:
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
    def _process_node_constraint(value: str, node: dict) -> str:
        if value in node["values"]:
            return Constants.Responses.correct
        return Constants.Responses.incorrect

    def _process_responses(self) -> None:
        print(self._responses)
        responses: dict = {}
        for expression in self._start_shape["expression"]["expressions"]:
            response: str = Constants.Responses.missing
            print(self._responses[expression["predicate"]])
            true = countOf(self._responses[expression["predicate"]].values(), Constants.Responses.correct)
            print(true)
            if Constants.Responses.correct in self._responses[expression["predicate"]].values():
                response = Constants.Responses.correct
            elif Constants.Responses.present in self._responses[expression["predicate"]].values():
                response = Constants.Responses.present
            cardinality: str = self._process_cardinality(expression)
            necessity: str = self.get_necessity(expression)
            if "extra" in self._start_shape:
                if expression["predicate"] in self._start_shape["extra"]:
                    cardinality = Constants.Responses.correct
            predicate: str = expression["predicate"].removeprefix(Constants.Prefixes.wdt)
            predicate = predicate.removeprefix(Constants.Prefixes.p)
            if predicate not in responses:
                responses[predicate] = {}
            responses[predicate]["necessity"] = necessity
            if cardinality == Constants.Responses.correct:
                responses[predicate]["response"] = response
            else:
                responses[predicate]["response"] = cardinality
        for claim in self._entities["entities"][self._entity]["claims"]:
            if claim not in responses:
                responses[claim] = {}
                responses[claim]["necessity"] = Constants.Necessities.absent
        for response in responses:
            responses[response]["name"] = self._names[response]
        self._properties = responses

    def _process_cardinality(self, expression: dict) -> str:
        cardinality_result: str = Constants.Responses.correct
        cardinality: int = len(self._responses[expression["predicate"]])
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

    @staticmethod
    def get_necessity(expression: dict) -> str:
        necessity_result: str = Constants.Necessities.required
        if "min" in expression and expression["min"] == 0:
            necessity_result = Constants.Necessities.optional
            if "max" in expression and expression["max"] == 0:
                necessity_result = Constants.Necessities.not_allowed
        return necessity_result


class Constants:
    class Prefixes:
        wdt: str = "http://www.wikidata.org/prop/direct/"
        wd: str = "http://www.wikidata.org/entity/"
        p: str = "http://www.wikidata.org/prop/"

    class Responses:
        absent: str = "absent"
        allowed: str = "allowed"
        correct: str = "correct"
        incorrect: str = "incorrect"
        missing: str = "missing"
        not_enough: str = "not enough statements"
        not_in_schema: str = "not in schema"
        present: str = "present"
        too_many: str = "too many statements"

    class Necessities:
        required: str = "required"
        optional: str = "optional"
        not_allowed: str = "not allowed"
        absent: str = "absent"


class SetupResponse:
    """
    This class downloads the entity being checked and sets up the structures needed for processing shapes
    """
    def __init__(self, entity: str, shapes: dict, language: str) -> None:
        self._entity: str = entity
        self._get_entity_json()
        self._shapes: dict = shapes
        self._language: str = language
        self._responses: dict = {}
        self._start_shape: dict = self._get_start_shape()
        self._names: dict = {}
        self._statements: dict = {}
        self._props: list = []
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

    def get_statements(self) -> dict:
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
        prop: str = property_id.removeprefix(Constants.Prefixes.wdt)
        prop = prop.removeprefix(Constants.Prefixes.p)
        self._props.append(prop)

    def _get_start_shape(self) -> dict:
        if "start" not in self._shapes:
            return {}
        if "shapes" not in self._shapes:
            return {}

        start: dict = self._shapes['start']
        for shape in self._shapes['shapes']:
            if shape["id"] == start:
                return shape

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
                entity: dict = json_text["entities"][item]
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

    def _get_statements(self) -> None:
        for claim in self._entities:
            property_id: dict = self._entities[claim][self._entity]["claims"]
            for prop in property_id:
                for snak in property_id[prop]:
                    self._statements[snak["id"]] = {}
