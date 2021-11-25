"""
Tests to test results from comparejsonld.py match those from comparejson.py
"""
import unittest

from comparejsonld import CompareJSONLD
from compareshape import CompareShape
from shape import Shape


class JSONLDCase(unittest.TestCase):
    """
    Testcases to test results from comparejsonld.py match those from comparejson.py
    """
    def setUp(self) -> None:
        language: str = "en"
        schema: str = "E236"
        entity: str = "Q1728820"
        shape: Shape = Shape(schema, language)
        self.comparison: CompareShape = CompareShape(shape.get_schema_shape(), entity, language)
        self.comparison2: CompareJSONLD = CompareJSONLD(shape.get_json_ld(), entity, language)

    def tearDown(self) -> None:
        # We don't need to tear anything down after the test
        pass

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
            self.assertEqual(self.comparison.get_properties()[prop]["response"],
                             self.comparison2.get_properties()[prop]["response"])

    def test_compare_property_p21(self) -> None:
        """
        tests to see that the P21 property is assessed the same in both cases

        :return: Nothing
        """
        self.assertEqual(self.comparison.get_properties()["P21"],
                         self.comparison2.get_properties()["P21"])


if __name__ == '__main__':
    unittest.main()
