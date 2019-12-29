
.. currentmodule:: squint

.. meta::
    :description: Use squint's Select class.
    :keywords: squint, Select

.. highlight:: python


.. _selecting-data:

##############
Selecting Data
##############

The following examples demonstrate squint's :class:`Select`
class. For these examples, we will use the following data set:

.. _intro-data-set:

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


Narrowing a Selection
=====================

Selections can be narrowed to rows that satisfy given *keyword arguments*.

Narrow a selection to rows where column **B** equals "foo", ``B='foo'``::

    >>> select(('A', 'B'), B='foo')
    Query(<squint.Select object at 0x7f978939>, [('A', 'B')], B='foo')
    ---- preview ----
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo')]

The keyword column does not have to be in the selected result::

    >>> select('A', B='foo')
    Query(<squint.Select object at 0x7f978939>, ['A'], B='foo')
    ---- preview ----
    ['x', 'x', 'y']

Narrow a selection to rows where column **A** equals "x" *or* "y",
``A={'x', 'y'}``::

    >>> select(('A', 'B'), A={'x', 'y'})
    Query(<squint.Select object at 0x7f97893>, [('A', 'B')], A={'y', 'x'})
    ---- preview ----
    [('x', 'foo'), ('x', 'foo'), ('y', 'foo'), ('y', 'bar')]

Narrow a selection to rows where column **A** equals "y" *and*
column **B** equals "bar", ``A='y', B='bar'``::

    >>> select(('A', 'B', 'C'), A='y', B='bar')
    Query(<squint.Select object at 0x7f97893>, [('A', 'B', 'C')], A='y', B='bar')
    ---- preview ----
    [('y', 'bar', '20')]

Only one row matches the above keyword conditions.


Getting the Data Out
====================

The examples so far have called :class:`Select` objects and gotten
:class:`Query` objects in return. While the preview shows what the
output will look like, it's still a Query object---not the data itself.
One way to get the actual data is to use the Query's :meth:`fetch()
<Query.fetch>` method.

Get the data out by calling the :meth:`fetch() <Query.fetch>` method:

.. code-block:: python

    >>> select('A').fetch()
    ['x', 'x', 'y', 'y', 'z', 'z']
