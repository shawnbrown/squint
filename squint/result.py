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
        result = Result(iterable, evaluation_type=list)

    .. warning::

        When iterated over, the *iterable* **must** yield only those
        values necessary for constructing an object of the given
        *evaluation_type* and no more. For example, when the
        *evaluation_type* is a set, the *iterable* must not contain
        duplicate or unhashable values. When the *evaluation_type*
        is a :py:class:`dict` or other mapping, the *iterable* must
        contain unique key-value pairs or a mapping.
    """
    def __init__(self, iterable, evaluation_type, closefunc=None):
        self._closefunc = closefunc

        if not isinstance(evaluation_type, type):
            msg = 'evaluation_type must be a type, found instance of {0}'
            raise TypeError(msg.format(evaluation_type.__class__.__name__))

        if isinstance(iterable, Mapping):
            iterable = IterItems(iterable)

        #: The underlying iterator---useful when introspecting
        #: or rewrapping.
        self.__wrapped__ = iter(iterable)

        #: The type of instance returned when data is evaluated
        #: with the :meth:`fetch <Result.fetch>` method.
        self.evaluation_type = evaluation_type

        self._cache = deque()
        self._preview_length = 5
        self._peek()
        self._initial_cache_length = len(self._cache)
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
        eval_name = self.evaluation_type.__name__
        hex_id = hex(id(self))
        template = '<{0} object (evaluation_type={1}) at {2}>'
        return template.format(cls_name, eval_name, hex_id)

    def __next__(self):
        if self._cache:
            return self._cache.popleft()  # <- EXIT!

        try:
            return next(self.__wrapped__)
        except StopIteration:
            self.close()
            raise

    def next(self):
        return self.__next__()  # For Python 2 compatibility.

    def __del__(self):
        self.close()

    def _peek(self):
        """Peek into the iterator and get a list of upcoming values."""
        cache = self._cache
        wrapped = self.__wrapped__
        peek_length = self._preview_length + 1
        while len(cache) < peek_length:
            try:
                cache.append(next(wrapped))
            except StopIteration:
                break

        return list(cache)

    def _preview(self):
        """Get a pretty-print formatted string to preview the results."""
        if self._initial_cache_length != len(self._cache):
            self._started_iteration = True
        cache = self._peek()
        preview_length = self._preview_length

        if issubclass(self.evaluation_type, Mapping):
            preview = []
            for k, v in cache:
                if isinstance(v, Result):
                    v_iter = list(v._peek())
                    if len(v_iter) > preview_length:
                        v_iter[preview_length] = _TRUNCATED_ENDING
                    v = Result(v_iter, evaluation_type=v.evaluation_type)
                preview.append((k,v))
            compact = True

            if len(preview) > preview_length:
                preview[preview_length] = (_TRUNCATED_ENDING, _TRUNCATED_ENDING)

            if preview and self._started_iteration:
                preview = [(_TRUNCATED_BEGINNING, _TRUNCATED_BEGINNING)] + preview

        else:
            preview = list(cache)
            compact = False
            for value in preview:
                if len(repr(value)) > 72:
                    compact = True
                    break

            if len(preview) > preview_length:
                preview[preview_length] = _TRUNCATED_ENDING

            if preview and self._started_iteration:
                preview = [_TRUNCATED_BEGINNING] + preview

        result = Result(preview, evaluation_type=self.evaluation_type).fetch()
        return pformat(result, compact=compact)

    def fetch(self):
        """Evaluate the entire iterator and return its result::

            result = Result(iter([...]), evaluation_type=set)
            result_set = result.fetch()  # <- Returns a set of values.

        When evaluating a :py:class:`dict` or other mapping type, any
        values that are, themselves, :class:`Result` objects will
        also be evaluated.
        """
        evaluation_type = self.evaluation_type
        if issubclass(evaluation_type, Mapping):
            def func(obj):
                if hasattr(obj, 'evaluation_type'):
                    return obj.evaluation_type(obj)
                return obj

            return evaluation_type((k, func(v)) for k, v in self)

        return evaluation_type(self)
