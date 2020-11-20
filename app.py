import requests

from compareshape import CompareShape
from flask import Flask, request, json
from flask_cors import CORS
from requests import Response
from shape import Shape

app = Flask(__name__)
CORS(app)


@app.route("/api")
def data():
    schema: str = request.args.get("entityschema", type=str)
    entity: str = request.args.get("entity", type=str)
    if "Lexeme" in entity:
        entity = entity[7:]
    language: str = request.args.get("language", type=str)
    try:
        # valid: Dict = check_against_pyshexy(schema, entity)
        valid: dict = {}
        shape: Shape = Shape(schema, language)
        comparison: CompareShape = CompareShape(shape.schema_shape, entity, language)
        payload: dict = {'schema': schema, 'name': shape.name, 'validity': valid,
                         'properties': comparison.properties, 'statements': comparison.statements, 'error': ""}
        print(payload)
        status: int = 200
    except Exception as e:
        payload = {'schema': "", 'name': "", 'validity': "", 'properties': "", 'statements': "",
                   'error': "An error has occurred while translating this schema"}
        status = 500
        print(e)
    response: Response = app.response_class(response=json.dumps(payload), status=status, mimetype="application/json")
    return response


def check_against_pyshexy(entityschema: str, entity: str):
    json_text: dict
    url: str = f"https://tools.wmflabs.org/pyshexy/api?entityschema={entityschema}&entity={entity}"
    try:
        response: Response = requests.get(url)
        json_text = response.json()
    except Exception as e:
        print(e)
        json_text = {}
    return json_text


if __name__ == '__main__':
    app.run(debug=True)
