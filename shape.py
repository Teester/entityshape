import re
import requests


class Shape:
    """
    Produces a shape in the form of a json for a wikidata entityschema (e.g. E10)

    :param schema: The identifier of the entityschema to be processed
    :param language: The language to get the schema name in

    :return name: the name of the entityschema
    :return shape: a json representation of the entityschema
    """

    def __init__(self, schema, language):
        self.__shapes = {}
        self.__schema_shapes = {}
        self.__language = language
        self.__get_schema_json(schema)
        self.__strip_schema_comments()
        self.__get_schema_name()
        self.__get_default_shape()
        self.__translate_schema()

    def __translate_schema(self):
        """
        Converts the entityschema to a json representation
        """
        for shape in self.__shapes:
            new_shape = self.__convert_shape_to_array(shape)

            for schema_line in new_shape:
                if re.match(r".+:P\d", schema_line):
                    selected_property = re.search(r"P\d+", schema_line).group(0)
                    snak = self.__get_snak_type(schema_line)
                    if selected_property in self.__shape_json:
                        child = self.__shape_json[selected_property]
                    else:
                        child = {}
                    if "@<" in schema_line:
                        sub_shape_name = re.search(r"<.*>", schema_line).group(0)
                        child["shape"] = sub_shape_name[1:-1]
                    if re.search(r"\[.*]", schema_line):
                        required_parameters_string = re.search(r"\[.*]", schema_line).group(0)
                        required_parameters_string = re.sub(r"wd:", "", required_parameters_string)
                        if "^" in schema_line:
                            child["notallowed"] = required_parameters_string[1:-1].split()
                        else:
                            child["allowed"] = required_parameters_string[1:-1].split()
                    cardinality = self.__get_cardinality(schema_line)
                    necessity = "optional"
                    if cardinality:
                        child["cardinality"] = cardinality
                        if "min" in cardinality:
                            necessity = "required"
                    child["necessity"] = necessity
                    child["status"] = snak
                    self.__shape_json[selected_property] = child
            self.__schema_shapes[shape] = self.__shape_json
        schema_json = self.__schema_shapes[self.__default_shape_name]
        for key in schema_json:
            if "shape" in schema_json[key]:
                schema_json[key] = self.__translate_sub_shape(schema_json[key])
            if "required" in schema_json[key]:
                if "required" in schema_json[key]["required"]:
                    schema_json[key]["required"] = schema_json[key]["required"]["required"]
        self.shape = schema_json

    def __convert_shape_to_array(self, shape):
        new_shape = self.__shapes[shape].replace("\n", "")
        self.__get_shape_properties(new_shape[new_shape.find(">")+1:new_shape.find("{")-1])
        new_shape = new_shape[new_shape.find("{")+1:new_shape.rfind("}")-1]
        return new_shape.split(";")

    def __get_shape_properties(self, first_line):
        """
        Get the overall properties of the shape
        :param first_line: The first line of the shape
        """
        self.__shape_json = {}
        if "CLOSED" in first_line:
            self.__shape_json = {"closed": "closed"}
        if "EXTRA" in first_line:
            properties = re.findall(r"P\d+", first_line)
            for wikidata_property in properties:
                self.__shape_json[wikidata_property] = {"extra": "allowed"}

    def __get_schema_json(self, schema):
        """
        Downloads the schema from wikidata
        :param schema: the entityschema to be downloaded
        """
        url = f"https://www.wikidata.org/wiki/EntitySchema:{schema}?action=raw"
        response = requests.get(url)
        self.__json_text = response.json()

    def __strip_schema_comments(self):
        """
        Strips the comments out of the schema and converts parts we don't care about because they're enforced by
        wikidata
        """
        schema_text = ""
        for line in self.__json_text["schemaText"].splitlines():
            head, sep, tail = line.partition('# ')
            schema_text += f"\n{head.strip()}"
        schema_text = schema_text.replace("IRI", ".")
        schema_text = schema_text.replace("LITERAL", ".")
        schema_text = schema_text.replace("xsd:dateTime", ".")
        schema_text = schema_text.replace("xsd:string", ".")
        schema_text = schema_text.replace("xsd:decimal", ".")
        schema_text = schema_text.replace("[ <http://commons.wikimedia.org/wiki/Special:FilePath>~ ]", ".")
        schema_text = schema_text.replace("[ <http://www.wikidata.org/entity>~ ]", ".")
        self.__schema_text = schema_text

    def __get_schema_name(self):
        """
        Gets the name of the entityschema in the preferred language
        """
        if self.__json_text["labels"][self.__language]:
            self.name = self.__json_text["labels"][self.__language]
        else:
            self.name = ""

    def __get_default_shape(self):
        """
        Gets the default shape to start at in the schema
        """
        default_shape_name = re.search(r"start = @<.*>", self.__schema_text)
        default_name = default_shape_name.group(0).replace(" ", "")
        self.__default_shape_name = default_name[8:-1]
        shape_names = re.findall(r"\n<.*>", self.__schema_text)
        for name in shape_names:
            self.__shapes[name[2:-1]] = self.__get_specific_shape(name[2:-1])

    def __get_specific_shape(self, shape_name):
        """
        Extracts a specific shape from the schema
        :param shape_name: The name of the shape to be extracted
        :return: The extracted shape
        """
        search = re.compile(r"<%s>.*{.*(\n[^}]*)*}" % shape_name, re.MULTILINE)
        default_shape = re.search(search, self.__schema_text)
        return default_shape.group(0)

    def __translate_sub_shape(self, schema_json):
        """
        Converts a subshape to a json representation
        :param schema_json: The json containing the shape to be extracted
        :return: The extracted shape
        """
        sub_shape = self.__schema_shapes[schema_json["shape"]]
        del schema_json["shape"]
        qualifier_child = {}
        reference_child = {}
        for key in sub_shape:
            if "status" in sub_shape[key]:
                if "shape" in sub_shape[key]:
                    sub_shape_json = self.__translate_sub_shape(sub_shape[key])
                    if sub_shape[key]["status"] == "statement":
                        schema_json["required"] = sub_shape_json
                if sub_shape[key]["status"] == "statement":
                    if "allowed" in sub_shape[key]:
                        value = sub_shape[key]["allowed"]
                        schema_json["required"] = {key: value}
                if sub_shape[key]["status"] == "qualifier":
                    qualifier_child[key] = sub_shape[key]
                if sub_shape[key]["status"] == "reference":
                    reference_child[key] = sub_shape[key]
        schema_json["qualifiers"] = qualifier_child
        schema_json["references"] = reference_child
        return schema_json

    def __get_cardinality(self, schema_line):
        """
        Gets the cardinality of a line of the schema
        :param schema_line: The line to be processed
        :return: A json representation of the cardinality
        """
        cardinality = {}
        if "?" in schema_line:
            cardinality["max"] = 1
        elif "*" in schema_line:
            pass
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

    def __get_snak_type(self, schema_line):
        """
        Gets the type of snak from a schema line
        :param schema_line: The line to be processed
        :return: statement, qualifier or reference
        """
        if any(prop in schema_line for prop in ["wdt:", "ps:", "p:"]):
            snak = "statement"
        elif "pq:" in schema_line:
            snak = "qualifier"
        else:
            snak = "reference"
        return snak
