class CompareProperties2:
    def __init__(self, entity: str, entities: dict, props: list, schema: dict, names: dict) -> None:
        self._entity = entity
        self._entities = entities
        self._props = props
        self._schema = schema
        self._names = names
        self._start_shape = self._get_start_shape()

    def compare_properties(self) -> dict:
        return {}

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