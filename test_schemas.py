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
        Tests all wikidata entityschemas return 200

        This test iterates through each entityschema on wikidata and checks to see that
        each one returns a "200" code when compared with a specific entity
        The "200" code tells us that the entityschema was successfully compared
        with the entity, but not whether it passes or not.  This will give us a list of
        entityschemas that we have problems with.  This may be due to a bug in entityshape
        or a problem with the entityschema itself.
        """
        skips: list = ["E59", "E70", "E93", "E123", "E165",
                       "E245", "E246", "E247", "E251", "E999"]
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
                print(schema)
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
        Tests all properties of Q1728820 pass E236

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
        Tests item with repeated properties works correctly

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
        Tests item with cardinality of 0 evaluates correctly

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

    def test_entityschema_e126(self):
        """
        Tests that a comment line # without a space after passes

        This test tests entityschema E126 against entity Q85396849.
        The schema has a comment line that starts with #{ rather than # {.
        The test checks that we get a 200 response
        """
        response = self.app.get(f'/api?entityschema=E126&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)

    def test_entityschema_e278(self):
        """
        Tests that {} containing non cardinalities arent evaluated as cardinalities

        This test tests entityschema E278 against entity Q85396849 (Drumlohan).
        The schema contains a line ps:P279 { wdt:P31 wd:Q67101749 }.  The test makes
        sure that we get a 200 and that the contents of the {} aren't
        evaluated as a cardinality
        """
        response = self.app.get(f'/api?entityschema=E278&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)

    def test_entityschema_e3(self):
        """
        Tests that shapes with [] are evaluated

        This test tests entityschema E3 against entity Q85396849 (Drumlohan).
        The schema has a shape <wikimedia_projects> [ ].  The test makes sure
        that the schema returns a 200 response, indicating that it evaluates []
        """
        response = self.app.get(f'/api?entityschema=E3&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)

    def test_entityschema_e176(self):
        """
        Tests that where <shape> and { are on different lines, it works

        This test tests entityschema E176 against entity Q85396849 (Drumlohan).
        The schema contains a shape where the name and { are on different lines.
        The test checks that this evaluates correctly
        """
        response = self.app.get(f'/api?entityschema=E176&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)

    def test_entityschema_e187(self):
        """
        Tests that shapes with no brackets work

        This test tests entityschema E187 against entity Q85396849 (Drumlohan).
        The schema has a shape of the form <shape> geo:Literal.  The test
        makes sure that this evaluates
        """
        response = self.app.get(f'/api?entityschema=E187&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)

    def test_entityschema_e275(self):
        """
        Tests that schemas importing other schemas don't fail

        This test tests entityschema E275 against entity Q85396849 (Drumlohan).
        The schema imports another schema and references it. The test makes sure
        that this still returns a 200 response
        """
        response = self.app.get(f'/api?entityschema=E275&entity=Q85396849&language=en',
                                follow_redirects=True)
        self.assertEqual(200, response.status_code)


if __name__ == '__main__':
    unittest.main()
