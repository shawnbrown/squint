# -*- coding: utf-8 -*-
import unittest
from datatest.dataaccess.source import DataSource
from datatest.dataaccess.source import DataQuery
from datatest.dataaccess.query import BaseQuery
from datatest.dataaccess.result import DataResult


class TestDataQuery(unittest.TestCase):
    def test_from_parts(self):
        source = DataSource([(1, 2), (1, 2)], columns=['A', 'B'])
        query = DataQuery._from_parts(initializer=source)
        self.assertIsInstance(query, BaseQuery)  # <- Subclass of BaseQuery.

        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            wrong_type = ['hello', 'world']
            query = DataQuery._from_parts(initializer=wrong_type)

    def test_eval(self):
        query = DataQuery()
        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            query.eval(['hello', 'world'])  # <- Expects None or DataQuery, not list!


class TestDataSourceBasics(unittest.TestCase):
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_columns(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.source.columns(), expected)

    def test_iter(self):
        """Test __iter__."""
        result = [row for row in self.source]
        expected = [
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value': '5' },
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ]
        self.assertEqual(expected, result)

    def test_select_single_value(self):
        result = self.source._select('label1')
        self.assertIsInstance(result, DataResult)
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(list(result), expected)

        arg_dict = {'label1': 'value'}
        result = self.source._select(arg_dict)
        self.assertEqual(arg_dict, {'label1': 'value'}, 'should not alter arg_dict')

    def test_select_tuple_of_values(self):
        result = self.source._select('label1', 'label2')
        expected = [
            ('a', 'x'),
            ('a', 'x'),
            ('a', 'y'),
            ('a', 'z'),
            ('b', 'z'),
            ('b', 'y'),
            ('b', 'x'),
        ]
        self.assertEqual(list(result), expected)

    def test_select_dict_of_values(self):
        result = self.source._select({'label1': 'value'})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_value_tuples(self):
        result = self.source._select({'label1': ('label2', 'value')})
        expected = {
            'a': [
                ('x', '17'),
                ('x', '13'),
                ('y', '20'),
                ('z', '15'),
            ],
            'b': [
                ('z', '5'),
                ('y', '40'),
                ('x', '25'),
            ],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_key_tuples(self):
        result = self.source._select({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'z'): ['5'],
            ('b', 'y'): ['40'],
            ('b', 'x'): ['25'],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_dict_with_key_and_value_tuples(self):
        result = self.source._select({('label1', 'label2'): ('label2', 'value')})
        expected = {
            ('a', 'x'): [('x', '17'), ('x', '13')],
            ('a', 'y'): [('y', '20')],
            ('a', 'z'): [('z', '15')],
            ('b', 'z'): [('z', '5')],
            ('b', 'y'): [('y', '40')],
            ('b', 'x'): [('x', '25')],
        }
        self.assertEqual(result.eval(), expected)

    def test_select_nested_dicts(self):
        """Support for nested dictionaries was removed (for now).
        It's likely that arbitrary nesting would complicate the ability
        to check complex data types that are, themselves, mappings.
        """
        regex = "{'label2': 'value'} not in DataSource"
        with self.assertRaisesRegex(LookupError, regex):
            self.source._select({'label1': {'label2': 'value'}})

    def test_call(self):
        result = self.source('label1')
        self.assertIsInstance(result, DataQuery)

        result = list(result.eval())
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(result, expected)

        result = self.source({'label1': 'label2'})
        self.assertIsInstance(result, DataQuery)

        result = dict(result.eval())
        expected = {
            'a': ['x', 'x', 'y', 'z'],
            'b': ['z', 'y', 'x'],
        }
        self.assertEqual(result, expected)


class TestDataSourceOptimizations(unittest.TestCase):
    """."""
    def setUp(self):
        columns = ['label1', 'label2', 'value']
        data = [['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.source = DataSource(data, columns)

    def test_select_aggregate(self):
        result = self.source._select_aggregate('SUM', 'value')
        self.assertEqual(result, 135)

        result = self.source._select_aggregate('SUM', 'value', label1='a')
        self.assertEqual(result, 65)

        result = self.source._select_aggregate('SUM', 'value', label1='z')
        self.assertEqual(result, None)

        with self.assertRaises(ValueError):
            self.source._select_aggregate('SUM', 'value', 'value')

    def test_select_aggregate_grouped(self):
        result = self.source._select_aggregate('SUM', {'label1': 'value'})
        self.assertEqual(result.eval(), {'a': 65, 'b': 70})

        result = self.source._select_aggregate('MAX', {'label1': 'value'})
        self.assertEqual(result.eval(), {'a': '20', 'b': '5'})

        result = self.source._select_aggregate('SUM', {'label1': 'value'}, label2='x')
        self.assertEqual(result.eval(), {'a': 30, 'b': 25})

        result = self.source._select_aggregate('SUM', {('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): 30,
            ('a', 'y'): 20,
            ('a', 'z'): 15,
            ('b', 'x'): 25,
            ('b', 'y'): 40,
            ('b', 'z'): 5,
        }
        self.assertEqual(result.eval(), expected)

        result = self.source._select_aggregate('COUNT', {'label2': 'value'})
        self.assertEqual(result.eval(), {'x': 3, 'y': 2, 'z': 2})
