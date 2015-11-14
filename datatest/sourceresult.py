"""Result objects from data source queries."""
from numbers import Number

from ._builtins import *
from ._collections import Mapping
from ._collections import Set
from ._collections import Sequence
from ._functools import wraps
from . import _itertools as itertools

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem
from .diff import InvalidNumber
from .diff import NotProperSubset
from .diff import NotProperSuperset


def _coerce_other(target_type, *type_args, **type_kwds):
    """Callable decorator for comparison methods to convert *other* argument
    into given *target_type* instance.

    """
    def callable(f):
        @wraps(f)
        def wrapped(self, other):
            if not isinstance(other, target_type):
                try:
                    other = target_type(other, *type_args, **type_kwds)
                except TypeError:
                    return NotImplemented
            return f(self, other)
        return wrapped

    return callable


class ResultSet(set):
    """DataSource query result set."""
    def __init__(self, data):
        """Initialize object."""
        if isinstance(data, Mapping):
            raise TypeError('cannot be mapping')

        try:
            if isinstance(data, Set):
                first_value = next(iter(data))
            else:
                data = iter(data)
                first_value = next(data)
                data = itertools.chain([first_value], data)  # Rebuild original.
        except StopIteration:
            first_value = None

        if isinstance(first_value, tuple) and len(first_value) == 1:
            data = set(x[0] for x in data)  # Unpack single-item tuple.
        elif not isinstance(data, Set):
            data = set(data)

        set.__init__(self, data)

    def make_iter(self, names):
        """Return an iterable of dictionary rows (like ``csv.DictReader``)
        using *names* to construct dictionary keys.

        """
        is_container = lambda x: not isinstance(x, str) and isinstance(x, Sequence)
        single_value = next(iter(self))
        if is_container(single_value):
            assert len(names) == len(single_value), "length of 'names' must match data items"
            iterable = iter(dict(zip(names, values)) for values in self)
        else:
            if is_container(names):
                assert len(names) == 1, "length of 'names' must match data items"
                names = names[0]  # Unwrap names value.
            iterable = iter({names: value} for value in self)
        return iterable

    def compare(self, other, op='=='):
        """Compare *self* to *other* and return a list of difference objects.
        If *other* is callable, constructs a list of InvalidItem objects
        for values where *other* returns False.  If *other* is a ResultSet or
        other collection, differences are compiled as a list of ExtraItem and
        MissingItem objects.

        """
        if callable(other):
            differences = [InvalidItem(x) for x in self if not other(x)]
        else:
            if not isinstance(other, ResultSet):
                other = ResultSet(other)

            if op in ('==', '<=', '<'):
                extra = self.difference(other)
                if op == '<' and not (extra or other.difference(self)):
                    extra = [NotProperSubset()]
                else:
                    extra = (ExtraItem(x) for x in extra)
            else:
                extra = []

            if op in ('==', '>=', '>'):
                missing = other.difference(self)
                if op == '>' and not (missing or self.difference(other)):
                    missing = [NotProperSuperset()]
                else:
                    missing = (MissingItem(x) for x in missing)
            else:
                missing = []

            differences = list(itertools.chain(extra, missing))

        return differences


# Decorate ResultSet comparison magic methods (cannot be decorated in-line as
# class must first be defined).
_other_to_resultset = _coerce_other(ResultSet)
ResultSet.__eq__ = _other_to_resultset(ResultSet.__eq__)
ResultSet.__ne__ = _other_to_resultset(ResultSet.__ne__)
ResultSet.__lt__ = _other_to_resultset(ResultSet.__lt__)
ResultSet.__gt__ = _other_to_resultset(ResultSet.__gt__)
ResultSet.__le__ = _other_to_resultset(ResultSet.__le__)
ResultSet.__ge__ = _other_to_resultset(ResultSet.__ge__)


class ResultMapping(object):
    """DataSource query result mapping."""
    def __init__(self, data, grouped_by):
        """Initialize object."""
        if not isinstance(data, Mapping):
            data = dict(data)
        if isinstance(grouped_by, str):
            grouped_by = [grouped_by]

        try:
            iterable = iter(data.items())
            first_key, first_value = next(iterable)
            if isinstance(first_key, tuple) and len(first_key) == 1:
                iterable = itertools.chain([(first_key, first_value)], iterable)
                iterable = ((k[0], v) for k, v in iterable)
                data = dict(iterable)
        except StopIteration:
            pass

        self._data = data
        self.grouped_by = grouped_by

    def __eq__(self, other):
        return self._data == other._data

    def __ne__(self, other):
        return not self.__eq__(other)

    def make_iter(self, names):
        """Return an iterable of dictionary rows (like ``csv.DictReader``)
        using *names* to construct dictionary keys.

        """
        is_container = lambda x: not isinstance(x, str) and isinstance(x, Sequence)

        if not is_container(names):
            names = (names,)

        grouped_by = self.grouped_by
        if not is_container(grouped_by):
            grouped_by = (grouped_by,)

        collision = set(names) & set(grouped_by)
        if collision:
            collision = ', '.join(collision)
            raise ValueError("names conflict: {0}".format(collision))

        single_key, single_value = next(iter(self._data.items()))
        iterable = self._data.items()
        if not is_container(single_key):
            iterable = (((k,), v) for k, v in iterable)
            single_key = (single_key,)
        if not is_container(single_value):
            iterable = ((k, (v,)) for k, v in iterable)
            single_value = (single_value,)

        assert len(single_key) == len(grouped_by)
        assert len(single_value) == len(names)

        def make_dictrow(k, v):
            x = dict(zip(grouped_by, k))
            x.update(dict(zip(names, v)))
            return x
        return iter(make_dictrow(k, v) for k, v in iterable)

    def compare(self, other):
        """Compare *self* to *other* and return a list of difference objects.
        If *other* is callable, constructs a list of InvalidItem objects
        for values where *other* returns False.  If *other* is a ResultMapping
        or other mapping object (like a dict), differences are compiled as a
        list of InvalidNumber and InvalidItem objects.

        """
        # Evaluate self._data with function.
        if callable(other):
            keys = sorted(self._data.keys())
            differences = []
            for key in keys:
                value = self._data[key]
                if not other(value):
                    if isinstance(key, str):
                        key = (key,)
                    kwds = dict(zip(self.grouped_by, key))
                    differences.append(InvalidItem(value, **kwds))
        # Compare self._data to other._data.
        else:
            if not isinstance(other, ResultMapping):
                other = ResultMapping(other, grouped_by=None)
            keys = itertools.chain(self._data.keys(), other._data.keys())
            keys = sorted(set(keys))
            differences = []
            for key in keys:
                self_val = self._data.get(key)
                other_val = other._data.get(key)
                if isinstance(key, str):
                    key = (key,)
                one_num = any((
                    isinstance(self_val, Number),
                    isinstance(other_val, Number),
                ))
                num_or_none = all((
                    isinstance(self_val, Number) or self_val == None,
                    isinstance(other_val, Number) or other_val == None,
                ))
                # Numeric comparison.
                if one_num and num_or_none:
                    self_num = self_val if self_val != None else 0
                    other_num = other_val if other_val != None else 0
                    if self_num != other_num:
                        diff = self_num - other_num
                        kwds = dict(zip(self.grouped_by, key))
                        invalid = InvalidNumber(diff, other_val, **kwds)
                        differences.append(InvalidNumber(diff, other_val, **kwds))
                # Object comparison.
                else:
                    if self_val != other_val:
                        kwds = dict(zip(self.grouped_by, key))
                        differences.append(InvalidItem(self_val, other_val, **kwds))

        return differences


# Decorate ResultMapping comparison magic methods (cannot be decorated in-line
# as class must first be defined).
_other_to_resultmapping = _coerce_other(ResultMapping, grouped_by=None)
ResultMapping.__eq__ = _other_to_resultmapping(ResultMapping.__eq__)
ResultMapping.__ne__ = _other_to_resultmapping(ResultMapping.__ne__)
