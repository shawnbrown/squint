
***********************************************
squint: Simple query interface for tabular data
***********************************************

..
    Project badges for quick reference:

|buildstatus| |devstatus| |license| |pyversions|


.. start-inclusion-marker-description

Squint is a simple query interface for tabular data that's light-weight
and easy to learn. A core feature of Squint is that **the structure of a
query's selection determines the structure of its result**. With
it you can:

* Select data using Python literals—sets, lists, dictionaries,
  etc.—and get results in the same format.
* Aggregate, map, filter, reduce, and otherwise manipulate data.
* Lazily iterate over results, write them to a file, or eagerly
  evaluate them in memory.
* Analyze data from CSV, Excel, SQL, and other data sources.

.. end-inclusion-marker-description


:Documentation:
    | https://squint.readthedocs.io/ (stable)
    | https://squint.readthedocs.io/en/latest/ (latest)

:Official:
    | https://pypi.org/project/squint/

:Development:
    | https://github.com/shawnbrown/squint


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
| set of columns               | list of sets with values from        |
|                              | those columns                        |
| .. code-block:: python       |                                      |
|                              | .. code-block:: python               |
|   select({'A', 'B'})         |                                      |
|                              |   [{'x', 'foo'},                     |
|                              |    {'x', 'foo'},                     |
|                              |    {'y', 'foo'},                     |
|                              |    {'y', 'bar'},                     |
|                              |    {'z', 'bar'},                     |
|                              |    {'z', 'bar'}]                     |
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
|                              | (Notice that values are grouped by   |
|                              | matching key.)                       |
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


Installation
============

.. start-inclusion-marker-install

The Squint package is tested on Python 2.7, 3.4 through 3.8, PyPy,
and PyPy3; and is freely available under the Apache License, version 2.

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


----------

Freely licensed under the Apache License, Version 2.0

Copyright 2015 - 2020 National Committee for an Effective Congress, et al.


..
  SUBSTITUTION DEFINITONS:

.. |buildstatus| image:: https://travis-ci.org/shawnbrown/squint.svg?branch=master
    :target: https://travis-ci.org/shawnbrown/squint
    :alt: Current Build Status

.. |devstatus| image:: https://img.shields.io/pypi/status/squint.svg
    :target: https://pypi.org/project/squint/
    :alt: Development Status

.. |license| image:: https://img.shields.io/badge/license-Apache%202-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache 2.0 License

.. |pyversions| image:: https://img.shields.io/pypi/pyversions/squint.svg
    :target: https://pypi.org/project/squint/#supported-versions
    :alt: Supported Python Versions

.. |githubstars| image:: https://img.shields.io/github/stars/shawnbrown/squint.svg
    :target: https://github.com/shawnbrown/squint/stargazers
    :alt: GitHub users who have starred this project

.. |pypiversion| image:: https://img.shields.io/pypi/v/squint.svg
    :target: https://pypi.org/project/squint/
    :alt: Current PyPI Version
