"""
A class to compare a wikidata entity with a JSON-LD representation of an entityschema
"""
import json
import re
from typing import Dict, Any, List

import requests
from requests import Response

from entityshape.api_v3.compareshape import WikidataShExValidator


class CompareJSONLD:
    """
    A class to compare a wikidata entity with a JSON-LD representation of an entityschema
    """

    def __init__(self, shape: dict, entity: str, language: str) -> None:
        """
        Compares json from a wikidata entity with the json-ld representation of an entityschema

        :param dict shape: The json-ld representation of the entityschema to be assessed against
        :param str entity: The Q number of the wikidata entity to be assessed
        :param str language: The language to return the results in as a 2-letter code
        """
        self._entity: str = entity
        self._shape: dict = shape
        self._entities: dict = {}
        self._props: list = []
        self._property_responses: dict = {}

        self._get_entity_json()
        self._get_entity_nt()

        if "entities" in self._entities and self._entities["entities"][self._entity]:
            self._get_props(self._entities["entities"][self._entity]['claims'])
        self._get_property_names(language)
        # self.start_shape: dict = self._get_start_shape()

        entity_node = f"http://www.wikidata.org/entity/{self._entity}"
        comparison: WikidataShExValidator = WikidataShExValidator(json.dumps(shape))
        comparison.load_ntriples(self._nt)
        self._result = {"status": ""}
        self.response = {"properties": [], "statements": []}
        if "start" in comparison.schema:
            self._result = comparison.validate_node(focus_node_iri= entity_node,
                                               start_shape_id= comparison.schema["start"])
            self.response = self.format_validation_report(self._result)

    def get_validity(self):
        return self._result["status"]

    def get_properties(self) -> dict:
        """
        Gets the result of comparison for each property with the schema
        :return: json for comparison of properties
        """
        return self.response["properties"]

    def get_statements(self) -> dict:
        """
        Gets the result of comparison of each statement with the schema
        :return: json for comparison of statements
        """
        return self.response["statements"]

    def get_general(self) -> dict:
        """
        Gets general properties of the comparison

        :return: json for general properties of the comparison
        """
        if "shapes" not in self._shape:
            return {}
        if "entities" not in self._entities:
            return {}

        general: dict = {}
        properties: list = ["lexicalCategory", "language"]
        for item in properties:
            data_string: str = json.dumps(self._shape["shapes"])
            if item in data_string and item in self._entities["entities"][self._entity]:
                general[item] = "incorrect"
                expected: list = self._shape["shapes"]
                actual: str = self._entities["entities"][self._entity][item]
                if actual in expected:
                    general[item] = "correct"
        return general

    def _get_entity_json(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.json"
        response: Response = requests.get(url=url,
                                          headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        if response.status_code == 200:
            self._entities = response.json()

    def _get_entity_nt(self) -> None:
        """
        Downloads the entity from wikidata and assigns the json to self._entities
        """
        triples: str = ""
        url: str = f"https://www.wikidata.org/wiki/Special:EntityData/{self._entity}.nt"
        response: Response = requests.get(url=url,
                                          headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        if response.status_code == 200:
            triples = response.text
        self._nt = triples

    def _get_props(self, claims: dict) -> None:
        """
        Gets a list of properties included in the entity and assigns them to self._props

        :param claims: The claims in the entity
        """
        self._props: list = []
        # Get properties from the entity
        for claim in claims:
            if claim not in self._props:
                self._props.append(claim)
        # Get properties from the shape
        if "shapes" in self._shape:
            for shape in self._shape["shapes"]:
                properties: list = re.findall(r'P\d+', json.dumps(shape))
                for prop in properties:
                    if prop not in self._props and prop.startswith("P") and len(prop) > 1:
                        self._props.append(prop)

    def _get_property_names(self, language: str) -> None:
        """
        Gets the names of properties from wikidata and assigns them as a dict to self._names

        :param str language: The language in which to get the property names
        :return: Nothing
        """
        self._names: dict = {}
        wikidata_property_list: list = [self._props[i * 49:(i + 1) * 49]
                                        for i in range((len(self._props) + 48) // 48)]
        for element in wikidata_property_list:
            required_properties: str = "|".join(element)
            response: Response = requests.get(url="https://www.wikidata.org/w/api.php",
                                              params={"action": "wbgetentities",
                                                      "ids": required_properties,
                                                      "props": "labels",
                                                      "languages": language,
                                                      "format": "json"},
                                              headers={'User-Agent': 'Entityshape API by User:Teester'})
            json_text: dict = response.json()
            for item in element:
                try:
                    self._names[json_text["entities"][item]["id"]] = \
                        json_text["entities"][item]["labels"][language]["value"]
                except KeyError:
                    self._names[json_text["entities"][item]["id"]] = ""

    def _get_start_shape(self) -> dict:
        """
        Gets the shape associated with the start parameter of the entityschema

        :return: the start shape
        """
        if "start" not in self._shape:
            return {}
        if "shapes" not in self._shape:
            return {}

        for shape in self._shape['shapes']:
            if shape["id"] == self._shape["start"]:
                return shape
        return {}

    def format_validation_report(self, detailed_report: Dict[str, Any]) -> Dict[str, Any]:
        print(f"detailed report = {json.dumps(detailed_report, indent=2)}")
        properties_dict = {}
        statements_dict = {}

        # Grab the pre-parsed property labels map from the validator's output structure
        labels_lookup = detailed_report.get("property_labels", {})

        evaluations = detailed_report.get("property_evaluations", [])

        for prop_eval in evaluations:
            predicate_iri = prop_eval["predicate"]
            prop_id = predicate_iri.split("/")[-1]

            card = prop_eval["cardinality"]
            min_card = card["expected_min"]
            max_card = card["expected_max"]
            actual_count = card["counted_for_cardinality"]

            is_extra = prop_eval.get("is_marked_extra", False)
            prop_status = prop_eval["status"]

            # 1. Necessity
            if min_card == 0 and max_card == 0:
                necessity = "absent"
            elif min_card > 0:
                necessity = "required"
            else:
                necessity = "optional"

            # 2. Property Response
            if prop_status == "FAIL":
                if max_card != -1 and actual_count > max_card:
                    prop_response = "too many statements"
                elif actual_count < min_card:
                    if actual_count == 0:
                        prop_response = "missing"
                    else:
                        prop_response = "not enough correct statements"
                else:
                    prop_response = "incorrect"
            else:
                if is_extra:
                    prop_response = "correct"
                elif len(prop_eval["statements_evaluated"]) > 0:
                    prop_response = "present"
                else:
                    prop_response = "missing" if necessity == "required" else "correct"

            # INJECTED: Look up the plain-text property label name string, fallback to ID if missing
            properties_dict[prop_id] = {
                "necessity": necessity,
                "response": prop_response
            }
            if prop_id.startswith("P"):
                properties_dict[prop_id]["name"] = self._names[prop_id]

            # 3. Process Individual Statements
            statements_evaluated = prop_eval.get("statements_evaluated", [])
            for stmt in statements_evaluated:
                stmt_status = stmt["status"]
                stmt_id = stmt["statement_id"]

                if stmt_status == "PASS":
                    stmt_response = "correct"
                else:
                    if prop_response == "missing" or prop_response == "not enough correct statements":
                        stmt_response = "not enough correct statements"
                    elif is_extra:
                        stmt_response = "allowed"
                    else:
                        stmt_response = "incorrect"

                statements_dict[stmt_id] = {
                    "property": prop_id,
                    "response": stmt_response
                }

            if "nested_subshape_error" in prop_eval:
                nested_results = self.format_validation_report(prop_eval["nested_subshape_error"])
                if nested_results["properties"]:
                    properties_dict.update(nested_results["properties"][0])
                if nested_results["statements"]:
                    statements_dict.update(nested_results["statements"][0])

        return {
            "properties": [properties_dict],
            "statements": [statements_dict]
        }