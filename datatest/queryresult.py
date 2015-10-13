"""Scratchpad for DataSource query result objects."""
import itertools
from collections import Mapping
from collections import Set
from functools import wraps
from numbers import Number

from ._builtins import *

from .diff import ExtraItem
from .diff import MissingItem
from .diff import InvalidItem
from .diff import InvalidNumber


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


class ResultSet(object):
    """DataSource query result set."""
    def __init__(self, values):
        """Initialize object."""
        if not isinstance(values, Set):
            if isinstance(values, Mapping):
                raise TypeError('cannot be mapping')
            values = set(values)
        self.values = values

    def __eq__(self, other):
        return self.values == other.values

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.values < other.values

    def __gt__(self, other):
        return self.values > other.values

    def __le__(self, other):
        return self.values <= other.values

    def __ge__(self, other):
        return self.values >= other.values

    def __contains__(self, item):
        return item in self.values

    def compare(self, other):
        """Compare *self* to *other* and return a list of difference objects.
        If *other* is callable, constructs a list of InvalidItem objects
        for values where *other* returns False.  If *other* is a ResultSet or
        other collection, differences are compiled as a list of ExtraItem and
        MissingItem objects.

        """
        if callable(other):
            differences = [InvalidItem(x) for x in self.values if not other(x)]
        else:
            if not isinstance(other, ResultSet):
                other = ResultSet(other)
            extra = self.values.difference(other.values)
            extra = (ExtraItem(x) for x in extra)
            missing = other.values.difference(self.values)
            missing = (MissingItem(x) for x in missing)
            differences = list(itertools.chain(extra, missing))
        return differences

    def all(self, func):
        """Return True if *func* evaluates to True for all items in set."""
        return all(func(x) for x in self.values)


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
    def __init__(self, values, grouped_by):
        """Initialize object."""
        if not isinstance(values, Mapping):
            values = dict(values)
        self.values = values

        if isinstance(grouped_by, str):
            grouped_by = [grouped_by]
        self.grouped_by = grouped_by

    def __eq__(self, other):
        return self.values == other.values

    def __ne__(self, other):
        return not self.__eq__(other)

    def compare(self, other):
        """Compare *self* to *other* and return a list of difference objects.
        If *other* is callable, constructs a list of InvalidItem objects
        for values where *other* returns False.  If *other* is a ResultMapping
        or other mapping object (like a dict), differences are compiled as a
        list of InvalidNumber and InvalidItem objects.

        """
        # Evaluate self.values with function.
        if callable(other):
            keys = sorted(self.values.keys())
            differences = []
            for key in keys:
                value = self.values[key]
                if not other(value):
                    kwds = dict(zip(self.grouped_by, key))
                    differences.append(InvalidItem(value, **kwds))
        # Compare self.values to other.values.
        else:
            if not isinstance(other, ResultMapping):
                other = ResultMapping(other, grouped_by=None)
            keys = itertools.chain(self.values.keys(), other.values.keys())
            keys = sorted(set(keys))
            differences = []
            for key in keys:
                self_val = self.values.get(key)
                other_val = other.values.get(key)
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