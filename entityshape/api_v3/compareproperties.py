from entityshape.api_v3.utilities import Utilities


class CompareProperties:

    def __init__(self, entity: str, entities: dict, props: list, schema: dict, names: dict) -> None:
        self._utilities: Utilities = Utilities()
        self._entities: dict = entities
        self._entity: str = entity
        self._schema: dict = schema
        self._props: list = props
        self._names: dict = names
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
        if self._start_shape is None:
            return {}
        if "id" not in self._start_shape:
            return {}
        claims: dict = self._entities["entities"][self._entity]["claims"]
        my_response: dict = {}
        for entity in self._entities["entities"]:
            my_response = self._process_shape(self._schema, self._entities["entities"][entity], self._start_shape["id"] )
        response: dict = {}
        if "name" not in my_response:
            response = my_response
        for claim in claims:
            if "name" in my_response:
                response[claim] = my_response
            if claim not in response:
                response[claim] = {"name": self._names[claim], "necessity": "absent"}
        return response

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
        print(expression)
        print(occurrences)
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

    def _process_each_of_for_start_shape(self, shape, entity) -> dict:
        """
        Processes an EachOf in the start shape.  This ignores any each of in the start shape to
        allow a breakdown of the properties.

        Assumptions of this method:
         - shape["type"] will be EachOf
         - there will be shape[expressions] present

        :param shape: a JSONLD representation of a shape
        :param entity: a JSON representation of the entity
        :return: a dict representing a response
        """
        print("in process each of for start shape")
        response = {}
        for expression in shape:
            allowed = ""
            if expression["type"]  == "TripleConstraint":
                predicate = self._get_property_name(expression["predicate"])
                allowed = self._process_triple_constraint_2(expression, entity, allowed)
                if predicate in self._names:
                    name = self._names[predicate]
                else:
                    name = predicate
                expression_response = {"name": name,
                                       "necessity": self._utilities.calculate_necessity(predicate, self._start_shape),
                                       "response": allowed}
                response[predicate] = expression_response
            else:
                print(f"error: {expression['type']} not supported")
            print(f"allowed = {allowed}")
        print(f"response = {response}")
        return response

    def _process_each_of_for_non_start_shape(self, shape, entity) -> str:
        """
        Process an EachOf expression type when the shape being assessed is not the start shape

        Assumptions of this method:
         - shape["type"] will be EachOf
         - there will be shape[expressions], all of which must be satisfied to pass

        :param shape: the shape to be assessed against
        :param entity: the entity to assess
        :return: a string indicating whether the entity conforms to the shape
        """
        allowed_list = []
        for expression in shape:
            if "type" not in expression:
                return ""
            if expression["type"]  == "TripleConstraint":
                allowed_list.append(self._process_triple_constraint_2(expression, entity, ""))
            elif expression["type"] == "NodeConstraint":
                allowed_list.append(self._utilities.process_node_constraint(entity, expression, ""))
            else:
                print(f"error: {expression['type']} not supported")
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

    def _process_shape(self, shape: dict, entity: dict, current_shape: str="") -> dict:
        """
        Processes the type of shape and sends it on to the relevant function

        :param shape: The shape to be assessed
        :param entity: The entity the shape is assessed against
        :return: a response
        """
        if "type" not in shape:
            return {}
        print("in process")
        if shape["type"] == "Schema":
            print(f"schema = {shape}")
            return self._process_schema(shape, entity)
        if shape["type"] == "Shape":
            print(f"shape = {shape}")
            result = self._process_shape_2(shape, entity)
            print(f"shape result = {result}")
            return result
        if shape["type"] == "EachOf":

            print(f"eachof = {shape}")
            return self._process_each_of(shape, entity, current_shape)
        if shape["type"] == "OneOf":
            return self._process_one_of()
        if shape["type"] == "TripleConstraint":

            print(f"triple = {shape}")
            result = self._process_triple_constraint(shape, entity)
            print(f"triple result = {result}")
            return result
        print("none of the above")
        return {}

    def _process_schema(self, schema, entity) -> dict:
        """
        Processes a schema type

        :param schema: the schema to be processed
        :param entity: the entity to be processed
        :return: a result
        """
        for shape in schema["shapes"]:
            if shape["id"] == schema["start"]:
                return self._process_shape(shape, entity)
        return {}

    def _process_shape_2(self, shape, entity) -> dict:
        if "expression" in shape:
            print(f"processing {shape['id']}, expression = {shape['expression']}")
            return self._process_shape(shape["expression"], entity, current_shape=shape["id"])
        else:
            return {}

    def _process_each_of(self, shape, entity, current_shape) -> dict:
        if current_shape is self._start_shape["id"]:
            return self._process_each_of_for_start_shape(shape["expressions"], entity)
        else:
            return self._process_each_of_for_non_start_shape(shape["expressions"], entity)

    def _process_one_of(self) -> dict:
        return {}

    def _process_triple_constraint(self, shape, entity) -> dict:
        property_name: str = self._get_property_name(shape["predicate"])
        return {"name": property_name,
                "necessity": self._utilities.required_or_absent(shape),
                "response": self._process_triple_constraint_2(shape, entity,"")}

    def _process_triple_constraint_2(self, shape: dict, entity: dict, allowed: str) -> str:
        """
        Processes a triple constraint

        Method = Check the property in the triple constraint is in the entity
                 Get the statements with the property from the entity
                 if the triple constraint contains a node constraint - check those are correct
                 Should we check the cardinality and necessity here too?

        :param entity: a wikidata entity json without the initial QXXX
        :param shape: part of an entityschema with type TripleConstraint
        :param allowed: a text value indicating whether the statement contains statements allowed by the entityschema

        :return: allowed as it has been changed by the method
        """
        if "predicate" not in shape:
            return allowed
        # determine the property to be checked
        property_name: str = self._get_property_name(shape["predicate"])
        if property_name not in entity["claims"]:
            return "missing"
        statements: dict = entity["claims"][property_name]
        if len(statements) > 0:
            allowed = "present"

        if "valueExpr" not in shape:
            occurrences: int = len(statements)
            cardinalities: str = self._get_cardinalities(occurrences, shape)
            if cardinalities != "correct":
                allowed = cardinalities
            return allowed

        allowed_list: list = []
        if isinstance(shape["valueExpr"], str):
            # this is another shape
            # we need to get the result back for that shape and process it
            # if the shape fails then the triple constraint fails
            new_shape: dict = self._get_shape(shape["valueExpr"])
            allowed_list.append(self._process_shape(new_shape, entity, shape["valueExpr"]))
        elif shape["valueExpr"]["type"] == "NodeConstraint":
            for statement in statements:
                allowed_list.append(self._utilities.process_node_constraint(statement["mainsnak"],
                                                                            shape["valueExpr"],
                                                                            allowed))
        if "correct" in allowed_list:
            allowed = "correct"
        necessity: str = self._utilities.required_or_absent(shape)
        occurrences: int = allowed_list.count("correct") + allowed_list.count("present")
        cardinalities: str = self._get_cardinalities(occurrences, shape)
        if cardinalities != "correct":
            allowed = cardinalities

        child: dict = {"name": property_name,
                       "necessity": necessity,
                       "response": allowed}
        return allowed

    def _get_shape(self, required_shape: str) -> dict:
        """
        Gets a specified shape from the schema

        :param required_shape: the name of the shape required
        :return: the shape required
        """
        if "shapes" not in self._schema:
            return {}

        for shape in self._schema["shapes"]:
            if shape["id"] == required_shape:
                return shape
        return {}

    @staticmethod
    def _get_property_name(predicate) -> str:
        """
        Gets a property name from a predicate.
        e.g. http://www.wikidata.org/prop/P31 -> P31

        :param predicate: The predicate to assess
        :return: the property as a string
        """
        return predicate.rsplit('/', 1)[1]
