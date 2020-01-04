
.. currentmodule:: squint

.. meta::
    :description: Squint API Reference
    :keywords: squint, data handling, API


#############
API Reference
#############


******
Select
******

.. autoclass:: Select

    When multiple sources are loaded into a single Select,
    data is aligned by fieldname and missing fields receive
    empty strings:

    .. figure:: /_static/multisource.svg
       :figwidth: 75%
       :alt: Data can be loaded from multiple files.

    .. automethod:: load_data

    .. autoattribute:: fieldnames

    .. automethod:: __call__

    .. automethod:: create_index


*****
Query
*****

.. class:: Query(columns, **where)
           Query(select, columns, **where)

    A class to query data from a source object. Queries can be
    created, modified, and passed around without actually computing
    the result---computation doesn't occur until the query object
    itself or its :meth:`fetch` method is called.

    The given *columns* and *where* arguments can be any values
    supported by :meth:`Select.__call__`.

    Although Query objects are usually created by :meth:`calling
    <datatest.Select.__call__>` an existing Select, it's
    possible to create them independent of any single data source::

        query = Query('A')

    .. automethod:: from_object


    .. _aggregate-methods:

    **AGGREGATE METHODS**

    Aggregate methods operate on a collection of elements and produce
    a single result.

    .. automethod:: sum

    .. automethod:: avg

    .. automethod:: min

    .. automethod:: max

    .. automethod:: count


    .. _functional-methods:

    **FUNCTIONAL METHODS**

    Functional methods take a user-provided function and use it
    to perform a specified procedure.

    .. automethod:: apply

    .. automethod:: map

    .. automethod:: filter

    .. automethod:: reduce

    .. automethod:: starmap


    .. _datahandling-methods:

    **DATA HANDLING METHODS**

    Data handling methods operate on a collection of elements by
    reshaping or otherwise reformatting the data.

    .. automethod:: distinct

    .. automethod:: flatten

    .. automethod:: unwrap


    .. _dataoutput-methods:

    **DATA OUTPUT METHODS**

    Data output methods evaluate the query and return its results.

    .. automethod:: execute

    .. automethod:: fetch

    .. automethod:: to_csv


******
Result
******

.. autoclass:: Result

    .. attribute:: evaltype

        The type of instance returned by the
        :meth:`fetch <Result.fetch>` method.

    .. automethod:: fetch

    .. attribute:: __wrapped__

        The underlying iterator---useful when introspecting
        or rewrapping.


.. _predicate-docs:

*********
Predicate
*********

Squint can use :class:`Predicate` objects for narrowing and filtering
selections.

.. autoclass:: Predicate
