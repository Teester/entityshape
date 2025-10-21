from api_v2.utilities import Utilities


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
        if "entities" not in self._entities:
            return {}
        if self._entity not in self._entities["entities"]:
            return {}
        if "claims" not in self._entities["entities"][self._entity]:
            return {}

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
            elif response != "present":
                child["response"] = response
            properties[prop] = child
        return properties

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
        occurrences: int = allowed_list.count("correct")
        occurrences += allowed_list.count("present")
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

        if expression["predicate"].endswith(statement["property"]):
            allowed = "present"
            try:
                if expression["valueExpr"]["type"] == "NodeConstraint":
                    allowed = Utilities.process_node_constraint(statement,
                                                                expression["valueExpr"],
                                                                allowed)
            except (KeyError, TypeError):
                pass
        return allowed
