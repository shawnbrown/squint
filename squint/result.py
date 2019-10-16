# -*- coding: utf-8 -*-
from __future__ import absolute_import
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

        while isinstance(iterable, Result):
            iterable = iterable.__wrapped__

        if isinstance(iterable, Mapping):
            iterable = IterItems(iterable)

        #: The underlying iterator---useful when introspecting
        #: or rewrapping.
        self.__wrapped__ = iter(iterable)

        #: The type of instance returned when data is evaluated
        #: with the :meth:`fetch <Result.fetch>` method.
        self.evaluation_type = evaluation_type

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
        try:
            return next(self.__wrapped__)
        except StopIteration:
            self.close()
            raise

    def next(self):
        return next(self.__wrapped__)  # For Python 2 compatibility.

    def __del__(self):
        self.close()

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
