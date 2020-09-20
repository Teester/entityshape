import requests

from flask import Flask, request, json
from flask_cors import CORS

from shape import Shape
from compareshape import CompareShape

app = Flask(__name__)
CORS(app)


@app.route("/api")
def data():
    schema = request.args.get("entityschema", type=str)
    entity = request.args.get("entity", type=str)
    language = request.args.get("language", type=str)
    try:
        valid = check_against_pyshexy(schema, entity)
        shape = Shape(schema, language)
        comparison = CompareShape(shape.shape, entity, language)
        payload = {'schema': schema, 'name': shape.name, 'validity': valid,
                   'properties': comparison.properties, 'statements': comparison.statements, 'error': ""}
        print(payload)
        status = 200
    except Exception as e:
        payload = {'schema': "", 'name': "", 'validity': "", 'properties': "", 'statements': "",
                   'error': "An error has occurred while translating this schema"}
        status = 500
        print(e)
    response = app.response_class(response=json.dumps(payload), status=status, mimetype="application/json")
    return response


def check_against_pyshexy(entityschema, entity):
    url = f"https://tools.wmflabs.org/pyshexy/api?entityschema={entityschema}&entity={entity}"
    try:
        response = requests.get(url)
        json_text = response.json()
    except Exception as e:
        print(e)
        json_text = ""
    return json_text


if __name__ == '__main__':
    app.run(debug=True)
