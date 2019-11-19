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

    def test_bad_evaluation_type(self):
        regex = 'evaluation_type must be a type, found instance of list'
        with self.assertRaisesRegex(TypeError, regex):
            typed = Result([1, 2, 3], [1])


class TestPreview(unittest.TestCase):
    def test_get_cache_length(self):
        peek_length = Result._preview_length + 1

        result = Result([1, 2, 3, 4], evaluation_type=list)
        self.assertEqual(result._get_cache_length(), 4)

        result = Result([1, 2, 3, 4, 5, 6, 7, 8], evaluation_type=list)
        self.assertEqual(result._get_cache_length(), peek_length)

        result = Result(
            {'x': Result([1, 2], evaluation_type=list),
             'y': Result([3, 4], evaluation_type=list)},
            evaluation_type=dict,
        )
        self.assertEqual(result._get_cache_length(), 4)

        result = Result(
            {'x': Result([1, 2, 3, 4, 5, 6, 7, 8], evaluation_type=list),
             'y': Result([1, 2, 3, 4, 5, 6, 7, 8], evaluation_type=list)},
            evaluation_type=dict,
        )
        self.assertEqual(result._get_cache_length(), peek_length)
        self.assertEqual(result.fetch(),                   # Make sure data
                         {'x': [1, 2, 3, 4, 5, 6, 7, 8],   # still fetches
                          'y': [1, 2, 3, 4, 5, 6, 7, 8]})  # properly.

    def test_refresh_cache(self):
        result = Result((1, 2, 3, 4, 5, 6, 7), tuple)

        self.assertEqual(result._cache, deque([1, 2, 3, 4, 5, 6]))

        next(result)  # 1
        result._refresh_cache()
        self.assertEqual(result._cache, deque([2, 3, 4, 5, 6, 7]))

        next(result)  # 2
        result._refresh_cache()
        self.assertEqual(result._cache, deque([3, 4, 5, 6, 7]))

        list(result)  # [3, 4, 5, 6, 7]
        result._refresh_cache()
        self.assertEqual(result._cache, deque([]))

    def test_refresh_cache_mapping(self):
        result = Result(OrderedDict([('a', 1), ('b', 2)]), dict)
        self.assertEqual(result._cache, deque([('a', 1), ('b', 2)]))

        result = Result(IterItems([('a', 1), ('b', 2)]), dict)
        self.assertEqual(result._cache, deque([('a', 1), ('b', 2)]))

        result = Result(iter([iter(['a', 1]), iter(['b', 2])]), dict)
        self.assertEqual(result._cache, deque([('a', 1), ('b', 2)]))

        with self.assertRaises(ValueError):
            result = Result([('a', 1), 'b'], dict)

    def test_shared_iterator(self):
        """Dict result should not assume independent source iterators."""
        def generate_items():  # <- Generator that reads from single iterator.
            shared = iter([
                'x', 1, 1, 1, 2, 2, 2, 3, 3, 3,
                'y', 4, 4, 4, 5, 5, 5, 6, 6, 6,
            ])
            yield next(shared), Result(islice(shared, 9), evaluation_type=list)
            yield next(shared), Result(islice(shared, 9), evaluation_type=list)

        result = Result(generate_items(), evaluation_type=dict)

        expected = {
            'x': [1, 1, 1, 2, 2, 2, 3, 3, 3],
            'y': [4, 4, 4, 5, 5, 5, 6, 6, 6],
        }
        self.assertEqual(result.fetch(), expected)

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
        short_dict = {'a': 1}
        long_dict = {'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7}

        result = Result(short_dict, dict)
        self.assertEqual(result._preview(), "{'a': 1}")

        result = Result(long_dict, dict)
        preview = result._preview()

        if sys.version_info[:2] >= (3, 7):
            self.assertTrue(not preview.startswith('{...: ...'))
            self.assertTrue(preview.endswith('...: ...}'))
        else:
            self.assertEqual(preview.count('...: ...'), 1)  # Truncated ending.

        result = Result(long_dict, dict)
        next(result)
        preview = result._preview()
        if sys.version_info[:2] >= (3, 7):
            self.assertTrue(preview.startswith('{...: ...'))
            self.assertTrue(preview.endswith('...: ...}'))
        else:
            self.assertEqual(preview.count('...: ...'), 2)  # Truncated beginning and end.

        result = Result(IterItems([('a', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list))]), dict)
        preview = result._preview()
        self.assertEqual(preview, "{'a': [1, 2, 3, 4, 5, ...]}")

        ###############################################################
        # TODO: Look into implementing more precise preview truncation.
        ###############################################################

        #iterable = IterItems([
        #    ('a', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
        #    ('b', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
        #])
        #result = Result(iterable, dict)
        #preview = result._preview()
        #self.assertEqual(preview, "{'a': [1, 2, 3, 4, 5, ...], ...: ...}")
        #
        #iterable = IterItems([
        #    ('a', Result([1, 2, 3], list)),
        #    ('b', Result([4, 5, 6], list)),
        #])
        #result = Result(iterable, dict)
        #preview = result._preview()
        #self.assertEqual(preview, "{'a': [1, 2, 3], 'b': [4, 5, ...]}")
        #
        #iterable = IterItems([
        #    ('a', Result([1, 2, 3], list)),
        #    ('b', Result([4, 5, 6], list)),
        #    ('c', Result([7, 8, 9], list)),
        #])
        #result = Result(iterable, dict)
        #preview = result._preview()
        #self.assertEqual(preview, "{'a': [1, 2, 3], 'b': [4, 5, ...], ...: ...}")

    def test_get_formatting_parts(self):
        cache = [1, 2, 3, 4, 5, 6, 7]
        parts = Result._get_formatting_parts(cache, list)
        self.assertEqual(parts, ('[', ']'))

        cache = [1, 2, 3, 4, 5, 6, 7]
        parts = Result._get_formatting_parts(cache, tuple)
        self.assertEqual(parts, ('(', ')'))

        cache = [1]
        parts = Result._get_formatting_parts(cache, tuple)
        self.assertEqual(parts, ('(', ',)'), msg='single item tuple syntax')

        cache = []
        parts = Result._get_formatting_parts(cache, tuple)
        self.assertEqual(parts, ('(', ')'))

        cache = [(1, 1), (2, 2)]
        parts = Result._get_formatting_parts(cache, OrderedDict)
        self.assertEqual(parts, ('OrderedDict([', '])'))

        cache = [1, 2, 3, 4, 5, 6, 7]
        parts = Result._get_formatting_parts(cache, deque)
        self.assertEqual(parts, ('deque([', '])'))


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
