
.. currentmodule:: squint

.. meta::
    :description: Use squint's Select, Query, and Result classes.
    :keywords: squint, Select, Query, Result

.. highlight:: python


.. _querying-data:

#############
Querying Data
#############

The following examples demonstrate squint's :class:`Select`,
:class:`Query`, and :class:`Result` classes. This introduction
is written with the intent that you follow along and type the
examples into Python's interactive prompt yourself. This will
give you hands-on experience working with Select and Query
objects.


.. _intro-data-set:

For these examples, we will use the following data set:

    ===  ===  ===
     A    B    C
    ===  ===  ===
     x   foo   20
     x   foo   30
     y   foo   10
     y   bar   20
     z   bar   10
     z   bar   10
    ===  ===  ===


Get Started
===========

Download the data set as a CSV file:

    :download:`example.csv </_static/example.csv>`


Start the Interactive Prompt
----------------------------

Open a command prompt and navigate to the folder that contains
the example data. Then start Python in interactive mode so you
can type commands at the ``>>>`` prompt:

.. code-block:: none

    $ python3
    Python 3.8.0 (default, Oct 16 2019, 12:47:36) 
    [GCC 9.2.1 20190827 (Red Hat 9.2.1-1)] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>>


.. sidebar:: Supported Formats

    Using :class:`Select`, you can load data from difference sources:

    * CSV files
    * Database connections
    * MS Excel files
    * DBF files
    * Pandas objects: DataFrame, Series, Index, or MultiIndex

    You can also use shell-style wildcards to load multiple files
    into a single Select object:

    .. code-block:: python

        select = Select('*.csv')


Load the Data
-------------

Import Squint and load the CSV data into a :class:`Select` object:

    >>> import squint
    >>> select = squint.Select('example.csv')


Inspect Field Names
===================

The :attr:`fieldnames <Select.fieldnames>` attribute contains
a list of field names used in the data:

.. code-block:: python

    >>> select.fieldnames
    ['A', 'B', 'C']


Select Elements
===============

A Select object can be called like a function---doing so returns
a :class:`Query` object.


Select a list of elements from column **A**:

.. code-block:: python

    >>> select('A')
    Query(<squint.Select object at 0x7f02919d>, ['A'])
    ---- preview ----
    ['x', 'x', 'y', 'y', 'z', 'z']

Above, look at the "preview" and notice that these values come
from column **A** in our :ref:`data set <intro-data-set>`.


Select a list of :py:class:`tuple` elements from columns
**A** and **B**, ``('A', 'B')``:

.. code-block:: python

    >>> select(('A', 'B'))
    Query(<squint.Select object at 0x7f02919d>, [('A', 'B')])
    ---- preview ----
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo'), ('y', 'bar'),
     ('z', 'bar'), ('z', 'bar')]


Select a list of :py:class:`list` elements from columns
**A** and **B**, ``['A', 'B']``:

.. code-block:: python

    >>> select(['A', 'B'])
    Query(<squint.Select object at 0x7f02919d>, [['A', 'B']])
    ---- preview ----
    [['x', 'foo'], ['x', 'foo'], ['y', 'foo'], ['y', 'bar'],
     ['z', 'bar'], ['z', 'bar']]


The container type used in a selection determines the container
types returned in the result. You can think of the selection as
a template that describes the values and data types that are
returned.

.. note::

    In the examples above, we did not specify an outer-container
    type and---when unspecified---a :py:class:`list` is used. So
    the outer-containers for all of the previous results were lists:
    a list of strings, a list of tuples, and a list of lists.


Specify Outer-Container Data Types
----------------------------------

Compatible sequence and set types can be selected as inner- and
outer-containers as needed. To specify an outer-container type,
provide one of the following:

* a container that holds a single field name
* a container that holds another container (this second,
  inner-container can hold one or more field names)


Select a :py:class:`set` of elements from column **A**, ``{'A'}``:

.. code-block:: python

    >>> select({'A'})
    Query(<squint.Select object at 0x7f02919d>, {'A'})
    ---- preview ----
    {'x', 'y', 'z'}


Select a :py:class:`set` of :py:class:`tuple` elements from
columns **A** and **B**, ``{('A', 'B')}``:

.. code-block:: python

    >>> select({('A', 'B')})
    Query(<squint.Select object at 0x7f02919d>, {('A', 'B')})
    ---- preview ----
    {('x', 'foo'), ('y', 'foo'), ('y', 'bar'), ('z', 'bar')}


.. tip::

    As mentioned previously, the default outer-container is a list,
    so when an early example used ``select('A')``, that was actually a
    shorthand for ``select(['A'])``. Likewise, ``select(('A', 'B'))``,
    was a shorthand for ``select([('A', 'B')])``.


Specify Single-Item Inner-Containers
------------------------------------

When only one container type is given, it's used as an outer-container
if it holds a single item and used as an inner-container if it holds
multiple items (while the outer-container type defaults to a
:py:class:`list`). To specify a single-item inner-container, you must
provide both inner- and outer-types explicitly---you cannot use the
implicit :py:class:`list` shorthand shown previously.

Select single-item :py:class:`sets <set>` of elements from column **B**,
``[{'B'}]``:

.. code-block:: python

    >>> select([{'B'}])
    Query(<squint.Select object at 0x7ff9292ffb90>, [{'B'}])
    ---- preview ----
    [{'foo'}, {'foo'}, {'foo'}, {'bar'}, {'bar'}, {'bar'}]


Select Groups of Elements
=========================

To select groups of elements, use a :py:class:`dict` (or other mapping
type) as the outer-container---this dictionary must hold a single
key-value pair. The *key* elements determine the "groups" used to arrange
the results. And *value* elements are assigned to the same group when
their associated keys are the same.


Select groups arranged by elements from column **A** that contain
lists of elements from column **B**, ``{'A': 'B'}``:

.. code-block:: python

    >>> select({'A': 'B'})
    Query(<squint.Select object at 0x7f02919d>, {'A': ['B']})
    ---- preview ----
    {'x': ['foo', 'foo'], 'y': ['foo', 'bar'], 'z': ['bar', 'bar']}


Select groups arranged by elements from column **A** that contain
lists of :py:class:`tuple` elements from columns **B** and **C**,
``{'A': ('B', 'C')}``:

.. code-block:: python

    >>> select({'A': ('B', 'C')})
    Query(<squint.Select object at 0x7f8cbc77>, {'A': [('B', 'C')]})
    ---- preview ----
    {'x': [('foo', '20'), ('foo', '30')],
     'y': [('foo', '10'), ('bar', '20')],
     'z': [('bar', '10'), ('bar', '10')]}


To group by multiple columns, we use a :py:class:`tuple` of key
fields. Select groups arranged by elements from columns **A**
and **B** that contain lists of elements from column **C**,
``{('A', 'B'): 'C'}``:

.. code-block:: python

    >>> select({('A', 'B'): 'C'})
    Query(<squint.Select object at 0x7f8cbc77>, {('A', 'B'): ['C']})
    ---- preview ----
    {('x', 'foo'): ['20', '30'],
     ('y', 'bar'): ['20'],
     ('y', 'foo'): ['10'],
     ('z', 'bar'): ['10', '10']}


Specify Container Types for Groups
----------------------------------

When selecting groups of elements, you can specify inner- and
outer-container types for the *value*. The previous groupings
used the default :py:class:`list` shorthand. But as with non-grouped
selections, you can specify a type explicitly.


Select groups arranged by elements from column **A** that contain
:py:class:`sets <set>` of elements from column **B**, ``{'A': {'B'}}``:

.. code-block:: python

    >>> select({'A': {'B'}})
    Query(<squint.Select object at 0x7f2c36ee>, {'A': {'B'}})
    ---- preview ----
    {'x': {'foo'}, 'y': {'foo', 'bar'}, 'z': {'bar'}}


Select groups arranged by elements from column **A** that contain
:py:class:`sets <set>` of :py:class:`tuple` elements from columns
**B** and **C**, ``{'A': {('B', 'C')}}``:

.. code-block:: python

    >>> select({'A': {('B', 'C')}})
    Query(<squint.Select object at 0x7fc4a060>, {'A': {('B', 'C')}})
    ---- preview ----
    {'x': {('foo', '30'), ('foo', '20')},
     'y': {('foo', '10'), ('bar', '20')},
     'z': {('bar', '10')}}


Using More Exotic Data Types
============================

In addition to lists, tuples, and sets, you can also use other container
types. For example, you can use :py:class:`frozensets <frozenset>`,
:py:class:`deques <collections.deque>`, :py:func:`namedtuples
<collections.namedtuple>`, etc. However, normal object limitations
still apply---for example, sets and dictionary keys can only
contain `immutable <http://docs.python.org/3/glossary.html#term-immutable>`_
types (like :py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`,
etc.).


Narrowing a Selection
=====================

Selections can be narrowed to rows that satisfy given keyword
arguments.

Narrow a selection to rows where column **B** equals "foo"::

    >>> select(('A', 'B'), B='foo').fetch()
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo')]

The keyword column does not have to be in the selected result::

    >>> select('A', B='foo').fetch()
    ['x', 'x', 'y']

Narrow a selection to rows where column **A** equals "x" *or* "y"::

    >>> select(('A', 'B'), A=['x', 'y']).fetch()
    [('x', 'foo'),
     ('x', 'foo'),
     ('y', 'foo'),
     ('y', 'bar')]

Narrow a selection to rows where column **A** equals "y" *and*
column **B** equals "bar"::

    >>> select([('A', 'B', 'C')], A='y', B='bar').fetch()
    [('y', 'bar', '20')]

Only one row matches the above keyword conditions.


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
