from flask import Blueprint, request, Response, json

from api_v3 import comparejsonld
from api_v3.comparejsonld import CompareJSONLD
from api_v3.compareshape import WikidataShExValidator
from entityshape.api_v2.getjsonld import JSONLDShape

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
    language: str = request.args.get("language", type=str)
    try:
        valid: dict = {}
        names: list = []
        general: list = []
        properties: list = []
        statements: list = []
        compare = CompareJSONLD(schema, entity, "en")
        nt = compare.get_properties()
        for schema in schema_list:
            shape: JSONLDShape = JSONLDShape(schema, language)
            print(shape.get_json_ld())
            comparison: WikidataShExValidator = WikidataShExValidator(json.dumps(shape.get_json_ld()))
            comparison.load_ntriples(nt)
            result = comparison.validate_node(focus_node= entity,
                                               start_shape_id= comparison.schema["start"])
            print(json.dumps(result, indent=2))
        payload: dict = {'schema': schema_list,
                         'name': '',
                         'validity': result["status"],
                         'general': [],
                         'properties': [],
                         'statements': [],
                         'error': ""}
        print(f"payload = {payload}")
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
    response: Response = Response( response=json.dumps(payload),
                                   status=status,
                                   mimetype="application/json")
    return response