# -*- coding: utf-8 -*-
import collections
import csv
import inspect
import io
import itertools
import os
import sqlite3
import sys
import warnings
from decimal import Decimal

from datatest._builtins import *

#pattern = 'test*.py'
prefix = 'test_'


class BaseDataSource(object):
    """Common base class for all data sources."""

    def __init__(self):
        """Initialize self."""
        return NotImplemented

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return NotImplemented

    def columns(self):
        """Return sequence or collection of column names."""
        return NotImplemented

    def set(self, column, **kwds):
        """Return set of values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return set(x[column] for x in iterable)

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        iterable = (x for x in iterable if x)
        return sum(Decimal(x[column]) for x in iterable)

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        iterable = self._filtered(self.slow_iter(), **kwds)
        return sum(bool(x[column]) for x in iterable)

    def groups(self, *columns, **kwds):
        """Return iterable of unique dictionaries grouped by given columns."""
        iterable = self._filtered(self.slow_iter(), **kwds)   # Filtered rows only.
        fn = lambda dic: tuple((k, dic[k]) for k in columns)  # Subset as item-tuples.

        iterable = set(fn(x) for x in iterable)               # Unique.
        iterable = sorted(iterable)                           # Ordered.
        # Explore possible TODOs:
        # replace unique with `unique_everseen` https://docs.python.org/3.4/library/itertools.html
        # remove sorted() call and make sorting optional
        return (dict(item) for item in iterable)              # Make dicts.

    @staticmethod
    def _filtered(iterable, **kwds):
        """Filter iterable by keywords (column=value, etc.)."""
        mktup = lambda v: (v,) if not isinstance(v, (list, tuple)) else v
        kwds = dict((k, mktup(v)) for k, v in kwds.items())
        for row in iterable:
            if all(row[k] in v for k, v in kwds.items()):
                yield row


class SqliteDataSource(BaseDataSource):
    """SQLite data source."""

    def __init__(self, connection, table):
        """Initialize self."""
        self.__name__ = 'SQLite Table {0!r}'.format(table)
        self._connection = connection
        self._table = table

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)
        column_names = self.columns()
        mkdict = lambda x: dict(zip(column_names, x))
        return (mkdict(row) for row in cursor.fetchall())

    def columns(self):
        """Return list of column names."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def set(self, column, **kwds):
        """Return set of values in column."""
        assert column in self.columns(), 'No column %r' % column
        select_clause = 'DISTINCT "' + column + '"'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return set(x[0] for x in cursor)

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        select_clause = 'SUM("' + column + '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        select_clause = 'COUNT("' + column +  '")'
        cursor = self._execute_query(self._table, select_clause, **kwds)
        return cursor.fetchone()[0]

    def groups(self, *columns, **kwds):
        """Return sorted iterable of unique dictionaries grouped by given columns."""
        column_names = ['"{0}"'.format(x) for x in columns]
        select_clause = 'DISTINCT ' + ', '.join(column_names)
        trailing_clause = 'ORDER BY ' + ', '.join(column_names)
        cursor = self._execute_query(self._table, select_clause,
                                     trailing_clause, **kwds)
        return (dict(zip(columns, x)) for x in cursor)

    def _execute_query(self, table, select_clause, trailing_clause=None, **kwds):
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            #print(stmnt, params)
            cursor.execute(stmnt, params)
        except Exception as e:
            exc_cls = e.__class__
            msg = '%s\n  query: %s\n  params: %r' % (e, stmnt, params)
            raise exc_cls(msg)
        return cursor

    @classmethod
    def _build_query(cls, table, select_clause, **kwds):
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**kwds)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**kwds):
        clause = []
        params = []
        items = kwds.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if hasattr(val, '__iter__') and not isinstance(val, str):
                clause.append(key + ' IN (%s)' % (', '.join('?' * len(val))))
                for x in val:
                    params.append(x)
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params


class _UnicodeCsvReader:
    def __init__(self, file, encoding='utf-8', dialect='excel', **fmtparams):
        self.file = file
        self.dialect = dialect
        self.encoding = encoding
        self.fmtparams = fmtparams

    def __enter__(self):
        self.f = self._get_file_handle(self.file, self.encoding)
        self.reader = csv.reader(self.f, dialect=self.dialect, **self.fmtparams)
        return self

    def __exit__(self, type, value, traceback):
        if self.f != self.file:
            self.f.close()

    def __iter__(self):
        return self

    @staticmethod
    def _get_file_handle(file, encoding):
        if isinstance(file, str):
            return open(file, 'rt', encoding=encoding, newline='')
        if hasattr(file, 'mode'):
            assert 'b' not in file.mode, "File must be open in text mode ('rt')."
        elif issubclass(file.__class__, io.IOBase):
            assert issubclass(file.__class__, io.TextIOBase), ("Stream object must inherit "
                                                               "from io.TextIOBase.")
        file.seek(0)
        return file

    def __next__(self):
        return next(self.reader)


# Patch `_UnicodeCsvReader` if using Python 2.
if sys.version < '3':
    _py3_UnicodeCsvReader = _UnicodeCsvReader
    class _UnicodeCsvReader(_py3_UnicodeCsvReader):
        @staticmethod
        def _get_file_handle(file, encoding):
            if isinstance(file, str):
                return open(file, 'rb')
            if hasattr(file, 'mode'):
                assert 'b' in file.mode, ("When using Python 2, file must "
                                          "be open in binary mode ('rb').")
            elif issubclass(file.__class__, io.IOBase):
                assert not issubclass(file.__class__, io.TextIOBase), ("When using Python 2, "
                                                                       "must use byte stream "
                                                                       "(not text stream).")
            return file

        def next(self):
            row = next(self.reader)
            return [s.decode(self.encoding) for s in row]

        def __next__(self):
            return self.next()


class CsvDataSource(SqliteDataSource):
    """CSV file data source."""

    def __init__(self, file, encoding=None, in_memory=False):
        """Initialize self."""
        # If `file` is relative path, uses directory of calling file as base.
        if isinstance(file, str) and not os.path.isabs(file):
            calling_frame = sys._getframe(1)
            calling_file = inspect.getfile(calling_frame)
            base_path = os.path.dirname(calling_file)
            file = os.path.join(base_path, file)

        # Create database (an empty string denotes use of a temp file).
        sqlite_path = ':memory:' if in_memory else ''
        connection = sqlite3.connect(sqlite_path)

        # Populate database.
        if encoding:
            with _UnicodeCsvReader(file, encoding=encoding) as reader:
                self._populate_database(connection, reader)
        else:
            try:
                with _UnicodeCsvReader(file, encoding='utf-8') as reader:
                    self._populate_database(connection, reader)

            except UnicodeDecodeError:
                with _UnicodeCsvReader(file, encoding='iso8859-1') as reader:
                    self._populate_database(connection, reader)

                try:
                    filename = os.path.basename(file)
                except AttributeError:
                    filename = repr(file)
                msg = ('\nData in file {0!r} does not appear to be encoded '
                       'as UTF-8 (used ISO-8859-1 as fallback). To assure '
                       'correct operation, please specify a text encoding.')
                warnings.warn(msg.format(filename))

        SqliteDataSource.__init__(self, connection, 'main')

    @classmethod
    def _populate_database(cls, connection, reader, table='main'):
        _isolation_level = connection.isolation_level
        connection.isolation_level = None
        cursor = connection.cursor()
        cursor.execute('BEGIN TRANSACTION')
        try:
            csv_header = next(reader)
            statement = cls._build_create_statement(table, csv_header)
            cursor.execute(statement)

            for row in reader:  # Insert all rows.
                if not row:
                    continue  # Skip if row is empty.
                statement, params = cls._build_insert_statement(table, row)
                try:
                    cursor.execute(statement, params)
                except Exception as e:
                    exc_cls = e.__class__
                    msg = ('\n'
                           '    row -> %s\n'
                           '    sql -> %s\n'
                           ' params -> %s' % (row, statement, params))
                    msg = str(e).strip() + msg
                    raise exc_cls(msg)
            connection.commit()

        except Exception as e:
            connection.rollback()
            raise e

        finally:
            connection.isolation_level = _isolation_level  # Restore original.

    @classmethod
    def _build_create_statement(cls, table, columns):
        """Return 'CREATE TABLE' statement."""
        cls._assert_unique(columns)
        columns = [cls._normalize_column(x) for x in columns]
        return 'CREATE TABLE %s (%s)' % (table, ', '.join(columns))

    @staticmethod
    def _build_insert_statement(table, row):
        """Return 'INSERT INTO' statement."""
        statement = 'INSERT INTO ' + table + ' VALUES (' + ', '.join(['?'] * len(row)) + ')'
        parameters = row
        return statement, parameters

    @staticmethod
    def _normalize_column(name):
        """Normalize value for use as SQLite column name."""
        name = name.strip()
        name = name.replace('"', '""')  # Escape quotes.
        if name == '':
            name = '_empty_'
        return '"' + name + '"'

    @staticmethod
    def _assert_unique(lst):
        """Asserts that list of items is unique, raises Exception if not."""
        values = []
        duplicates = []
        for x in lst:
            if x in values:
                if x not in duplicates:
                    duplicates.append(x)
            else:
                values.append(x)

        if duplicates:
            raise ValueError('Duplicate values: ' + ', '.join(duplicates))


class MultiDataSource(BaseDataSource):
    """Composite of multiple data source objects."""

    def __init__(self, *sources):
        """Initialize self."""
        for source in sources:
            msg = 'Sources must be derived from BaseDataSource'
            assert isinstance(source, BaseDataSource), msg
        self.sources = sources

    def slow_iter(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        for source in self.sources:
            for row in source.slow_iter():
                for col in columns:
                    if col not in row:
                        row[col] = ''
                yield row

    def columns(self):
        """Return sequence or collection of column names."""
        columns = []
        for source in self.sources:
            for col in source.columns():
                if col not in columns:
                    columns.append(col)  # TODO: Look at improving order!
        return columns

    def set(self, column, **kwds):
        """Return set of values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        result_sets = []
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                result_sets.append(source.set(column, **subkwds))
            else:
                result_sets.append(set(['']))

        return set(itertools.chain(*result_sets))

    def sum(self, column, **kwds):
        """Return sum of values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                result = source.sum(column, **subkwds)
                if result:
                    total_result += result

        return total_result

    def count(self, column, **kwds):
        """Return count of non-empty values in column."""
        if column not in self.columns():
            msg = 'No sub-sources not contain {0!r} column.'.format(column)
            raise Exception(msg)

        total_result = 0
        for source in self.sources:
            subcols = source.columns()
            if column in subcols:
                if any(v != '' for k, v in kwds.items() if k not in subcols):
                    continue
                subkwds = dict((k, v) for k, v in kwds.items() if k in subcols)
                total_result += source.count(column, **subkwds)

        return total_result

    #def groups(self, *columns, **kwds):
    #    """Return unsorted iterable of unique dictionaries grouped by given columns."""


#DefaultDataSource = CsvDataSource
