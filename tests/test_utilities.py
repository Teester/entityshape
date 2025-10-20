import unittest

from entityshape.utilities import Utilities


class UtilitiesTests(unittest.TestCase):

    def setUp(self):
        self.utilities = Utilities()

    def test_calculate_necessity_with_nothing(self):
        prop = ""
        shape = {}
        test_method = self.utilities.calculate_necessity(prop, shape)
        self.assertEqual("absent", test_method)

    def test_calculate_necessity_with_values_with_required(self):
        prop = "P31"
        shape = {"type": "Shape",
                 "id": "test",
                 "expression": {
                     "type": "EachOf",
                     "expressions": [
                         {
                             "type": "TripleConstraint",
                             "predicate": "http://www.wikidata.org/prop/direct/P31"
                         }
                     ]
                 }
                 }
        necessity = self.utilities.calculate_necessity(prop, shape)
        self.assertEqual("required", necessity)

    def test_calculate_necessity_with_values_with_optional(self):
        prop = "P31"
        shape = {"type": "Shape",
                 "id": "test",
                 "expression": {
                     "type": "EachOf",
                     "expressions": [
                         {
                             "type": "TripleConstraint",
                             "predicate": "http://www.wikidata.org/prop/direct/P31",
                             "min": 0
                         }
                     ]
                 }
                 }
        test_method = self.utilities.calculate_necessity(prop, shape)
        self.assertEqual("optional", test_method)

    def test_calculate_necessity_with_values_with_absent(self):
        prop = "P32"
        shape = {"type": "Shape",
                 "id": "test",
                 "expression": {
                     "type": "EachOf",
                     "expressions": [
                         {
                             "type": "TripleConstraint",
                             "predicate": "http://www.wikidata.org/prop/direct/P31",
                             "min": 0
                         }
                     ]
                 }
                 }
        test_method = self.utilities.calculate_necessity(prop, shape)
        self.assertEqual("absent", test_method)

    def test_required_or_absent_with_nothing(self):
        expression = {}
        test_method = self.utilities.required_or_absent(expression)
        self.assertEqual("required", test_method)

    def test_required_or_absent_with_optional(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'min': 0,
                      }
        test_method = self.utilities.required_or_absent(expression)
        self.assertEqual("optional", test_method)

    def test_required_or_absent_with_required(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'min': 1,
                      }
        test_method = self.utilities.required_or_absent(expression)
        self.assertEqual("required", test_method)

    def test_required_or_absent_with_absent(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'min': 0,
                      'max': 0,
                      }
        test_method = self.utilities.required_or_absent(expression)
        self.assertEqual("absent", test_method)

    def test_process_cardinalities_with_nothing(self):
        expression = {}
        claim = {}
        test_method = self.utilities.process_cardinalities(expression, claim)
        self.assertEqual("not enough correct statements", test_method)

    def test_process_cardinalities_with_max(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'max': 0,
                      }
        claim = {'mainsnak':
                    {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '851b1c24539bd7aa725376baba4bcf0928099a66',
                     'datatype': 'wikibase-item'
                     }
                 }

        test_method = self.utilities.process_cardinalities(expression, claim)
        self.assertEqual("too many statements", test_method)

    def test_process_cardinalities_with_min(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'min': 0,
                      }
        claim = {'mainsnak':
                    {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '851b1c24539bd7aa725376baba4bcf0928099a66',
                     'datatype': 'wikibase-item'
                     }
                 }
        test_method = self.utilities.process_cardinalities(expression, claim)
        self.assertEqual("correct", test_method)

    def test_process_cardinalities_with_max_and_min(self):
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'min': 0,
                      'max': 0
                      }
        claim = {'mainsnak':
                    {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '851b1c24539bd7aa725376baba4bcf0928099a66',
                     'datatype': 'wikibase-item'
                     }
                 }
        test_method = self.utilities.process_cardinalities(expression, claim)
        self.assertEqual("too many statements", test_method)

    def test_process_node_constraint_incorrect(self):
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '851b1c24539bd7aa725376baba4bcf0928099a66',
                     'datavalue': {
                         'value': {
                             'entity-type': 'item',
                             'numeric-id': 110430875,
                             'id': 'Q110430875'},
                         'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'
                     }
        expression = {'type': 'NodeConstraint',
                      'values': ['http://www.wikidata.org/entity/Q5']
                      }
        test_method = self.utilities.process_node_constraint(statement, expression, "")
        self.assertEqual("incorrect", test_method)

    def test_process_node_constraint_nothing(self):
        statement = {}
        expression = {}
        test_method = self.utilities.process_node_constraint(statement, expression, "")
        self.assertEqual("", test_method)

    def test_process_node_constraint_correct(self):
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '851b1c24539bd7aa725376baba4bcf0928099a66',
                     'datavalue': {
                         'value': {
                             'entity-type': 'item',
                             'numeric-id': 110430875,
                             'id': 'Q5'},
                         'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'
                     }
        expression = {'type': 'NodeConstraint',
                      'values': ['http://www.wikidata.org/entity/Q5']
                      }
        test_method = self.utilities.process_node_constraint(statement, expression, "")
        self.assertEqual("correct", test_method)


if __name__ == '__main__':
    unittest.main()
