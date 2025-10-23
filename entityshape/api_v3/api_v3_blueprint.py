from flask import Blueprint, request, json, Response

from entityshape.api_v3.getjsonld import JSONLDShape
from entityshape.api_v3.comparejsonld import CompareJSONLD


api_v3 = Blueprint('api_v3', __name__,)

@api_v3.route('/')
def v3():
    """
    Compares an entityschema with a wikidata item
    :return: a response to the query
    """
    schema: str = request.args.get("entityschema", type=str)
    schema_list: list = schema.split(', ')
    entity: str = request.args.get("entity", type=str)
    if "Lexeme" in entity:
        entity = entity[7:]
    try:
        valid: dict = {}
        names: list = []
        general: list = []
        properties: list = []
        statements: list = []
        for schema in schema_list:
            shape: JSONLDShape = JSONLDShape(schema)
            comparison: CompareJSONLD = CompareJSONLD(shape.get_json_ld(), entity)
            names.append(schema)
            general.append(comparison.get_general())
            properties.append(comparison.get_properties())
            statements.append(comparison.get_statements())
        payload: dict = {'schema': schema_list,
                         'name': names,
                         'validity': valid,
                         'general': general,
                         'properties': properties,
                         'statements': statements,
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
    response: Response = Response(response=json.dumps(payload),
                                  status=status,
                                  mimetype="application/json")
    return response