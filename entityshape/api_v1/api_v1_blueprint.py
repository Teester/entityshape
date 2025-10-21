from flask import Blueprint, request, json, Response

from entityshape.api_v1.shape import Shape
from entityshape.api_v1.compareshape import CompareShape

api_v1 = Blueprint('api_v1', __name__,)

@api_v1.route('/')
def v1():
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
        valid: dict = {}
        entity_shape: Shape = Shape(schema, language)
        comparison: CompareShape = CompareShape(entity_shape.get_schema_shape(), entity, language)
        payload: dict = {'schema': schema,
                         'name': entity_shape.get_name(),
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
    response: Response = Response(response=json.dumps(payload),
                                  status=status,
                                  mimetype="application/json")
    return response