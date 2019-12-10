# -*- coding: utf-8 -*-
from __future__ import absolute_import
import io
import sys
from .common import redirect_stdout
from .common import unittest

from squint.select import Select
from squint._displayhook import (
    preview_query,
    #DEFAULT_MAX_LINES,
    #DEFAULT_MAX_CHARS,
)


class TestPreviewQuery(unittest.TestCase):
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

    def test_preview_query(self):
        query = self.select('A')

        f = io.StringIO()
        with redirect_stdout(f):
            preview_query(query)
        actual = f.getvalue()

        expected= (
            "^Query\\(<squint.Select object at [^>]+>, \\['A']\\)\n"
            "---- preview ----\n"
            "\\[u?'x', u?'x', u?'y', u?'y', u?'z', u?'z'\\]\n"
        )
        self.assertRegex(actual, expected)
