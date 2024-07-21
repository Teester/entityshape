"""
Tests to test wikidata entityschemas against wikidata items
"""
import time
import unittest

from comparejsonld import CompareJSONLD
from comparejsonld2 import CompareJSONLD2
from compareshape import CompareShape
from shape import Shape


class TestV3Schemas(unittest.TestCase):
    """
    Testcases to test wikidata entityschemas against wikidata items
    """

    def test_shape(self):
        shape = Shape("E438", "en")
        tic = time.perf_counter()
        for _ in range(10):
            shape.get_schema_shape()
        tac = time.perf_counter()
        for _ in range(10):
            shape.get_json_ld()
        toe = time.perf_counter()
        print(f"Time for shape: {tac - tic}s")
        print(f"Time for json_ld: {toe - tac}s")
        self.assertLess((toe - tac), (tac - tic))

    def test_comparison(self):
        shape: Shape = Shape("E438", "en")
        compare_shape = CompareShape(shape.get_schema_shape(), "Q11645745", "en")
        compare_json_ld = CompareJSONLD(shape.get_json_ld(), "Q11645745", "en")
        compare_json_ld2 = CompareJSONLD2(shape.get_json_ld(), "Q11645745", "en")
        tea = time.perf_counter()
        for _ in range(10):
            compare_shape.get_properties()
        tic = time.perf_counter()
        for _ in range(10):
            compare_json_ld.get_properties()
        tac = time.perf_counter()
        for _ in range(10):
            compare_json_ld2.get_properties()
        toe = time.perf_counter()
        print(f"Time for v1: {tic-tea}s")
        print(f"Time for v2: {tac-tic}s")
        print(f"Time for v3: {toe-tac}s")
        self.assertLess((toe-tac), (tac-tic))


if __name__ == '__main__':
    unittest.main()
