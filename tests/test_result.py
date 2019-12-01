# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
from .common import unittest
from squint._compatibility.collections import deque
from squint._compatibility.collections import OrderedDict
from squint._compatibility.itertools import islice
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

    def test_bad_evaltype(self):
        regex = 'evaltype must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = Result([1, 2, 3], [1])


class TestSharedIterator(unittest.TestCase):
    def test_shared_iterator(self):
        """Dict result should not assume independent source iterators."""
        def generate_items():  # <- Generator that reads from single iterator.
            shared = iter([
                'x', 1, 1, 1, 2, 2, 2, 3, 3, 3,
                'y', 4, 4, 4, 5, 5, 5, 6, 6, 6,
            ])
            yield next(shared), Result(islice(shared, 9), evaltype=list)
            yield next(shared), Result(islice(shared, 9), evaltype=list)

        result = Result(generate_items(), evaltype=dict)

        expected = {
            'x': [1, 1, 1, 2, 2, 2, 3, 3, 3],
            'y': [4, 4, 4, 5, 5, 5, 6, 6, 6],
        }
        self.assertEqual(result.fetch(), expected)


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
