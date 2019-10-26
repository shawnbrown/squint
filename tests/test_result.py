# -*- coding: utf-8 -*-
from __future__ import absolute_import
from .common import unittest
from squint._utils import IterItems
from squint.result import Result
from squint.result import _TRUNCATED_BEGINNING
from squint.result import _TRUNCATED_ENDING


class TestFetch(unittest.TestCase):
    def test_nonmappings(self):
        """Check collection types (i.e., sized, iterable containers)."""
        result = Result([1, 2, 3], list)
        self.assertEqual(result.fetch(), [1, 2, 3])

        result = Result([1, 2, 3], set)
        self.assertEqual(result.fetch(), set([1, 2, 3]))

        result = Result(iter([1, 2, 3]), set)
        self.assertEqual(result.fetch(), set([1, 2, 3]))

    def test_mappings(self):
        result = Result({'a': 1, 'b': 2}, dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 2})

        result = Result(IterItems([('a', 1), ('b', 2)]), dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 2})

        result = Result(iter([iter(['a', 1]), iter(['b', 2])]), dict)
        self.assertEqual(result.fetch(), {'a': 1, 'b': 2})

        with self.assertRaises(ValueError):
            result = Result([('a', 1), 'b'], dict)
            result.fetch()  # <- Fails late (on fetch, only)

    def test_bad_evaluation_type(self):
        regex = 'evaluation_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = Result([1, 2, 3], [1])


class TestPreview(unittest.TestCase):
    def test_peek(self):
        result = Result((1, 2, 3, 4, 5, 6, 7), tuple)

        self.assertEqual(result._peek(), [1, 2, 3, 4, 5, 6])

        next(result)  # 1
        self.assertEqual(result._peek(), [2, 3, 4, 5, 6, 7])

        next(result)  # 2
        self.assertEqual(result._peek(), [3, 4, 5, 6, 7])

        list(result)  # [3, 4, 5, 6, 7]
        self.assertEqual(result._peek(), [])

    def test_preview(self):
        result = Result([1, 2, 3, 4, 5, 6, 7], tuple)

        self.assertEqual(result._preview(), '(1, 2, 3, 4, 5, ...)')

        next(result)  # 1
        self.assertEqual(result._preview(), '(..., 2, 3, 4, 5, 6, ...)')

        next(result)  # 2
        self.assertEqual(result._preview(), '(..., 3, 4, 5, 6, 7)')

        list(result)  # (3, 4, 5, 6, 7)
        self.assertEqual(result._preview(), '()')

    def test_preview_mapping(self):
        result = Result({'a': 1}, dict)
        self.assertEqual(result._preview(), "{'a': 1}")

        result = Result({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7}, dict)
        preview = result._preview()
        self.assertTrue(not preview.startswith('{...: ...'))
        self.assertTrue(preview.endswith('...: ...}'))

        result = Result({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7}, dict)
        next(result)
        preview = result._preview()
        self.assertTrue(preview.startswith('{...: ...'))
        self.assertTrue(preview.endswith('...: ...}'))


class TestClosing(unittest.TestCase):
    def setUp(self):
        self.log = []

        def closefunc():
            self.log.append('closed')

        self.closefunc = closefunc

    def test_explicit_close(self):
        result = Result(iter([1, 2, 3]), set, closefunc=self.closefunc)
        self.assertEqual(self.log, [], msg='verify log is empty')

        result.close()
        self.assertEqual(self.log, ['closed'], msg='see if close was called')

        result.close()  # <- Second call.
        self.assertEqual(self.log, ['closed'], msg='multiple calls pass without error')

    def test_stopiteration(self):
        """"Should call close() method when iterable is exhausted."""
        result = Result(iter([1, 2, 3]), set, closefunc=self.closefunc)
        self.assertEqual(self.log, [], msg='verify log is empty')

        list(result)  # Exhaust iterable.
        self.assertEqual(self.log, ['closed'])

    def test_delete(self):
        """"Should call close() when object is garbage collected."""
        result = Result(iter([1, 2, 3]), set, closefunc=self.closefunc)
        self.assertEqual(self.log, [], msg='verify log is empty')

        result.__del__()  # Call __del__() directly.
        self.assertEqual(self.log, ['closed'])
