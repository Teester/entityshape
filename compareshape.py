import requests


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
    def __init__(self, shape, entity, language):
        self.properties = {}
        self.statements = {}

        self.__entity = entity
        self.__language = language
        self.__shape = shape

        self.__property_responses = {}
        self.__get_entity_json()
        self.__get_props(self.__entities["entities"][self.__entity]['claims'])
        self.__get_property_names()
        self.__compare_statements()
        self.__compare_properties()
    
    def __compare_statements(self):
        """
        Compares the statements in the entity to the schema
        """
        claims = self.__entities["entities"][self.__entity]['claims']
        for claim in claims:
            statement_results = []
            property_statement_results = []
            for statement in claims[claim]:
                child = {"property": claim}
                allowed = "not in schema"
                qualifiers = ""
                required = ""
                extra = ""
                if claim in self.__shape:
                    allowed = "present"
                    if "necessity" in self.__shape[claim]:
                        child["necessity"] = self.__shape[claim]["necessity"]
                        allowed = "allowed"
                    if "allowed" in self.__shape[claim]:
                        allowed = "correct"
                        value = statement["mainsnak"]["datavalue"]["value"]["id"]
                        if value not in self.__shape[claim]["allowed"]:
                            allowed = "incorrect"
                    if "notallowed" in self.__shape[claim]:
                        value = statement["mainsnak"]["datavalue"]["value"]["id"]
                        if value in self.__shape[claim]["notallowed"]:
                            allowed = "not allowed"
                    if "extra" in self.__shape[claim]:
                        extra = "extra"
                    if "qualifiers" in self.__shape[claim]:
                        allowed_qualifiers = []
                        for qualifier in self.__shape[claim]["qualifiers"]:
                            if "qualifiers" in statement:
                                if qualifier not in statement["qualifiers"]:
                                    allowed_qualifiers.append(qualifier)
                        if len(allowed_qualifiers) > 0:
                            qualifiers = "missing qualifiers: " + ", ".join(allowed_qualifiers)
                        else:
                            qualifiers = ""
                    if "required" in self.__shape[claim]:
                        if "required" in self.__shape[claim]["required"]:
                            required_property = list(self.__shape[claim]["required"]["required"].keys())[0]
                            required_value = self.__shape[claim]["required"]["required"][required_property][0]
                        else:
                            required_property = list(self.__shape[claim]["required"].keys())[0]
                            required_value = self.__shape[claim]["required"][required_property][0]

                        query_entity = statement["mainsnak"]["datavalue"]["value"]["id"]
                        url = f"https://www.wikidata.org/w/api.php?action=wbgetclaims" \
                              f"&entity={query_entity}&property={required_property}&format=json"
                        response = requests.get(url)
                        json_text = response.json()
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
                if allowed == "incorrect":
                    if extra == "extra":
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
            self.__property_responses[claim] = property_statement_results
        print("statements = " + str(self.statements))
        print("properties responses = " + str(self.__property_responses))

    def __compare_properties(self):
        """
        Compares the properties in the entity to the schema
        """
        for claim in self.__props:
            response = "missing"
            required = "correct"
            child = {"name": self.__names[claim], "necessity": "absent"}
            if claim in self.__shape:
                if "necessity" in self.__shape[claim]:
                    child["necessity"] = self.__shape[claim]["necessity"]
            if claim in self.__entities["entities"][self.__entity]['claims']:
                cardinality = ""
                if "incorrect" in self.__property_responses[claim]:
                    allowed = "incorrect"
                elif "correct" in self.__property_responses[claim]:
                    allowed = "correct"
                else:
                    allowed = "present"
                if claim in self.__shape:
                    if child["necessity"] != "absent":
                        cardinality = "correct"
                    if "cardinality" in self.__shape[claim]:
                        if "extra" in self.__shape[claim]:
                            number_of_statements = self.__property_responses[claim].count("correct")
                        else:
                            number_of_statements = len(self.__property_responses[claim])
                        min_cardinality = True
                        max_cardinality = True
                        if "min" in self.__shape[claim]["cardinality"]:
                            if number_of_statements < self.__shape[claim]["cardinality"]["min"]:
                                min_cardinality = False
                        if "max" in self.__shape[claim]["cardinality"]:
                            if number_of_statements > self.__shape[claim]["cardinality"]["max"]:
                                max_cardinality = False
                        if min_cardinality and not max_cardinality:
                            cardinality = "too many statements"
                        if max_cardinality and not min_cardinality:
                            cardinality = "not enough correct statements"
                if cardinality == "correct":
                    response = allowed
                else:
                    response = cardinality
                if required == "correct":
                    if response == "allowed":
                        response = "correct"
            if response != "":
                child["response"] = response
            self.properties[claim] = child
        print("properties = " + str(self.properties))

    def __get_entity_json(self):
        """
        Downloads the entity from wikidata
        """
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{self.__entity}.json"
        response = requests.get(url)
        self.__entities = response.json()

    def __get_props(self, claims):
        """
        Gets a list of properties included in the entity
        :param claims: The claims in the entity
        """
        self.__props = []
        for claim in claims:
            if claim not in self.__props:
                self.__props.append(claim)
        for claim in self.__shape:
            if claim not in self.__props:
                self.__props.append(claim)

    def __get_property_names(self):
        """
        Gets the names of properties from wikidata
        """
        self.__names = {}
        wikidata_property_list = [self.__props[i * 49:(i + 1) * 49]
                                  for i in range((len(self.__props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties = "|".join(element)
            url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={required_properties}&" \
                  f"props=labels&languages={self.__language}&format=json"
            response = requests.get(url)
            json_text = response.json()
            for item in element:
                try:
                    self.__names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][self.__language]["value"]
                except KeyError:
                    self.__names[json_text["entities"][item]["id"]] = ""
