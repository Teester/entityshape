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
        if "snaktype" not in statement:
            return allowed
        if "datavalue" not in statement:
            return allowed
        if "type" not in statement["datavalue"]:
            return allowed

        if statement["snaktype"] == "value" and \
                statement["datavalue"]["type"] == "wikibase-entityid":
            obj = f'http://www.wikidata.org/entity/{statement["datavalue"]["value"]["id"]}'
            if "values" in expression:
                if obj in expression["values"]:
                    allowed = "correct"
                else:
                    allowed = "incorrect"
        return allowed
