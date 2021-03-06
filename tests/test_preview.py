# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import sys
from .common import redirect_stdout
from .common import unittest

from squint.select import (
    Select,
    Query,
)

from squint._preview import displayhook



class PreviewTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.select = Select([
            ['A', 'B', 'C'],
            ['x', 'foo', 20],
            ['x', 'foo', 30],
            ['y', 'foo', 10],
            ['y', 'bar', 20],
            ['z', 'bar', 10],
            ['z', 'bar', 10]
        ])


class TestQueryBuildPreview(PreviewTestCase):
    """Tests for the Query._build_preview() method."""

    def test_result_object(self):
        query = self.select('A')

        actual = query._build_preview()

        expected= (
            "---- preview ----\n"
            "\\[u?'x', u?'x', u?'y', u?'y', u?'z', u?'z'\\]"
        )
        self.assertRegex(actual, expected)

    def test_empty_result_object(self):
        query = self.select('A', B='no match')
        actual = query._build_preview()
        expected = '---- preview ----\n[]'
        self.assertEqual(actual, expected)

        query = self.select(set(['A']), B='no match')
        actual = query._build_preview()
        expected = '---- preview ----\n' + repr(set([]))
        self.assertEqual(actual, expected)

    def test_nonresult_object(self):
        query = self.select('C').sum()

        actual = query._build_preview()

        expected= (
            "---- preview ----\n"
            "100"
        )
        self.assertRegex(actual, expected)

    def test_truncation(self):
        select = Select([
            ['X', 'Y'],
            ['aaa', 1],
            ['bbb', 2],
            ['ccc', 3],
            ['ddd', 4],
            ['eee', 5],
            ['fff', 6],
            ['ggg', 7],
            ['hhh', 8],
            ['iii', 9],
        ])
        query = select({'X': 'Y'}).unwrap()

        actual = query._build_preview()

        expected = (
            "---- preview ----\n"
            "\\{u?'aaa': 1,\n"
            " u?'bbb': 2,\n"
            " u?'ccc': 3,\n"
            " u?'ddd': 4,\n"
            " u?'eee': 5,\n"
            " u?'fff': 6,\n"
            " u?'ggg': 7,\n"
            " \\.\\.\\."
        )
        self.assertRegex(actual, expected)


class TestIPythonReprPretty(PreviewTestCase):
    """Tests for Query._repr_pretty_() (IPython extension hook)."""

    def setUp(self):
        """A mock IPython printer class to inspect _repr_pretty_()."""
        class MockPrinter(object):
            def __init__(self):
                self.output = []

            def text(self, obj):
                self.output.append(str(obj))

            def break_(self):
                self.output.append('\n')

        self.p = MockPrinter()

    def test_no_cycle(self):
        query = self.select('A')
        query._repr_pretty_(self.p, cycle=False)  # Sends to MockPrinter output.

        output = self.p.output
        self.assertEqual(output[0], repr(query))
        self.assertEqual(output[1], '\n')
        self.assertRegex(
            output[2],
            ("---- preview ----\n"
             "\\[u?'x', u?'x', u?'y', u?'y', u?'z', u?'z'\\]"),
        )

    def test_cycle(self):
        query = self.select('A')
        query._repr_pretty_(self.p, cycle=True)  # Sends to MockPrinter output.
        self.assertEqual(self.p.output, [repr(query)])


class TestDisplayhook(PreviewTestCase):
    """Test sys.displayhook handling."""

    def test_displayhook(self):
        query = self.select('A')

        f = io.StringIO()
        with redirect_stdout(f):
            displayhook(query)
        actual = f.getvalue()

        expected= (
            "^Query\\(<squint.Select object at [^>]+>, \\['A']\\)\n"
            "---- preview ----\n"
            "\\[u?'x', u?'x', u?'y', u?'y', u?'z', u?'z'\\]\n"
        )
        self.assertRegex(actual, expected)
