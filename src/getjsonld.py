import json

import requests
from jsonasobj import as_json
from pyshexc.parser_impl.generate_shexj import parse


class JSONLDShape:
    """
    Produces a shape in the form of a json for a wikidata entityschema (e.g. E10)

    :param schema: The identifier of the entityschema to be processed
    :param language: The language to get the schema name in

    :return name: the name of the entityschema
    :return shape: a json representation of the entityschema
    """
    def __init__(self, schema: str, language: str) -> None:
        self._language: str = language
        self._get_schema_json(schema)

    def get_json_ld(self) -> dict:
        """
        Gets the JSON_LD form of the Schema
        """
        try:
            return json.loads(as_json(parse(self._json_text["schemaText"])))
        except (KeyError, IndexError, AttributeError, ValueError):
            return {}

    def _get_schema_json(self, schema) -> None:
        """
        Downloads the schema from wikidata

        :param schema: the entityschema to be downloaded
        """
        url: str = f"https://www.wikidata.org/wiki/EntitySchema:{schema}?action=raw"
        response = requests.get(url=url,
                                headers={'User-Agent': 'Userscript Entityshape by User:Teester'})
        self._json_text: dict = response.json()

    def get_name(self) -> str:
        """
        Gets the name of the schema

        :return: the name of the schema
        """
        if self._language in self._json_text["labels"]:
            return self._json_text["labels"][self._language]
        return ""