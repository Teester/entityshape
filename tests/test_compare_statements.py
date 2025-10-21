import unittest

from entityshape.api_v2.comparejsonld import CompareStatements


class TestCompareStatements(unittest.TestCase):
    def setUp(self):
        entities = {"entities":
                        {'Q1':
                            {'title': 'Q1',
                             'type': 'item',
                             'id': 'Q1',
                             'claims': {'P31': [{'mainsnak':
                                                     {'snaktype': 'value',
                                                      'property': 'P31',
                                                      'hash': '1',
                                                      'datavalue': {'value':
                                                                        {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                                                    'type': 'wikibase-entityid'},
                                                      'datatype': 'wikibase-item'},
                                                 'type': 'statement',
                                                 'id': '1',
                                                 'rank': 'normal'}],
                                        },
                             'sitelinks': {}}}}
        entity = "Q1"
        statement = {"type": "Shape",
                     "id": "test",
                     "expression": {
                         "type": "EachOf",
                         "expressions": [
                             {
                                 "type": "TripleConstraint",
                                 "predicate": "http://www.wikidata.org/prop/direct/P31"
                             }
                         ]
                     }}
        self.compare_statements = CompareStatements(entities, entity, statement)

    def test_compare_statements_with_nothing(self):
        entities = {}
        entity = ""
        statement = {}
        test_method = CompareStatements(entities, entity, statement)
        self.assertEqual({}, test_method.compare_statements())

    def test_compare_statements(self):
        result = {'1': {'necessity': 'required',
                        'property': 'P31',
                        'response': 'allowed'}}
        self.assertEqual(result, self.compare_statements.compare_statements())

    def test_process_shape_with_nothing(self):
        statement = {}
        shape = {}
        child = {}
        child, allowed = self.compare_statements._process_shape(statement, shape, child)
        self.assertEqual({"response": "not in schema"}, child)
        self.assertEqual("not in schema", allowed)

    def test_process_shape_with_values(self):
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '1',
                     'datavalue': {'value':
                                      {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                   'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'}
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
                 }}
        child = {}
        child, allowed = self.compare_statements._process_shape(statement, shape, child)
        self.assertEqual({"response": "allowed"}, child)
        self.assertEqual("allowed", allowed)

    def test_process_expressions_with_nothing(self):
        expression = {}
        shape = {}
        statement = {}
        allowed = ""
        self.assertEqual("", self.compare_statements.process_expressions(expression, shape, statement, allowed))

    def test_process_expressions_with_values(self):
        expression = {"type": "TripleConstraint",
                      "predicate": "http://www.wikidata.org/prop/direct/P31"
                      }
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
                 }}
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '1',
                     'datavalue': {'value':
                                      {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                   'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'}
        allowed = "allowed"
        self.assertEqual("allowed", self.compare_statements.process_expressions(expression, shape, statement, allowed))

    def test_process_triple_constraint_with_nothing(self):
        statement = {}
        expression = {}
        allowed = ""
        self.assertEqual("", self.compare_statements._process_triple_constraint(statement, expression, allowed))

    def test_process_triple_constraint_with_values(self):
        expression = {"type": "TripleConstraint",
                      "predicate": "http://www.wikidata.org/prop/direct/P31"
                      }
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '1',
                     'datavalue': {'value':
                                      {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                   'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'}
        allowed = "allowed"
        self.assertEqual("allowed", self.compare_statements._process_triple_constraint(statement, expression, allowed))


if __name__ == '__main__':
    unittest.main()
