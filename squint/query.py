# -*- coding: utf-8 -*-
from __future__ import absolute_import
import csv
import inspect
import sqlite3
import sys
from numbers import Number

from ._compatibility.builtins import *
from ._compatibility import (
    abc,
    contextlib,
    functools,
    itertools,
)
from ._compatibility.collections import namedtuple
from ._compatibility.collections.abc import (
    Collection,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    Set,
    Sized,
)
from ._vendor.predicate import (
    get_matcher,
)
from ._utils import (
    _flatten,
    IterItems,
    iterpeek,
    nonstringiter,
    pformat_lines,
    sortable,
    exhaustible,
    _make_sentinel,
    _unique_everseen,
    file_types,
    string_types,
)
from .result import (
    Result,
)


PY2 = sys.version_info[0] == 2

PREVIEW_MAX_LINES = 8


class BaseElement(abc.ABC):
    """An abstract base class used to determine if an object should
    be treated as a single data element or as a collection of multiple
    data elements.

    Objects that are considered individual data elements include:

    * non-iterable objects
    * strings
    * mappings
    * tuples
    """
    @abc.abstractmethod
    def __init__(self, *args, **kwds):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        if cls is BaseElement:
            if (issubclass(subclass, (string_types, Mapping, tuple))
                    or not issubclass(subclass, Iterable)):
                return True
        return NotImplemented


def _get_iteritems(iterable):
    """Verify that the first item of *iterable* is appropriate to
    use as a key-value pair for a dictionary or other mapping and
    return an IterItems object. The underlying iterable should not
    contain duplicate keys and they should be appropriate for
    constructing a dictionary or other mapping.
    """
    if isinstance(iterable, Mapping):
        return IterItems(iterable)  # <- EXIT!

    if isinstance(iterable, BaseQuery):
        iterable = iterable.execute()

    first_item, iterable = iterpeek(iterable)

    # Assert that first item contains a suitable key-value pair.
    if first_item:
        if not isinstance(first_item, tuple) \
                and isinstance(first_item, BaseElement):
            raise TypeError((
                'dictionary update sequence items can not be '
                'registered BaseElement types, got {0}: {1!r}'
            ).format(first_item.__class__.__name__, first_item))
        try:
            first_item = tuple(first_item)
        except TypeError:
            raise TypeError('cannot convert dictionary update '
                            'sequence element #0 to a sequence')
        if len(first_item) != 2:
            ValueError(('dictionary update sequence element #0 has length '
                        '{0}; 2 is required').format(len(first_item)))
        first_key = first_item[0]
        if not isinstance(first_key, Hashable):
            raise ValueError((
                'unhashable type {0}: {1!r}'
            ).format(first_key.__class__.__name__, first_key))

    return IterItems(iterable)


def _is_collection_of_items(obj):
    while isinstance(obj, Result):
        obj = obj.__wrapped__
    return isinstance(obj, IterItems)


def _get_evaltype(obj, default=list):
    """Return object's evaltype property. If the object does not have
    an evaltype property and is a mapping, sequence, or set, then
    return the type of the object itself. If the object is an iterable,
    return None. Raises a Type error for any other object.
    """
    if hasattr(obj, 'evaltype'):
        return obj.evaltype

    if isinstance(obj, IterItems):
        return dict

    if isinstance(obj, Collection):
        return obj.__class__

    if isinstance(obj, Iterable):
        return default

    err_msg = 'unable to determine evaluation type for {0!r} instance'
    raise TypeError(err_msg.format(obj.__class__.__name__))


def _make_dataresult(iterable):
    if isinstance(iterable, Result):
        return iterable

    evaltype = _get_evaltype(iterable)
    return Result(iterable, evaltype)


def _apply_to_data(function, data_iterator):
    """Apply a *function* of one argument to the to the given
    iterator *data_iterator*.
    """
    if _is_collection_of_items(data_iterator):
        result = _get_iteritems((k, function(v)) for k, v in data_iterator)
        return Result(result, _get_evaltype(data_iterator))
    return function(data_iterator)


def _map_data(function, iterable):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            return function(iterable)  # <- EXIT!

        evaltype = _get_evaltype(iterable)
        if issubclass(evaltype, Set):
            evaltype = list
        return Result(map(function, iterable), evaltype)

    return _apply_to_data(wrapper, iterable)


def _starmap_data(function, iterable):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            if not isinstance(iterable, Iterable):
                iterable = (iterable,)
            return function(*iterable)  # <- EXIT!

        evaltype = _get_evaltype(iterable)
        if issubclass(evaltype, Set):
            evaltype = list
        iterable = (x if isinstance(x, Iterable) else (x,) for x in iterable)
        return Result(itertools.starmap(function, iterable), evaltype)

    return _apply_to_data(wrapper, iterable)


def _reduce_data(function, iterable, initializer_factory=None):
    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            return iterable

        if initializer_factory is None:
            return functools.reduce(function, iterable)

        initializer = initializer_factory()
        return functools.reduce(function, iterable, initializer)

    return _apply_to_data(wrapper, iterable)


def _filter_data(predicate, iterable):
    if callable(predicate) and not isinstance(predicate, type):
        function = predicate
    else:
        predicate = get_matcher(predicate)
        if hasattr(predicate, '_func'):
            function = predicate._func
        else:
            def function(x):
                return predicate == x

    def wrapper(iterable):
        if isinstance(iterable, BaseElement):
            raise TypeError(('filter expects a collection of data elements, '
                             'got 1 data element: {0}').format(iterable))
        filtered_data = filter(function, iterable)
        return Result(filtered_data, _get_evaltype(iterable))

    return _apply_to_data(wrapper, iterable)


def _apply_data(function, data):
    """Group-wise function application."""
    return _apply_to_data(function, data)


def _flatten_data(iterable):
    if isinstance(iterable, Mapping):
        iterable = _get_iteritems(iterable)

    if isinstance(iterable, BaseElement) or not _is_collection_of_items(iterable):
        return iterable

    def combined(k, v):
        if not isinstance(k, tuple):
            k = (k,)
        if not isinstance(v, tuple):
            v = (v,)
        return k + v

    def flatten(items):
        for k, v in items:
            if isinstance(v, BaseElement):
                yield combined(k, v)
            else:
                for x in v:
                    yield combined(k, x)

    return Result(flatten(iterable), list)


def _unwrap_data(iterable):
    """Unwrap single-item sequences or sets."""
    def unwrap(iterable):
        if not isinstance(iterable, (Sequence, Set, Result)):
            return iterable  # <- EXIT!

        first_values = list(itertools.islice(iterable, 2))

        if len(first_values) == 1:
            unwrapped = first_values[0]
            return unwrapped  # <- EXIT!

        if exhaustible(iterable):
            evaltype = _get_evaltype(iterable)
            iterable = itertools.chain(first_values, iterable)
            return Result(iterable, evaltype)  # <- EXIT!

        return iterable

    return _apply_to_data(unwrap, iterable)


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
    if isinstance(iterable, BaseElement):
        iterable = [iterable]
    iterable = (_sqlite_cast_as_real(x) for x in iterable if x != None)
    try:
        start_value = next(iterable)
    except StopIteration:  # From SQLite docs: "If there are no non-NULL
        return None        # input rows then sum() returns NULL..."
    return sum(iterable, start_value)


def _sqlite_count(iterable):
    """Return the number non-NULL (!= None) elements in iterable."""
    if isinstance(iterable, BaseElement):
        iterable = [iterable]
    return sum(1 for x in iterable if x != None)


# The SQLite BLOB/Binary type in sortable Python 2 but unsortable in Python 3.
Binary = sqlite3.Binary  # Pull into local namespace to eliminate dot-lookup.
_unsortable_blob_type = not sortable(Binary(b'0'))


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
    if value is None:                    # NULL (sort group 0)
        return (0, 0)
    if isinstance(value, Number):        # INTEGER and REAL (sort group 1)
        return (1, value)
    if isinstance(value, string_types):  # TEXT (sort group 2)
        return (2, value)
    if isinstance(value, Binary):        # BLOB (sort group 3)
        if _unsortable_blob_type:
            value = bytes(value)
        return (3, value)
    return (4, value)  # unsupported type (sort group 4)


def _sqlite_avg(iterable):
    """Return the average of elements in iterable. Returns None if all
    elements are None.
    """
    if isinstance(iterable, BaseElement):
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
    if isinstance(iterable, BaseElement):
        return iterable  # <- EXIT!
    iterable = (x for x in iterable if x != None)
    return min(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_max(iterable):
    """Return the maximum value of all values. Returns None if all
    values are None.
    """
    if isinstance(iterable, BaseElement):
        return iterable  # <- EXIT!
    return max(iterable, default=None, key=_sqlite_sortkey)


def _sqlite_distinct(iterable):
    """Filter iterable to unique values, while maintaining
    evaltype.
    """
    def dodistinct(itr):
        if isinstance(itr, BaseElement):
            return itr
        return Result(_unique_everseen(itr), _get_evaltype(itr))

    if _is_collection_of_items(iterable):
        result = _get_iteritems((k, dodistinct(v)) for k, v in iterable)
        return Result(result, _get_evaltype(iterable))
    return dodistinct(iterable)


########################################################
# Functions to validate and parse query 'select' syntax.
########################################################

def _validate_fields(fields):
    if isinstance(fields, string_types):
        return  # <- EXIT!

    for field in fields:
        if not isinstance(field, string_types):
            message = "expected 'str' elements, got {0!r}"
            raise ValueError(message.format(field))


def _normalize_columns(columns):
    """Returns normalized *columns* selection or raise error if
    unsupported.
    """
    if not isinstance(columns, Sized):
        raise ValueError(('unsupported columns '
                          'format, got {0!r}').format(columns))

    if isinstance(columns, Mapping):
        if len(columns) != 1:
            raise ValueError(('expected container of 1 item, got {0} '
                              'items: {1!r}').format(len(columns), columns))

        key, value = tuple(columns.items())[0]
        if isinstance(value, Mapping):
            message = 'mappings can not be nested, got {0!r}'
            raise ValueError(message.format(columns))

        if isinstance(value, str) or len(value) > 1:
            columns = {key: [value]}  # Rebuild with default list container.

        _validate_fields(key)
        _validate_fields(tuple(value)[0])
        return columns  # <- EXIT!

    if isinstance(columns, str) or len(columns) > 1:
        columns = [columns]  # Wrap with default list container.

    _validate_fields(tuple(columns)[0])
    return columns


def _parse_columns(columns):
    """Expects a normalized *columns* selection and returns its
    *key* and *value* components as a tuple.
    """
    if isinstance(columns, Mapping):
        key, value = tuple(columns.items())[0]
    else:
        key, value = tuple(), columns
    return key, value


##################
# Helper Functions
##################
def _make_args_repr(args):
    func = lambda x: getattr(x, '__name__', repr(x))
    return ', '.join(func(x) for x in args)

def _make_kwds_repr(kwds):
    func = lambda x: getattr(x, '__name__', repr(x))
    kwds_repr = [(k, func(v)) for k, v in kwds.items()]
    kwds_repr = ['{0}={1}'.format(k, v) for k, v in kwds_repr]
    return ', '.join(kwds_repr)


##########################################
# Functions for query and execution steps.
##########################################

def _get_step_repr(step):
    """Helper function to return repr for a single query step."""
    func, args, kwds = step
    func_repr = getattr(func, '__name__', repr(func))
    args_repr = _make_args_repr(args)
    kwds_repr = _make_kwds_repr(kwds)
    return '{0}, ({1}), {{{2}}}'.format(func_repr, args_repr, kwds_repr)


_query_step = namedtuple(
    typename='query_step',
    field_names=('name', 'args', 'kwds')
)

_execution_step = namedtuple(
    typename='execution_step',
    field_names=('function', 'args', 'kwds')
)

RESULT_TOKEN = _make_sentinel(
    'ResultSentinelType',
    '<RESULT>',
    'Token for representing a data result when optimizing execution plan.',
)


########################################################
# BaseQuery class
########################################################

class BaseQuery(abc.ABC):
    @property
    @abc.abstractmethod
    def _select_cls(self):
        """"A reference to the Select class."""
        raise NotImplementedError

    def __init__(self, *args, **where):
        """Initialize self.

        Query(columns, **where)
        Query(select, columns, **where)
        """
        argcount = len(args)
        if argcount == 2:
            select, columns = args
            if not isinstance(select, self._select_cls):
                raise TypeError('select must be {0} object, got {1}'.format(
                    self._select_cls.__name__,
                    select.__class__.__name__,
                ))
            flattened = _flatten([_parse_columns(columns), where.keys()])
            try:
                select._assert_fields_exist(flattened)
            except LookupError:
                __tracebackhide__ = True
                raise
        elif argcount == 1:
            select, columns = None, args[0]
        else:
            msg = 'expects 1 or 2 positional arguments but {0} were given'
            raise TypeError(msg.format(argcount))

        self.source = select
        self.args = (_normalize_columns(columns),)
        self.kwds = where
        self._query_steps = []

    @classmethod
    def from_object(cls, obj):
        """Creates a query and associates it with the given object.

        .. code-block:: python

            mylist = [1, 2, 3, 4]
            query = Query.from_object(mylist)

        If *obj* is a Query itself, a copy of the original query
        is created.
        """
        if isinstance(obj, BaseQuery):
            return obj.__copy__()

        if not nonstringiter(obj):
            obj = [obj]

        new_query = cls.__new__(cls)
        new_query.source = obj
        new_query.args = ()
        new_query.kwds = {}
        new_query._query_steps = []
        return new_query

    def _validate_source(self, source):
        if not isinstance(source, self._select_cls):
            raise TypeError('expected {0!r}, got {1!r}'.format(
                self._select_cls.__name__,
                source.__class__.__name__,
            ))

    def __copy__(self):
        new_query = self.__class__.__new__(self.__class__)
        new_query.source = self.source
        new_query.args = self.args
        new_query.kwds = dict(self.kwds)                  # Makes copies of
        new_query._query_steps = list(self._query_steps)  # mutable types.
        return new_query

    def _add_step(self, name, *args, **kwds):
        step = _query_step(name, args, kwds)
        new_query = self.__copy__()
        new_query._query_steps.append(step)
        return new_query

    def map(self, function):
        """Apply *function* to each element, keeping the results.
        If the group of data is a set type, it will be converted
        to a list (as the results may not be distinct or hashable).
        """
        return self._add_step('map', function)

    def starmap(self, function):
        return self._add_step('starmap', function)

    def filter(self, predicate=True):
        """Filter elements, keeping only those values that match the
        given *predicate*. When *predicate* is True, this method keeps
        all elements for which :py:class:`bool` returns True (see
        :ref:`predicate-docs` for details).
        """
        return self._add_step('filter', predicate)

    def reduce(self, function, initializer_factory=None):
        """Reduce elements to a single value by applying a *function*
        of two arguments cumulatively to all elements from left to
        right. If the optional *initializer_factory* is present, it
        is called without arguments to provide a value that is placed
        before the items of the sequence in the calculation, and serves
        as a default when the sequence is empty. If initializer_factory
        is not given and sequence contains only one item, the first
        item is returned.
        """
        if initializer_factory is not None and not callable(initializer_factory):
            raise TypeError('initializer_factory must be callable or None')
        return self._add_step('reduce', function, initializer_factory)

    def apply(self, function):
        """Apply *function* to entire group keeping the resulting data.
        If element is not iterable, it will be wrapped as a single-item
        list.
        """
        return self._add_step('apply', function)

    def sum(self):
        """Get the sum of non-None elements."""
        return self._add_step('sum')

    def count(self):
        """Get the count of non-None elements."""
        return self._add_step('count')

    def avg(self):
        """Get the average of non-None elements. Strings and other
        objects that do not look like numbers are interpreted as 0.
        """
        return self._add_step('avg')

    def min(self):
        """Get the minimum value from elements."""
        return self._add_step('min')

    def max(self):
        """Get the maximum value from elements."""
        return self._add_step('max')

    def distinct(self):
        """Filter elements, removing duplicate values."""
        return self._add_step('distinct')

    def flatten(self):
        """Flatten dictionary into list of tuple rows. If data is not
        a dictionary, the original values are returned unchanged.
        """
        return self._add_step('flatten')

    def unwrap(self):
        """Unwrap single-item sequences or sets."""
        return self._add_step('unwrap')

    @staticmethod
    def _translate_step(query_step):
        """Accept a query step and return a corresponding execution
        step.
        """
        name, query_args, query_kwds = query_step

        if name == 'map':
            function = _map_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'starmap':
            function = _starmap_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'filter':
            function = _filter_data
            args = (query_args[0], RESULT_TOKEN,)
        elif name == 'reduce':
            function = _reduce_data
            args = (query_args[0], RESULT_TOKEN, query_args[1])
        elif name == 'apply':
            function = _apply_data
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
        elif name == 'flatten':
            function = _flatten_data
            args = (RESULT_TOKEN,)
        elif name == 'unwrap':
            function = _unwrap_data
            args = (RESULT_TOKEN,)
        elif name == 'select':
            raise ValueError("this method does not handle 'select' step")
        else:
            raise ValueError('unrecognized query function {0!r}'.format(name))

        return _execution_step(function, args, {})

    def _get_execution_plan(self, source, query_steps):
        if isinstance(source, self._select_cls):
            execution_plan = [
                _execution_step(getattr, (RESULT_TOKEN, '_select'), {}),
                _execution_step(RESULT_TOKEN, self.args, self.kwds),
            ]
        else:
            execution_plan = [
                _execution_step(_make_dataresult, (RESULT_TOKEN,), {}),
            ]
        for query_step in query_steps:
            execution_step = self._translate_step(query_step)
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
        else:
            optimized_steps = ()

        if optimized_steps:
            return optimized_steps + remaining_steps
        return None

    def execute(self, source=None, optimize=True):
        """A Query can be executed to return a single value or an
        iterable :class:`Result` appropriate for lazy evaluation::

            query = source('A')
            result = query.execute()  # <- Returns Result (iterator)

        Setting *optimize* to False turns-off query optimization.
        """
        if source:
            if self.source:
                raise ValueError((
                    "cannot take 'source' argument, query is "
                    "already associated with a data source: {0!r}"
                ).format(self.source))
            self._validate_source(source)
        else:
            if not self.source:
                raise ValueError("missing 'source' argument, none found")
            source = self.source

        execution_plan = self._get_execution_plan(source, self._query_steps)
        if optimize:
            execution_plan = self._optimize(execution_plan) or execution_plan

        result = source
        replace_token = lambda x: result if x is RESULT_TOKEN else x
        for step in execution_plan:
            function, args, keywords = step  # Unpack 3-tuple.
            function = replace_token(function)
            args = tuple(replace_token(x) for x in args)
            keywords = dict((k, replace_token(v)) for k, v in keywords.items())
            result = function(*args, **keywords)

        return result

    def __iter__(self):
        """Executes query and returns an eagerly evaluated result."""
        result = self.execute()
        if isinstance(result, Iterator):
            return result
        return iter([result])

    def fetch(self):
        """Executes query and returns an eagerly evaluated result."""
        result = self.execute()
        if isinstance(result, Result):
            return result.fetch()
        return result

    def _explain(self, optimize=True, file=sys.stdout):
        """A convenience method primarily intended to help when
        debugging and developing execution plan optimizations.

        Prints execution plan to the text stream *file* (defaults
        to stdout). If *optimize* is True, an optimized plan will
        be printed if one can be constructed.

        If *file* is set to None, returns execution plan as a string.
        """
        source = self.source
        if source is not None:
            source_repr = repr(source)
            if len(source_repr) > 70:
                source_repr = source_repr[:67] + '...'
        else:
            source = self._select_cls([], fieldnames=['dummy_source'])
            source_repr = '<none given> (assuming Select object)'

        execution_plan = self._get_execution_plan(source, self._query_steps)

        optimized_text = ''
        if optimize:
            optimized_plan = self._optimize(execution_plan)
            if optimized_plan:
                execution_plan = optimized_plan
                optimized_text = ' (optimized)'

        steps = [_get_step_repr(step) for step in execution_plan]
        steps = '\n'.join('  {0}'.format(step) for step in steps)

        formatted = 'Data Source:\n  {0}\nExecution Plan{1}:\n{2}'
        formatted = formatted.format(source_repr, optimized_text, steps)

        if file:
            file.write(formatted)
            file.write('\n')
        else:
            return formatted

    def __repr__(self):
        class_repr = self.__class__.__name__

        if isinstance(self.source, self._select_cls):
            source_repr = super(self._select_cls, self.source).__repr__()
            is_from_object = False
        elif self.source:
            source_repr = repr(self.source)
            is_from_object = True
        else:
            source_repr = ''
            is_from_object = False

        args_repr = _make_args_repr(self.args)
        if source_repr and args_repr:
            args_repr = ', ' + args_repr

        kwds_repr = _make_kwds_repr(self.kwds)
        if kwds_repr:
            kwds_repr = ', ' + kwds_repr

        all_steps_repr = []
        for step_name, step_args, step_kwds in self._query_steps:
            if step_kwds:
                step_kwds_repr = ', ' + _make_kwds_repr(step_kwds)
            else:
                step_kwds_repr = ''
            step_args_repr = _make_args_repr(step_args)
            step_repr = '{0}({1}{2})'.format(step_name, step_args_repr, step_kwds_repr)
            all_steps_repr.append(step_repr)

        if all_steps_repr:
            query_steps_repr = '.' + ('.'.join(all_steps_repr))
        else:
            query_steps_repr = ''

        if is_from_object:
            return '{0}.from_object({1}){2}'.format(
                class_repr, source_repr, query_steps_repr)
        return '{0}({1}{2}{3}){4}'.format(
            class_repr, source_repr, args_repr, kwds_repr, query_steps_repr)

    def _build_preview(self):
        """Return a formatted preview string of the query result."""
        result = self.execute()

        if isinstance(result, Result):
            preview_lines = []
            while len(preview_lines) <= PREVIEW_MAX_LINES:
                try:
                    result._next_cache()
                except StopIteration:
                    break
                preview_lines = pformat_lines(result._get_cache())
        else:
            preview_lines = pformat_lines(result)

        # If too long, truncate list and append an ellipsis.
        if len(preview_lines) > PREVIEW_MAX_LINES:
            preview_lines = preview_lines[:PREVIEW_MAX_LINES]
            last_row = preview_lines.pop()
            position = len(last_row) - len(last_row.lstrip())
            padding = last_row[:position]
            preview_lines.append('{0}...'.format(padding))

        preview = '\n'.join(preview_lines)
        return '---- preview ----\n{0}'.format(preview)

    def _repr_pretty_(self, p, cycle):
        """Pretty print extension method for IPython."""
        p.text(repr(self))

        if not cycle:
            p.break_()
            p.text(self._build_preview())

    def to_reader(self, fieldnames=None):
        """Return a reader object which will iterate over the records
        returned from the Query. If the *fieldnames* argument is not
        provided, this method tries to construct names using the
        columns given when calling the Select object.
        """
        iterable = self.flatten().execute()
        if not nonstringiter(iterable):
            iterable = [(iterable,)]

        first_row, iterable = iterpeek(iterable)
        if not nonstringiter(first_row):
            first_row = (first_row,)
            iterable = ((x,) for x in iterable)

        if fieldnames:
            if not nonstringiter(fieldnames):
                fieldnames = (fieldnames,)
        else:
            if self.args:
                fieldnames = self.__class__.from_object(self.args[0])
                (fieldnames,) = fieldnames.flatten().fetch()
                if not nonstringiter(fieldnames):
                    fieldnames = (fieldnames,)
                if len(first_row) != len(fieldnames):
                    fieldnames = None

        if fieldnames:
            yield fieldnames

        for value in iterable:
            yield value

    def to_csv(self, file, fieldnames=None, **fmtparams):
        """Execute the query and write the results as a CSV file
        (dictionaries and other mappings will be seralized).

        The given *file* can be a path or file-like object;
        *fieldnames* will be printed as a header row; and
        *fmtparams* can be any values supported by
        :py:func:`csv.writer`.

        When *fieldnames* are not provided, names from the query's
        original *columns* argument will be used if the number of
        selected columns matches the number of resulting columns.
        """
        reader = self.to_reader(fieldnames)

        if not isinstance(file, file_types):
            if PY2:
                csvfile = open(file, 'wb')
            else:
                csvfile = open(file, 'w', newline='')
            autoclose = True
        else:
            csvfile = file
            autoclose = False

        try:
            writer = csv.writer(csvfile, **fmtparams)

            for row in reader:
                if nonstringiter(row):
                    writer.writerow(row)
                else:
                    writer.writerow([row])
        finally:
            if autoclose:
                csvfile.close()


with contextlib.suppress(AttributeError):  # inspect.Signature() is new in 3.3
    BaseQuery.__init__.__signature__ = inspect.Signature([
        inspect.Parameter('self', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('columns', inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter('where', inspect.Parameter.VAR_KEYWORD),
    ])
