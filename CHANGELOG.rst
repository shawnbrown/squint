
Squint Changelog
================

COMING SOON (0.2.0)
-------------------

* Fixed preview of queries that return empty containers.


2020-01-11 (0.1.0)
------------------

* Added a Query preview feature for interactive use:

      >>> select({'fruit': 'kilos'}).sum()
      Query(<squint.Select object at 0x7f209c30>, {'fruit': ['kilos']}).sum()
      ---- preview ----
      {'apple': 50,
       'grape': 10,
       'pair': 20,
       ...

  Previews provide immediate feedback when building queries interactively.
  Once the query is finished, you can evaluate it with the `fetch()` or
  `execute()` methods as before.

  The preview feature works with the standard interactive prompt, IPython,
  bpython, and Jupyter. However, at the time of this release, ptpython does
  not support this type of customization.

* Added rewritten and expanded tutorial documentation.
* Changed Result attribute from "evaluation_type" to "evaltype" (the old
  name is now deprecated).
* Added Python 3.9 testing and support.
* Removed support for very old versions of Python (2.6, 3.2, and 3.3).


2019-09-15 (0.0.2)
------------------

* Added a package description.
* Added get-reader (with optional extras) to installation requirements.


2019-08-11 (0.0.1)
------------------

* First public release of `squint` as its own repository.
* Added traceback handling to `create_index()` method.
* Removed non-squint/datatest-specific commits from version history.


2019-05-01 (0.0.1.dev9, datatest 0.9.5)
---------------------------------------

* Changed name of Selector class to Select ("Selector" is now deprecated).


2019-04-21 (0.0.1.dev8, datatest 0.9.4)
---------------------------------------

* Added Python 3.8 testing and support.
* Added Predicate class to formalize behavior--also provides inverse-matching
  with the inversion operator (~).
* Added new methods to Query class:

  * Added unwrap() to remove single-element containers and return their
    unwrapped contents.
  * Added starmap() to unpack grouped arguments when applying a function
    to elements.


2018-08-08 (0.0.1.dev7, datatest 0.9.2)
---------------------------------------

* Changed Query class:

  * Added flatten() method to serialize dictionary results.
  * Added to_csv() method to quickly save results as a CSV file.
  * Changed reduce() method to accept "initializer_factory" as
    an optional argument.
  * Changed filter() method to support predicate matching.

* Added True and False as predicates to support "truth value testing" on
  arbitrary objects (to match on truthy or falsy).
* Changed Selector class keyword filtering to support predicate matching.


2018-04-29 (0.0.1.dev6, datatest 0.9.0)
---------------------------------------

* Added formal predicate object handling.
* Changed DataSource to Selector, DataQuery to Query, and DataResult to
  Result.


2017-11-26 (0.0.1.dev5, datatest 0.8.3)
---------------------------------------

* Changed DataQuery selections now default to a list type when no
  outer-container is specified.
* Added DataQuery.apply() method for group-wise function application.
* Added support for user-defined functions to narrow DataSource selections.
* Fixed bug in DataQuery.map() method--now converts set types into lists.


2017-06-11 (0.0.1.dev4, datatest 0.8.2)
---------------------------------------

* Added proper __repr__() support to DataSource and DataQuery.
* Changed DataQuery so it fails early if bad "select" syntax is used or if
  unknown columns are selected.
* Added __copy__() method to DataQuery.


2017-05-31 (0.0.1.dev3, datatest 0.8.1)
---------------------------------------

* Changed DataQuery select behavior to fail immediately when invalid syntax is
  used (rather than later when attempting to execute the query).


2017-05-30 (0.0.1.dev2, datatest 0.8.0)
---------------------------------------

* Added query optimization and a simpler and more expressive syntax.


2016-05-29 (0.0.1.dev1, datatest 0.6.0.dev1)
--------------------------------------------

* First public release of rewritten code base.


Changelog Guidelines
====================

* Begin each section with the date followed by the version number in
  parenthesis. Use the following format: "YYYY-MM-DD (x.y.z)".
* The initial bullet-point may provide a one-line description of the release.
* Following bullet-points should begin with "Added", "Changed", "Fixed", or
  "Removed" when describing the notable changes.
* Limit lines to 80 character width.
