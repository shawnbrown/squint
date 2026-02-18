
.. currentmodule:: squint

.. meta::
    :description: Use squint's Result class.
    :keywords: squint, Result

.. highlight:: python


.. _using-results:

#############
Using Results
#############

The following examples demonstrate squint's :class:`Result` class.
This document builds on the previous :ref:`making-selections` and
:ref:`building-queries` tutorials.


Get Started
===========

We will get started the same way we did in the previous tutorials. Begin
by starting the Python interactive prompt in the same directory as the
:download:`example.csv </_static/example.csv>` file. Once you are at
the ``>>>`` prompt, import squint and load the data::

    >>> import squint
    >>> select = squint.Select('example.csv')


Creating a Result Object
========================

Typically, we create :class:`Result` objects by calling a Query's
:meth:`execute() <Query.execute>` method::

    >>> select('A').execute()
    <Result object (evaltype=list) at 0x7ff5f372>

We can also create Results directly with the following syntax::

    >>> iterable = [1, 2, 3, 4, 5]
    >>> squint.Result(iterable, evaltype=list)
    <Result object (evaltype=list) at 0x7ff5f38d>


The ``evaltype`` Attribute
==========================

The :attr:`evaltype <Result.evaltype>` attribute---short
for "evaluation type"---indicates the type of container
that a Result represents::

    >>> result = select('A').execute()
    >>> result.evaltype
    <class 'list'>


.. _eager-evaluation:

Eager Evaluation
================

When a Result is *eagerly evaluated*, all of its contents
are loaded into memory at the same time. Doing this returns
a container of elements whose type is determined by the
Result's :attr:`evaltype <Result.evaltype>`.

Use the :meth:`fetch() <Result.fetch>` method to eagerly
evaluate a result and get its contents::

    >>> result = select('A').execute()
    >>> result.fetch()
    ['x', 'x', 'y', 'y', 'z', 'z']

For many results, eager evaluation is entirely acceptible.
But large results might use a lot of memory or even exceed
the memory available on your system.


.. _lazy-evaluation:

Lazy Evaluation
===============

When a Result is *lazily evaluated*, its individual elements are
computed one-at-a-time as they are needed. In fact, the primary
purpose of a Result object is to facilitate lazy evaluation when
possible.

Use a ``for`` loop to lazily evaluate a result and get its
contents::

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

For each iteration of the loop in the above example, the next
element is evaluated and the previous element is discarded. **At
no point in time do all of the elements occupy memory together.**

.. note::

    When lazily evaluating a Result, you are free to check the
    :attr:`evaltype <Result.evaltype>` but it is never actually
    used to create an object of that type.
