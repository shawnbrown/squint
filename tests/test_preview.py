# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import sys
from .common import redirect_stdout
from .common import unittest

from squint.select import Select
from squint._preview import (
    build_preview,
    displayhook,
    #DEFAULT_MAX_LINES,
    #DEFAULT_MAX_CHARS,
)


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


class TestBuildPreview(PreviewTestCase):
    def test_basic_format(self):
        query = self.select('A')

        actual = build_preview(query)

        expected= (
            "---- preview ----\n"
            "\\[u?'x', u?'x', u?'y', u?'y', u?'z', u?'z'\\]"
        )
        self.assertRegex(actual, expected)


class TestDisplayhook(PreviewTestCase):
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
