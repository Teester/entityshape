from entityshape.api_v3.utilities import Utilities


class CompareProperties:

    def __init__(self, entity: str, entities: dict, props: list, schema: dict) -> None:
        self._utilities: Utilities = Utilities()
        self._entities: dict = entities
        self._entity: str = entity
        self._props: list = props
        self._start_shape: dict = self._utilities.get_start_shape(schema)

    def compare_properties(self) -> dict:
        """
        Compares each property to the entityschema as follows:
         - Go through the list of properties
         - If the property is in the entity, check the claim for the props
         - Add the response to the property list
         - Return the property list

        :return: A list of properties with their conformance
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

        for prop in self._props:
            child: dict = {"property": prop,
                           "necessity": self._utilities.calculate_necessity(prop, self._start_shape)}
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
        """
        Checks for the property in the claims as follows:
         - assume allowed is present
         - for each expression in the start shape, if the predicate ends with prop, get the allowed list
         - then get the cardinalities of the expression
         - if there is a correct in the allowed list, assume allowed is correct
         - match it to the cardinality if that is not correct
         - return the response

        :param claims: the claims of the entity
        :param prop: the property to be checked
        :return: the response
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
        """
        Gets a list of allowed claims as follows:
         - for each statement with the prop as a predicate process the tripleconstraint for that statement
         - If the shape has an "extra" property, make sure even incorrect items are allowed

        :param claims: the claims of the entity
        :param prop: the property to be checked
        :param expression: the expression to be checked against
        :return: the list of claims that are allowed
        """
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
        """
        Processes the cardinalities of the expression
         - count the number of "correct"s and "present"s in the allowed list
         - for each expression with the prop, get the cardinalities
         - if the shape has the "extra" property for the prop, let the cardinality be correct even if there are too many

        :param expression: The expression to be checked
        :param allowed_list: The list of entities allowed
        :param shape: the shape to be checked against
        :param prop: the property to be checked against
        :return: the conformance of the cardinality of the claim to the expression
        """
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
        """
        Get the cardinality conformance for the claim as follows:
         - get the cardinalities in the expression
         - compare the occurrences to the allowed cardinalities

        :param occurrences: the number of occurrences of the prop in the entity
        :param expression: the expression to be checked against
        :return: the conformance of the cardinality
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
        Processes triple constraint expression types in the shape as follows:
         - if the property in the statement is in the expression then allowed is present
         - if so, check if there are any NodeConstraints and check them

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

    def _process_each_of(self, expression, statement) -> str:
        # expression["type"] will be EachOf
        # there will be expression[expressions], all of which must be satisfied to pass
        allowed_list = []

        for expr in expression:
            if "type" not in expr:
                return ""
            if expr["type"]  == "TripleConstraint":
                allowed_list.append(self._process_triple_constraint_2(statement, expr, ""))
            elif expr["type"] == "NodeConstraint":
                allowed_list.append(self._utilities.process_node_constraint(statement, expr, ""))
            else:
                print(f"error: {expr['type']} not supported")
                allowed_list.append("")

        # return the lowest value
        if "" in allowed_list:
            return "error"
        if any(item in allowed_list for item in ("incorrect", "not enough correct statements")):
            return "incorrect"
        if "present" in allowed_list:
            return "present"
        if "correct" in allowed_list:
            return "correct"
        return ""

    def _process_shape(self, shape: dict, expression: dict) -> str:
        """
        Processes the type of shape and sends it on to the relevant function

        :param shape: The shape to be assessed
        :param expression: The entity the shape is assessed against
        :return: a response
        """
        if "type" not in shape:
            return ""
        print(self._start_shape)
        if "id" in self._start_shape:
            print(self._start_shape["id"])
        if shape["type"] == "Schema":
            for sub_shape in shape["shapes"]:
                if sub_shape["id"] == shape["start"]:
                    return self._process_shape(sub_shape, expression)
        if shape["type"] == "Shape":
            # If the shape is a start shape how do we process each of/one of as we'll want to ignore them to get a
            # breakdown of what's allowed
            return self._process_shape(shape["expression"], expression)
        if shape["type"] == "EachOf":
            print(shape)
            print(shape["id"])
            if shape["id"] != self._start_shape:
                return self._process_each_of(shape["expressions"], expression)
            else:
                return ""
        if shape["type"] == "OneOf":
            print("one of")
            return ""
        if shape["type"] == "TripleConstraint":
            return self._process_triple_constraint_2(expression, shape, "")
        print("none of the above")
        return ""


    def _process_triple_constraint_2(self, entity: dict, expression: dict, allowed: str) -> str:
        """
        Processes a triple constraint

        Method = Check the property in the triple constraint is in the entity
                 Get the statements with the property from the entity
                 if the triple constraint contains a node constraint - check those are correct
                 Should we check the cardinality and necessity here too?

        :param entity: a wikidata entity json without the initial QXXX
        :param expression: part of an entityschema with type TripleConstraint
        :param allowed: a text value indicating whether the statement contains statements allowed by the entityschema

        :return: allowed as it has been changed by the method
        """
        print("in process")
        print(expression)
        if "predicate" not in expression:
            return allowed
        print("predicate")
        # determine the property to be checked
        property_name: str = expression["predicate"]
        property_name = property_name.rsplit('/', 1)[1]

        if property_name not in entity["claims"]:
            return "absent"
        print("property")
        statements: dict = entity["claims"][property_name]
        if len(statements) > 0:
            allowed = "present"

        if "valueExpr" not in expression:
            return allowed
        allowed_list: list = []
        if expression["valueExpr"]["type"] == "NodeConstraint":
            for statement in statements:
                allowed_list.append(self._utilities.process_node_constraint(statement["mainsnak"],
                                                                            expression["valueExpr"],
                                                            ""))
        if "correct" in allowed_list:
            allowed = "correct"
        utilities: Utilities = Utilities()
        necessity: str = utilities.required_or_absent(expression)
        occurrences: int = allowed_list.count("correct") + allowed_list.count("present")
        cardinalities: str = self._get_cardinalities(occurrences, expression)
        if cardinalities != "correct":
            allowed = cardinalities

        child: dict = {"name": property_name,
                       "necessity": necessity,
                       "response": allowed}
        print(f"response = {child}")
        return allowed
