
.. currentmodule:: squint

.. meta::
    :description: How-to guide for squint Select, Query, and Result classes.
    :keywords: squint, how-to

.. highlight:: python


############
How-To Guide
############

Many of the following sections use the example CSV from the
tutorials. You can download it here:

    :download:`example.csv </_static/example.csv>`


How To Install Squint
=====================

.. include:: ../README.rst
    :start-after: start-inclusion-marker-install
    :end-before: end-inclusion-marker-install


How To Convert an Element's Type
================================

To change the data type of individual elements, use the :meth:`map()
<Query.map>` method to apply a type to each element.

In the following example, we convert string elements into the float
type, ``map(float)``:

.. code-block:: python
    :emphasize-lines: 5

    >>> import squint
    >>>
    >>> select = squint.Select('example.csv')
    >>>
    >>> select('C').map(float)
    Query(<squint.Select object at 0x7fcaac15>, ['C']).map(float)
    ---- preview ----
    [20.0, 30.0, 10.0, 20.0, 10.0, 10.0]

In the preview above, we see that every element in column **C**
has been converted into a :py:class:`float` value.


How To Convert a Container's Type
=================================

While you can control a container's type *during* selection, there
are times when you will want to convert a container's type *after*
selection. To do this, use the :meth:`apply() <Query.apply>` method
to apply a container type to the entire group of elements.

In the following example, we convert a list of elements into a tuple
of elements, ``apply(tuple)``:

.. code-block:: python
    :emphasize-lines: 5

    >>> import squint
    >>>
    >>> select = squint.Select('example.csv')
    >>>
    >>> select('A').apply(tuple)
    Query(<squint.Select object at 0x7f8ed8b6>, ['A']).apply(tuple)
    ---- preview ----
    ('x', 'x', 'y', 'y', 'z', 'z')

In the preview above, we see that our query returns a :py:class:`tuple`
instead of a list.


How To Select Single-Item Inner-Containers
==========================================

To specify a single-item inner-container, you must provide both
inner- and outer-types explicitly.

For example, select single-item :py:class:`sets <set>` of elements
from column **B**, ``[{'B'}]``:

.. code-block:: python
    :emphasize-lines: 5

    >>> import squint
    >>>
    >>> select = squint.Select('example.csv')
    >>>
    >>> select([{'B'}])
    Query(<squint.Select object at 0x7ff9292f>, [{'B'}])
    ---- preview ----
    [{'foo'}, {'foo'}, {'foo'}, {'bar'}, {'bar'}, {'bar'}]

This is necessary because a single-item container---when used by
itself---specifies an outer-container type. You cannot use the
implicit :py:class:`list` shorthand demonstrated elsewhere in the
documentation.


How To Select Exotic Data Types
===============================

Most examples demonstrate the use of squint's :class:`Select` class with
list, tuple and set types, but it's possible to use a wide variety of
other containers, too. For instance, :py:class:`frozensets <frozenset>`,
:py:class:`deques <collections.deque>`, :py:func:`namedtuples
<collections.namedtuple>`, etc. can be used the same way you would
use any of the previously mentioned types.

For example, select a :py:class:`deque <collections.deque>` of
:py:func:`namedtuple <collections.namedtuple>` elements from
columns **A** and **B**, ``deque([ntup('A', 'B')])``:

.. code-block:: python
    :emphasize-lines: 9

    >>> from collections import deque
    >>> from collections import namedtuple
    >>> import squint
    >>>
    >>> select = squint.Select('example.csv')
    >>>
    >>> ntup = namedtuple('ntup', ['first', 'second'])
    >>>
    >>> select(deque([ntup('A', 'B')]))
    Query(<squint.Select object at 0x7f4cf01c>, deque([ntup(first='A', second='B')]))
    ---- preview ----
    deque([ntup(first='x', second='foo'), ntup(first='x', second='foo'),
           ntup(first='y', second='foo'), ntup(first='y', second='bar'),
           ntup(first='z', second='bar'), ntup(first='z', second='bar')])

.. note::

    You can mix and match container types as desired, but the normal object
    limitations still apply. For example, sets and dictionary keys can only
    contain `immutable <http://docs.python.org/3/glossary.html#term-immutable>`_
    types (like :py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`,
    etc.).
