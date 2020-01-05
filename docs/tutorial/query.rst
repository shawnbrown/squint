
.. currentmodule:: squint

.. meta::
    :description: Use squint's Query class.
    :keywords: squint, Query

.. highlight:: python


.. _building-queries:

################
Building Queries
################

The following examples demonstrate squint's :class:`Query` class.
This document builds on the :ref:`selecting-data` tutorial.


Get Started
===========

We will get started the same way we did in the first tutorial. Begin
by starting the Python interactive prompt in the same directory as the
:download:`example.csv </_static/example.csv>` file. Once you are at
the ``>>>`` prompt, import squint and load the data::

    >>> import squint
    >>> select = squint.Select('example.csv')


Creating a Query Object
=======================

In the :ref:`selecting-data` tutorial, we created several Query
objects. Each call to a :class:`Select` object returns a Query.

By selecting a list of elements from column **C**, we get a
:class:`Query` object in return::

    >>> select('C')
    Query(<squint.Select object at 0x7ffa625b>, ['C'])
    ---- preview ----
    ['20', '30', '10', '20', '10', '10']

We can also create Queries directly using the following syntax
(although it's rarely necessary to do so)::

    >>> squint.Query(select, 'C')
    Query(<squint.Select object at 0x7ffa625b>, ['C'])
    ---- preview ----
    ['20', '30', '10', '20', '10', '10']

Once a Query has been created, we can perform additional operations
on it using the methods described below.


Aggregate Methods
=================

Aggregate methods operate on a collection of elements and produce
a single result. The Query class provides several aggregate methods:
:meth:`sum() <Query.sum>`, :meth:`avg() <Query.avg>`,
:meth:`min() <Query.min>`, :meth:`max() <Query.max>`, and
:meth:`count() <Query.count>`. For more information see the
:ref:`aggregate methods <aggregate-methods>` reference documentation.


Use the :meth:`sum() <Query.sum>` method to sum the elements in
column **C**::

    >>> select('C').sum()
    Query(<squint.Select object at 0x7ffa625b>, ['C']).sum()
    ---- preview ----
    100


When an aggregate method is called on a :py:class:`dict` or other
mapping, the groups---the dictionary values---are operated on
separately.

Use the :meth:`sum() <Query.sum>` method to sum each group of
elements::

    >>> select({'A': 'C'}).sum()
    Query(<squint.Select object at 0x7ffa625b>, {'A': ['C']}).sum()
    ---- preview ----
    {'x': 50, 'y': 30, 'z': 20}


.. admonition:: Type Conversion

    The :class:`Query` class contains two methods that perform
    automatic type conversion:

    * :meth:`sum() <Query.sum>`
    * :meth:`avg() <Query.avg>`

    In the example above, column **C** contains :py:class:`str`
    elements. These strings are automatically converted to
    :py:class:`float` values. The other functional methods
    do not do this---use :meth:`map() <Query.map>` to convert
    values explicitly.


Functional Methods
==================

Functional methods take a user-provided function and use it
to perform a specified procedure. The Query class provides
the following functional methods: :meth:`map() <Query.map>`,
:meth:`filter() <Query.filter>`, :meth:`reduce() <Query.reduce>`,
:meth:`apply() <Query.apply>`, etc. For more information see the
:ref:`functional methods <functional-methods>` reference
documentation.


Use the :meth:`map() <Query.map>` method to apply a function
to each element::

    >>> def uppercase(value):
    ...     return value.upper()
    ...
    >>> select('B').map(uppercase)
    Query(<squint.Select object at 0x7ffa625b>, ['B']).map(uppercase)
    ---- preview ----
    ['FOO', 'FOO', 'FOO', 'BAR', 'BAR', 'BAR']


Use the :meth:`filter() <Query.filter>` method to narrow the selection
to items for which the function returns True::

    >>> def not_bar(value):
    ...     return value != 'bar'
    ...
    >>> select('B').filter(not_bar)
    Query(<squint.Select object at 0x7ffa625b>, ['B']).filter(not_bar)
    ---- preview ----
    ['foo', 'foo', 'foo']


.. admonition:: Element-Wise vs Group-Wise Methods

    The :meth:`map() <Query.map>`, :meth:`filter() <Query.filter>`, and
    :meth:`reduce() <Query.reduce>` methods perform element-wise
    procedures---they call their user-provided functions for each
    element and do something with the result. The :meth:`apply()
    <Query.apply>` method, however, performs a group-wise procedure. Rather
    than calling its user-provided function for each element, it calls the
    function once per *container* of elements.


Use the :meth:`apply() <Query.apply>` method to apply a function
to an entire container of elements::

    >>> def join_strings(container):
    ...     return '-'.join(container)
    ...
    >>> select('B').apply(join_strings)
    Query(<squint.Select object at 0x7ffa625b>, ['B']).apply(join_strings)
    ---- preview ----
    'foo-foo-foo-bar-bar-bar'

Like the aggregate methods, when :meth:`apply() <Query.apply>` is
called on a :py:class:`dict` or other mapping, the groups---the
dictionary values---are operated on separately.

Use the :meth:`apply() <Query.apply>` method to apply a function
for each container of elements::

    >>> select({'A': 'B'}).apply(join_strings)
    Query(<squint.Select object at 0x7ffa625b>, {'A': ['B']}).apply(join_strings)
    ---- preview ----
    {'x': 'foo-foo', 'y': 'foo-bar', 'z': 'bar-bar'}


Data Handling Methods
=====================

Data handling methods operate on a collection of elements by reshaping
or otherwise reformatting the data. The Query class provides the
following data handling methods: :meth:`flatten() <Query.flatten>`,
:meth:`unwrap() <Query.unwrap>`, and :meth:`distinct() <Query.distinct>`.
For more information see the :ref:`data handling methods
<datahandling-methods>` reference documentation.


The :meth:`flatten() <Query.flatten>` method serializes a :py:class:`dict`
or other mapping into list of tuple rows. Let's start by observing the
structure of a selected dictionary ``{'B': 'C'}``::

    >>> select({'B': 'C'})
    Query(<squint.Select object at 0x7ffa625b>, {'B': ['C']})
    ---- preview ----
    {'foo': ['20', '30', '10'],
     'bar': ['20', '10', '10']}

Now, use the :meth:`flatten() <Query.flatten>` method to serialize this
same selection (``{'B': 'C'}``) into a list of tuples::

    >>> select({'B': 'C'}).flatten()
    Query(<squint.Select object at 0x7ffa625b>, {'B': ['C']}).flatten()
    ---- preview ----
    [('foo', '20'), ('foo', '30'), ('foo', '10'),
     ('bar', '20'), ('bar', '10'), ('bar', '10')]


The :meth:`unwrap() <Query.unwrap>` method unwraps single-element
containers and returns the element itself. Multi-element containers
are untouched. Observe the structure of the
following preview, ``{('A', 'B'): 'C'}``::

    >>> select({('A', 'B'): 'C'})
    Query(<squint.Select object at 0x7ffa625b>, {('A', 'B'): ['C']})
    ---- preview ----
    {('x', 'foo'): ['20', '30'],
     ('y', 'bar'): ['20'],
     ('y', 'foo'): ['10'],
     ('z', 'bar'): ['10', '10']}


Use the :meth:`unwrap() <Query.unwrap>` method to unwrap ``['20']``
and ``['10']`` but leave the multi-element lists untouched::

    >>> select({('A', 'B'): 'C'}).unwrap()
    Query(<squint.Select object at 0x7ffa625b>, {('A', 'B'): ['C']}).unwrap()
    ---- preview ----
    {('x', 'foo'): ['20', '30'],
     ('y', 'bar'): '20',
     ('y', 'foo'): '10',
     ('z', 'bar'): ['10', '10']}


Data Output Methods
===================

Data output methods evaluate the query and return its results.
The Query class provides the following data output methods:
:meth:`fetch() <Query.fetch>`, :meth:`execute() <Query.execute>`
and :meth:`to_csv() <Query.to_csv>`. For more information see
the :ref:`data output methods <dataoutput-methods>` reference
documentation.


Use the :meth:`fetch() <Query.fetch>` method to eagerly evaluate
the query and return its results::

    >>> select('A').fetch()
    ['x', 'x', 'y', 'y', 'z', 'z']


Use the :meth:`execute() <Query.execute>` method to lazily evaluate the
query by returning a :class:`Result` object:

    >>> select('A').execute()
    <Result object (evaltype=list) at 0x7fa32d16>


.. admonition:: Eager vs Lazy Evaluation

    When a query is *eagerly* evaluated, all of its results are
    loaded into memory at the same time. But when a query is
    *lazily* evaluated, its individual elements are computed
    one-at-a-time as they are needed.

    For many result sets, eager evaluation is entirely acceptible.
    But large result sets might use too much memory or even exceed
    the available memory on your system. An example of lazy evaluation::

        >>> result = select('A').execute()
        >>> for element in result:
        ...     print(element)
        ...
        ...
        x
        x
        y
        y
        z
        z

    For each iteration of the loop above, the next element is
    evaluated and the previous element is discarded. At no point
    in time do all of the elements occupy memory together.


Use the :meth:`to_csv() <Query.to_csv>` method to save the
query results into a CSV file::

    >>> select('A').to_csv('myresults.csv')


Method Chaining
===============

You can build increasingly complex queries by chaining methods
together as needed::

    >>> def not_z(value):
    ...     return value != 'z'
    ...
    >>> def uppercase(value):
    ...     return str(value).upper()
    ...
    >>> select('A').filter(not_z).map(uppercase).fetch()
    ['X', 'X', 'Y', 'Y']

In the example above, the :meth:`filter() <Query.filter>`,
:meth:`map() <Query.map>`, and :meth:`fetch() <Query.fetch>`
methods are chained together to perform multiple operations
within  a single statement and then output the data.

.. admonition:: Method Order

    The order of most Query methods can be mixed and matched
    as needed. But the data output methods---like
    :meth:`fetch() <Query.fetch>`, :meth:`execute() <Query.execute>`,
    and :meth:`to_csv() <Query.to_csv>`---can only appear at the
    end of a chain, not in the middle of one.
