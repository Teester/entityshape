import unittest

from entityshape.app import app

class v3_tests(unittest.TestCase):
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
                response = self.app.get(f'/api/v3?entityschema={key}&entity={value}&language=en',
                                        follow_redirects=True)
                print(f"response = {response.json}")
                self.assertIsNotNone(response.json["statements"])
                self.assertIsNotNone(response.json["properties"])