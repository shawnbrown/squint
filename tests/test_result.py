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


class TestPreview(unittest.TestCase):
    def test_get_cache_length(self):
        peek_length = Result._preview_length + 1

        result = Result([1, 2, 3, 4], evaltype=list)
        self.assertEqual(result._get_cache_length(), 4)

        result = Result([1, 2, 3, 4, 5, 6, 7, 8], evaltype=list)
        self.assertEqual(result._get_cache_length(), peek_length)

        result = Result(
            iterable={'x': Result([1, 2], evaltype=list),
                      'y': Result([3, 4], evaltype=list)},
            evaltype=dict,
        )
        self.assertEqual(result._get_cache_length(), 4)

        result = Result(
            iterable={'x': Result([1, 2, 3, 4, 5, 6, 7, 8], evaltype=list),
                      'y': Result([1, 2, 3, 4, 5, 6, 7, 8], evaltype=list)},
            evaltype=dict,
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
            yield next(shared), Result(islice(shared, 9), evaltype=list)
            yield next(shared), Result(islice(shared, 9), evaltype=list)

        result = Result(generate_items(), evaltype=dict)

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

    def test_get_repr_length(self):
        # List containing multiple reprs.
        beginning = '('
        repr_list = ["'aaaaa'", "'bbbbb'", "'ccccc'"]
        ending = ')'
        actual = Result._get_repr_length(beginning, repr_list, ending)
        expected_repr = "('aaaaa', 'bbbbb', 'ccccc')"
        msg = 'should match len({0!r})'.format(expected_repr)
        self.assertEqual(actual, len(expected_repr), msg=msg)

        # List containing only 1 repr (no separator).
        beginning = '['
        repr_list = ["'aaaaabbbbbccccc'"]
        ending = ']'
        actual = Result._get_repr_length(beginning, repr_list, ending)
        expected = len("['aaaaabbbbbccccc']")
        self.assertEqual(actual, expected, msg='should match repr length')

    def test_preview2_length_handling(self):
        """Test handling of item length and truncation."""
        result = Result([1, 2, 3, 4, 5, 6, 7], tuple)

        self.assertEqual(result._preview2(), '(1, 2, 3, 4, 5, ...)')

        next(result)  # Get next item: 1
        self.assertEqual(result._preview2(), '(..., 2, 3, 4, 5, 6, ...)')

        next(result)  # Get next item: 2
        self.assertEqual(result._preview2(), '(..., 3, 4, 5, 6, 7)')

        list(result)  # Exhaust iterator: (3, 4, 5, 6, 7)
        self.assertEqual(result._preview2(), '()')

    def test_preview2_width_handling(self):
        """Test handling of line breaks and long-line truncation."""
        data = ['a' * 10] * 5  # 71 chararcter repr
        actual = Result(data, tuple)._preview2()
        expected = "('aaaaaaaaaa', 'aaaaaaaaaa', 'aaaaaaaaaa', 'aaaaaaaaaa', 'aaaaaaaaaa')"
        self.assertEqual(actual, expected)

        data = ['a' * 11] * 5  # greater than 72 chararcter repr
        actual = Result(data, tuple)._preview2()
        expected = (
            "('aaaaaaaaaaa',\n"
            " 'aaaaaaaaaaa',\n"
            " 'aaaaaaaaaaa',\n"
            " 'aaaaaaaaaaa',\n"
            " 'aaaaaaaaaaa')"
        )
        self.assertEqual(actual, expected)

        data = ['a' * (Result._preview_width + 1)] * 2  # two long lines
        actual = Result(data, tuple)._preview2()
        expected = (
            "('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...,\n"
            " 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...)"
        )
        self.assertEqual(actual, expected)

    @unittest.skip('refactoring')
    def test_preview2_mapping_handling(self):
        result = Result({'a': 1}, dict)
        self.assertEqual(result._preview2(), "{'a': 1}")

        dict_items = [
            ('a', 1),
            ('b', 2),
            ('c', 3),
            ('d', 4),
            ('e', 5),
            ('f', 6),
            ('g', 7),
        ]

        result = Result(IterItems(dict_items), dict)
        preview = result._preview2()

        self.assertTrue(preview.startswith("{'a': 1,"))
        self.assertTrue(preview.endswith('...}'))

        result = Result(IterItems(dict_items), dict)
        next(result)
        preview = result._preview2()
        self.assertTrue(preview.startswith('{...,'))
        self.assertTrue(preview.endswith('...}'))

        result = Result(IterItems([('a', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list))]), dict)
        preview = result._preview2()
        self.assertEqual(preview, "{'a': [1, 2, 3, 4, 5, ...]}")

        iterable = IterItems([
            ('a', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('b', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
        ])
        result = Result(iterable, dict)
        preview = result._preview2()
        expected = "{'a': [1, 2, 3, 4, 5, ...], 'b': [1, 2, 3, 4, 5, ...]}"
        self.assertEqual(preview, expected)

        iterable = IterItems([
            ('a', Result([1, 2, 3], list)),
            ('b', Result([1, 2, 3], list)),
            ('c', Result([1, 2, 3], list)),
            ('d', Result([1, 2, 3], list)),
            ('e', Result([1, 2, 3], list)),
            ('f', Result([1, 2, 3], list)),
        ])
        result = Result(iterable, dict)
        preview = result._preview2()
        expected = (
            "{'a': [1, 2, 3],\n"
            " 'b': [1, 2, 3],\n"
            " 'c': [1, 2, 3],\n"
            " 'd': [1, 2, 3],\n"
            " 'e': [1, 2, 3],\n"
            " ...}"
        )
        self.assertEqual(preview, expected)

        iterable = IterItems([
            ('a', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('b', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('c', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('d', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('e', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
            ('f', Result([1, 2, 3, 4, 5, 6, 7, 8, 9], list)),
        ])
        result = Result(iterable, dict)
        preview = result._preview2()
        expected = (
            "{'a': [1, 2, 3, 4, 5, ...],\n"
            " 'b': [1, 2, 3, 4, 5, ...],\n"
            " 'c': [1, 2, 3, 4, 5, ...],\n"
            " 'd': [1, 2, 3, 4, 5, ...],\n"
            " 'e': [1, 2, 3, 4, 5, ...],\n"
            " ...}"
        )
        self.assertEqual(preview, expected)

        iterable = IterItems([
            ('a', 'a' * 100),
            ('b', 'b' * 100),
            ('c', 'c' * 100),
        ])
        result = Result(iterable, dict)
        preview = result._preview2()
        expected = (
            "{'a': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa...,\n"
            " 'b': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb...,\n"
            " 'c': 'ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc...}"
        )
        self.assertEqual(preview, expected)


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
