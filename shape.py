import re
import requests
from typing import Optional, Match, Union, Pattern, Any


class Shape:
    """
    Produces a shape in the form of a json for a wikidata entityschema (e.g. E10)

    :param schema: The identifier of the entityschema to be processed
    :param language: The language to get the schema name in

    :return name: the name of the entityschema
    :return shape: a json representation of the entityschema
    """
    # TODO: Process groups in shapes
    # TODO: Process OR and NOT in shapes
    def __init__(self, schema: str, language: str):
        self.name: str = ""
        self.schema_shape: dict = {}

        self._shapes: dict = {}
        self._schema_shapes: dict = {}
        self._language: str = language

        self._get_schema_json(schema)
        self._strip_schema_comments()
        self._get_schema_name()
        if self._schema_text != "":
            self._get_default_shape()
            self._translate_schema()

    def _translate_schema(self):
        """
        Converts the entityschema to a json representation
        """
        for shape in self._shapes:
            self._convert_shape(shape)
        schema_json: dict = self._schema_shapes[self._default_shape_name]
        for key in schema_json:
            if "shape" in schema_json[key]:
                schema_json[key] = self._translate_sub_shape(schema_json[key])
            if "required" in schema_json[key] and\
                    "required" in schema_json[key]["required"]:
                schema_json[key]["required"] = schema_json[key]["required"]["required"]
        self.schema_shape = schema_json

    def _convert_shape(self, shape: str):
        """
        Converts a shape into its json representation

        :param shape: the name of the shape to be converted
        """
        new_shape: str = self._shapes[shape].replace("\n", "")
        shape_array: list = new_shape[new_shape.find("{")+1:new_shape.rfind("}")].split(";")
        shape_json: dict = self._get_shape_properties(re.search(r"<(.*?){", new_shape).group(1))

        for line in shape_array:
            if re.match(r".+:P\d", line):
                selected_property: str = re.search(r"P\d+", line).group(0)
                child: dict = {}
                if selected_property in shape_json:
                    child = shape_json[selected_property]
                shape_json[selected_property] = self._assess_property(line, child)
        self._schema_shapes[shape] = shape_json

    def _assess_property(self, line: str, child: dict):
        """
        converts a line og a schema to a json representation of itself

        :param line: The line to be converted
        :param child: the existing json shape
        :return: a json object to be added to the shape
        """
        snak: str = self._get_snak_type(line)
        if "@<" in line:
            sub_shape_name: str = re.search(r"<.*>", line).group(0)
            child["shape"] = sub_shape_name[1:-1]
        if re.search(r"\[.*]", line):
            required_parameters_string: str = re.search(r"\[.*]", line).group(0)
            required_parameters_string = re.sub(r"wd:", "", required_parameters_string)
            if "^" in line:
                child["not_allowed"] = required_parameters_string[1:-1].split()
            else:
                child["allowed"] = required_parameters_string[1:-1].split()
        cardinality: dict = self._get_cardinality(line)
        necessity: str = "optional"
        if cardinality:
            child["cardinality"] = cardinality
            if "min" in cardinality:
                necessity = "required"
        child["necessity"] = necessity
        child["status"] = snak
        return child

    @staticmethod
    def _get_shape_properties(first_line: str):
        """
        Get the overall properties of the shape

        :param first_line: The first line of the shape
        :return: a json representation of the properties of the first line
        """
        # a closed shape
        shape_json: dict = {}
        if "CLOSED" in first_line:
            shape_json = {"closed": "closed"}
        # a shape where values other than those specified are allowed for the specified properties
        if "EXTRA" in first_line:
            properties = re.findall(r"P\d+", first_line)
            for wikidata_property in properties:
                shape_json[wikidata_property] = {"extra": "allowed"}
        return shape_json

    def _get_schema_json(self, schema):
        """
        Downloads the schema from wikidata

        :param schema: the entityschema to be downloaded
        """
        url: str = f"https://www.wikidata.org/wiki/EntitySchema:{schema}?action=raw"
        response = requests.get(url)
        self._json_text: dict = response.json()

    def _strip_schema_comments(self):
        """
        Strips the comments out of the schema and converts parts we don't care about because they're enforced by
        wikidata
        """
        schema_text: str = ""
        # remove comments from the schema
        for line in self._json_text["schemaText"].splitlines():
            head, sep, tail = line.partition('# ')
            schema_text += f"\n{head.strip()}"
        # replace data types with the any value designator(.).  Since wikidata won't allow items to enter the
        # incorrect type (eg. trying to enter a LITERAL value where an IRI (i.e. a wikidata item) is required
        # will fail to save
        schema_text = schema_text.replace("IRI", ".")
        schema_text = schema_text.replace("LITERAL", ".")
        schema_text = schema_text.replace("xsd:dateTime", ".")
        schema_text = schema_text.replace("xsd:string", ".")
        schema_text = schema_text.replace("xsd:decimal", ".")
        schema_text = schema_text.replace("[ <http://commons.wikimedia.org/wiki/Special:FilePath>~ ]", ".")
        schema_text = schema_text.replace("[ <http://www.wikidata.org/entity>~ ]", ".")
        self._schema_text = schema_text

    def _get_schema_name(self):
        """
        Gets the name of the entityschema in the preferred language
        """
        if self._json_text["labels"][self._language]:
            self.name = self._json_text["labels"][self._language]

    def _get_default_shape(self):
        """
        Gets the default shape to start at in the schema
        """
        default_shape_name: Optional[Match[str]] = re.search(r"start.*=.*@<.*>", self._schema_text, re.IGNORECASE)
        default_name: str = default_shape_name.group(0).replace(" ", "")
        self._default_shape_name = default_name[8:-1]
        shape_names: list = re.findall(r"\n<.*>", self._schema_text)
        for name in shape_names:
            self._shapes[name[2:-1]] = self._get_specific_shape(name[2:-1])

    def _get_specific_shape(self, shape_name: str):
        """
        Extracts a specific shape from the schema

        :param shape_name: The name of the shape to be extracted
        :return: The extracted shape
        """
        search: Union[Pattern[Union[str, Any]], Pattern] = re.compile(r"<%s>.*{.*(\n[^}]*)*}"
                                                                      % shape_name, re.MULTILINE)
        shape: Optional[Match[Union[str, Any]]] = re.search(search, self._schema_text)
        return shape.group(0)

    def _translate_sub_shape(self, schema_json: dict):
        """
        Converts a sub-shape to a json representation

        :param schema_json: The json containing the shape to be extracted
        :return: The extracted shape
        """
        sub_shape: dict = self._schema_shapes[schema_json["shape"]]
        del schema_json["shape"]
        qualifier_child: dict = {}
        reference_child: dict = {}
        for key in sub_shape:
            if "status" in sub_shape[key]:
                if "shape" in sub_shape[key]:
                    sub_shape_json = self._translate_sub_shape(sub_shape[key])
                    if sub_shape[key]["status"] == "statement":
                        schema_json["required"] = sub_shape_json
                if sub_shape[key]["status"] == "statement" and\
                        "allowed" in sub_shape[key]:
                    value = sub_shape[key]["allowed"]
                    schema_json["required"] = {key: value}
                if sub_shape[key]["status"] == "qualifier":
                    qualifier_child[key] = sub_shape[key]
                if sub_shape[key]["status"] == "reference":
                    reference_child[key] = sub_shape[key]
        schema_json["qualifiers"] = qualifier_child
        schema_json["references"] = reference_child
        return schema_json

    @staticmethod
    def _get_cardinality(schema_line: str):
        """
        Gets the cardinality of a line of the schema

        :param schema_line: The line to be processed
        :return: A json representation of the cardinality in the form {min:x, max:y}
        """
        cardinality: dict = {}
        if "?" in schema_line:
            cardinality["max"] = 1
        elif "*" in schema_line:
            cardinality = {}
        elif "+" in schema_line:
            cardinality["min"] = 1
        elif re.search(r"{.+}", schema_line):
            match = re.search(r"{.+}", schema_line).group()
            cardinalities = match[1:-1].split(",")
            cardinality["min"] = cardinalities[0]
            if len(cardinalities) == 1:
                cardinality["max"] = cardinalities[0]
            else:
                cardinality["max"] = cardinalities[1]
        else:
            cardinality["min"] = 1
            cardinality["max"] = 1
        return cardinality

    @staticmethod
    def _get_snak_type(schema_line: str):
        """
        Gets the type of snak from a schema line

        :param schema_line: The line to be processed
        :return: statement, qualifier or reference
        """
        if any(prop in schema_line for prop in ["wdt:", "ps:", "p:"]):
            return "statement"
        elif "pq:" in schema_line:
            return "qualifier"
        else:
            return "reference"
