import requests

from requests import Response


class CompareShape:
    """
    Compares a wikidata entity (e.g. Q42) with a shape and returns the conformity of the statements and properties in
    the entity to the shape

    :param shape: The a json representation of the shape to be compared against
    :param entity: The entity to be compared (e.g. Q42)
    :param language: The language to use for details like property names

    :returns properties: a json representation of the conformity of each property in the entity
    :returns statements: a json representation of the conformity of each statement in the entity
    """
    # TODO: Process CLOSED comparison
    # TODO: Process OR and NOT comparison
    # TODO: Process groups in comparison
    def __init__(self, shape: dict, entity: str, language: str):
        self.properties: dict = {}
        self.statements: dict = {}

        self._entity: str = entity
        self._language: str = language
        self._shape: dict = shape
        self._property_responses: dict = {}

        self._get_entity_json()
        self._get_props(self._entities["entities"][self._entity]['claims'])
        self._get_property_names()
        self._compare_statements()
        self._compare_properties()
    
    def _compare_statements(self):
        """
        Compares the statements in the entity to the schema
        """
        claims: dict = self._entities["entities"][self._entity]['claims']
        for claim in claims:
            statement_results: list = []
            property_statement_results: list = []
            for statement in claims[claim]:
                child: dict = {"property": claim}
                allowed: str = "not in schema"
                qualifiers: str = ""
                required: str = ""
                extra: str = ""
                if claim in self._shape:
                    allowed = "present"
                    if "necessity" in self._shape[claim]:
                        child["necessity"] = self._shape[claim]["necessity"]
                        allowed = "allowed"
                    if "allowed" in self._shape[claim]:
                        allowed = "correct"
                        value: str = statement["mainsnak"]["datavalue"]["value"]["id"]
                        if value not in self._shape[claim]["allowed"]:
                            allowed = "incorrect"
                    if "not_allowed" in self._shape[claim]:
                        value: str = statement["mainsnak"]["datavalue"]["value"]["id"]
                        if value in self._shape[claim]["not_allowed"]:
                            allowed = "not allowed"
                    if "extra" in self._shape[claim]:
                        extra: str = "extra"
                    if "qualifiers" in self._shape[claim]:
                        allowed_qualifiers: list = []
                        for qualifier in self._shape[claim]["qualifiers"]:
                            if "qualifiers" in statement and qualifier not in statement["qualifiers"]:
                                allowed_qualifiers.append(qualifier)
                        if len(allowed_qualifiers) > 0:
                            qualifiers: str = "missing qualifiers: " + ", ".join(allowed_qualifiers)
                        else:
                            qualifiers = ""
                    if "required" in self._shape[claim]:
                        if "required" in self._shape[claim]["required"]:
                            required_property: str = list(self._shape[claim]["required"]["required"].keys())[0]
                            required_value: str = self._shape[claim]["required"]["required"][required_property][0]
                        else:
                            required_property: str = list(self._shape[claim]["required"].keys())[0]
                            required_value: str = self._shape[claim]["required"][required_property][0]

                        query_entity: str = statement["mainsnak"]["datavalue"]["value"]["id"]
                        url: str = f"https://www.wikidata.org/w/api.php?action=wbgetclaims" \
                            f"&entity={query_entity}&property={required_property}&format=json"
                        response: Response = requests.get(url)
                        json_text: dict = response.json()
                        if required_property in json_text["claims"]:
                            for key in json_text["claims"][required_property]:
                                if key["mainsnak"]["datavalue"]["value"]["id"] == required_value:
                                    required = "present"
                                else:
                                    required = "incorrect"
                        else:
                            required = "missing"
                if required == "present":
                    if qualifiers == "":
                        allowed = "correct"
                    else:
                        allowed = qualifiers
                if required == "incorrect":
                    if extra == "extra":
                        allowed = "allowed"
                    else:
                        if qualifiers == "":
                            allowed = "allowed"
                        else:
                            allowed = qualifiers
                if allowed == "incorrect" and extra == "extra":
                    allowed = "allowed"
                if required == "missing":
                    allowed = required
                if allowed != "":
                    child["response"] = allowed
                self.statements[statement["id"]] = child
                statement_results.append(allowed)
                if allowed.startswith("missing"):
                    allowed = "incorrect"
                property_statement_results.append(allowed)
            self._property_responses[claim] = property_statement_results
        print("statements = " + str(self.statements))
        print("properties responses = " + str(self._property_responses))

    def _compare_properties(self):
        """
        Compares the properties in the entity to the schema
        """
        for claim in self._props:
            response: str = "missing"
            required: str = "correct"
            child: dict = {"name": self._names[claim], "necessity": "absent"}
            if claim in self._shape and "necessity" in self._shape[claim]:
                child["necessity"] = self._shape[claim]["necessity"]
            if claim in self._entities["entities"][self._entity]['claims']:
                cardinality: str = ""
                allowed: str
                if "incorrect" in self._property_responses[claim]:
                    allowed = "incorrect"
                elif "correct" in self._property_responses[claim]:
                    allowed = "correct"
                else:
                    allowed = "present"
                if claim in self._shape:
                    if child["necessity"] != "absent":
                        cardinality = "correct"
                    if "cardinality" in self._shape[claim]:
                        if "extra" in self._shape[claim]:
                            number_of_statements = self._property_responses[claim].count("correct")
                        else:
                            number_of_statements = len(self._property_responses[claim])
                        min_cardinality = True
                        max_cardinality = True
                        if "min" in self._shape[claim]["cardinality"] and\
                                number_of_statements < self._shape[claim]["cardinality"]["min"]:
                            min_cardinality = False
                        if "max" in self._shape[claim]["cardinality"] and \
                                number_of_statements > self._shape[claim]["cardinality"]["max"]:
                            max_cardinality = False
                        if min_cardinality and not max_cardinality:
                            cardinality = "too many statements"
                        if max_cardinality and not min_cardinality:
                            cardinality = "not enough correct statements"
                if cardinality == "correct":
                    response = allowed
                else:
                    response = cardinality
                if required == "correct" and response == "allowed":
                    response = "correct"
            if response != "":
                child["response"] = response
            self.properties[claim] = child
        print("properties = " + str(self.properties))

    def _get_entity_json(self):
        """
        Downloads the entity from wikidata
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url)
        self._entities = response.json()

    def _get_props(self, claims: dict):
        """
        Gets a list of properties included in the entity
        :param claims: The claims in the entity
        """
        self._props: list = []
        for claim in claims:
            if claim not in self._props:
                self._props.append(claim)
        for claim in self._shape:
            if claim not in self._props:
                self._props.append(claim)

    def _get_property_names(self):
        """
        Gets the names of properties from wikidata
        """
        self._names: dict = {}
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            url: str = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={required_properties}&" \
                       f"props=labels&languages={self._language}&format=json"
            response: Response = requests.get(url)
            json_text: dict = response.json()
            for item in element:
                try:
                    self._names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][self._language]["value"]
                except KeyError:
                    self._names[json_text["entities"][item]["id"]] = ""
