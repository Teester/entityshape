from typing import Tuple, Any

from utilities import Utilities


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
        if "type" not in expression:
            return allowed
        if "predicate" not in expression:
            return allowed
        if "property" not in statement:
            return allowed

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
        if "property" not in statement:
            return allowed
        if "predicate" not in expression:
            return allowed

        if expression["predicate"].endswith(statement["property"]):
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
