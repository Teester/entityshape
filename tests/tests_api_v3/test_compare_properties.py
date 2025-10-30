import unittest

from entityshape.api_v3.comparejsonld import CompareProperties


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
        statement = {"type": "Schema",
                     "start": "test",
                     "shapes": [{
                         "type": "Shape",
                         "id": "test",
                         "expression": {
                             "type": "EachOf",
                             "expressions": [{
                                 "type": "TripleConstraint",
                                 "predicate": "http://www.wikidata.org/prop/direct/P31" }]
                             }
                         }]
                     }
        props = ["P31"]
        names = {"P31": "instance of"}
        self.compare_properties = CompareProperties(entities, entity, props, statement, names)

    def test_compare_properties_with_nothing(self):
        entity = {}
        entities = ""
        statement = {}
        props = []
        names = {}
        test_method = CompareProperties(entities, entity, props, statement, names)
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

    def test_process_triple_constraint_2_with_nothing(self):
        statement = {}
        expression = {}
        allowed = ""
        self.assertEqual("", self.compare_properties._process_triple_constraint_2(statement, expression, allowed))

    def test_process_triple_constraint_2_with_values(self):
        statement = {'title': 'Q1',
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
                                }
                     }
        expression = {'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q2']}}
        allowed = "Q2"
        self.assertEqual("correct", self.compare_properties._process_triple_constraint_2(statement, expression, allowed))


    def test_each_of_without_each_of(self):
        statement = {'title': 'Q1',
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
                     'sitelinks': {}}
        expression = [{'type': 'TripleConstraint',
                      'predicate': 'http://www.wikidata.org/prop/direct/P31',
                      'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q2']}}]
        self.assertEqual("correct", self.compare_properties._process_each_of(expression, statement))

    def test_each_of_with_each_of(self):
        statement = {'title': 'Q1',
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
                      'sitelinks': {}}
        expression = [{'type': 'TripleConstraint',
                        'predicate': 'http://www.wikidata.org/prop/direct/P31',
                        'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q2']}},
                      {'type': 'TripleConstraint',
                       'predicate': 'http://www.wikidata.org/prop/direct/P31',
                       'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q1']}}
                      ]
        self.assertEqual("incorrect", self.compare_properties._process_each_of(expression, statement))

    def test_complete_schema_against_process_shape(self):
        schema = {'type': 'Schema',
                  'start': 'TD',
                  'shapes': [
                      {'type': 'Shape',
                       'id': 'TD',
                       'extra': ['http://www.wikidata.org/prop/direct/P39',
                                 'http://www.wikidata.org/prop/direct/P106',
                                 'http://www.wikidata.org/prop/direct/P27'],
                       'expression': {
                           'type': 'EachOf',
                           'expressions': [
                               {'type': 'TripleConstraint',
                                'predicate': 'http://www.wikidata.org/prop/direct/P31',
                                'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P4690'},
                               {'type': 'TripleConstraint',
                                'predicate': 'http://www.wikidata.org/prop/direct/P39',
                                'valueExpr': {'type': 'NodeConstraint',
                                              'values': ['http://www.wikidata.org/entity/Q654291', 'http://www.wikidata.org/entity/Q18043391']},
                                'min': 1,
                                'max': -1},
                               {'type': 'TripleConstraint',
                                'predicate': 'http://www.wikidata.org/prop/direct/P106',
                                'valueExpr': {'type': 'NodeConstraint',
                                              'values': ['http://www.wikidata.org/entity/Q82955']}},
                               {'type': 'TripleConstraint',
                                'predicate': 'http://www.wikidata.org/prop/direct/P734', 'min': 1, 'max': -1},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P735', 'min': 1, 'max': -1},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P569'},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P102', 'min': 0, 'max': -1},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P21',
                                'valueExpr': {'type': 'NodeConstraint',
                                              'values': ['http://www.wikidata.org/entity/Q6581097', 'http://www.wikidata.org/entity/Q6581072', 'http://www.wikidata.org/entity/Q1097630', 'http://www.wikidata.org/entity/Q1052281', 'http://www.wikidata.org/entity/Q2449503', 'http://www.wikidata.org/entity/Q48270']}},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P27',
                                'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q27', 'http://www.wikidata.org/entity/Q31747', 'http://www.wikidata.org/entity/Q1140152']},
                                'min': 1, 'max': -1},
                               {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P18', 'min': 1, 'max': -1}]}}]}
        entity = {'title': 'Q1',
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
                  'sitelinks': {}}
        self.assertEqual("incorrect", self.compare_properties._process_shape(schema, entity))

    def test_shape_against_process_shape2(self):
        schema = {"type": "Schema", "start": "TD", "shapes": [{'type': 'Shape',
                'id': 'TD',
                'extra': ['http://www.wikidata.org/prop/direct/P39',
                          'http://www.wikidata.org/prop/direct/P106',
                          'http://www.wikidata.org/prop/direct/P27'],
                'expression': {
                    'type': 'EachOf',
                    'expressions': [
                        {'type': 'TripleConstraint',
                         'predicate': 'http://www.wikidata.org/prop/direct/P31',
                         'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P4690'},
                        {'type': 'TripleConstraint',
                         'predicate': 'http://www.wikidata.org/prop/direct/P39',
                         'valueExpr': {'type': 'NodeConstraint',
                                       'values': ['http://www.wikidata.org/entity/Q654291', 'http://www.wikidata.org/entity/Q18043391']},
                         'min': 1,
                         'max': -1},
                        {'type': 'TripleConstraint',
                         'predicate': 'http://www.wikidata.org/prop/direct/P106',
                         'valueExpr': {'type': 'NodeConstraint',
                                       'values': ['http://www.wikidata.org/entity/Q82955']}},
                        {'type': 'TripleConstraint',
                         'predicate': 'http://www.wikidata.org/prop/direct/P734', 'min': 1, 'max': -1},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P735', 'min': 1, 'max': -1},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P569'},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P102', 'min': 0, 'max': -1},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P21',
                         'valueExpr': {'type': 'NodeConstraint',
                                       'values': ['http://www.wikidata.org/entity/Q6581097', 'http://www.wikidata.org/entity/Q6581072', 'http://www.wikidata.org/entity/Q1097630', 'http://www.wikidata.org/entity/Q1052281', 'http://www.wikidata.org/entity/Q2449503', 'http://www.wikidata.org/entity/Q48270']}},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P27',
                         'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q27', 'http://www.wikidata.org/entity/Q31747', 'http://www.wikidata.org/entity/Q1140152']},
                         'min': 1, 'max': -1},
                        {'type': 'TripleConstraint', 'predicate': 'http://www.wikidata.org/prop/direct/P18', 'min': 1, 'max': -1}]}}]}
        entity = {'title': 'Q1',
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
                  'sitelinks': {}}
        props = ["P31"]
        names = {"P31": "instance of"}
        compare_properties2 = CompareProperties(entity["id"], entity, props, schema, names)
        self.assertEqual("incorrect", compare_properties2._process_shape(schema, entity))

    def test_triple_constraint_against_process_shape2_which_fails(self):
        schema = {'type': 'TripleConstraint',
                 'predicate': 'http://www.wikidata.org/prop/direct/P31',
                 'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}}
        entity = {'title': 'Q1',
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
                  'sitelinks': {}}
        self.assertEqual("not enough correct statements", self.compare_properties._process_shape(schema, entity))


    def test_triple_constraint_against_process_shape2_which_passes(self):
        schema = {'type': 'TripleConstraint',
                 'predicate': 'http://www.wikidata.org/prop/direct/P31',
                 'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']} }
        entity = {'title': 'Q1',
                  'type': 'item',
                  'id': 'Q1',
                  'claims': {'P31': [{'mainsnak':
                                          {'snaktype': 'value',
                                           'property': 'P31',
                                           'hash': '1',
                                           'datavalue': {'value':
                                                             {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q5'},
                                                         'type': 'wikibase-entityid'},
                                           'datatype': 'wikibase-item'},
                                      'type': 'statement',
                                      'id': '1',
                                      'rank': 'normal'}],
                             },
                  'sitelinks': {}}
        self.assertEqual("correct", self.compare_properties._process_shape(schema, entity))

    def test_triple_constraint_against_process_shape2_which_passes_cardinality(self):
        schema = {'type': 'TripleConstraint',
                 'predicate': 'http://www.wikidata.org/prop/direct/P31',
                 'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}, "min":2, "max":2 }
        entity = {'title': 'Q1',
                  'type': 'item',
                  'id': 'Q1',
                  'claims': {'P31': [{'mainsnak':
                                          {'snaktype': 'value',
                                           'property': 'P31',
                                           'hash': '1',
                                           'datavalue': {'value':
                                                             {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q5'},
                                                         'type': 'wikibase-entityid'},
                                           'datatype': 'wikibase-item'},
                                      'type': 'statement',
                                      'id': '1',
                                      'rank': 'normal'},
                                     {'mainsnak':
                                          {'snaktype': 'value',
                                           'property': 'P31',
                                           'hash': '1',
                                           'datavalue': {'value':
                                                             {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q5'},
                                                         'type': 'wikibase-entityid'},
                                           'datatype': 'wikibase-item'},
                                      'type': 'statement',
                                      'id': '1',
                                      'rank': 'normal'}],
                             },
                  'sitelinks': {}}
        self.assertEqual("correct", self.compare_properties._process_shape(schema, entity))

    def test_triple_constraint_against_process_shape2_which_fails_cardinality(self):
        schema = {'type': 'TripleConstraint',
                 'predicate': 'http://www.wikidata.org/prop/direct/P31',
                 'valueExpr': {'type': 'NodeConstraint', 'values': ['http://www.wikidata.org/entity/Q5']}, "min":2, "max":2 }
        entity = {'title': 'Q1',
                  'type': 'item',
                  'id': 'Q1',
                  'claims': {'P31': [{'mainsnak':
                                          {'snaktype': 'value',
                                           'property': 'P31',
                                           'hash': '1',
                                           'datavalue': {'value':
                                                             {'entity-type': 'item', 'numeric-id': 2, 'id': 'Q5'},
                                                         'type': 'wikibase-entityid'},
                                           'datatype': 'wikibase-item'},
                                      'type': 'statement',
                                      'id': '1',
                                      'rank': 'normal'}],
                             },
                  'sitelinks': {}}
        self.assertEqual("not enough correct statements", self.compare_properties._process_shape(schema, entity))


if __name__ == '__main__':
    unittest.main()
