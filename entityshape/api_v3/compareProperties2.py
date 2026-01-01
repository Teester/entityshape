class CompareProperties2:
    def __init__(self, entity: str, entities: dict, props: list, schema: dict, names: dict) -> None:
        self._entity: str = entity
        self._entities: dict = entities
        self._props: list = props
        self._schema: dict = schema
        self._names: dict = names
        self._start_shape: str = self._get_start_shape()

    def compare_properties(self) -> dict:
        if self._start_shape == "":
            return {}
        if "entities" not in self._entities:
            return {}
        if self._entity not in self._entities["entities"]:
            return {}

        shape: dict = self._get_shape(self._start_shape)
        entity: dict = self._entities["entities"][self._entity]
        response: dict = self._process_shape(shape, entity)
        return response

    def _process_shape(self, shape: dict, entity: dict) -> dict:
        # process the shape - is it a schema, a shape, a triple constraint, a node constraint etc
        if "type" not in shape:
            return {}
        if shape["type"] == "Schema":
            return self._process_schema(shape, entity)
        if shape["type"] == "Shape":
            return self._process_shape_in_shape(shape, entity)
        if shape["type"] == "EachOf":
            return self._process_each_of(shape, entity)
        if shape["type"] == "OneOf":
            return self._process_one_of()
        if shape["type"] == "TripleConstraint":
            return self._process_triple_constraint(shape, entity)
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

    def _process_shape_in_shape(self, shape, entity) -> dict:
        if "expression" in shape:
            return self._process_shape(shape["expression"], entity)
        return {}

    def _process_each_of(self, shape, entity) -> dict:
        if shape["id"] == self._start_shape:
            return self._process_each_of_for_start_shape(shape["expressions"], entity)
        else:
            return self._process_each_of_for_non_start_shape(shape["expressions"], entity)

    def _process_one_of(self) -> dict:
        return {}

    def _process_triple_constraint(self, shape, entity) -> dict:
        property_name: str = self._get_property_name(shape["predicate"])
        return {"name": property_name,
                "necessity": self._get_necessity(shape),
                "response": self._process_triple_constraint_2(shape, entity, "")}

    def _get_start_shape(self) -> str:
        """
        gets the start shape name from a schema

        :return: a string of the start shape name
        """
        if "start" in self._schema:
            return self._schema["start"]
        return ""

    def _get_shape(self, shape_id) -> dict:
        """
        Gets a specified shape from the schema

        :param shape_id: the name of the shape required
        :return: the shape required
        """
        if "shapes" not in self._schema:
            return {}

        for shape in self._schema["shapes"]:
            if shape["id"] == shape_id:
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

    @staticmethod
    def _get_necessity(expression: dict) -> str:
        necessity: str = "optional"
        if ("min" in expression and expression["min"] > 0) or ("min" not in expression and "max" not in expression):
            necessity = "required"
        if "min" in expression and "max" in expression and expression["min"] == 0 and expression["max"] == 0:
            necessity = "absent"
        return necessity