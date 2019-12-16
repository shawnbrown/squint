# -*- coding: utf-8 -*-
from __future__ import absolute_import
from ._compatibility.collections import deque
from ._compatibility.collections.abc import (
    Iterator,
    Mapping,
)
from ._utils import IterItems


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
        self._started_iteration = False

    @property
    def evaluation_type(self):
        import warnings
        warnings.warn(
            "attribute 'evaluation_type' is deprecated, use 'evaltype' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.evaltype

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

    def _get_cache(self):
        preview = list(self._cache)

        if issubclass(self.evaltype, Mapping):
            def cache_only(value):
                if isinstance(value, Result):
                    return Result(value._cache, evaltype=value.evaltype).fetch()
                return value

            preview = [(k, cache_only(v)) for k, v in preview]

        return Result(preview, evaltype=self.evaltype).fetch()

    def _next_cache(self):
        # Try to cache the next item of a nested Result and exit.
        if self._cache and issubclass(self.evaltype, Mapping):
            _, last_value = self._cache[-1]
            try:
                return last_value._next_cache()  # <- EXIT!
            except (AttributeError, StopIteration):
                pass

        # Cache the next item of the outer Result.
        item = next(self.__wrapped__)

        if issubclass(self.evaltype, Mapping):
            key, value = item
            if isinstance(value, Result):
                value._next_cache()
            item = (key, value)

        self._cache.append(item)

    def __del__(self):
        self.close()

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
