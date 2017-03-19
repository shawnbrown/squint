# -*- coding: utf-8 -*-
from __future__ import absolute_import
import abc
import collections
import functools
import io
import itertools
import os
import sys
from numbers import Number
from sqlite3 import Binary

from .utils.builtins import *
from .utils.misc import _is_nsiterable
from .utils.misc import _get_calling_filename
from .utils.misc import _is_sortable
from .utils.misc import _unique_everseen
from .load.sqltemp import TemporarySqliteTable
from .load.sqltemp import _from_csv


class ItemsIter(collections.Iterator):
    """A simple wrapper used to identify iterators that should
    return a 2-tuple of key-value pairs. The underlying iterable
    should not contain duplicate keys and it should be appropriate
    for constructing a dictionary or other mapping.
    """
    def __init__(self, iterable):
        while hasattr(iterable, '__wrapped__'):
            iterable = iterable.__wrapped__
        self.__wrapped__ = iter(iterable)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.


def _is_collection_of_items(obj):
    while hasattr(obj, '__wrapped__'):
        if isinstance(obj, ItemsIter):
            return True
        obj = obj.__wrapped__
    return isinstance(obj, collections.ItemsView)


class DataResult(collections.Iterator):
    """An iterator of results from a :class:`DataQuery` object.
    While they are usually constructed inernally when executing
    a query, it's possible to create them directly::

        iterable = iter([...])
        data = DataResult(iterable, evaluation_type=list)

    The *iterable* is expected to return data appropriate for
    constructing an object of the given *evaluation_type*. When
    the *evaluation_type* is a :py:class:`dict` or other mapping,
    the *iterable* should contain suitable key-value pairs.

    The primary purpose of this wrapper is to facilitate the lazy
    evaluation of data objects (where possible) when asserting
    data validity.
    """
    def __init__(self, iterable, evaluation_type):
        if not isinstance(evaluation_type, type):
            msg = 'evaluation_type must be a type, found instance of {0}'
            raise TypeError(msg.format(evaluation_type.__class__.__name__))

        while (hasattr(iterable, '__wrapped__')
                   and not isinstance(iterable, ItemsIter)):
            iterable = iterable.__wrapped__

        if isinstance(iterable, collections.Mapping):
            iterable = ItemsIter(iterable.items())

        if (issubclass(evaluation_type, collections.Mapping)
                and not _is_collection_of_items(iterable)):
            cls_name = iterable.__class__.__name__
            raise TypeError('when evaluation_type is a mapping, '
                            'iterator must be ItemsIter or ItemsView, '
                            'found {0} instead'.format(cls_name))

        #: The underlying iterator---useful when introspecting
        #: or rewrapping.
        self.__wrapped__ = iter(iterable)

        #: The type of instance returned by the
        #: :meth:`evaluate <DataResult.evaluate>` method.
        self.evaluation_type = evaluation_type

    def __iter__(self):
        return self

    def __repr__(self):
        cls_name = self.__class__.__name__
        eval_name = self.evaluation_type.__name__
        hex_id = hex(id(self))
        template = '<{0} object (evaluation_type={1}) at {2}>'
        return template.format(cls_name, eval_name, hex_id)

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.

    def evaluate(self):
        """Evaluate the entire iterator and return its result::

            iterable = iter([...])
            data = DataResult(iterable, evaluation_type=list)
            data_list = data.evaluate()  # <- Returns a list of values.

        When evaluating the keys and values of a :py:class:`dict`
        or other mapping, any values that are, themselves,
        :class:`DataResult` objects will also be evaluated.
        """
        evaluation_type = self.evaluation_type
        if issubclass(evaluation_type, collections.Mapping):
            def func(obj):
                if hasattr(obj, 'evaluation_type'):
                    return obj.evaluation_type(obj)
                return obj

            return evaluation_type((k, func(v)) for k, v in self)

        return evaluation_type(self)


def _get_evaluation_type(obj):
    """Return object's evaluation_type property. If the object does
    not have an evaluation_type property and is a mapping, sequence,
    or set, then return the type of the object itself. If the object
    is an iterable, return None. Raises a Type error for any other
    object.
    """
    if hasattr(obj, 'evaluation_type'):
        return obj.evaluation_type  # <- EXIT!

    #if _is_collection_of_items(obj):
    #    return dict

    if isinstance(obj, (collections.Mapping,
                        collections.Sequence,
                        collections.Set)):
        return type(obj)  # <- EXIT!

    if isinstance(obj, collections.Iterable):
        return None  # <- EXIT!

    cls_name = obj.__class__.__name__
    err_msg = 'unable to determine intended type for {0!r} instance'
    raise TypeError(err_msg.format(cls_name))


def _apply_to_data(function, data_iterator):
    """Apply a *function* of one argument to the to the given
    iterator *data_iterator*.
    """
    if _is_collection_of_items(data_iterator):
        result = ItemsIter((k, function(v)) for k, v in data_iterator)
        return DataResult(result, _get_evaluation_type(data_iterator))
    return function(data_iterator)


def _map_data(function, iterable):
    def wrapper(iterable):
        if _is_nsiterable(iterable):
            evaluation_type = _get_evaluation_type(iterable)
            return DataResult(map(function, iterable), evaluation_type)
        return function(iterable)

    return _apply_to_data(wrapper, iterable)


def _reduce_data(function, iterable):
    def wrapper(iterable):
        if not _is_nsiterable(iterable):
            return iterable  # <- Not iterable, return object.
        return functools.reduce(function, iterable)

    return _apply_to_data(wrapper, iterable)


def _filter_data(function, iterable):
    def wrapper(iterable):
        if not _is_nsiterable(iterable):
            msg= 'filter expects a non-string iterable, found {0}'
            raise TypeError(msg.format(iterable.__class__.__name__))
        filtered_data = filter(function, iterable)
        return DataResult(filtered_data, _get_evaluation_type(iterable))

    return _apply_to_data(wrapper, iterable)


def _sqlite_cast_as_real(value):
    """Convert value to REAL (float) or default to 0.0 to match SQLite
    behavior. See the "Conversion Processing" table in the "CAST
    expressions" section for details:

        https://www.sqlite.org/lang_expr.html#castexpr
    """
    # TODO: Implement behavioral parity with SQLite and add tests.
    try:
        return float(value)
    except ValueError:
        return 0.0


def _sqlite_sum(iterable):
    """Sum the elements and return the total (should match SQLite
    behavior).
    """
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


def _sqlite_count(iterable):
    """Return the number non-NULL (!= None) elements in iterable."""
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    return sum(1 for x in iterable if x != None)


# The SQLite BLOB/Binary type in sortable Python 2 but unsortable in Python 3.
_unsortable_blob_type = not _is_sortable(Binary(b'0'))


def _sqlite_sortkey(value):
    """Key function for use with sorted(), min(), max(), etc. that
    makes a best effort to match SQLite ORDER BY behavior for
    supported classes.

    From SQLite docs:

        "...values with storage class NULL come first, followed by
        INTEGER and REAL values interspersed in numeric order, followed
        by TEXT values in collating sequence order, and finally BLOB
        values in memcmp() order."

    For more details see "Datatypes In SQLite Version 3" section
    "4.1. Sort Order" <https://www.sqlite.org/datatype3.html>.
    """
    if value is None:              # NULL (sort group 0)
        return (0, 0)
    if isinstance(value, Number):  # INTEGER and REAL (sort group 1)
        return (1, value)
    if isinstance(value, str):     # TEXT (sort group 2)
        return (2, value)
    if isinstance(value, Binary):  # BLOB (sort group 3)
        if _unsortable_blob_type:
            value = bytes(value)
        return (3, value)
    return (4, value)  # unsupported type (sort group 4)


def _sqlite_avg(iterable):
    """Return the average of elements in iterable. Returns None if all
    elements are None.
    """
    if not _is_nsiterable(iterable):
        iterable = [iterable]
    iterable = (x for x in iterable if x != None)
    total = 0.0
    count = 0
    for x in iterable:
        total = total + _sqlite_cast_as_real(x)
        count += 1
    return total / count if count else None


def _sqlite_min(iterable):
    """Return the minimum non-None value of all values. Returns
    None only if all values are None.
    """
    if not _is_nsiterable(iterable):
        return iterable  # <- EXIT!
    iterable = (x for x in iterable if x != None)
    return min(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_max(iterable):
    """Return the maximum value of all values. Returns None if all
    values are None.
    """
    if not _is_nsiterable(iterable):
        return iterable  # <- EXIT!
    return max(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_distinct(iterable):
    """Filter iterable to unique values, while maintaining
    evaluation_type.
    """
    def dodistinct(itr):
        if not _is_nsiterable(itr):
            return itr
        return DataResult(_unique_everseen(itr), _get_evaluation_type(itr))

    if _is_collection_of_items(iterable):
        result = ItemsIter((k, dodistinct(v)) for k, v in iterable)
        return DataResult(result, _get_evaluation_type(iterable))
    return dodistinct(iterable)


def _cast_as_set(iterable):
    """Change evaluation_type to set."""
    def makeset(itr):
        if not _is_nsiterable(itr):
            itr = [itr]
        return DataResult(itr, evaluation_type=set)

    if _is_collection_of_items(iterable):
        result = ItemsIter((k, makeset(v)) for k, v in iterable)
        return DataResult(result, _get_evaluation_type(iterable))
        # TODO: Check above line looks like it's eagerly evaluating.
    return makeset(iterable)


def _set_data(iterable):
    """Filter iterable to unique values and change evaluation_type to
    set.
    """
    return _cast_as_set(_sqlite_distinct(iterable))


def _get_step_repr(step):
    """Helper function to return repr for a single query step."""
    func, args, kwds = step

    def _callable_name_or_repr(x):  # <- Helper function for
        if callable(x):             #    the helper function!
            try:
                return x.__name__
            except NameError:
                pass
        return repr(x)

    func_repr = _callable_name_or_repr(func)

    args_repr = ', '.join(_callable_name_or_repr(x) for x in args)

    kwds_repr = kwds.items()
    kwds_repr = [(k, _callable_name_or_repr(v)) for k, v in kwds_repr]
    kwds_repr = ['{0}={1}'.format(k, v) for k, v in kwds_repr]
    kwds_repr = ', '.join(kwds_repr)
    return '{0}, ({1}), {{{2}}}'.format(func_repr, args_repr, kwds_repr)


_query_step = collections.namedtuple(
    typename='query_step',
    field_names=('name', 'args', 'kwds')
)
_execution_step = collections.namedtuple(
    typename='execution_step',
    field_names=('function', 'args', 'kwds')
)


class _RESULT_TOKEN(object):
    def __repr__(self):
        return '<RESULT>'
RESULT_TOKEN = _RESULT_TOKEN()
del _RESULT_TOKEN


class DataQuery(object):
    """A class to query data from a :class:`DataSource` object.

    A DataQuery can be created and passed around without actually
    computing the result. No data computation occurs until the
    :meth:`execute` method is called.
    """
    def __init__(self, selection, **where):
        self._query_steps = tuple([
            _query_step('select', (selection,), where),
        ])
        self._source = None

    @staticmethod
    def _validate_source(source):
        if not isinstance(source, DataSource):
            raise TypeError('expected {0!r}, got {1!r}'.format(
                DataSource.__name__,
                source.__class__.__name__,
            ))

    #@staticmethod
    #def _validate_steps(steps):
    #    pass

    @classmethod
    def _from_parts(cls, query_steps=None, source=None):
        # TODO: Make query_steps mandatory (should not allow None).
        if source:
            cls._validate_source(source)

        if query_steps:
            query_steps = tuple(query_steps)
        else:
            query_steps = tuple()

        new_cls = cls.__new__(cls)
        new_cls._query_steps = query_steps
        new_cls._source = source
        return new_cls

    def _add_step(self, name, *args, **kwds):
        steps = self._query_steps + (_query_step(name, args, kwds),)
        new_query = self.__class__._from_parts(steps, self._source)
        return new_query

    def map(self, function):
        """Apply *function* to each value keeping the resulting data."""
        return self._add_step('map', function)

    def filter(self, function):
        """Filter data, keeping only those values for which *function*
        returns true. If *function* is None, this method keeps all
        values for which :py:class:`bool` returns true.
        """
        return self._add_step('filter', function)

    def reduce(self, function):
        """Reduce data to a single value by applying a *function* of
        two arguments cumulatively to all values from left to right.
        """
        return self._add_step('reduce', function)

    def sum(self):
        """Sum all non-None values in the group to produce a total."""
        return self._add_step('sum')

    def count(self):
        """Count the number of all non-None values in the group."""
        return self._add_step('count')

    def avg(self):
        """Get the average value of all non-None values. String and
        other objects that do not look like numbers are interpreted
        as 0.
        """
        return self._add_step('avg')

    def min(self):
        """Get the minimum value of all values."""
        return self._add_step('min')

    def max(self):
        """Get the maximum value of all values."""
        return self._add_step('max')

    def distinct(self):
        """Filter data, removing duplicate values."""
        return self._add_step('distinct')

    def set(self):
        """Change result's evaluation type to :py:class:`set`."""
        return self._add_step('set')

    @staticmethod
    def _translate_step(query_step):
        """Accept a query step and return a corresponding execution
        step.
        """
        name, query_args, query_kwds = query_step

        if name == 'map':
            function = _map_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'filter':
            function = _filter_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'reduce':
            function = _reduce_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'sum':
            function = _apply_to_data
            args = (_sqlite_sum, RESULT_TOKEN)
        elif name == 'count':
            function = _apply_to_data
            args = (_sqlite_count, RESULT_TOKEN)
        elif name == 'avg':
            function = _apply_to_data
            args = (_sqlite_avg, RESULT_TOKEN)
        elif name == 'min':
            function = _apply_to_data
            args = (_sqlite_min, RESULT_TOKEN)
        elif name == 'max':
            function = _apply_to_data
            args = (_sqlite_max, RESULT_TOKEN)
        elif name == 'distinct':
            function = _sqlite_distinct
            args = (RESULT_TOKEN,)
        elif name == 'set':
            function = _set_data
            args = (RESULT_TOKEN,)
        elif name == 'select':
            raise ValueError("this method does not handle 'select' step")
        else:
            raise ValueError('unrecognized query function {0!r}'.format(name))

        return _execution_step(function, args, {})

    @classmethod
    def _get_execution_plan(cls, query_steps):
        if not query_steps:
            return ()
        query_steps = iter(query_steps)
        first_name, first_args, first_kwds = next(query_steps)
        assert first_name == 'select', "first query step must be a 'select'"
        execution_plan = [
            _execution_step(getattr, (RESULT_TOKEN, '_select'), {}),
            _execution_step(RESULT_TOKEN, first_args, first_kwds),
        ]
        for query_step in query_steps:
            execution_step = cls._translate_step(query_step)
            execution_plan.append(execution_step)
        return tuple(execution_plan)

    @staticmethod
    def _optimize(execution_plan):
        try:
            step_0 = execution_plan[0]
            step_1 = execution_plan[1]
            step_2 = execution_plan[2]
            remaining_steps = execution_plan[3:]
        except IndexError:
            return None  # <- EXIT!

        if step_0 != (getattr, (RESULT_TOKEN, '_select'), {}):
            return None  # <- EXIT!

        if step_2[0] == _apply_to_data:
            func_dict = {
                _sqlite_sum: 'SUM',
                _sqlite_count: 'COUNT',
                _sqlite_avg: 'AVG',
                _sqlite_min: 'MIN',
                _sqlite_max: 'MAX',
            }
            py_function = step_2[1][0]
            sqlite_function = func_dict.get(py_function, None)
            if sqlite_function:
                func_1, args_1, kwds_1 = step_1
                args_1 = (sqlite_function,) + args_1  # <- Add SQL function
                optimized_steps = (                   #    as 1st arg.
                    (getattr, (RESULT_TOKEN, '_select_aggregate'), {}),
                    (func_1, args_1, kwds_1),
                )
            else:
                optimized_steps = ()
        elif step_2 == (_sqlite_distinct, (RESULT_TOKEN,), {}):
            optimized_steps = (
                (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
                step_1,
            )
        elif step_2 == (_set_data, (RESULT_TOKEN,), {}):
            optimized_steps = (
                (getattr, (RESULT_TOKEN, '_select_distinct'), {}),
                step_1,
                (_cast_as_set, (RESULT_TOKEN,), {}),
            )
        else:
            optimized_steps = ()

        if optimized_steps:
            return optimized_steps + remaining_steps
        return None

    def execute(self, source=None, **kwds):
        """
        execute(source=None, *, evaluate=True, optimize=True)

        Execute the query and return its result. A *source* is
        unnecessary if the query was created by a :class:`DataSource`
        call. But a *source* must be provied if the query was created
        directly.

        By default, results are eagerly evaluated and loaded into
        memory. For lazy evaluation, set *evaluate* to False to
        return a :class:`DataResult` iterator instead.

        Set *optimize* to False to turn-off query optimization.
        """
        result = source or self._source
        if result is None:
            raise ValueError('must provide source, None found')
        self._validate_source(result)

        evaluate = kwds.pop('evaluate', True)  # Emulate keyword-only
        optimize = kwds.pop('optimize', True)  # behavior for 2.7 and
        if kwds:                               # 2.6 compatibility.
            key, _ = kwds.popitem()
            raise TypeError('got an unexpected keyword '
                            'argument {0!r}'.format(key))

        execution_plan = self._get_execution_plan(self._query_steps)
        if optimize:
            execution_plan = self._optimize(execution_plan) or execution_plan

        replace_token = lambda x: result if x is RESULT_TOKEN else x
        for step in execution_plan:
            function, args, keywords = step  # Unpack 3-tuple.
            function = replace_token(function)
            args = tuple(replace_token(x) for x in args)
            keywords = dict((k, replace_token(v)) for k, v in keywords.items())
            result = function(*args, **keywords)

        if isinstance(result, DataResult) and evaluate:
            result = result.evaluate()

        return result

    def _explain(self, optimize=True, file=sys.stdout):
        """A convenience method primarily intended to help when
        debugging and developing execution plan optimizations.

        Prints execution plan to the text stream *file* (defaults
        to stdout). If *optimize* is True, an optimized plan will
        be printed if one can be constructed.

        If *file* is set to None, returns execution plan as a string.
        """
        execution_plan = self._get_execution_plan(self._query_steps)

        optimized_text = ''
        if optimize:
            optimized_plan = self._optimize(execution_plan)
            if optimized_plan:
                execution_plan = optimized_plan
                optimized_text = ' (optimized)'

        steps = [_get_step_repr(step) for step in execution_plan]
        steps = '\n'.join('  {0}'.format(step) for step in steps)
        formatted = 'Execution Plan{0}:\n{1}'.format(optimized_text, steps)

        if file:
            file.write(formatted)
            file.write('\n')
        else:
            return formatted


class DataSource(object):
    """A basic data source to quickly load and query data.

    The given *data* should be an iterable of rows. The rows
    themselves can be lists (as below), dictionaries, or other
    sequences or mappings. *columns* must be a sequence of strings
    to use when referencing data by column name::

        data = [
            ['x', 100],
            ['y', 200],
            ['z', 300],
        ]
        columns = ['A', 'B']
        source = datatest.DataSource(data, columns)

    If *data* is an iterable of :py:class:`dict` or
    :py:func:`namedtuple <collections.namedtuple>` rows,
    then *columns* can be omitted::

        data = [
            {'A': 'x', 'B': 100},
            {'A': 'y', 'B': 200},
            {'A': 'z', 'B': 300},
        ]
        source = datatest.DataSource(data)
    """
    def __init__(self, data, columns=None):
        """Initialize self."""
        temptable = TemporarySqliteTable(data, columns)
        self._connection = temptable.connection
        self._table = temptable.name

    @classmethod
    def from_csv(cls, file, encoding=None, relative_to=None, **fmtparams):
        """Create a DataSource from a CSV *file* (a path or file-like
        object)::

            source = datatest.DataSource.from_csv('mydata.csv')

        If *file* is an iterable of files, data will be loaded and
        aligned by column name::

            files = ['mydata1.csv', 'mydata2.csv']
            source = datatest.DataSource.from_csv(files)
        """
        if not _is_nsiterable(file) or isinstance(file, io.IOBase):
            file = [file]

        if relative_to is None:
            relative_to = _get_calling_filename(frame_index=2)
        dirname = os.path.dirname(relative_to)

        def get_path(f):
            if isinstance(f, str) and not os.path.isabs(f):
                f = os.path.join(dirname, f)
                return os.path.normpath(f)
            return f
        file = [get_path(f) for f in file]

        new_cls = cls.__new__(cls)
        temptable = _from_csv(file, encoding, **fmtparams)
        new_cls._connection = temptable.connection
        new_cls._table = temptable.name
        return new_cls

    @classmethod
    def from_excel(cls, path, worksheet=0):
        """Create a DataSource from an Excel worksheet. The *path*
        must specify to an XLSX or XLS file and the *worksheet* must
        specify the index or name of the worksheet to load (defaults
        to the first worksheet). This constructor requires the optional,
        third-party library `xlrd <https://pypi.python.org/pypi/xlrd>`_.

        Load first worksheet::

            source = datatest.DataSource.from_excel('mydata.xlsx')

        Specific worksheets can be loaded by name (a string) or
        index (an integer)::

            source = datatest.DataSource.from_excel('mydata.xlsx', 'Sheet 2')
        """
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "No module named 'xlrd'\n"
                "\n"
                "This is an optional constructor that requires the "
                "third-party library 'xlrd'."
            )

        book = xlrd.open_workbook(path, on_demand=True)
        try:
            if isinstance(worksheet, int):
                sheet = book.sheet_by_index(worksheet)
            else:
                sheet = book.sheet_by_name(worksheet)
            data = (sheet.row(i) for i in range(sheet.nrows))  # Build *data*
            data = ([x.value for x in row] for row in data)    # and *columns*
            columns = next(data)                               # from rows.
            new_instance = cls(data, columns)  # <- Create instance.
        finally:
            book.release_resources()

        return new_instance

    def columns(self):
        """Return a list of column names.

        .. code-block:: python

            source = datatest.DataSource(...)
            columns = source.columns()
        """
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA table_info(' + self._table + ')')
        return [x[1] for x in cursor.fetchall()]

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        cursor = self._connection.cursor()
        cursor.execute('SELECT * FROM ' + self._table)

        column_names = self.columns()
        dict_row = lambda x: dict(zip(column_names, x))
        return (dict_row(row) for row in cursor.fetchall())

    def _assert_columns_exist(self, columns):
        """Assert that given columns are present in data source,
        raises LookupError if columns are missing.
        """
        if (not _is_nsiterable(columns)
                or isinstance(columns, collections.Mapping)):
            columns = (columns,)
        self_cols = self.columns()
        is_missing = lambda col: col not in self_cols
        missing = [c for c in columns if is_missing(c)]
        if missing:
            missing = ', '.join(repr(x) for x in missing)
            msg = '{0} not in {1}'.format(missing, self.__repr__())
            raise LookupError(msg)

    def __call__(self, *columns, **kwds_filter):
        steps = (_query_step('select', columns, kwds_filter),)
        return DataQuery._from_parts(steps, source=self)

    def _sql_select_cols(self, selection):
        """Return a string of normalized columns to use with a
        SELECT clause.
        """
        if isinstance(selection, str):
            self._assert_columns_exist(selection)
            return self._normalize_column(selection)  # <- EXIT!

        if isinstance(selection, (collections.Sequence, collections.Set)):
            self._assert_columns_exist(selection)
            row_type = type(selection)
            select_clause = (self._normalize_column(x) for x in selection)
            return ', '.join(select_clause)  # <- EXIT!

        if isinstance(selection, collections.Mapping):
            assert len(selection) == 1
            key, value = tuple(selection.items())[0]
            if isinstance(key, str):
                key = (key,)
            if isinstance(value, str):
                value = (value,)
            self._assert_columns_exist(key)
            self._assert_columns_exist(value)
            key_tuple = tuple(self._normalize_column(x) for x in key)
            value_tuple = tuple(self._normalize_column(x) for x in value)
            return ', '.join(key_tuple + value_tuple)  # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _sql_group_order_cols(self, selection):
        """Return a string of normalized column names appropriate
        for use with a GROUP BY or ORDER BY clause.

        The *selection* can be a string, sequence, set or mapping--see
        the _select() method for details.
        """
        if isinstance(selection, str):
            return self._normalize_column(selection)  # <- EXIT!

        if isinstance(selection, (collections.Sequence, collections.Set)):
            columns = tuple(self._normalize_column(x) for x in selection)
            return ', '.join(columns)  # <- EXIT!

        if isinstance(selection, collections.Mapping):
            key = tuple(selection.keys())[0]
            if isinstance(key, str):
                return self._normalize_column(key)  # <- EXIT
            key_tuple = tuple(self._normalize_column(x) for x in key)
            return ', '.join(key_tuple)  # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _format_results(self, selection, cursor):
        """Return an iterator of results formatted by *selection*
        types from DBAPI2-compliant *cursor*.

        The *selection* can be a string, sequence, set or mapping--see
        the _select() method for details.
        """
        if isinstance(selection, str):
            result = (row[0] for row in cursor)
            return DataResult(result, evaluation_type=list) # <- EXIT!

        if isinstance(selection, (collections.Sequence, collections.Set)):
            result_type = type(selection)
            result = (result_type(x) for x in cursor)
            return DataResult(result, evaluation_type=list) # <- EXIT!

        if isinstance(selection, collections.Mapping):
            result_type = type(selection)
            key, value = tuple(selection.items())[0]
            key_type = type(key)
            value_type = type(value)
            slice_index = 1 if issubclass(key_type, str) else len(key)

            if issubclass(key_type, str):
                keyfunc = lambda row: row[0]
            else:
                keyfunc = lambda row: key_type(row[:slice_index])
            grouped = itertools.groupby(cursor, keyfunc)

            if issubclass(value_type, str):
                def valuefunc(group):
                    result = (row[-1] for row in group)
                    return DataResult(result, evaluation_type=list)
            else:
                def valuefunc(group):
                    group = (row[slice_index:] for row in group)
                    result = (value_type(row) for row in group)
                    return DataResult(result, evaluation_type=list)

            result =  ItemsIter((k, valuefunc(g)) for k, g in grouped)
            return DataResult(result, evaluation_type=result_type) # <- EXIT!

        raise TypeError('type {0!r} not supported'.format(type(selection)))

    def _select(self, selection, **where):
        select = self._sql_select_cols(selection)
        if isinstance(selection, collections.Mapping):
            order_cols = self._sql_group_order_cols(selection)
            order_by = 'ORDER BY {0}'.format(order_cols)
        else:
            order_by = None
        cursor = self._execute_query(select, order_by, **where)
        return self._format_results(selection, cursor)

    def _select_distinct(self, selection, **where):
        select_cols = self._sql_select_cols(selection)
        select = 'DISTINCT {0}'.format(select_cols)
        if isinstance(selection, collections.Mapping):
            order_cols = self._sql_group_order_cols(selection)
            order_by = 'ORDER BY {0}'.format(order_cols)
        else:
            order_by = None
        cursor = self._execute_query(select, order_by, **where)
        return self._format_results(selection, cursor)

    def _select_aggregate(self, sqlfunc, selection, **where):
        """."""
        sqlfunc = sqlfunc.upper()

        if isinstance(selection, collections.Mapping):
            value_cols = tuple(selection.values())[0]
            self._assert_columns_exist(value_cols)
            if isinstance(value_cols, str):
                normalized = self._normalize_column(value_cols)
                formatted = '{0}({1})'.format(sqlfunc, normalized)
            else:
                normalized = [self._normalize_column(x) for x in value_cols]
                formatted = ['{0}({1})'.format(sqlfunc, x) for x in normalized]
                formatted = ', '.join(formatted)
            key_cols = self._sql_group_order_cols(selection)
            select = '{0}, {1}'.format(key_cols, formatted)
            group_by = 'GROUP BY {0}'.format(key_cols)
        else:
            if isinstance(selection, str):
                normalized = self._normalize_column(selection)
                select = '{0}({1})'.format(sqlfunc, normalized)
                group_by = None
            elif isinstance(selection, (collections.Sequence, collections.Set)):
                normalized = [self._normalize_column(x) for x in selection]
                formatted = ['{0}({1})'.format(sqlfunc, x) for x in normalized]
                select = ', '.join(formatted)
                group_by = None
            else:
                raise TypeError('type {0!r} not supported'.format(type(selection)))

        cursor = self._execute_query(select, group_by, **where)
        results = self._format_results(selection, cursor)

        if isinstance(selection, collections.Mapping):
            results = ItemsIter((k, next(v)) for k, v in results)
            return DataResult(results, evaluation_type=dict)
        return next(results)

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        conn_name = str(self._connection)
        tbl_name = self._table
        return '{0}({1}, table={2!r})'.format(cls_name, conn_name, tbl_name)

    def _execute_query(self, select_clause, trailing_clause=None, **kwds_filter):
        """Execute query and return cursor object."""
        try:
            stmnt, params = self._build_query(self._table, select_clause, **kwds_filter)
            if trailing_clause:
                stmnt += '\n' + trailing_clause
            cursor = self._connection.cursor()
            cursor.execute('PRAGMA synchronous=OFF')
            #print(stmnt, params)
            cursor.execute(stmnt, params)
        except Exception as e:
            exc_cls = e.__class__
            msg = '%s\n  query: %s\n  params: %r' % (e, stmnt, params)
            raise exc_cls(msg)
        return cursor

    @classmethod
    def _build_query(cls, table, select_clause, **kwds_filter):
        """Return 'SELECT' query."""
        query = 'SELECT ' + select_clause + ' FROM ' + table
        where_clause, params = cls._build_where_clause(**kwds_filter)
        if where_clause:
            query = query + ' WHERE ' + where_clause
        return query, params

    @staticmethod
    def _build_where_clause(**kwds_filter):
        """Return 'WHERE' clause that implements *kwds_filter*
        constraints.
        """
        clause = []
        params = []
        items = kwds_filter.items()
        items = sorted(items, key=lambda x: x[0])  # Ordered by key.
        for key, val in items:
            if _is_nsiterable(val):
                clause.append(key + ' IN (%s)' % (', '.join('?' * len(val))))
                for x in val:
                    params.append(x)
            else:
                clause.append(key + '=?')
                params.append(val)

        clause = ' AND '.join(clause) if clause else ''
        return clause, params

    def create_index(self, *columns):
        """Create an index for specified columns---can speed up
        testing in many cases.

        If you repeatedly use the same few columns to group or
        filter results, then you can often improve performance by
        adding an index for these columns::

            source.create_index('town')

        Using two or more columns creates a multi-column index::

            source.create_index('town', 'postal_code')

        Calling the function multiple times will create multiple
        indexes::

            source.create_index('town')
            source.create_index('postal_code')

        .. note:: Indexes should be added with discretion to tune
                  a test suite's over-all performance.  Creating
                  several indexes before testing even begins could
                  lead to longer run times so use indexes with care.
        """
        self._assert_columns_exist(columns)

        # Build index name.
        whitelist = lambda col: ''.join(x for x in col if x.isalnum())
        idx_name = '_'.join(whitelist(col) for col in columns)
        idx_name = 'idx_{0}_{1}'.format(self._table, idx_name)

        # Build column names.
        col_names = [self._normalize_column(x) for x in columns]
        col_names = ', '.join(col_names)

        # Prepare statement.
        statement = 'CREATE INDEX IF NOT EXISTS {0} ON {1} ({2})'
        statement = statement.format(idx_name, self._table, col_names)

        # Create index.
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute(statement)

    @staticmethod
    def _normalize_column(column):
        """Normalize value for use as SQLite column name."""
        if not isinstance(column, str):
            msg = "expected column of type 'str', got {0!r} instead"
            raise TypeError(msg.format(column.__class__.__name__))
        column = column.strip()
        column = column.replace('"', '""')  # Escape quotes.
        if column == '':
            column = '_empty_'
        return '"' + column + '"'
