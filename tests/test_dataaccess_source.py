# -*- coding: utf-8 -*-
from __future__ import absolute_import
import textwrap
from . import _io as io

from . import _unittest as unittest
from datatest.utils import collections
from datatest.utils.misc import _is_nsiterable
from datatest.load.source import DataSource
from datatest.load.source import DataQuery
from datatest.load.source import RESULT_TOKEN
from datatest.load.source import DataResult
from datatest.load.source import _map_data
from datatest.load.source import _filter_data
from datatest.load.source import _reduce_data
from datatest.load.source import _apply_to_data
from datatest.load.source import _sqlite_sum
from datatest.load.source import _sqlite_count
from datatest.load.source import _sqlite_avg
from datatest.load.source import _sqlite_min
from datatest.load.source import _sqlite_max
from datatest.load.source import _sqlite_distinct
from datatest.load.source import _set_data
from datatest.load.source import _cast_as_set
from datatest.load.source import ItemsIter


def convert_iter_to_type(iterable, target_type):
    """Helper function to convert lists-of-lists into tuple-of-tuples."""
    if isinstance(iterable, collections.Mapping):
        dic = {}
        for k, v in iterable.items():
            dic[k] = convert_iter_to_type(v, target_type)
        output = dic
    else:
        lst = []
        for obj in iterable:
            if _is_nsiterable(obj):
                obj = convert_iter_to_type(obj, target_type)
            lst.append(obj)
        output = target_type(lst)
    return output


class TestDataResult(unittest.TestCase):
    def test_init(self):
        untyped = iter([1, 2, 3, 4])

        typed = DataResult(untyped, list)
        self.assertEqual(typed.evaluation_type, list)

        typed = DataResult(iterable=untyped, evaluation_type=list)
        self.assertEqual(typed.evaluation_type, list)

        regex = 'evaluation_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = DataResult(untyped, [1, 2])


class TestItemsIter(unittest.TestCase):
    def test_itemsiter(self):
        foo = ItemsIter([1,2,3])
        self.assertEqual(list(foo), [1,2,3])


class TestMapData(unittest.TestCase):
    def test_dataiter_list(self):
        iterable = DataResult([1, 2, 3], list)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, list)
        self.assertEqual(result.evaluate(), [2, 4, 6])

    def test_single_int(self):
        function = lambda x: x * 2
        result = _map_data(function, 3)
        self.assertEqual(result, 6)

    def test_dataiter_dict_of_containers(self):
        iterable = DataResult({'a': [1, 2], 'b': (3, 4)}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': [2, 4], 'b': (6, 8)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        function = lambda x: x * 2
        result = _map_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 4, 'b': 6})


class TestFilterData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([-4, -1, 2, 3], list)

        function = lambda x: x > 0
        result = _filter_data(function, iterable)
        self.assertEqual(result.evaluate(), [2, 3])

    def test_bad_iterable_type(self):
        function = lambda x: x > 0
        with self.assertRaises(TypeError):
            _filter_data(function, 3)  # <- int

        function = lambda x: x == 'a'
        with self.assertRaises(TypeError):
            _filter_data(function, 'b')  # <- str

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, 2, 3], 'b': [4, 5, 6]}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': [2], 'b': [4, 6]})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        iseven = lambda x: x % 2 == 0
        result = _filter_data(iseven, iterable)
        with self.assertRaises(TypeError):
            result.evaluate()


class TestReduceData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3], list)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        function = lambda x, y: x + y
        result = _reduce_data(function, 3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        function = lambda x, y: x + y
        result = _reduce_data(function, 'abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, 2], 'b': [3, 4]}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)

        function = lambda x, y: x + y
        result = _reduce_data(function, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestSumData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3], list)
        result = _sqlite_sum(iterable)
        self.assertEqual(result, 6)

    def test_single_integer(self):
        result = _sqlite_sum(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_sum('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, 2], 'b': [3, 4]}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 7})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)
        result = _apply_to_data(_sqlite_sum, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestCountData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult(['a', None, 3], list)
        result = _sqlite_count(iterable)
        self.assertEqual(result, 2)

    def test_single_value(self):
        result = _sqlite_count(3)
        self.assertEqual(result, 1)

        result = _sqlite_count('abc')
        self.assertEqual(result, 1)

        result = _sqlite_count(None)
        self.assertEqual(result, 0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({'a': [1, None], 'b': ['x', None, 0]}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 2})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': -5, 'b': None, 'c': 'xyz'}, dict)
        result = _apply_to_data(_sqlite_count, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 0, 'c': 1})


class TestAvgData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_avg(iterable)
        self.assertEqual(result, 2.5)

    def test_single_integer(self):
        result = _sqlite_avg(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_avg('abc')
        self.assertEqual(result, 0.0)

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, None],
            'b': ['xx', 1, 2, 3, None],
            'c': [None, None, None]}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1.5, 'b': 1.5, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_avg, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestMinData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_min(iterable)
        self.assertEqual(result, 1)

    def test_single_integer(self):
        result = _sqlite_min(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_min('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 1, 'b': 1, 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_min, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestMaxData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 3, 4], list)
        result = _sqlite_max(iterable)
        self.assertEqual(result, 4)

    def test_single_integer(self):
        result = _sqlite_max(3)
        self.assertEqual(result, 3)

    def test_single_string(self):
        result = _sqlite_max('abc')
        self.assertEqual(result, 'abc')

    def test_dict_iter_of_lists(self):
        iterable = DataResult({
            'a': [1, 2, 3],
            'b': [None, 1, 2, 3, 'xx'],
            'c': [None, None]}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 3, 'b': 'xx', 'c': None})

    def test_dict_iter_of_integers(self):
        iterable = DataResult({'a': 2, 'b': 3, 'c': None}, dict)
        result = _apply_to_data(_sqlite_max, iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3, 'c': None})


class TestDistinctData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 1, 2, 3], list)
        result = _sqlite_distinct(iterable)
        self.assertEqual(result.evaluate(), [1, 2, 3])

    def test_single_int(self):
        result = _sqlite_distinct(3)
        self.assertEqual(result, 3)

    def test_dataiter_dict_of_containers(self):
        iterable = DataResult({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': [1, 2], 'b': (3, 4)})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)
        result = _sqlite_distinct(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': 2, 'b': 3})


class TestSetData(unittest.TestCase):
    def test_list_iter(self):
        iterable = DataResult([1, 2, 1, 2, 3], list)
        result = _set_data(iterable)
        self.assertEqual(result.evaluate(), set([1, 2, 3]))

    def test_single_int(self):
        result = _set_data(3)
        self.assertEqual(result.evaluate(), set([3]))

    def test_dataiter_dict_of_containers(self):
        iterable = DataResult({'a': [1, 2, 1, 2], 'b': (3, 4, 3)}, dict)
        result = _set_data(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': set([1, 2]), 'b': set([3, 4])})

    def test_dataiter_dict_of_ints(self):
        iterable = DataResult({'a': 2, 'b': 3}, dict)
        result = _set_data(iterable)

        self.assertIsInstance(result, DataResult)
        self.assertEqual(result.evaluation_type, dict)
        self.assertEqual(result.evaluate(), {'a': set([2]), 'b': set([3])})


class TestDataQuery(unittest.TestCase):
    def test_init(self):
        query = DataQuery('foo', bar='baz')
        expected = (
            ('select', ('foo',), {'bar': 'baz'}),
        )
        self.assertEqual(query._query_steps, expected)
        self.assertEqual(query._source, None)

        with self.assertRaises(TypeError, msg='should require select args'):
            DataQuery()

    def test_from_parts(self):
        source = DataSource([(1, 2), (1, 2)], columns=['A', 'B'])
        query = DataQuery._from_parts(source=source)
        self.assertEqual(query._query_steps, tuple())
        self.assertIs(query._source, source)

        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            wrong_type = ['hello', 'world']
            query = DataQuery._from_parts(source=wrong_type)

    def test_execute(self):
        source = DataSource([('1', '2'), ('1', '2')], columns=['A', 'B'])
        query = DataQuery._from_parts(source=source)
        query._query_steps = [
            ('select', ('B',), {}),
            ('map', (int,), {}),
            ('map', (lambda x: x * 2,), {}),
            ('sum', (), {}),
        ]
        result = query.execute()
        self.assertEqual(result, 8)

        query = DataQuery('A')
        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            query.execute(['hello', 'world'])  # <- Expects None or DataQuery, not list!

    def test_map(self):
        query1 = DataQuery('col2')
        query2 = query1.map(int)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, [2, 2])

    def test_filter(self):
        query1 = DataQuery('col1')
        query2 = query1.filter(lambda x: x == 'a')
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, ['a'])

    def test_reduce(self):
        query1 = DataQuery('col1')
        query2 = query1.reduce(lambda x, y: x + y)
        self.assertIsNot(query1, query2, 'should return new object')

        source = DataSource([('a', '2'), ('b', '2')], columns=['col1', 'col2'])
        result = query2.execute(source)
        self.assertEqual(result, 'ab')

    def test_optimize_sum(self):
        """
        Unoptimized:
            DataQuery._select({'col1': 'values'}, col2='xyz').sum()

        Optimized:
            DataQuery._select_aggregate('SUM', {'col1': 'values'}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_apply_to_data, (_sqlite_sum, RESULT_TOKEN,), {}),
        )
        optimized = DataQuery._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_aggregate'), {}),
            (RESULT_TOKEN, ('SUM', {'col1': 'values'},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_distinct(self):
        """
        Unoptimized:
            DataQuery._select({'col1': 'values'}, col2='xyz').distinct()

        Optimized:
            DataQuery._select_distinct({'col1': 'values'}, col2='xyz')
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_sqlite_distinct, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
        )
        self.assertEqual(optimized, expected)

    def test_optimize_set(self):
        """
        Unoptimized:
            DataQuery._select({'col1': 'values'}, col2='xyz').set()

        Optimized:
            DataQuery._select_distinct({'col1': 'values'}, col2='xyz')._cast_as_set()
        """
        unoptimized = (
            (getattr, (RESULT_TOKEN, '_select'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_set_data, (RESULT_TOKEN,), {}),
        )
        optimized = DataQuery._optimize(unoptimized)

        expected = (
            (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
            (RESULT_TOKEN, ({'col1': 'values'},), {'col2': 'xyz'}),
            (_cast_as_set, (RESULT_TOKEN,), {}),
        )
        self.assertEqual(optimized, expected)

    def test_explain(self):
        query = DataQuery('col1')
        expected = """
            Execution Plan:
              getattr, (<RESULT>, '_select'), {}
              <RESULT>, ('col1'), {}
        """
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(query._explain(file=None), expected)

        # TODO: Add assert for query that can be optimized.


class TestDataSourceConstructors(unittest.TestCase):
    @staticmethod
    def get_table_contents(source):
        connection = source._connection
        table = source._table
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM ' + table)
        return list(cursor)

    def test_from_sequence_rows(self):
        data = [('x', 1),
                ('y', 2),
                ('z', 3)]
        columns = ['A', 'B']

        source = DataSource(data, columns)
        table_contents = self.get_table_contents(source)
        self.assertEqual(set(table_contents), set(data))

    def test_from_dict_rows(self):
        data = [{'A': 'x', 'B': 1},
                {'A': 'y', 'B': 2},
                {'A': 'z', 'B': 3}]

        source = DataSource(data)
        table_contents = self.get_table_contents(source)
        expected = [('x', 1), ('y', 2), ('z', 3)]
        self.assertEqual(set(table_contents), set(expected))

        source = DataSource(data, columns=['B', 'A'])  # <- Set column order.
        table_contents = self.get_table_contents(source)
        expected = [(1, 'x'), (2, 'y'), (3, 'z')]
        self.assertEqual(set(table_contents), set(expected))

    @staticmethod
    def _get_filelike(string, encoding):
        """Return file-like stream object."""
        import _io as io
        import sys
        filelike = io.BytesIO(string)
        if encoding and sys.version >= '3':
            filelike = io.TextIOWrapper(filelike, encoding=encoding)
        return filelike

    def test_from_csv_file(self):
        csv_file = self._get_filelike(b'A,B\n'
                                      b'x,1\n'
                                      b'y,2\n'
                                      b'z,3\n', encoding='utf-8')
        source = DataSource.from_csv(csv_file)
        table_contents = self.get_table_contents(source)
        expected = [('x', '1'), ('y', '2'), ('z', '3')]
        self.assertEqual(set(table_contents), set(expected))

    def test_from_multiple_csv_files(self):
        file1 = self._get_filelike(b'A,B\n'
                                   b'x,1\n'
                                   b'y,2\n'
                                   b'z,3\n', encoding='utf-8')

        file2 = self._get_filelike(b'B,C\n'
                                   b'4,j\n'
                                   b'5,k\n'
                                   b'6,l\n', encoding='ascii')

        source = DataSource.from_csv([file1, file2])
        table_contents = self.get_table_contents(source)

        expected = [('x', '1', ''), ('y', '2', ''), ('z', '3', ''),
                    ('', '4', 'j'), ('', '5', 'k'), ('', '6', 'l')]
        self.assertEqual(set(table_contents), set(expected))


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

    def test_select_column_no_container(self):
        result = self.source._select('label1')
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertEqual(list(result), expected)

    def test_select_column_not_found(self):
        with self.assertRaises(LookupError):
            result = self.source._select('bad_column_name')

    def test_select_column_as_list(self):
        result = self.source._select(['label1'])
        expected = [['a'], ['a'], ['a'], ['a'], ['b'], ['b'], ['b']]
        self.assertEqual(list(result), expected)

        result = self.source._select(['label1', 'label2'])
        expected = [['a', 'x'], ['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        self.assertEqual(list(result), expected)

    def test_select_column_as_tuple(self):
        result = self.source._select(('label1',))
        expected = [('a',), ('a',), ('a',), ('a',), ('b',), ('b',), ('b',)]
        self.assertEqual(list(result), expected)

    def test_select_column_as_set(self):
        result = self.source._select(set(['label1']))
        expected = [set(['a']), set(['a']), set(['a']), set(['a']),
                    set(['b']), set(['b']), set(['b'])]
        self.assertEqual(list(result), expected)

    def test_select_dict(self):
        result = self.source._select({('label1', 'label2'): 'value'})
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        self.assertEqual(result.evaluate(), expected)

    def test_select_dict_with_values_container(self):
        result = self.source._select({('label1', 'label2'): ['value']})
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        self.assertEqual(result.evaluate(), expected)

    def test_select_dict_frozenset_key(self):
        result = self.source._select({frozenset(['label1']): 'label2'})
        expected = {
            frozenset(['a']): ['x', 'x', 'y', 'z'],
            frozenset(['b']): ['z', 'y', 'x'],
        }
        self.assertEqual(result.evaluate(), expected)

    def test_select_dict_with_values_container2(self):
        result = self.source._select({'label1': ['label2', 'label2']})
        expected = {
            'a': [['x', 'x'], ['x', 'x'], ['y', 'y'], ['z', 'z']],
            'b': [['z', 'z'], ['y', 'y'], ['x', 'x']]
        }
        self.assertEqual(result.evaluate(), expected)

        result = self.source._select({'label1': set(['label2', 'label2'])})
        expected = {
            'a': [set(['x']), set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        self.assertEqual(result.evaluate(), expected)

    def test_select_distinct_column_no_container(self):
        result = self.source._select_distinct('label1')
        expected = ['a', 'b']
        self.assertEqual(list(result), expected)

    def assertContainsType(self, iterable, required_type):
        """Assert that itereable contains elements of the
        *required_type* only.
        """
        for element in iterable:
            if not isinstance(element, required_type):
                cls_name = element.__class__.__name__
                msg = 'expected {0}, found {1!r}'
                self.fail(msg.format(required_type, cls_name))

    def test_select_distinct_column_as_list(self):
        result = self.source._select_distinct(['label1'])
        self.assertIsInstance(result, DataResult)

        result = result.evaluate()
        self.assertIsInstance(result, list)
        self.assertContainsType(result, list)

        expected = [['a'], ['b']]
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

        # Same but more complex elements.
        result = self.source._select_distinct(['label1', 'label2'])
        expected = [['a', 'x'], ['a', 'y'], ['a', 'z'],
                    ['b', 'z'], ['b', 'y'], ['b', 'x']]
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

    def test_select_distinct_column_as_tuple(self):
        result = self.source._select_distinct(('label1',))
        expected = [('a',), ('b',)]
        self.assertEqual(list(result), expected)

    def test_select_distinct_column_as_set(self):
        result = self.source._select_distinct(set(['label1']))
        expected = [set(['a']), set(['b'])]
        self.assertEqual(list(result), expected)

    def test_select_distinct_dict(self):
        result = self.source._select_distinct({('label1', 'label2'): 'value'})
        result = result.evaluate()
        expected = {
            ('a', 'x'): ['17', '13'],
            ('a', 'y'): ['20'],
            ('a', 'z'): ['15'],
            ('b', 'x'): ['25'],
            ('b', 'y'): ['40'],
            ('b', 'z'): ['5'],
        }
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

    def test_select_distinct_dict_with_values_container(self):
        result = self.source._select_distinct({('label1', 'label2'): ['value']})
        result = result.evaluate()
        expected = {
            ('a', 'x'): [['17'], ['13']],
            ('a', 'y'): [['20']],
            ('a', 'z'): [['15']],
            ('b', 'x'): [['25']],
            ('b', 'y'): [['40']],
            ('b', 'z'): [['5']],
        }
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

    def test_select_distinct_dict_frozenset_key(self):
        result = self.source._select_distinct({frozenset(['label1']): 'label2'})
        result = result.evaluate()
        expected = {
            frozenset(['a']): ['x', 'y', 'z'],
            frozenset(['b']): ['z', 'y', 'x'],
        }
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

    def test_select_distinct_dict_with_values_container2(self):
        result = self.source._select_distinct({'label1': ['label2', 'label2']})
        result = result.evaluate()
        expected = {
            'a': [['x', 'x'], ['y', 'y'], ['z', 'z']],
            'b': [['z', 'z'], ['y', 'y'], ['x', 'x']],
        }
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

        result = self.source._select_distinct({'label1': set(['label2', 'label2'])})
        result = result.evaluate()
        expected = {
            'a': [set(['x']), set(['y']), set(['z'])],
            'b': [set(['z']), set(['y']), set(['x'])],
        }
        result_set = convert_iter_to_type(result, frozenset)
        expected_set = convert_iter_to_type(expected, frozenset)
        self.assertEqual(result_set, expected_set)

    def test_select_aggregate(self):
        # Not grouped, single result.
        result = self.source._select_aggregate('SUM', 'value')
        self.assertEqual(result, 135)

        # Not grouped, multiple results.
        result = self.source._select_aggregate('SUM', ['value', 'value'])
        self.assertEqual(result, [135, 135])

        # Simple group by (grouped by keys).
        result = self.source._select_aggregate('SUM', {'label1': 'value'})
        self.assertIsInstance(result, DataResult)

        expected = {
            'a': 65,
            'b': 70,
        }
        self.assertEqual(result.evaluate(), expected)

        # Composite value.
        result = self.source._select_aggregate('SUM', {'label1': ['value', 'value']})
        expected = {
            'a': [65, 65],
            'b': [70, 70],
        }
        self.assertEqual(dict(result), expected)

        # Composite key and composite value.
        result = self.source._select_aggregate('SUM', {('label1', 'label1'): ['value', 'value']})
        expected = {
            ('a', 'a'): [65, 65],
            ('b', 'b'): [70, 70],
        }
        self.assertEqual(dict(result), expected)

    def test_select_nested_dicts(self):
        """Support for nested dictionaries was removed (for now).
        It's likely that arbitrary nesting would complicate the ability
        to check complex data values that are, themselves, mappings
        (like probability mass functions represented as a dictionary).
        """
        regex = "{'label2': 'value'} not in DataSource"
        with self.assertRaisesRegex(LookupError, regex):
            self.source._select({'label1': {'label2': 'value'}})

    def test_call(self):
        query = self.source('label1')
        expected = ['a', 'a', 'a', 'a', 'b', 'b', 'b']
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.execute(), expected)

        query = self.source(('label1', 'label2'))
        expected = [('a', 'x'), ('a', 'x'), ('a', 'y'), ('a', 'z'),
                    ('b', 'z'), ('b', 'y'), ('b', 'x')]
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.execute(), expected)

        query = self.source(set(['label1', 'label2']))
        expected = [set(['a', 'x']),
                    set(['a', 'x']),
                    set(['a', 'y']),
                    set(['a', 'z']),
                    set(['b', 'z']),
                    set(['b', 'y']),
                    set(['b', 'x'])]
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.execute(), expected)

        query = self.source({'label1': 'label2'})
        expected = {'a': ['x', 'x', 'y', 'z'], 'b': ['z', 'y', 'x']}
        self.assertIsInstance(query, DataQuery)
        self.assertEqual(query.execute(), expected)

    def test_explain(self):
        query = DataQuery('label1')

        expected = """
            Execution Plan:
              getattr, (<RESULT>, '_select'), {}
              <RESULT>, ('label1'), {}
        """
        expected = textwrap.dedent(expected).strip()

        # Defaults to stdout (redirected to StringIO for testing).
        string_io = io.StringIO()
        returned_value = query._explain(file=string_io)
        self.assertIsNone(returned_value)

        printed_value = string_io.getvalue().strip()
        self.assertEqual(printed_value, expected)

        # Get result as string.
        returned_value = query._explain(file=None)
        self.assertEqual(returned_value, expected)
