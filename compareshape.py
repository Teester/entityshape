"""
Compares a json shape from shape.py with wikidata json
"""
import requests
from requests import Response


class CompareShape:
    """
    Compares a wikidata entity (e.g. Q42) with a shape and returns the conformity of
    the statements and properties in the entity to the shape

    :param shape: The a json representation of the shape to be compared against
    :param entity: The entity to be compared (e.g. Q42)
    :param language: The language to use for details like property names

    :returns properties: a json representation of the conformity of each property in the entity
    :returns statements: a json representation of the conformity of each statement in the entity
    """
    def __init__(self, shape: dict, entity: str, language: str, domain: str):
        self._entity: str = entity
        self._shape: dict = shape
        self._property_responses: dict = {}

        self._get_entity_json(domain)
        if self._entities["entities"][self._entity]:
            self._get_props(self._entities["entities"][self._entity]['claims'])
        self._get_property_names(language)
        self._compare_statements()
        self._compare_properties()

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        return self._compare_properties()

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        return self._compare_statements()

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison
        :return: json for general properties of the comparison
        """
        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            if item in self._shape and item in self._entities["entities"][self._entity]:
                expected: list = self._shape[item]["allowed"]
                actual: str = self._entities["entities"][self._entity][item]
                general[item] = "incorrect"
                if actual in expected:
                    general[item] = "correct"
        return general

    def _compare_statements(self):
        """
        Compares the statements in the entity to the schema
        """
        statements: dict = {}
        claims: dict = self._entities["entities"][self._entity]['claims']
        for claim in claims:
            statement_results: list = []
            property_statement_results: list = []
            for statement in claims[claim]:
                child: dict = {"property": claim}
                allowed: str = "not in schema"
                if claim in self._shape:
                    allowed, extra, qualifiers, required = \
                        self._process_claim_in_shape(claim, statement, child)
                    allowed = self._process_allowed(allowed, required, qualifiers, extra)
                if allowed != "":
                    child["response"] = allowed
                statements[statement["id"]] = child
                statement_results.append(allowed)
                if allowed.startswith("missing"):
                    allowed = "incorrect"
                property_statement_results.append(allowed)
            self._property_responses[claim] = property_statement_results
        return statements

    def _compare_properties(self):
        """
        Compares the properties in the entity to the schema
        """
        properties: dict = {}
        for claim in self._props:
            response: str = "missing"
            child: dict = {"name": self._names[claim], "necessity": "absent"}
            if claim in self._shape and "necessity" in self._shape[claim]:
                child["necessity"] = self._shape[claim]["necessity"]
            if claim in self._entities["entities"][self._entity]['claims']:
                response = self._process_claim(claim, child)
            if response != "":
                child["response"] = response
            properties[claim] = child
        return properties

    def _process_claim(self, claim, child):
        cardinality: str = ""
        allowed: str
        if "incorrect" in self._property_responses[claim]:
            allowed = "incorrect"
        elif "correct" in self._property_responses[claim]:
            allowed = "correct"
        else:
            allowed = "present"
        if claim in self._shape:
            cardinality = self._assess_cardinality(claim, child)
        if cardinality == "correct":
            response = allowed
        else:
            response = cardinality
        if response == "allowed":
            response = "correct"
        return response

    def _assess_cardinality(self, claim, child):
        cardinality: str = ""
        number_of_statements: int = len(self._property_responses[claim])
        min_cardinality = False
        max_cardinality = False
        if child["necessity"] != "absent":
            cardinality = "correct"
        if "cardinality" in self._shape[claim]:
            claim_cardinality = self._shape[claim]["cardinality"]
            min_cardinality = True
            max_cardinality = True
            if "extra" in self._shape[claim]:
                number_of_statements = self._property_responses[claim].count("correct")
            if "min" in claim_cardinality and number_of_statements < claim_cardinality["min"]:
                min_cardinality = False
            if "max" in claim_cardinality and number_of_statements > claim_cardinality["max"]:
                max_cardinality = False
        if min_cardinality and not max_cardinality:
            cardinality = "too many statements"
        if max_cardinality and not min_cardinality:
            cardinality = "not enough correct statements"
        return cardinality

    def _get_entity_json(self, domain: str):
        """
        Downloads the entity from wikidata
        """
        url: str = f"https://{domain}/wiki/Special:EntityData/{self._entity}.json"
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
            if claim not in self._props and claim.startswith("P"):
                self._props.append(claim)

    def _get_property_names(self, language: str):
        """
        Gets the names of properties from wikidata
        """
        self._names: dict = {}
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            url: str = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids=" \
                       f"{required_properties}&props=labels&languages={language}&format=json"
            response: Response = requests.get(url)
            json_text: dict = response.json()
            for item in element:
                try:
                    self._names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][language]["value"]
                except KeyError:
                    self._names[json_text["entities"][item]["id"]] = ""

    def _process_allowed_in_shape_claim(self, claim, param):
        allowed = "correct"
        if "id" in param["value"]:
            value: str = param["value"]["id"]
            if value not in self._shape[claim]["allowed"]:
                allowed = "incorrect"
        return allowed

    @staticmethod
    def _process_required_in_shape_claim(shape_claim, datavalue):
        required: str = ""
        if "required" in shape_claim["required"]:
            shape_claim_required = shape_claim["required"]["required"]
            required_property: str = list(shape_claim_required.keys())[0]
            required_value: str = shape_claim_required[required_property][0]
        else:
            required_property: str = list(shape_claim["required"].keys())[0]
            required_value: str = shape_claim["required"][required_property][0]

        query_entity: str = datavalue["value"]["id"]
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
        return required

    @staticmethod
    def _process_allowed(allowed, required, qualifiers, extra):
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
        return allowed

    @staticmethod
    def _process_qualifiers_in_shape_claim(shape_claim, statement):
        allowed_qualifiers: list = []
        for qualifier in shape_claim["qualifiers"]:
            if "qualifiers" in statement and \
                    qualifier not in statement["qualifiers"]:
                allowed_qualifiers.append(qualifier)
        if len(allowed_qualifiers) > 0:
            qualifiers: str = "missing qualifiers: " + ", ".join(allowed_qualifiers)
        else:
            qualifiers = ""
        return qualifiers

    def _process_claim_in_shape(self, claim, statement, child):
        datavalue: dict = statement["mainsnak"]["datavalue"]
        shape_claim: dict = self._shape[claim]
        qualifiers: str = ""
        required: str = ""
        extra: str = ""

        allowed = "present"
        if "necessity" in shape_claim:
            child["necessity"] = shape_claim["necessity"]
            allowed = "allowed"
        if "allowed" in shape_claim:
            allowed = self._process_allowed_in_shape_claim(claim, datavalue)
        if "not_allowed" in shape_claim and "id" in datavalue["value"]:
            value: str = datavalue["value"]["id"]
            if value in shape_claim["not_allowed"]:
                allowed = "not allowed"
        if "extra" in shape_claim:
            extra: str = "extra"
        if "qualifiers" in shape_claim:
            qualifiers = self._process_qualifiers_in_shape_claim(shape_claim, statement)
        if "required" in shape_claim:
            required = self._process_required_in_shape_claim(shape_claim, datavalue)
        return allowed, extra, qualifiers, required
