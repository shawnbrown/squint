
.. currentmodule:: squint

.. meta::
    :description: How-to guide for squint Select, Query, and Result classes.
    :keywords: squint, how-to

.. highlight:: python


############
How-to Guide
############


How To Select Exotic Data Types
===============================

In addition to lists, tuples, and sets, you can also use other container
types. For example, you can use :py:class:`frozensets <frozenset>`,
:py:class:`deques <collections.deque>`, :py:func:`namedtuples
<collections.namedtuple>`, etc. However, normal object limitations
still apply---for example, sets and dictionary keys can only
contain `immutable <http://docs.python.org/3/glossary.html#term-immutable>`_
types (like :py:class:`str`, :py:class:`tuple`, :py:class:`frozenset`,
etc.).

Specifying more exotic data types works the same as previous
examples. Select a deque of namedtuple elements from columns
**A** and **B**, ``deque([ntup('A', 'B')])``:

.. code-block:: python
    :emphasize-lines: 9

    >>> import squint
    >>> from collections import deque
    >>> from collections import namedtuple
    >>>
    >>> ntup = namedtuple('ntup', ['first', 'second'])
    >>>
    >>> select = squint.Select('example.csv')
    >>>
    >>> select(deque([ntup('A', 'B')]))
    Query(<squint.Select object at 0x7f4cf01c>, deque([ntup(first='A', second='B')]))
    ---- preview ----
    deque([ntup(first='x', second='foo'), ntup(first='x', second='foo'),
           ntup(first='y', second='foo'), ntup(first='y', second='bar'),
           ntup(first='z', second='bar'), ntup(first='z', second='bar')])
