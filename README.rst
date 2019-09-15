
***********************************************
squint: Simple query interface for tabular data
***********************************************

.. start-inclusion-marker-description

Squint is a light-weight query interface for tabular data that's
easy to learn and quick to use. A core feature of ``squint`` is that
the structure of a query's *selection* matches the structure of its
*result*. With it you can:

* Select data using Python literals—sets, lists, dictionaries,
  etc.—and get results in the same format.
* Aggregate, map, filter, reduce, and otherwise manipulate data.
* Lazily iterate over results, write them to a file, or eagerly
  evaluate them in memory.
* Analyze data from CSV, Excel, SQL, and other data sources.

.. end-inclusion-marker-description


Installation
============

.. start-inclusion-marker-install

The ``squint`` package is tested on Python 2.6, 2.7, 3.2 through 3.8,
PyPy, and PyPy3; and is freely available under the Apache License,
version 2.

The easiest way to install squint is to use `pip <https://pip.pypa.io>`_:

.. code-block:: console

    pip install squint

To upgrade an existing installation, use the "``--upgrade``" option:

.. code-block:: console

    pip install --upgrade squint

The development repository for ``squint`` is hosted on
`GitHub <https://github.com/shawnbrown/squint>`_. If you need bug-fixes
or features that are not available in the current stable release, you can
"pip install" the development version directly from GitHub:

.. code-block:: console

    pip install --upgrade https://github.com/shawnbrown/squint/archive/master.zip

All of the usual caveats for a development install should
apply—only use this version if you can risk some instability
or if you know exactly what you're doing. While care is taken
to never break the build, it can happen.

.. end-inclusion-marker-install


Some Examples
=============

The examples below will query a CSV file containing the following
data (**example.csv**):

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

To begin, we load the CSV file into a Select object:

.. code-block:: python

    import squint

    select = squint.Select('example.csv')


+------------------------------+--------------------------------------+
| When you select a            | The result contains a                |
+==============================+======================================+
| single column                | list of values from that column      |
|                              |                                      |
| .. code-block:: python       | .. code-block:: python               |
|                              |                                      |
|   select('A')                |   ['foo',                            |
|                              |    'foo',                            |
|                              |    'foo',                            |
|                              |    'bar',                            |
|                              |    'bar',                            |
|                              |    'bar']                            |
+------------------------------+--------------------------------------+
| tuple of columns             | list of tuples with values from      |
|                              | those columns                        |
| .. code-block:: python       |                                      |
|                              | .. code-block:: python               |
|   select(('A', 'B'))         |                                      |
|                              |   [('x', 'foo'),                     |
|                              |    ('x', 'foo'),                     |
|                              |    ('y', 'foo'),                     |
|                              |    ('y', 'bar'),                     |
|                              |    ('z', 'bar'),                     |
|                              |    ('z', 'bar')]                     |
+------------------------------+--------------------------------------+
| dictionary of columns        | dictionary with keys and values      |
|                              | from those columns                   |
| .. code-block:: python       |                                      |
|                              | .. code-block:: python               |
|   select({'A': 'C'})         |                                      |
|                              |   {'x': [20, 30],                    |
|                              |    'y': [10, 20],                    |
|                              |    'z': [10, 10]}                    |
|                              |                                      |
|                              | (values are grouped by matching      |
|                              | key)                                 |
+------------------------------+--------------------------------------+
| dictionary with a tuple of   | dictionary with keys and tuples of   |
| column values                | values from those columns            |
|                              |                                      |
| .. code-block:: python       | .. code-block:: python               |
|                              |                                      |
|   select({'A': ('B', 'C')})  |   {'x': [('foo', 20), ('foo', 30)],  |
|                              |    'y': [('foo', 10), ('bar', 20)],  |
|                              |    'z': [('bar', 10), ('bar', 10)]}  |
+------------------------------+--------------------------------------+
| dictionary with a tuple of   | dictionary with tuple keys and       |
| column keys                  | values from those columns            |
|                              |                                      |
| .. code-block:: python       | .. code-block:: python               |
|                              |                                      |
|   select({('A', 'B'): 'C'})  |   {('x', 'foo'): [20, 30],           |
|                              |    ('y', 'foo'): [10],               |
|                              |    ('y', 'bar'): [20],               |
|                              |    ('z', 'bar'): [10, 10]}           |
+------------------------------+--------------------------------------+


----------

Freely licensed under the Apache License, Version 2.0

Copyright 2015 - 2019 National Committee for an Effective Congress, et al.
