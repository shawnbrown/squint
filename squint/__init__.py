# -*- coding: utf-8 -*-
"""squint: simple query interface for tabular data

PYTEST_DONT_REWRITE
"""
from __future__ import absolute_import


# Check that `sqlite3` is available. Some non-standard builds
# of Python do not include the full standard library (e.g.,
# Jython 2.7 and Jython 2.5).
try:
    import sqlite3 as _sqlite3
except ImportError as err:
    import sys
    message = (
        'The standard library "sqlite3" package is missing '
        'from the current Python installation:\n\nPython {0}'
    ).format(sys.version)
    raise ImportError(message)


# Check that `sqlite3` is not too old. Some very old builds
# of Python were compiled with versions of SQLite that are
# incompatible with Squint (e.g., certain builds of Python
# 3.1.4 and Python 2.6.6).
if _sqlite3.sqlite_version_info < (3, 6, 8):
    import sys
    message = (
        'Squint requires SQLite 3.6.8 or newer but the current '
        'Python installation was built with an old version:\n\n'
        'Python {0}\n\nBuilt with SQLite {1}'
    ).format(sys.version, _sqlite3.sqlite_version)
    raise ImportError(message)


############################################
# Import squint objects into main namespace.
############################################
from .query import BaseElement
from .query import Select
from .query import Query
from .query import Result
from ._vendor.predicate import Predicate
