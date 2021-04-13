"""
A Flask app to compare entityschema with wikidata items without using SPARQL
"""
from json import JSONDecodeError

import requests

from flask import Flask, request, json
from flask_cors import CORS
from requests import Response
from compareshape import CompareShape
from shape import Shape

app = Flask(__name__)
CORS(app)


@app.route("/api")
def data():
    """
    Compares an entityschema with a wikidata item
    :return: a response to the query
    """
    schema: str = request.args.get("entityschema", type=str)
    entity: str = request.args.get("entity", type=str)
    if "Lexeme" in entity:
        entity = entity[7:]
    language: str = request.args.get("language", type=str)
    try:
        # valid: dict = check_against_pyshexy(schema, entity)
        valid: dict = {}
        shape: Shape = Shape(schema, language)
        comparison: CompareShape = CompareShape(shape.get_schema_shape(), entity, language)
        payload: dict = {'schema': schema,
                         'name': shape.get_name(),
                         'validity': valid,
                         'general': comparison.get_general(),
                         'properties': comparison.get_properties(),
                         'statements': comparison.get_statements(),
                         'error': ""}
        status: int = 200
    except (AttributeError, TypeError, KeyError, IndexError) as exception:
        payload: dict = {'schema': "",
                         'name': "",
                         'validity': "",
                         'general': "",
                         'properties': "",
                         'statements': "",
                         'error': "An error has occurred while translating this schema"}
        status = 500
        print(f"Schema: {schema} - {type(exception).__name__}: {exception}")
    response: Response = app.response_class(response=json.dumps(payload),
                                            status=status,
                                            mimetype="application/json")
    return response


def check_against_pyshexy(entityschema: str, entity: str):
    """
    Checks the entityschema and item against the pyshexy api
    :param entityschema: the entityschema E number to be checked
    :param entity: The entity Q number to be checked
    :return: the response from pyshexy
    """
    json_text: dict
    url: str = f"https://tools.wmflabs.org/pyshexy/api?entityschema={entityschema}&entity={entity}"
    try:
        response: Response = requests.get(url)
        json_text = response.json()
    except JSONDecodeError as exception:
        print(f"{type(exception).__name__}: {exception}")
        json_text = {}
    return json_text


if __name__ == '__main__':
    app.run()
