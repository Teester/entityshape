"""
Tests to test results from comparejsonld.py match those from comparejson.py
"""
import os
import json
import re
import unittest
from unittest.mock import patch, MagicMock

from entityshape.api_v2.comparejsonld import CompareJSONLD
from entityshape.api_v1.compareshape import CompareShape
from entityshape.api_v1.shape import Shape
from entityshape.api_v2.getjsonld import JSONLDShape


class JSONLDTests(unittest.TestCase):
    """
    Testcases to test results from comparejsonld.py match those from comparejson.py
    """
    @classmethod
    def setUpClass(cls) -> None:
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        cls.fixture_path = os.path.join(parent_dir, 'fixtures')

        cls.patcher_item_v1 = patch('entityshape.api_v1.compareshape.requests.get')
        cls.patcher_schema_v1 = patch('entityshape.api_v1.shape.requests.get')
        cls.patcher_item_v2 = patch('entityshape.api_v2.comparejsonld.requests.get')
        cls.patcher_schema_v2 = patch('entityshape.api_v2.getjsonld.requests.get')
        
        cls.mock_item_v1 = cls.patcher_item_v1.start()
        cls.mock_schema_v1 = cls.patcher_schema_v1.start()
        cls.mock_item_v2 = cls.patcher_item_v2.start()
        cls.mock_schema_v2 = cls.patcher_schema_v2.start()

        cls.mock_item_v1.side_effect = cls.dynamic_mock_response
        cls.mock_schema_v1.side_effect = cls.dynamic_mock_response
        cls.mock_item_v2.side_effect = cls.dynamic_mock_response
        cls.mock_schema_v2.side_effect = cls.dynamic_mock_response

        language: str = "en"
        schema: str = "E236"
        entity: str = "Q1728820"
        shape: Shape = Shape(schema, language)
        shape2: JSONLDShape = JSONLDShape(schema, language)
        cls.comparison: CompareShape = CompareShape(shape.get_schema_shape(), entity, language)
        cls.comparison2: CompareJSONLD = CompareJSONLD(shape2.get_json_ld(), entity, language)

    @classmethod
    def tearDownClass(cls) -> None:
        # Stop the patchers when the class is finished
        cls.patcher_item_v1.stop()
        cls.patcher_schema_v1.stop()
        cls.patcher_item_v2.stop()
        cls.patcher_schema_v2.stop()

    @staticmethod
    def dynamic_mock_response(url, *args, **kwargs):
        """Smart resolver to find JSON fixtures by ID"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        if url == "https://www.wikidata.org/w/api.php":
            target_id = "names"
        # Extract ID from URL (e.g., E236 or Q1728820)
        match = re.search(r'([EQ]\d+)', url)
        if match:
            target_id = match.group(1)
            # Re-calculating path inside static method
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        fixture_file = os.path.join(parent_dir, 'fixtures', f"{target_id}.json")
        
        if os.path.exists(fixture_file):
            with open(fixture_file, 'r') as f:
                mock_resp.json.return_value = json.load(f)
            return mock_resp
        
        mock_resp.status_code = 404
        return mock_resp

    def test_compare_property_names(self) -> None:
        """
        tests to see if the names of the properties are the same in both cases

        :return: Nothing
        """
        for prop in self.comparison.get_properties():
            self.assertEqual(self.comparison.get_properties()[prop]["name"],
                             self.comparison2.get_properties()[prop]["name"])

    def test_compare_property_necessity(self) -> None:
        """
        tests to see if the necessity of the properties are the same in both cases

        :return: Nothing
        """
        for prop in self.comparison.get_properties():
            self.assertEqual(self.comparison.get_properties()[prop]["necessity"],
                             self.comparison2.get_properties()[prop]["necessity"])

    def test_compare_property_response(self) -> None:
        """
        tests to see if the response of the properties are the same in both cases

        :return: Nothing
        """
        for prop in self.comparison.get_properties():
            if "response" in self.comparison2.get_properties()[prop]:
                self.assertEqual(self.comparison.get_properties()[prop]["response"],
                                 self.comparison2.get_properties()[prop]["response"])

    def test_compare_property_p21(self) -> None:
        """
        tests to see that the P21 property is assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_properties()["P21"],
                         self.comparison2.get_properties()["P21"])

    def test_compare_property_p734(self) -> None:
        """
        tests to see that the P734 property is assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_properties()["P734"],
                         self.comparison2.get_properties()["P734"])

    def test_compare_properties(self) -> None:
        """
        tests to see that the properties are assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_properties(),
                         self.comparison2.get_properties())

    def test_compare_statements(self) -> None:
        """
        tests to see that the statements are assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_statements(),
                         self.comparison2.get_statements())

    def test_compare_statement_property(self) -> None:
        """
        tests to see if the names of the properties are the same in both cases

        :return: Nothing
        """
        for statement in self.comparison.get_statements():
            self.assertEqual(self.comparison.get_statements()[statement]["property"],
                             self.comparison2.get_statements()[statement]["property"])

    def test_compare_statement_necessity(self) -> None:
        """
        tests to see if the necessity of the properties are the same in both cases

        :return: Nothing
        """
        for statement in self.comparison.get_statements():
            if "necessity" in self.comparison2.get_statements()[statement]:
                self.assertEqual(self.comparison.get_statements()[statement]["necessity"],
                                 self.comparison2.get_statements()[statement]["necessity"])

    def test_compare_statement_response(self) -> None:
        """
        tests to see if the response of the properties are the same in both cases

        :return: Nothing
        """
        for statement in self.comparison.get_statements():
            if "response" in self.comparison2.get_statements()[statement]:
                self.assertEqual(self.comparison.get_statements()[statement]["response"],
                                 self.comparison2.get_statements()[statement]["response"])

    def test_compare_general(self) -> None:
        """
        tests to see that general is assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_general(),
                         self.comparison2.get_general())


if __name__ == '__main__':
    unittest.main()
