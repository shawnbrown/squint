"""Integration tests for common usecases."""
from __future__ import absolute_import
from __future__ import division
from .common import (
    StringIO,
    unittest,
)

import squint


class TestUsecases(unittest.TestCase):
    def setUp(self):
        dummy_fh = StringIO(
            'A,B,C\n'
            'x,foo,20\n'
            'x,foo,30\n'
            'y,foo,10\n'
            'y,bar,20\n'
            'z,bar,10\n'
            'z,bar,10\n'
        )
        dummy_fh.name = 'example.csv'
        self.select = squint.Select(dummy_fh)

    def test_fieldnames(self):
        self.assertEqual(self.select.fieldnames, ['A', 'B', 'C'])

    def test_select_single_column(self):
        query = self.select('A')
        expected = [
            'x',
            'x',
            'y',
            'y',
            'z',
            'z',
        ]
        self.assertEqual(list(query), expected)

    def test_select_multiple_columns(self):
        query = self.select(('A', 'B'))
        expected = [
            ('x', 'foo'),
            ('x', 'foo'),
            ('y', 'foo'),
            ('y', 'bar'),
            ('z', 'bar'),
            ('z', 'bar'),
        ]
        self.assertEqual(list(query), expected)

    def test_select_all(self):
        query = self.select()
        expected = [
            ['x', 'foo', '20'],
            ['x', 'foo', '30'],
            ['y', 'foo', '10'],
            ['y', 'bar', '20'],
            ['z', 'bar', '10'],
            ['z', 'bar', '10'],
        ]
        self.assertEqual(list(query), expected)

