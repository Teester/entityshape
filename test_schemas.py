import unittest

import requests

from app import app


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.config["TESTING"] = True
        self.app = app.test_client()

    def tearDown(self) -> None:
        pass

    # This test iterates through each entityschema on wikidata and checks to see that
    # each one returns a "200" code when compared with a specific entity
    # The "200" code tells us that the entityschema was successfully compared
    # with the entity, but not whether it passes or not.  This will give us a list of
    # entityschemas that we have problems with.  This may be due to a bug in entityshape
    # or a problem with the entityschema itself.
    def test_something(self):
        url: str = "https://www.wikidata.org/w/api.php?" \
                   "action=query&format=json&list=allpages&aplimit=max&apnamespace=640"
        response = requests.get(url)
        json_text: dict = response.json()
        entity_schemas: list = []
        for schema in json_text["query"]["allpages"]:
            entity_schemas.append(schema["title"][13:])
        for schema in entity_schemas:
            with self.subTest(schema=schema):
                response = self.app.get(f'/api?entityschema={schema}&entity=Q100532807&language=en',
                                        follow_redirects=True)
                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
