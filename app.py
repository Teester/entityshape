"""
A Flask app to compare entityschema with wikidata items without using SPARQL
"""
import os
from json import JSONDecodeError

import requests
from flask import Flask, json, request
from flask_cors import CORS
from requests import Response

from compareshape import CompareShape
from pyshex.shex_evaluator import ShExEvaluator
from pyshex.utils.sparql_query import SPARQLQuery
from shape import Shape
from sparql_slurper import SlurpyGraph

app = Flask(__name__)
CORS(app)

@app.route("/ping")
def check_status():
    return {'status': 200}

@app.route("/api")
def data():
    """
    Compares an entityschema with a wikidata item
    :return: a response to the query
    """
    schema: str = request.args.get("entityschema", type=str)
    entity: str = request.args.get("entity", type=str)
    wiki_url: str = request.args.get("url", type=str)
    # endpoint: str = request.args.get("endpoint", type=str)
    if "Lexeme" in entity:
        entity = entity[7:]
    language: str = request.args.get("language", type=str)
    try:
        # valid: dict = check_against_pyshexy(schema, entity, endpoint)
        valid: dict = {}
        shape: Shape = Shape(schema, language, wiki_url)
        comparison: CompareShape = CompareShape(shape.get_schema_shape(), entity, language, wiki_url)
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

@app.route("/pyshexy")
def ps_data():
    wiki_url = request.args.get("url", type=str)
    entitySchema = request.args.get("entityschema", type=str)
    entity = request.args.get("entity", type=str)
    sparql = request.args.get("sparql", type=str)
    shexc = request.args.get("shexc", type=str)
    endpoint = request.args.get("endpoint", type=str)
    result = checkShex(wiki_url, shexc, entitySchema, entity, sparql, endpoint)
    payload = {}
    payload['results'] = result
    payload['length'] = len(result)
    response = app.response_class(
        response=json.dumps(payload),
        status=200,
        mimetype="application/json"
        )
    return response

def checkShex(wiki_url, shexc, entitySchema, entity, query, endpoint):
    result = []
    if endpoint is None:
        endpoint = 'https://sparql.demo5280.com/proxy/wdqs/bigdata/namespace/wdq/sparql'

    if query is None:
        query = f"SELECT ?item WHERE {{ BIND(wd:{entity} as ?item) }} LIMIT 1"

    if entitySchema:
        shex = f"{wiki_url}/wiki/Special:EntitySchemaText/{entitySchema}"
        shexString = processShex(shex)
    else:
        shexString = shexc

    results = ShExEvaluator(SlurpyGraph(endpoint),
                        shexString,
                        SPARQLQuery(endpoint, query).focus_nodes()).evaluate()
    for r in results:
        thisResult = {}
        thisResult['result'] = r.result
        thisResult['reason'] = r.reason if r.reason else ""
        thisResult['focus'] = r.focus if r.focus else ""
        thisResult['start'] = r.start if r.start else ""
        result.append(thisResult)
    return result
 
def processShex(shex):
    r = requests.get(shex)
    shexString = r.text

    # Replace import statements with the contents of those schemas since PyShEx doesn't do imports
    for line in shexString.splitlines():
        if line.startswith("IMPORT"):
            importString = line[line.find("<")+1:line.find(">")]
            s = requests.get(importString)
            shexString = shexString.replace(line, s.text)
    return shexString

def check_against_pyshexy(entityschema: str, entity: str, endpoint: str):
    """
    Checks the entityschema and item against the pyshexy api
    :param entityschema: the entityschema E number to be checked
    :param entity: The entity Q number to be checked
    :return: the response from pyshexy
    """
    json_text: dict
    url: str = f"https://tools.wmflabs.org/pyshexy/api?entityschema={entityschema}&entity={entity}&endpoint={endpoint}"
    try:
        response: Response = requests.get(url)
        json_text = response.json()
    except JSONDecodeError as exception:
        print(f"{type(exception).__name__}: {exception}")
        json_text = {}
    return json_text


if __name__ == "__main__":
    app.run()
