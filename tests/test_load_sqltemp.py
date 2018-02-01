# -*- coding: utf-8 -*-
import sqlite3

# Import compatiblity layers and helpers.
from . import _unittest as unittest
from datatest._compatibility import collections

# Import code to test.
from datatest.load.sqltemp import TemporarySqliteTable
from datatest.load.sqltemp import TemporarySqliteTableForCsv


class TestTemporarySqliteTable(unittest.TestCase):
    def test_assert_unique(self):
        # Should pass without error.
        TemporarySqliteTable._assert_unique(['foo', 'bar'])

        with self.assertRaises(ValueError):
            TemporarySqliteTable._assert_unique(['foo', 'foo'])

    def test_normalize_column(self):
        result = TemporarySqliteTable._normalize_column('foo')
        self.assertEqual('"foo"', result)

        result = TemporarySqliteTable._normalize_column('foo bar')
        self.assertEqual('"foo bar"', result)

        result = TemporarySqliteTable._normalize_column('foo "bar" baz')
        self.assertEqual('"foo ""bar"" baz"', result)

    def test_create_table_statement(self):
        stmnt = TemporarySqliteTable._create_table_statement('mytable', ['col1', 'col2'])
        self.assertEqual('CREATE TEMPORARY TABLE mytable ("col1", "col2")', stmnt)

    def test_make_new_table(self):
        tablename = TemporarySqliteTable._make_new_table(existing=[])
        self.assertEqual(tablename, 'tbl0')

        tablename = TemporarySqliteTable._make_new_table(existing=['tbl0', 'foo'])
        self.assertEqual(tablename, 'tbl1')

        tablename = TemporarySqliteTable._make_new_table(existing=['tbl0', 'foo', 'tbl1'])
        self.assertEqual(tablename, 'tbl2')

    def test_connection(self):
        cols = ('COL_A', 'COL_B')
        data = [
            ('1A', '1B'),
            ('2A', '2B')
        ]

        instance_x = TemporarySqliteTable(data, cols)
        instance_y = TemporarySqliteTable(data, cols)
        msg = 'Unless otherwise specified, instances should share the same connection.'
        self.assertIs(instance_x.connection, instance_y.connection)

        connection = sqlite3.connect(':memory:')
        instance_z = TemporarySqliteTable(data, cols, connection)
        msg = 'When specified, an alternative connection should be used.'
        self.assertIs(connection, instance_z.connection)
        self.assertIsNot(instance_x.connection, instance_z.connection)

    def test_init_with_tuple(self):
        # Test list of tuples.
        columns = ['foo', 'bar', 'baz']
        data = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        temptable = TemporarySqliteTable(data, columns)

        self.assertEqual(temptable.columns, columns)

        cursor = temptable.connection.cursor()
        cursor.execute('SELECT * FROM ' + temptable.name)
        result = list(cursor)
        self.assertEqual(data, result)

        # Test too few columns.
        columns = ['foo', 'bar']
        with self.assertRaises(sqlite3.ProgrammingError):
            temptable = TemporarySqliteTable(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(sqlite3.ProgrammingError):
            temptable = TemporarySqliteTable(data, columns)

    def test_init_with_dict(self):
        data = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]

        # Test basics.
        columns = ['foo', 'bar', 'baz']
        temptable = TemporarySqliteTable(data, columns)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        self.assertEqual(expected, list(cursor))

        # Test same data with different column order.
        columns = ['baz', 'foo', 'bar']
        temptable = TemporarySqliteTable(data, columns)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('1', 'a', 'x'),
            ('2', 'b', 'y'),
            ('3', 'c', 'z'),
        ]
        self.assertEqual(expected, list(cursor))

        # Test too few columns (should this fail?)
        #columns = ['foo', 'bar']
        #with self.assertRaises(AssertionError):
        #    temptable = TemporarySqliteTable(data, columns)

        # Test too many columns.
        columns = ['foo', 'bar', 'baz', 'qux']
        with self.assertRaises(KeyError):
            temptable = TemporarySqliteTable(data, columns)

        # Wrong column names (but correct number of them).
        columns = ['qux', 'quux', 'corge']
        with self.assertRaises(KeyError):
            temptable = TemporarySqliteTable(data, columns)

    def test_init_without_columns_arg(self):
        data_dict = [
            {'foo': 'a', 'bar': 'x', 'baz': '1'},
            {'foo': 'b', 'bar': 'y', 'baz': '2'},
            {'foo': 'c', 'bar': 'z', 'baz': '3'},
        ]

        # Iterable of dict-rows.
        temptable = TemporarySqliteTable(data_dict)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('x', '1', 'a'),
            ('y', '2', 'b'),
            ('z', '3', 'c'),
        ]
        self.assertEqual(expected, list(cursor))

        # Iterable of namedtuple-rows.
        ntup = collections.namedtuple('ntup', ['foo', 'bar', 'baz'])
        data_namedtuple = [
            ntup('a', 'x', '1'),
            ntup('b', 'y', '2'),
            ntup('c', 'z', '3'),
        ]
        temptable = TemporarySqliteTable(data_namedtuple)
        cursor = temptable._connection.cursor()
        cursor.execute('SELECT * FROM {0}'.format(temptable.name))
        expected = [
            ('a', 'x', '1'),
            ('b', 'y', '2'),
            ('c', 'z', '3'),
        ]
        self.assertEqual(expected, list(cursor))

        # Type that doesn't support omitted columns (should raise TypeError).
        data_tuple = [('a', 'x', '1'), ('b', 'y', '2'), ('c', 'z', '3')]
        regex = ('columns argument can only be omitted if data '
                 'contains dict-rows or namedtuple-rows')
        with self.assertRaisesRegex(TypeError, regex):
            temptable = TemporarySqliteTable(data_tuple)

    def test_init_with_empty_data(self):
        """Empty data iterable should result in empty table."""
        columns = ['foo', 'bar', 'baz']
        data = []  # <- Empty!
        temptable = TemporarySqliteTable(data, columns)
        cursor = temptable.connection.cursor()

        self.assertEqual(temptable.columns, columns,
                         msg='Table should exist and include given columns.')

        cursor.execute('SELECT * FROM ' + temptable.name)
        self.assertEqual(list(cursor), [], msg='Table should be empty.')


class TestTemporarySqliteTableForCsv(unittest.TestCase):
    def setUp(self):
        columns = ['foo', 'bar']
        data = [
            ('a', '1'),
            ('b', '2'),
        ]
        self.temptable = TemporarySqliteTableForCsv(data, columns)

    def get_table(self):
        cursor = self.temptable._connection.cursor()
        cursor.execute('SELECT * FROM ' + self.temptable._name)
        return list(cursor)

    def test_concat_all_same(self):
        columns = ['foo', 'bar']  # <- Same column names.
        data = [
            ('c', '3'),
            ('d', '4'),
        ]
        self.temptable._concatenate_data(data, columns)

        result = self.get_table()
        expected = [
            ('a', '1'),
            ('b', '2'),
            ('c', '3'),
            ('d', '4'),
        ]
        self.assertEqual(result, expected)

    def test_concat_one_different(self):
        columns = ['foo', 'baz']  # <- Column 'baz' not in existing table.
        data = [
            ('c', '3'),
            ('d', '4'),
        ]
        self.temptable._concatenate_data(data, columns)

        result = self.get_table()
        expected = [
            ('a', '1',  ''),
            ('b', '2',  ''),
            ('c',  '', '3'),
            ('d',  '', '4'),
        ]
        self.assertEqual(result, expected)

    def test_concat_all_different(self):
        columns = ['qux', 'quux']  # <- Neither column in existing table.
        data = [
            ('c', '3'),
            ('d', '4'),
        ]
        self.temptable._concatenate_data(data, columns)

        result = self.get_table()
        expected = [
            ('a', '1',  '',  ''),
            ('b', '2',  '',  ''),
            ('',  '',  'c', '3'),
            ('',  '',  'd', '4'),
        ]
        self.assertEqual(result, expected)
