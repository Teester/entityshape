import unittest

import requests

from app import app


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        app.config["TESTING"] = True
        self.app = app.test_client()

    def tearDown(self) -> None:
        # We don't need to tear anything down after the test
        pass

    def test_specific_wikidata_item_against_schema(self):
        """
        Tests a specific entity against a certain schema and checks that
        a statements and a properties response are returned
        """
        test_pairs: dict = {"E236": "Q1728820"}

        for key in test_pairs:
            with self.subTest(key=key):
                value = test_pairs[key]
                response = self.app.get(f'/api?entityschema={key}&entity={value}&language=en',
                                        follow_redirects=True)
                self.assertIsNotNone(response.json["statements"])
                self.assertIsNotNone(response.json["properties"])

    def test_lexical_category(self):
        """
        This test checks that a lexicalCategory response is returned when a
        lexeme is tested against a schema looking for a lexical category
        """
        test_pairs: dict = {"E56": "Lexeme:L42"}
        for key in test_pairs:
            with self.subTest(key=key):
                value = test_pairs[key]
                response = self.app.get(f'/api?entityschema={key}&entity={value}&language=en',
                                        follow_redirects=True)
                self.assertIsNotNone(response.json["general"]["lexicalCategory"])
                self.assertIsNotNone(response.json["general"]["language"])

    def test_wikidata_entityschemas(self) -> None:
        """
        This test iterates through each entityschema on wikidata and checks to see that
        each one returns a "200" code when compared with a specific entity
        The "200" code tells us that the entityschema was successfully compared
        with the entity, but not whether it passes or not.  This will give us a list of
        entityschemas that we have problems with.  This may be due to a bug in entityshape
        or a problem with the entityschema itself.
        """
        skips: list = ["E1", "E16", "E39", "E53", "E55", "E59",
                       "E70", "E89", "E93", "E165",
                       "E245", "E246", "E247", "E251", "E252",
                       "E999"]
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

    def test_specific_entityschema(self) -> None:
        """
        This test tests a specified schema against an entity and checks that a 200 response
        is received
        """
        schema: str = "E236"
        response = self.app.get(f'/api?entityschema={schema}&entity=Q100532807&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Member of the Oireachtas", response.json["name"])
        self.assertEqual({'name': 'occupation', 'necessity': 'required', 'response': 'missing'}, response.json["properties"]["P106"])


if __name__ == '__main__':
    unittest.main()
