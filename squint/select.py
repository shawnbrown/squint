# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sqlite3
from glob import glob

from get_reader import get_reader

from ._compatibility.builtins import *
from ._compatibility import (
    functools,
    itertools,
)
from ._compatibility.collections.abc import (
    Hashable,
    Mapping,
    Sequence,
    Set,
)
from ._vendor.load_csv import (
    load_csv,
)
from ._vendor.predicate import (
    MatcherObject,
    MatcherTuple,
    get_matcher,
)
from ._vendor.temptable import (
    load_data,
    new_table_name,
    savepoint,
    table_exists,
)
from ._utils import (
    file_types,
    string_types,
)
from .query import (
    BaseQuery,
    _get_iteritems,
    _parse_columns,
)
from .result import (
    Result,
)


try:
    FileNotFoundError  # New in Python 3.3.
except NameError:
    # If not available, use as an alias for OSError.
    FileNotFoundError = OSError


# For the following database connection, the synchronous flag is
# set to "OFF" for faster insertions and commits. Since the database
# is temporary, long-term integrity should not be a concern--in the
# unlikely event of data corruption, it should be entirely acceptable
# to simply rebuild the temporary tables.
DEFAULT_CONNECTION = sqlite3.connect('')  # <- Using '' makes a temp file.
DEFAULT_CONNECTION.execute('PRAGMA synchronous=OFF')
DEFAULT_CONNECTION.isolation_level = None  # <- Run in 'autocommit' mode.
_user_function_name_gen = ('FUNC{0}'.format(x) for x in itertools.count())


class Select(object):
    """A class to quickly load and select tabular data. The given
    *objs*, *\\*args*, and *\\*\\*kwds*, can be any values supported
    by :class:`get_reader()`. Additionally, *objs* can be a list
    of supported objects or a string with shell-style wildcards.
    If *objs* is already a reader-like object, it will be used as
    is.

    Load a single file::

        select = datatest.Select('myfile.csv')

    Load a reader-like iterable::

        select = datatest.Select([
            ['A', 'B'],
            ['x', 100],
            ['y', 200],
            ['z', 300],
        ])

    Load multiple files::

        select = datatest.Select(['myfile1.csv', 'myfile2.csv'])

    Load multple files using a shell-style wildcard::

        select = datatest.Select('*.csv')
    """
    def __init__(self, objs=None, *args, **kwds):
        """Initialize self."""
        self._connection = DEFAULT_CONNECTION
        self._user_function_dict = dict()  # User-defined SQLite functions.
        self._table = None  # Table name.
        self._obj_strings = []  # Strings for repr().
        if objs:
            try:
                self.load_data(objs, *args, **kwds)
            except FileNotFoundError:
                __tracebackhide__ = True
                raise

    def load_data(self, objs, *args, **kwds):
        """Load data from one or more objects into the Select. The
        given *objs*, *\\*args*, and *\\*\\*kwds*, can be any values
        supported by the :class:`Select` class initialization.

        Load a single file into an empty Select::

            select = datatest.Select()  # <- Empty Select.
            select.load_data('myfile.csv')

        Add a single file to an already-populated Select::

            select = datatest.Select('myfile1.csv')
            select.load_data('myfile2.xlsx', worksheet='Sheet2')

        Add multiple files to an already-populated Select::

            select = datatest.Select('myfile1.csv')
            select.load_data(['myfile2.csv', 'myfile3.csv'])
        """
        if isinstance(objs, string_types):
            obj_list = glob(objs)  # Get shell-style wildcard matches.
            if not obj_list:
                __tracebackhide__ = True
                raise FileNotFoundError('no files matching {0!r}'.format(objs))
        elif not isinstance(objs, list) \
                or isinstance(objs[0], (list, tuple, dict)):  # Not a list or is a
            obj_list = [objs]                                 # reader-like list.
        else:
            obj_list = objs

        cursor = self._connection.cursor()
        with savepoint(cursor):
            table = self._table or new_table_name(cursor)
            for obj in obj_list:
                if ((
                        isinstance(obj, string_types)
                        and obj.lower().endswith('.csv')
                    ) or (
                        isinstance(obj, file_types)
                        and getattr(obj, 'name', '').lower().endswith('.csv')
                    )
                ):
                    load_csv(cursor, table, obj, *args, **kwds)
                else:
                    reader = get_reader(obj, *args, **kwds)
                    load_data(cursor, table, reader)

                self._append_obj_string(obj)

        if not self._table and table_exists(cursor, table):
            self._table = table

    def _append_obj_string(self, obj):
        """Get string for *obj*, limit to one line, and append to list."""
        obj_str = repr(obj)
        obj_str = ' '.join(obj_str.split())  # Normalize whitespace.

        # Truncate to 63 characters. The limit of 63 was chosen
        # so that the repr for a single-source Select will never
        # exceed 72 characters (63 + len of other repr parts = 72).
        if len(obj_str) > 63:
            obj_str = '{0}...{1}'.format(obj_str[:52], obj_str[-8:])

        self._obj_strings.append(obj_str)

    def __repr__(self):
        """Return a string representation of the data source."""
        if not self._obj_strings:
            return '<Select (no data loaded)>'

        if len(self._obj_strings) == 1:
            return '<Select {0}>'.format(self._obj_strings[0])

        return '<Select ({0} sources):\n    {1}>'.format(
            len(self._obj_strings),
            '\n    '.join(sorted(self._obj_strings)),
        )

    @property
    def fieldnames(self):
        """A list of field names used by the data source."""
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info({0})'.format(self._table))
        return [x[1] for x in cursor]

    def __call__(self, columns, **where):
        """After a Select has been created, it can be called like a
        function to select fields and return an associated :class:`Query`
        object.

        The *columns* argument serves as a template to define the values
        and data types selected. All *columns* selections will be wrapped
        in an outer container. When a container is unspecified, a
        :py:class:`list` is used as the default::

            select = datatest.Select('example.csv')
            query = select('A')  # <- selects a list of values from 'A'

        When *columns* specifies an outer container, it must hold only
        one field---if a given container holds multiple fields, it is
        assumed to be an inner container (which gets wrapped in the
        default outer container)::

            query = select(('A', 'B'))  # <- selects a list of tuple
                                        #    values from 'A' and 'B'

        When *columns* is a :py:class:`dict`, values are grouped by
        key::

            query = select({'A': 'B'})  # <- selects a dict with
                                        #    keys from 'A' and
                                        #    values from 'B'

        Optional *where* keywords can narrow the selected data to
        matching rows. A key must specify the field to check and a
        value must be a predicate object (see :ref:`predicate-docs`
        for details). Rows where the predicate is a match are
        selected and rows where it doesn't match are excluded::

            select = datatest.Select('example.csv')
            query = select({'A'}, B='foo')  # <- selects only the rows
                                            #    where 'B' equals 'foo'

        See the :ref:`making-selections` tutorial for step-by-step
        examples.
        """
        try:
            return Query(self, columns, **where)
        except LookupError:
            __tracebackhide__ = True
            raise

    def _execute_query(self, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            # Build select-query.
            stmnt = 'SELECT {0} FROM {1}'.format(select_clause, self._table)
            where_clause, params = self._build_where_clause(kwds_filter)
            if where_clause:
                stmnt = '{0} WHERE {1}'.format(stmnt, where_clause)
            if trailing_clause:
                stmnt = '{0}\n{1}'.format(stmnt, trailing_clause)

            # Execute query.
            cursor = self._connection.cursor()
            cursor.execute(stmnt, params)

        except Exception as e:
            exc_cls = e.__class__
            msg = '{0}\n  query: {1}\n  params: {2}'.format(e, stmnt, params)
            raise exc_cls(msg)

        return cursor

    def _build_where_clause(self, where_dict):
        """Return SQL 'WHERE' clause that implements *where* keyword
        constraints.
        """
        clause = []
        params = []
        items = where_dict.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if isinstance(val, Set):
                clause.append('{key} IN ({qmarks})'.format(
                    key=key,
                    qmarks=', '.join('?' * len(val))
                ))
                params.extend(val)
            elif callable(val) and not isinstance(val, type):
                func_name = self._get_user_function(val)
                clause.append('{0}({1})'.format(func_name, key))
            else:
                pred = get_matcher(val)
                if isinstance(pred, MatcherObject):
                    func_name = self._get_user_function(pred._func, keyref=val)
                    clause.append('{0}({1})'.format(func_name, key))
                elif isinstance(pred, MatcherTuple):
                    def func(x):
                        return pred == x
                    func_name = self._get_user_function(func, keyref=val)
                    clause.append('{0}({1})'.format(func_name, key))
                else:
                    clause.append(key + '=?')
                    params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def _get_user_function(self, func, keyref=None):
        """Returns SQLite user-defined function name. If *keyref* is
        provided, it is used to generate the lookup-key for fetching
        (and storing) the function name from the _user_function_dict
        property.
        """
        if not keyref:
            keyref = func

        try:
            func_key = hash(keyref)
        except TypeError:
            func_key = id(keyref)

        try:
            return self._user_function_dict[func_key]
        except KeyError:
            self._create_user_function(func, func_key)
            return self._user_function_dict[func_key]

    def _create_user_function(self, func, func_key=None):
        """Register *func* with the SQLite connection using an
        automatically generated function name. Add the new name
        to the _user_function_dict using the given *func_key*.
        """
        if not func_key:
            try:
                func_key = hash(func)
            except TypeError:
                func_key = id(func)

        if func_key in self._user_function_dict:
            raise ValueError('function {0!r} already registered'.format(func))

        if not isinstance(func, Hashable):
            _func = func
            @functools.wraps(_func)
            def func(x):
                return _func(x)

        func_name = next(_user_function_name_gen)
        self._connection.create_function(func_name, 1, func)  # <- Register!
        self._user_function_dict[func_key] = func_name

    def _format_result_group(self, columns, cursor):
        outer_type = type(columns)
        inner_type = type(next(iter(columns)))
        if issubclass(inner_type, str):
            result = (row[0] for row in cursor)
        elif issubclass(inner_type, tuple) and hasattr(inner_type, '_fields'):
            result = (inner_type(*x) for x in cursor)  # If namedtuple.
        else:
            result = (inner_type(x) for x in cursor)
        return Result(result, evaltype=outer_type) # <- EXIT!

    def _format_results(self, columns, cursor):
        """Return an iterator of results formatted by *columns*
        types from DBAPI2-compliant *cursor*.

        The *columns* can be a string, sequence, set or mapping--see
        the _select() method for details.
        """
        if isinstance(columns, (Sequence, Set)):
            return self._format_result_group(columns, cursor)

        if isinstance(columns, Mapping):
            result_type = type(columns)
            key, value = tuple(columns.items())[0]
            key_type = type(key)
            slice_index = 1 if issubclass(key_type, str) else len(key)

            if issubclass(key_type, str):
                keyfunc = lambda row: row[0]
            elif issubclass(key_type, tuple) and hasattr(key_type, '_fields'):
                keyfunc = lambda row: key_type(*row[:slice_index])  # If namedtuple.
            else:
                keyfunc = lambda row: key_type(row[:slice_index])
            grouped = itertools.groupby(cursor, keyfunc)

            inner = next(iter(value))
            index = 1 if isinstance(inner, str) else len(inner)
            sliced = ((k, (x[-index:] for x in g)) for k, g in grouped)
            formatted = ((k, self._format_result_group(value, g)) for k, g in sliced)
            iteritems =  _get_iteritems(formatted)
            return Result(iteritems, evaltype=result_type) # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(columns)))

    def _assert_fields_exist(self, fieldnames):
        """Assert that given fieldnames are present in data source,
        raises LookupError if fields are missing.
        """
        available = self.fieldnames
        for name in fieldnames:
            if name not in available:
                msg = '{0!r} not in {1!r}'.format(name, self)
                __tracebackhide__ = True
                raise LookupError(msg)

    def _escape_field_name(self, name):
        """Escape field names for SQLite."""
        name = name.replace('"', '""')
        return '"{0}"'.format(name)

    def _parse_key_value(self, key, value):
        key_columns = (key,) if isinstance(key, str) else tuple(key)
        value = tuple(value)[0]
        value_columns = (value,) if isinstance(value, str) else  tuple(value)
        self._assert_fields_exist(key_columns)
        self._assert_fields_exist(value_columns)
        key_columns = tuple(self._escape_field_name(x) for x in key_columns)
        value_columns = tuple(self._escape_field_name(x) for x in value_columns)

        return key_columns, value_columns

    def _select(self, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        select_clause = ', '.join(key_columns + value_columns)
        if isinstance(value, Set):
            select_clause = 'DISTINCT ' + select_clause

        if key:
            order_by = 'ORDER BY {0}'.format(', '.join(key_columns))
        else:
            order_by = None
        cursor = self._execute_query(select_clause, order_by, **where)
        return self._format_results(columns, cursor)

    def _select_distinct(self, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        all_columns = ', '.join(key_columns + value_columns)
        select_clause = 'DISTINCT {0}'.format(all_columns)
        if key:
            order_by = 'ORDER BY {0}'.format(', '.join(key_columns))
        else:
            order_by = None
        cursor = self._execute_query(select_clause, order_by, **where)
        return self._format_results(columns, cursor)

    def _select_aggregate(self, sqlfunc, columns, **where):
        key, value = _parse_columns(columns)
        key_columns, value_columns = self._parse_key_value(key, value)

        if isinstance(value, Set):
            func = lambda col: 'DISTINCT {0}'.format(col)
            value_columns = tuple(func(col) for col in value_columns)

        sqlfunc = sqlfunc.upper()
        value_columns = tuple('{0}({1})'.format(sqlfunc, x) for x in value_columns)
        select_clause = ', '.join(key_columns + value_columns)
        if key:
            group_by = 'GROUP BY {0}'.format(', '.join(key_columns))
        else:
            group_by = None
        cursor = self._execute_query(select_clause, group_by, **where)
        results =  self._format_results(columns, cursor)

        if isinstance(columns, Mapping):
            results = _get_iteritems((k, next(v)) for k, v in results)
            return Result(results, evaltype=dict)
        return next(results)

    def __iter__(self):
        columns = self.fieldnames
        query = self(columns)
        return query.__iter__()

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up
        testing in many cases.

        If you repeatedly use the same few columns to group or
        filter results, then you can often improve performance by
        adding an index for these columns::

            select.create_index('town')

        Using two or more columns creates a multi-column index::

            select.create_index('town', 'postal_code')

        Calling the function multiple times will create multiple
        indexes::

            select.create_index('town')
            select.create_index('postal_code')

        .. note:: Indexes should be added with discretion to tune
                  a test suite's over-all performance.  Creating
                  several indexes before testing even begins could
                  lead to longer run times so use indexes with care.
        """
        try:
            self._assert_fields_exist(columns)
        except LookupError:
            __tracebackhide__ = True
            raise

        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        columns = tuple(self._escape_field_name(x) for x in columns)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, ', '.join(columns))

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute(statement)

    # NOTE: Do NOT add to_csv() method to Select. It's simple
    # enough to use Query.to_csv() as below:
    #
    #     select(select.fieldnames).to_csv(...)
    #


class Query(BaseQuery):
    """Query(columns, **where)
    Query(select, columns, **where)

    A class to query data from a source object.

    See documentation for full details.
    """
    @property
    def _select_cls(self):
        return Select
