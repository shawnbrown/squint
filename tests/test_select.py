# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import shutil
import sqlite3
import tempfile

from squint._compatibility.builtins import *
from squint._compatibility.collections import namedtuple
from .common import (
    StringIO,
    unittest,
)
from squint.select import Select
from squint.select import Query
from squint.result import Result


class HelperTestCase(unittest.TestCase):
    def setUp(self):
        data = [['label1', 'label2', 'value'],
                ['a', 'x', '17'],
                ['a', 'x', '13'],
                ['a', 'y', '20'],
                ['a', 'z', '15'],
                ['b', 'z', '5' ],
                ['b', 'y', '40'],
                ['b', 'x', '25']]
        self.select = Select(data)


class TestSelect(HelperTestCase):
    def test_empty_select(self):
        select = Select()

    def test_fieldnames(self):
        expected = ['label1', 'label2', 'value']
        self.assertEqual(self.select.fieldnames, expected)

        select = Select()  # <- Empty select.
        self.assertEqual(select.fieldnames, [], msg='should be empty list')

    def test_load_data(self):
        select = Select()  # <- Empty select.
        self.assertEqual(select.fieldnames, [])

        readerlike1 = [['col1', 'col2'], ['a', 1], ['b', 2]]
        select.load_data(readerlike1)
        self.assertEqual(select.fieldnames, ['col1', 'col2'])

        readerlike2 = [['col1', 'col3'], ['c', 'x'], ['d', 'y']]
        select.load_data(readerlike2)
        self.assertEqual(select.fieldnames, ['col1', 'col2', 'col3'])

    def test_repr(self):
        data = [['A', 'B'], ['x', 100], ['y', 200]]

        # Empty select.
        select = Select()
        self.assertEqual(repr(select), '<Select (no data loaded)>')

        # Data-only (no args)
        select = Select(data)
        expected = "<Select [['A', 'B'], ['x', 100], ['y', 200]]>"
        self.assertEqual(repr(select), expected)

        # Data with args (args don't affect repr)
        iterable = iter(data)
        select = Select(iterable, 'foo', bar='baz')
        regex = '<Select <[a-z_]+ object at [^\n>]+>>'
        self.assertRegex(repr(select), regex)

        # Extended after instantiation.
        select = Select()
        select.load_data([['A', 'B'], ['z', 300]])
        select.load_data([['A', 'B'], ['y', 200]])
        select.load_data([['A', 'B'], ['x', 100]])

        expected = (
            "<Select (3 sources):\n"
            "    [['A', 'B'], ['x', 100]]\n"
            "    [['A', 'B'], ['y', 200]]\n"
            "    [['A', 'B'], ['z', 300]]>"
        )
        self.assertEqual(repr(select), expected)

        # Test long repr truncation.
        select = Select([
            ['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'],
            ['yyyyyyyyyyyyyyyyyyyyyyyyyyyyyy'],
        ])

        self.assertEqual(len(repr(select)), 72)

        expected = "<Select [['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'], ['yyyyyyyyyyyyy...yyyyy']]>"
        self.assertEqual(repr(select), expected)

    def test_create_user_function(self):
        select = Select([['A', 'B'], ['x', 1], ['y', 2], ['z', 3]])

        # Verify that "_user_function_dict" us empty.
        self.assertEqual(select._user_function_dict, dict(), 'should be empty dict')

        # Create first function using a specified id.
        isodd = lambda x: x % 2 == 1
        select._create_user_function(isodd, 123)
        self.assertEqual(len(select._user_function_dict), 1)
        self.assertIn(123, select._user_function_dict)

        # Create second function using a specified id.
        iseven = lambda x: x % 2 == 0
        select._create_user_function(iseven, 456)
        self.assertEqual(len(select._user_function_dict), 2)
        self.assertIn(456, select._user_function_dict)

        # Make sure they are getting new SQLite function names.
        self.assertNotEqual(
            select._user_function_dict[123],
            select._user_function_dict[456],
        )

        # Create third function using a specified id.
        grteql2 = lambda x: x >= 2
        select._create_user_function(grteql2)
        self.assertEqual(len(select._user_function_dict), 3)

        # Attempt to recreate the third function again.
        with self.assertRaises(ValueError, msg='can not register same function twice'):
            select._create_user_function(grteql2)
        self.assertEqual(len(select._user_function_dict), 3)

    def test_get_user_function(self):
        select = Select([['A', 'B'], ['x', 1], ['y', 2], ['z', 3]])

        # Verify that "_user_function_dict" us empty.
        self.assertEqual(len(select._user_function_dict), 0, 'should be empty dict')

        # Get existing function.
        isodd = lambda x: x % 2 == 1
        select._create_user_function(isodd)
        func_name = select._get_user_function(isodd)
        self.assertEqual(len(select._user_function_dict), 1)
        self.assertRegex(func_name, r'FUNC\d+')

        # Get new function.
        iseven = lambda x: x % 2 == 0
        func_name = select._get_user_function(iseven)
        self.assertEqual(len(select._user_function_dict), 2, 'should be auto-created')
        self.assertRegex(func_name, r'FUNC\d+')

    def test_build_where_clause(self):
        select = Select([['A', 'B'], ['x', 1], ['y', 2], ['z', 3]])

        result = select._build_where_clause({'A': 'x'})
        expected = ('A=?', ['x'])
        self.assertEqual(result, expected)

        result = select._build_where_clause({'A': set(['x', 'y'])})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 'A IN (?, ?)')
        self.assertEqual(set(result[1]), set(['x', 'y']))

        # User-defined function.
        userfunc = lambda x: len(x) == 1
        result = select._build_where_clause({'A': userfunc})
        self.assertEqual(len(result), 2)
        self.assertRegex(result[0], r'FUNC\d+\(A\)')
        self.assertEqual(result[1], [])

        # Predicate (a type)
        prev_len = len(select._user_function_dict)
        predicate = int
        result = select._build_where_clause({'A': predicate})
        self.assertEqual(len(result), 2)
        self.assertRegex(result[0], r'FUNC\d+\(A\)')
        self.assertEqual(result[1], [])
        self.assertEqual(len(select._user_function_dict), prev_len + 1)

        # Predicate (a boolean)
        prev_len = len(select._user_function_dict)
        predicate = True
        result = select._build_where_clause({'A': predicate})
        self.assertEqual(len(result), 2)
        self.assertRegex(result[0], r'FUNC\d+\(A\)')
        self.assertEqual(result[1], [])
        self.assertEqual(len(select._user_function_dict), prev_len + 1)

    def test_execute_query(self):
        data = [['A', 'B'], ['x', 101], ['y', 202], ['z', 303]]
        source = Select(data)

        # Test where-clause function.
        def isodd(x):
            return x % 2 == 1
        result = source('A', B=isodd).fetch()
        self.assertEqual(result, ['x', 'z'])

        # Test replacing function.
        def iseven(x):
            return x % 2 == 0
        result = source('A', B=iseven).fetch()
        self.assertEqual(result, ['y'])

        # Test callable-but-unhashable.
        class IsEven(object):
            __hash__ = None

            def __call__(self, x):
                return x % 2 == 0

        unhashable_iseven = IsEven()
        result = source('A', B=unhashable_iseven).fetch()
        self.assertEqual(result, ['y'])

    def test_select_list_of_strings(self):
        result = self.select._select(['label1'])
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(result.fetch(), expected)

    def test_select_tuple_of_strings(self):
        result = self.select._select(('label1',))
        expected = ('a', 'a', 'a', 'a', 'b', 'b', 'b')
        self.assertEqual(result.fetch(), expected)

    def test_select_set_of_strings(self):
        result = self.select._select(set(['label1']))
        expected = set(['a', 'b'])
        self.assertEqual(result.fetch(), expected)

    def test_select_field_not_found(self):
        with self.assertRaises(LookupError):
            result = self.select._select(['bad_field_name'])

    def test_select_list_of_lists(self):
        result = self.select._select([['label1']])
        expected = [['a'], ['a'], ['a'], ['a'], ['b'], ['b'], ['b']]
        self.assertEqual(result.fetch(), expected)

        result = self.select._select([['label1', 'label2']])
        expected = [['a', 'x'], ['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        self.assertEqual(result.fetch(), expected)

    def test_select_list_of_tuples(self):
        result = self.select._select([('label1',)])
        expected = [('a',), ('a',), ('a',), ('a',), ('b',), ('b',), ('b',)]
        self.assertEqual(result.fetch(), expected)

    def test_select_list_of_namedtuples(self):
        namedtup = namedtuple('namedtup', ['label1', 'label2'])
        result = self.select._select([namedtup('label1', 'label2')])
        expected = [namedtup(label1='a', label2='x'),
                    namedtup(label1='a', label2='x'),
                    namedtup(label1='a', label2='y'),
                    namedtup(label1='a', label2='z'),
                    namedtup(label1='b', label2='z'),
                    namedtup(label1='b', label2='y'),
                    namedtup(label1='b', label2='x')]
        self.assertEqual(result.fetch(), expected)

    def test_select_set_of_frozensets(self):
        result = self.select._select(set([frozenset(['label1'])]))
        expected = set([frozenset(['a']), frozenset(['a']),
                        frozenset(['a']), frozenset(['a']),
                        frozenset(['b']), frozenset(['b']),
                        frozenset(['b'])])
        self.assertEqual(result.fetch(), expected)

    def test_select_dict(self):
        result = self.select._select({'label1': ['value']})
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict2(self):
        result = self.select._select({('label1', 'label2'): ['value']})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict3(self):
        result = self.select._select({('label1', 'label2'): [['value']]})
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict_with_namedtuple_keys(self):
        namedtup = namedtuple('namedtup', ['x', 'y'])
        result = self.select._select({namedtup('label1', 'label2'): ['value']})
        expected = {
            namedtup(x='a', y='x'): ['17', '13'],
            namedtup(x='a', y='y'): ['20'],
            namedtup(x='a', y='z'): ['15'],
            namedtup(x='b', y='x'): ['25'],
            namedtup(x='b', y='y'): ['40'],
            namedtup(x='b', y='z'): ['5'],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_dict_with_values_container2(self):
        result = self.select._select({'label1': [('label2', 'label2')]})
        expected = {
            'a': [('x', 'x'), ('x', 'x'), ('y', 'y'), ('z', 'z')],
            'b': [('z', 'z'), ('y', 'y'), ('x', 'x')]
        }
        self.assertEqual(result.fetch(), expected)

        result = self.select._select({'label1': [set(['label2', 'label2'])]})
        expected = {
            'a': [set(['x']), set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_alternate_mapping_type(self):
        class CustomDict(dict):
            pass

        result = self.select._select(CustomDict({'label1': ['value']}))
        result = result.fetch()
        expected = {
            'a': ['17', '13', '20', '15'],
            'b': ['5', '40', '25'],
        }
        self.assertIsInstance(result, CustomDict)
        self.assertEqual(result, expected)

    def test_select_distinct(self):
        result = self.select._select_distinct(['label1'])
        expected = ['a', 'b']
        self.assertEqual(list(result), expected)

        result = self.select._select_distinct({'label1': ['label2']})
        result = result.fetch()
        expected = {'a': ['x', 'y', 'z'], 'b': ['z', 'y', 'x']}

        self.assertIsInstance(result, dict)

        # Sort values for SQLite versions earlier than 3.7.12
        if (3, 7, 12) > sqlite3.sqlite_version_info:
            sortvalues = lambda x: dict((k, sorted(v)) for k, v in x.items())
            result = sortvalues(result)
            expected = sortvalues(expected)
        self.assertEqual(result, expected)

    def test_select_distinct_dict_grouping(self):
        """Dictionary grouping should work even when key elements
        are not adjacent in the original data source. To do this
        efficiently, results of the internal query should be sorted.
        """
        source = Select([
            ['A', 'B'],
            ['x', 1],
            ['y', 2],
            ['z', 3],
            ['x', 4],
            ['y', 5],
            ['z', 6],
        ])
        result = source._select_distinct({'A': ['B']})
        expected = {
            'x': [1, 4],
            'y': [2, 5],
            'z': [3, 6],
        }
        self.assertEqual(result.fetch(), expected)

    def test_select_aggregate(self):
        # Not grouped, single result.
        result = self.select._select_aggregate('COUNT', ['label2'])
        self.assertEqual(result, 7)

        # Not grouped, single result as set.
        result = self.select._select_aggregate('COUNT', set(['label2']))
        self.assertEqual(result, 3)

        # Not grouped, multiple results.
        result = self.select._select_aggregate('SUM', [['value', 'value']])
        self.assertEqual(result, [135, 135])

        # Simple group by (grouped by keys).
        result = self.select._select_aggregate('SUM', {'label1': ['value']})
        self.assertIsInstance(result, Result)

        expected = {
            'a': 65,
            'b': 70,
        }
        self.assertEqual(result.fetch(), expected)

        # Composite value.
        result = self.select._select_aggregate('SUM', {'label1': [('value', 'value')]})
        expected = {
            'a': (65, 65),
            'b': (70, 70),
        }
        self.assertEqual(dict(result), expected)

        # Composite key and composite value.
        result = self.select._select_aggregate('SUM', {('label1', 'label1'): [['value', 'value']]})
        expected = {
            ('a', 'a'): [65, 65],
            ('b', 'b'): [70, 70],
        }
        self.assertEqual(dict(result), expected)

    def test_select_dict_grouping(self):
        """Dictionary grouping should work even when key elements
        are not adjacent in the original data source. To do this
        efficiently, results of the internal query should be sorted.
        """
        source = Select([
            ['A', 'B'],
            ['x', 1],
            ['y', 2],
            ['z', 3],
            ['x', 4],
            ['y', 5],
            ['z', 6],
        ])
        result = source._select({'A': ['B']})
        expected = {
            'x': [1, 4],
            'y': [2, 5],
            'z': [3, 6],
        }
        self.assertEqual(result.fetch(), expected)


class TestCall(HelperTestCase):
    def test_list_of_elements(self):
        query = self.select(['label1'])
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

    def test_list_of_tuples(self):
        query = self.select([('label1', 'label2')])
        expected = [('a', 'x'), ('a', 'x'), ('a', 'y'), ('a', 'z'),
                    ('b', 'z'), ('b', 'y'), ('b', 'x')]
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

    def test_list_of_sets(self):
        query = self.select([set(['label1', 'label2'])])
        expected = [set(['a', 'x']),
                    set(['a', 'x']),
                    set(['a', 'y']),
                    set(['a', 'z']),
                    set(['b', 'z']),
                    set(['b', 'y']),
                    set(['b', 'x'])]
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)

    def test_dict_of_lists(self):
        query = self.select({'label1': ['label2']})
        expected = {'a': ['x', 'x', 'y', 'z'], 'b': ['z', 'y', 'x']}
        self.assertIsInstance(query, Query)
        self.assertEqual(query.fetch(), expected)


class TestQueryToCsv(unittest.TestCase):
    def setUp(self):
        self.select = Select([['A', 'B'], ['x', 1], ['y', 2]])

    def test_fmtparams(self):
        query = self.select(['A', 'B'])

        csvfile = StringIO()
        query.to_csv(csvfile, delimiter='|', lineterminator='\n')

        csvfile.seek(0)
        self.assertEqual(csvfile.readlines(), ['A|B\n', 'x|1\n', 'y|2\n'])

    def test_actual_file(self):
        query = self.select(['A', 'B'])

        try:
            tmpdir = tempfile.mkdtemp()

            path = os.path.join(tmpdir, 'tempfile.csv')
            query.to_csv(path, lineterminator='\n')

            with open(path) as fh:
                self.assertEqual(fh.read(), 'A,B\nx,1\ny,2\n')

        finally:
            shutil.rmtree(tmpdir)


class TestIterable(unittest.TestCase):
    def test_iterate(self):
        select = Select([('A', 'B'), (1, 2), (1, 2)])
        self.assertEqual(list(select), [[1, 2], [1, 2]])
