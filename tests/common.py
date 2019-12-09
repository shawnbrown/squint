# -*- coding: utf-8 -*-
import sys

version_info = sys.version_info[:2]


if version_info > (2, 6):
    import unittest
else:
    try:
        import unittest2 as unittest
    except ImportError:
        message = 'tests require `unittest2` for Python 2.6 and earlier'
        raise ImportError(message)

try:
    unittest.TestCase.assertRegex  # Renamed in 3.2
    unittest.TestCase.assertRaisesRegex
except AttributeError:
    unittest.TestCase.assertRegex = unittest.TestCase.assertRegexpMatches
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


if version_info > (2, 7):
    from io import StringIO
else:
    import StringIO as _StringIO
    class StringIO(_StringIO.StringIO):
        def write(self, str):
            str = unicode(str)
            return _StringIO.StringIO.write(self, str)


try:
    from contextlib import redirect_stdout  # New in Python 3.4
except ImportError:
    class redirect_stdout:
        def __init__(self, new_target):
            self._new_target = new_target
            self._old_targets = []  # List of old targets to make CM re-entrant.

        def __enter__(self):
            self._old_targets.append(sys.stdout)
            sys.stdout = self._new_target
            return self._new_target

        def __exit__(self, exctype, excinst, exctb):
            sys.stdout = self._old_targets.pop()
