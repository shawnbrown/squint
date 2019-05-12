# -*- coding: utf-8 -*-
"""Utility helper functions."""
from __future__ import absolute_import
import inspect
import re
from io import IOBase
from numbers import Number
from sys import version_info as _version_info

from ._compatibility.abc import ABC
from ._compatibility.builtins import callable
from ._compatibility.collections.abc import ItemsView
from ._compatibility.collections.abc import Iterable
from ._compatibility.collections.abc import Mapping
from ._compatibility.decimal import Decimal
from ._compatibility.itertools import chain
from ._compatibility.itertools import filterfalse
from ._compatibility.itertools import islice


try:
    string_types = (basestring,)  # Removed in Python 3.0
except NameError:
    string_types = (str,)

try:
    from StringIO import StringIO
    file_types = (IOBase, file, StringIO)
    # Above: StringIO module and file object were removed
    # in Python 3. Also, the old StringIO is not a subclass
    # of io.IOBase.
except (ImportError, NameError):
    file_types = (IOBase,)

regex_types = type(re.compile(''))


def nonstringiter(obj):
    """Returns True if *obj* is a non-string iterable object."""
    return not isinstance(obj, string_types) and isinstance(obj, Iterable)


def seekable(buf):
    """Returns True if *buf* is a seekable file-like buffer."""
    try:
        return buf.seekable()
    except AttributeError:
        try:
            buf.seek(buf.tell())  # <- For StringIO in Python 2.
            return True
        except Exception:
            return False


def sortable(obj):
    """Returns True if *obj* is sortable else returns False."""
    try:
        sorted([obj, obj])
        return True
    except TypeError:
        return False


def exhaustible(iterable):
    """Returns True if *iterable* is an exhaustible iterator."""
    return iter(iterable) is iter(iterable)
    # Above: This works because exhaustible iterators return themselves
    # when passed to iter() but non-exhaustible iterables will return
    # newly created iterators.


def iterpeek(iterable, default=None):
    if exhaustible(iterable):
        try:
            first_item = next(iterable)  # <- Do not use default value here!
            iterable = chain([first_item], iterable)
        except StopIteration:
            first_item = default
    else:
        first_item = next(iter(iterable), default)
    return first_item, iterable


def _safesort_key(obj):
    """Return a key suitable for sorting objects of any type."""
    if obj is None:
        index = 0
    elif isinstance(obj, Number):
        index = 1
    elif isinstance(obj, str):
        index = 2
    elif isinstance(obj, Iterable):
        index = 3
        obj = tuple(_safesort_key(x) for x in obj)
    else:
        index = id(obj.__class__)
        obj = str(obj)
    return (index, obj)


def _flatten(iterable):
    """Flatten an iterable of elements."""
    for element in iterable:
        if nonstringiter(element):
            for sub_element in _flatten(element):
                yield sub_element
        else:
            yield element


def _unique_everseen(iterable):  # Adapted from itertools recipes.
    """Returns unique elements, preserving order."""
    seen = set()
    seen_add = seen.add
    iterable = filterfalse(seen.__contains__, iterable)
    for element in iterable:
        seen_add(element)
        yield element


def _make_decimal(d):
    """Converts number into normalized Decimal object."""
    if isinstance(d, float):
        d = str(d)
    d = Decimal(d)

    if d == d.to_integral():           # Remove_exponent (from official
        return d.quantize(Decimal(1))  # docs: 9.4.10. Decimal FAQ).
    return d.normalize()


def _make_sentinel(name, reprstring, docstring, truthy=True):
    """Return a new object instance to use as a sentinel to represent
    an entity that cannot be used directly because of some logical
    reason or implementation detail.

    * Query uses a sentinel for the result data when optimizing
      queries because the result does not exist until the query
      is actually executed.
    * _get_error() uses a sentinel to build an appropriate error
      when objects normally required for processing are not found.
    * DataError uses a sentinel to compare float('nan') objects
      because they are not considered to be equal when directly
      compared.
    """
    cls_dict = {
        '__repr__': lambda self: reprstring,
        '__doc__': docstring,
    }

    if not truthy:  # Make object falsy.
        cls_dict['__bool__'] = lambda self: False
        cls_dict['__nonzero__'] = lambda self: False

    return type(name, (object,), cls_dict)()


def _get_arg_lengths(func):
    """Returns a two-tuple containing the number of positional arguments
    as the first item and the number of variable positional arguments as
    the second item.
    """
    try:
        funcsig = inspect.signature(func)
        params_dict = funcsig.parameters
        parameters = params_dict.values()
        args_type = (inspect._POSITIONAL_OR_KEYWORD, inspect._POSITIONAL_ONLY)
        args = [x for x in parameters if x.kind in args_type]
        vararg = [x for x in parameters if x.kind == inspect._VAR_POSITIONAL]
        vararg = vararg.pop() if vararg else None
    except AttributeError:
        try:
            try:  # For Python 3.2 and earlier.
                args, vararg = inspect.getfullargspec(func)[:2]
            except AttributeError:  # For Python 2.7 and earlier.
                args, vararg = inspect.getargspec(func)[:2]
        except TypeError:     # In 3.2 and earlier, raises TypeError
            raise ValueError  # but 3.3 and later raise a ValueError.
    return (len(args), (1 if vararg else 0))


if _version_info[:2] == (3, 4):  # For version 3.4 only!
    _builtin_objects = set([
        abs, all, any, ascii, bin, bool, bytearray, bytes, callable, chr,
        classmethod, compile, complex, delattr, dict, dir, divmod, enumerate,
        eval, filter, float, format, frozenset, getattr, globals, hasattr,
        hash, help, hex, id, input, int, isinstance, issubclass, iter, len,
        list, locals, map, max, memoryview, min, next, object, oct, open, ord,
        pow, property, range, repr, reversed, round, set, setattr, slice,
        sorted, staticmethod, str, sum, super, tuple, type, vars, zip,
        __import__,
    ])
    try:
        eval('_builtin_objects.add(exec)')   # Using eval prevents SyntaxError
        eval('_builtin_objects.add(print)')  # when parsing in 2.7 and earlier.
    except SyntaxError:
        pass
    _get_arg_lengths_orig = _get_arg_lengths
    def _get_arg_lengths(func):
        # In Python 3.4, an empty signature is returned for built-in
        # functions and types--but this is wrong! If this happens,
        # an error should be raised.
        lengths = _get_arg_lengths_orig(func)
        if lengths == (0, 0) and func in _builtin_objects:
            raise ValueError('cannot get lengths of builtin callables')
        return lengths


def _expects_multiple_params(func):
    """Returns True if *func* accepts multiple positional arguments and
    returns False if it accepts one or zero arguments.

    Returns None if the number of arguments cannot be determined--this
    is usually the case for built-in functions and types.
    """
    try:
        arglen, vararglen = _get_arg_lengths(func)
    except ValueError:
        return None
    return (arglen > 1) or (vararglen > 0)


class IterItems(ABC):
    """An iterator that returns item-pairs appropriate for constructing
    a dictionary or other mapping. The given *items_or_mapping* should
    be an iterable of key/value pairs or a mapping.

    .. warning::

        :class:`IterItems` does no type checking or verification of
        the iterable's contents. When iterated over, it should yield
        only those values necessary for constructing a :py:class:`dict`
        or other mapping and no more---no duplicate or unhashable keys.
    """
    def __init__(self, items_or_mapping):
        """Initialize self."""
        if not isinstance(items_or_mapping, (Iterable, Mapping)):
            msg = 'expected iterable or mapping, got {0!r}'
            raise TypeError(msg.format(items_or_mapping.__class__.__name__))

        if isinstance(items_or_mapping, Mapping):
            if hasattr(items_or_mapping, 'iteritems'):
                items = items_or_mapping.iteritems()
            else:
                items = items_or_mapping.items()
        else:
            items = items_or_mapping
            while isinstance(items, IterItems) and hasattr(items, '__wrapped__'):
                items = items.__wrapped__

        self.__wrapped__ = iter(items)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.__wrapped__)

    def next(self):
        return next(self.__wrapped__)

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{0}({1!r})'.format(cls_name, self.__wrapped__)

    # Set iteritems type as a class attribute.
    _iteritems_type = type(getattr(dict(), 'iteritems', dict().items)())

    @classmethod
    def __subclasshook__(cls, C):
        if cls is IterItems:
            if issubclass(C, (ItemsView, cls._iteritems_type, enumerate)):
                return True
        return NotImplemented
