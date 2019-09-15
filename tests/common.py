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
