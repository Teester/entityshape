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
                       "E70", "E89", "E93", "E123", "E165",
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
        self.assertEqual({'name': 'occupation', 'necessity': 'required', 'response': 'missing'},
                         response.json["properties"]["P106"])

    def test_entityschema_e236(self):
        """
        This test tests entityschema E236 (Member of the Oireachtas) against entity
        Q1728820 (Leo Varadkar).  All properties in the schema should pass
        """
        response = self.app.get(f'/api?entityschema=E236&entity=Q1728820&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)
        properties: list = ["P102", "P18", "P31", "P734", "P735", "P39", "P21",
                            "P27", "P106", "P569", "P4690"]
        for prop in properties:
            with self.subTest(prop=prop):
                self.assertTrue(response.json["properties"][prop]["response"] in ["correct", "present"])

    def test_entityschema_e297(self):
        """
        This test tests entityschema E297 (sailboat class) against entity
        Q97179551 (J/92s).  The schema has multiple statements about the same property.
        The test checks to ensure that the correct cardinality is calculated for
        the relevant property
        """
        response = self.app.get(f'/api?entityschema=E297&entity=Q97179551&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)
        properties: list = ["P2043", "P2067"]
        for prop in properties:
            with self.subTest(prop=prop):
                self.assertTrue(response.json["properties"][prop]["response"] in ["correct", "present"])

    def test_entityschema_e295(self):
        """
        This test tests entityschema E295 (townland) against entity Q85396849 (Drumlohan).
        The schema has a P361 (part of) with a cardinality of 0, meaning the item should
        not contain any P361.  The test checks that the response is false for this item
        """
        response = self.app.get(f'/api?entityschema=E295&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)
        properties: list = ["P361"]
        for prop in properties:
            with self.subTest(prop=prop):
                self.assertTrue(response.json["properties"][prop]["response"] in ["too many statements"])
                self.assertTrue(response.json["properties"][prop]["necessity"] in ["absent"])


if __name__ == '__main__':
    unittest.main()
