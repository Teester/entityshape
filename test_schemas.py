import unittest

import requests

from app import app


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.config["TESTING"] = True
        self.app = app.test_client()

    def tearDown(self) -> None:
        pass

    def test_specific_wikidata_item_against_schema(self):
        test_pairs: dict = {"E236" : "Q1728820"}

        for key in test_pairs:
            with self.subTest(key=key):
                value = test_pairs[key]
                response = self.app.get(f'/api?entityschema={key}&entity={value}&language=en',
                                        follow_redirects=True)
                self.assertIsNotNone(response.json["statements"])
                self.assertIsNotNone(response.json["properties"])

    # This test iterates through each entityschema on wikidata and checks to see that
    # each one returns a "200" code when compared with a specific entity
    # The "200" code tells us that the entityschema was successfully compared
    # with the entity, but not whether it passes or not.  This will give us a list of
    # entityschemas that we have problems with.  This may be due to a bug in entityshape
    # or a problem with the entityschema itself.
    def test_wikidata_entityschemas(self):
        skips: list = [ "E1", "E2", "E3", "E16", "E37", "E38", "E39", "E44", "E49", "E53", "E55", "E59",  
                        "E70", "E72", "E74", "E75", "E86", "E87", "E89", "E90", "E93", "E99", "E100",
                        "E103", "E117", "E118", "E128", "E129", "E132", "E150", "E165", "E166", "E169",
                        "E176", "E183", "E187", "E194", "E226", "E227", "E245", "E246", "E247", "E251",
                        "E252", "E258", "E259", "E261", "E262", "E263", "E265", "E266", "E269", "E999",
                        "E12345" ]
        url: str = "https://www.wikidata.org/w/api.php?" \
                   "action=query&format=json&list=allpages&aplimit=max&apnamespace=640"
        response = requests.get(url)
        json_text: dict = response.json()
        entity_schemas: list = []
        for schema in json_text["query"]["allpages"]:
            entity_schemas.append(schema["title"][13:])
        for schema in entity_schemas:
            with self.subTest(schema=schema):
                if schema in skips:
                    self.skipTest(f"Schema {schema} not supported")
                response = self.app.get(f'/api?entityschema={schema}&entity=Q100532807&language=en',
                                        follow_redirects=True)
                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
