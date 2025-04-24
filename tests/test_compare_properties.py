import unittest

from comparejsonld import CompareProperties


class TestCompareProperties(unittest.TestCase):
    def setUp(self):
        entity = {'entities':
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
        entities = "Q1"
        statement = {  "type": "Shape",
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
        props = ["P31"]
        names = {"P31" : "instance of"}
        self.compare_properties =  CompareProperties(entities, entity, props, names, statement)

    def test_compare_properties_with_nothing(self):
        entity = {}
        entities = ""
        statement = {}
        props = []
        names = {}
        test_method =  CompareProperties(entities, entity, props, names, statement)
        self.assertEqual({}, test_method.compare_properties())

    def test_compare_properties_with_values(self):
        result = {'P31': {'name': 'instance of',
                          'necessity': 'required',
                          'response': 'present'}}
        self.assertEqual(result, self.compare_properties.compare_properties())

    def test_check_claims_for_prop_with_nothing(self):
        claims = {}
        prop = ""
        self.assertEqual('not enough correct statements', self.compare_properties.check_claims_for_props(claims, prop))

    def test_check_claims_for_prop_with_values(self):
        claims = {'Q1':
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
                       'sitelinks': {}}}
        prop = "P31"
        self.assertEqual('not enough correct statements', self.compare_properties.check_claims_for_props(claims, prop))

    def test_get_allowed_list_with_nothing(self):
        claims = {}
        prop = ""
        expression = {}
        self.assertEqual([], self.compare_properties._get_allowed_list(claims, prop, expression))

    def test_get_allowed_list_with_values(self):
        claims = {'Q1':
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
                       'sitelinks': {}}}
        prop = "P31"
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}}
        self.assertEqual([], self.compare_properties._get_allowed_list(claims, prop, expression))

    def test_process_cardinalities_with_nothing(self):
        expression = {}
        shape = {}
        prop = ""
        allowed = []
        self.assertEqual("", self.compare_properties._process_cardinalities(expression, allowed, shape, prop))

    def test_process_cardinalities_with_values(self):
        expression = {'snaktype': 'value',
                      'property': 'P31',
                      'hash': '1',
                      'datavalue': {'value':
                                        {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                    'type': 'wikibase-entityid'},
                      'datatype': 'wikibase-item'}
        shape = {'type': 'TripleConstraint',
                 'predicate': 'http://www.wikidata.org/prop/direct/P31',
                 'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}}
        prop = "P31"
        allowed = ["Q5"]
        self.assertEqual("", self.compare_properties._process_cardinalities(expression, allowed, shape, prop))

    def test_get_cardinalities_with_nothing(self):
        occurrences = 1
        expression = {}
        self.assertEqual("correct", self.compare_properties._get_cardinalities(occurrences, expression))

    def test_get_cardinalities_with_values(self):
        occurrences = 1
        expression = {'snaktype': 'value',
                      'property': 'P31',
                      'hash': '1',
                      'datavalue': {'value':
                                        {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                    'type': 'wikibase-entityid'},
                      'datatype': 'wikibase-item'}
        self.assertEqual("correct", self.compare_properties._get_cardinalities(occurrences, expression))

    def test_process_triple_constraint_with_nothing(self):
        statement = {}
        expression = {}
        allowed = ""
        self.assertEqual("", self.compare_properties._process_triple_constraint(statement, expression, allowed))

    def test_process_triple_constraint_with_values(self):
        statement = {'snaktype': 'value',
                     'property': 'P31',
                     'hash': '1',
                     'datavalue': {'value':
                                       {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q2'},
                                   'type': 'wikibase-entityid'},
                     'datatype': 'wikibase-item'}
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q2']}}
        allowed = "Q2"
        self.assertEqual("correct", self.compare_properties._process_triple_constraint(statement, expression, allowed))


if __name__ == '__main__':
    unittest.main()
