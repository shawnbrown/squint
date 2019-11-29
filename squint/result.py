# -*- coding: utf-8 -*-
from __future__ import absolute_import
from pprint import pformat
from ._compatibility.collections import deque
from ._compatibility.collections.abc import (
    Iterator,
    Mapping,
)
from ._compatibility.functools import total_ordering
from ._utils import IterItems


@total_ordering
class _TruncationEllipsis(object):
    def __init__(self, always_lt):
        self.always_lt = always_lt

    def __hash__(self):
        return hash((_TruncationEllipsis, self.always_lt))

    def __repr__(self):
        return '...'

    def __eq__(self, other):
        return self is other

    def __lt__(self, other):
        return self is not other and self.always_lt


_TRUNCATED_BEGINNING = _TruncationEllipsis(True)
_TRUNCATED_ENDING = _TruncationEllipsis(False)


class Result(Iterator):
    """A simple iterator that wraps the results of :class:`Query`
    execution. This iterator is used to facilitate the lazy evaluation
    of data objects (where possible) when asserting data validity.

    Although Result objects are usually constructed automatically,
    it's possible to create them directly::

        iterable = iter([...])
        result = Result(iterable, evaltype=list)

    .. warning::

        When iterated over, the *iterable* **must** yield only those
        values necessary for constructing an object of the given
        *evaltype* and no more. For example, when the *evaltype* is a
        set, the *iterable* must not contain duplicate or unhashable
        values. When the *evaltype* is a :py:class:`dict` or other
        mapping, the *iterable* must contain unique key-value pairs
        or a mapping.
    """
    _preview_length = 5
    _preview_width = 72

    def __init__(self, iterable, evaltype, closefunc=None):
        self._closefunc = closefunc

        if not isinstance(evaltype, type):
            msg = 'evaltype must be a type, found instance of {0}'
            raise TypeError(msg.format(evaltype.__class__.__name__))

        if isinstance(iterable, Mapping):
            iterable = IterItems(iterable)

        #: The underlying iterator---useful when introspecting
        #: or rewrapping.
        self.__wrapped__ = iter(iterable)

        #: The type of instance returned when data is evaluated
        #: with the :meth:`fetch <Result.fetch>` method.
        self.evaltype = evaltype

        self._cache = deque()
        self._refresh_cache()
        self._started_iteration = False

    def close(self):
        """Closes any associated resources. If the resources have
        already been closed, this method passes without error.
        """
        if self._closefunc:
            self._closefunc()
            self._closefunc = None

    def __iter__(self):
        return self

    def __repr__(self):
        cls_name = self.__class__.__name__
        eval_name = self.evaltype.__name__
        hex_id = hex(id(self))
        template = '<{0} object (evaltype={1}) at {2}>'
        return template.format(cls_name, eval_name, hex_id)

    def __next__(self):
        """This method sets the 'started-iteration' flag to True,
        replaces itself with a standard __next__() method, then
        returns the first item from the iterator.
        """
        def __next__(subslf):
            """Return the next item or raise StopIteration."""
            if subslf._cache:
                return subslf._cache.popleft()  # <- EXIT!

            try:
                return next(subslf.__wrapped__)
            except StopIteration:
                subslf.close()
                raise

        bound_method = __next__.__get__(self, self.__class__)
        self.__next__ = bound_method  # <- Replace __next__ method!
        self._started_iteration = True
        return bound_method()

    def next(self):
        return self.__next__()  # For Python 2 compatibility.

    def __del__(self):
        self.close()

    def _refresh_cache(self):
        """Refresh self._cache up to preview_length + 1."""
        cache = self._cache
        wrapped = self.__wrapped__
        refresh_length = self._preview_length + 1

        if issubclass(self.evaltype, Mapping):
            def getnext(iterator):           # Make sure key-value
                key, value = next(iterator)  # pair is not exhaustible.
                return (key, value)
        else:
            getnext = next  # Get next item as-is.

        while self._get_cache_length() < refresh_length:
            try:
                cache.append(getnext(wrapped))
            except StopIteration:
                break

    def _get_cache_length(self):
        """Return cache length."""
        if not issubclass(self.evaltype, Mapping):
            return len(self._cache)  # <- EXIT!

        length = 0
        for item in self._cache:
            key, value = item
            if isinstance(value, Result):
                length += value._get_cache_length()
                continue
            length += 1
        return length

    def _preview(self):
        """Get a pretty-print formatted string to preview the results."""
        self._refresh_cache()

        preview_length = self._preview_length
        if issubclass(self.evaltype, Mapping):
            preview = []
            for k, v in self._cache:
                if isinstance(v, Result):
                    v_iter = v._cache
                    if len(v_iter) > preview_length:
                        v_iter[preview_length] = _TRUNCATED_ENDING
                    v = Result(v_iter, evaltype=v.evaltype)
                preview.append((k, v))

            if len(preview) > preview_length:
                preview[preview_length] = (_TRUNCATED_ENDING, _TRUNCATED_ENDING)

            if preview and self._started_iteration:
                preview = [(_TRUNCATED_BEGINNING, _TRUNCATED_BEGINNING)] + preview

        else:
            preview = list(self._cache)

            if len(preview) > preview_length:
                preview[preview_length] = _TRUNCATED_ENDING

            if preview and self._started_iteration:
                preview = [_TRUNCATED_BEGINNING] + preview

        result = Result(preview, evaltype=self.evaltype).fetch()
        return pformat(result, width=40)

    @staticmethod
    def _get_formatting_parts(cache, evaltype):
        """Get beginning and ending strings for formatting repr."""
        # Return parts for common types.
        if evaltype is list:
            return '[', ']'
        if evaltype is tuple:
            if len(cache) == 1:
                return '(', ',)'
            return '(', ')'
        if evaltype is set:
            return '{', '}'
        if evaltype is dict:
            return '{', '}'

        # For other types, build and examine a sample repr-string.
        sample_item = cache[0] if cache else None
        result = Result([sample_item], evaltype)
        container_repr = repr(result.fetch())
        item_repr = repr(sample_item)
        index = container_repr.index(item_repr, 1)  # Skip first char.
        beginning = container_repr[:index]
        ending = container_repr[index + len(item_repr):]
        return beginning, ending

    @staticmethod
    def _get_repr_length(beginning, repr_list, ending, sep=', '):
        """Return length of repr for collection of items."""
        if not repr_list:
            return len(beginning) + len(ending)  # <- EXIT!

        sum_items = sum(len(x) for x in repr_list)
        sum_separators = len(sep) * (len(repr_list) - 1)
        return len(beginning) + sum_items + sum_separators + len(ending)

    def _get_value_repr(self, value):
        if not isinstance(value, Result):
            return repr(value)  # <- EXIT!

        value._refresh_cache()

        cache = list(value._cache)

        preview_length = value._preview_length
        if len(cache) > preview_length:
            truncate_ending = True
            cache = cache[:preview_length]
        else:
            truncate_ending = False

        beginning, ending = value._get_formatting_parts(cache, value.evaltype)

        items = []
        if cache and value._started_iteration:
            items.append('...')

        for item in cache:
            if isinstance(item, Result):
                item_repr = object.__repr__(item)
            else:
                item_repr = repr(item)
            items.append(item_repr)

        if truncate_ending:
            items.append('...')

        join_str = ', '  # No line-break, all items on a single line.
        items = join_str.join(items)
        return '{0}{1}{2}'.format(beginning, items, ending)

    def _preview2(self):
        """Get a formatted string to preview the result data."""
        self._refresh_cache()

        cache = list(self._cache)

        preview_length = self._preview_length
        if len(cache) > preview_length:
            truncate_ending = True
            cache = cache[:preview_length]
        else:
            truncate_ending = False

        beginning, ending = self._get_formatting_parts(cache, self.evaltype)

        items = []
        if cache and self._started_iteration:
            items.append('...')

        if issubclass(self.evaltype, Mapping):
            for k, v in cache:
                v = self._get_value_repr(v)
                item_repr = '{0!r}: {1}'.format(k, v)
                if len(item_repr) > self._preview_width:
                    slice_end = self._preview_width - 3
                    item_repr = '{0}...'.format(item_repr[:slice_end])
                items.append(item_repr)
        else:
            for item in cache:
                item_repr = repr(item)
                if len(item_repr) > self._preview_width:
                    slice_end = self._preview_width - 3
                    item_repr = '{0}...'.format(item_repr[:slice_end])
                items.append(item_repr)

        if truncate_ending:
            items.append('...')

        char_count = self._get_repr_length(beginning, items, ending)
        if char_count > self._preview_width:
            padding = ' ' * len(beginning)
            join_str = ',\n{0}'.format(padding)  # Line-break for each item.
        else:
            join_str = ', '  # No line-break, all items on a single line.

        items = join_str.join(items)

        return '{0}{1}{2}'.format(beginning, items, ending)

    def fetch(self):
        """Evaluate the entire iterator and return its result::

            result = Result(iter([...]), evaltype=set)
            result_set = result.fetch()  # <- Returns a set of values.

        When evaluating a :py:class:`dict` or other mapping type, any
        values that are, themselves, :class:`Result` objects will
        also be evaluated.
        """
        evaltype = self.evaltype
        if issubclass(evaltype, Mapping):
            def func(obj):
                if hasattr(obj, 'evaltype'):
                    return obj.evaltype(obj)
                return obj

            return evaltype((k, func(v)) for k, v in self)

        return evaltype(self)
