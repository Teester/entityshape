"""
A Flask app to compare entityschema with wikidata items without using SPARQL
"""
from flask import Flask
from flask_cors import CORS

from api_v1.api_v1_blueprint import api_v1
from api_v2.api_v2_blueprint import api_v2

app = Flask(__name__)
CORS(app)

app.register_blueprint(api_v1, url_prefix="/api")
app.register_blueprint(api_v2, url_prefix="/api/v2")


if __name__ == '__main__':
    app.run()
