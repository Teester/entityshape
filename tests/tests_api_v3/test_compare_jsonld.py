import unittest

from api_v3.comparejsonld import CompareJSONLD


class CompareJSONLDCase(unittest.TestCase):
    def setUp(self):
        self.compare_json_ld = CompareJSONLD({}, "", "en")

    def test_get_props_with_nothing(self):
        self.assertEqual([], self.compare_json_ld._get_props())

    def test_get_props_with_values(self):
        self.assertEqual([], self.compare_json_ld._get_props())

    def test_get_property_names_with_nothing(self):
        self.assertEqual({}, self.compare_json_ld._get_property_names("en"))

    def test_get_property_names_with_values(self):
        self.assertEqual({}, self.compare_json_ld._get_property_names("en"))


if __name__ == '__main__':
    unittest.main()
