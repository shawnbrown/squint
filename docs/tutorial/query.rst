
.. currentmodule:: squint

.. meta::
    :description: Use squint's Query class.
    :keywords: squint, Query

.. highlight:: python


.. _building-queries:

################
Building Queries
################


Additional Operations
=====================

:class:`Query` objects also support methods for operating
on selected values.

:meth:`Sum <Query.sum>` the elements from column **C**::

    >>> select('C').sum().fetch()
    100

Group by column **A** the sums of elements from column **C**::

    >>> select({'A': 'C'}).sum().fetch()
    {'x': 50, 'y': 30, 'z': 20}

Group by columns **A** and **B** the sums of elements from column
**C**::

    >>> select({('A', 'B'): 'C'}).sum().fetch()
    {('x', 'foo'): 50,
     ('y', 'foo'): 10,
     ('y', 'bar'): 20,
     ('z', 'bar'): 20}

Select :meth:`distinct <Query.distinct>` elements::

    >>> select('A').distinct().fetch()
    ['x', 'y', 'z']

:meth:`Map <Query.map>` elements with a function::

    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> select('A').map(uppercase).fetch()
    ['X', 'X', 'Y', 'Y', 'Z', 'Z']

:meth:`Filter <Query.filter>` elements with a function::

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> select('A').filter(not_z).fetch()
    ['x', 'x', 'y', 'y']

Since each method returns a new Query, it's possible to
chain together multiple method calls to transform the data
as needed::

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> select('A').filter(not_z).map(uppercase).fetch()
    ['X', 'X', 'Y', 'Y']
