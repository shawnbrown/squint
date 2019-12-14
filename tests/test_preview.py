# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import sys
from .common import redirect_stdout
from .common import unittest

from squint.select import (
    Select,
    Query,
    #DEFAULT_MAX_LINES,
    #DEFAULT_MAX_CHARS,
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

    def test_nonresult_object(self):
        query = self.select('C').sum()

        actual = query._build_preview()

        expected= (
            "---- preview ----\n"
            "100"
        )
        self.assertRegex(actual, expected)


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
