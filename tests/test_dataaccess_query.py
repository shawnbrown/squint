# -*- coding: utf-8 -*-
import textwrap
import unittest

from datatest.dataaccess.query import _validate_call_chain
from datatest.dataaccess.query import BaseQuery
from datatest.dataaccess.query import _DataQuery
from datatest.dataaccess.source import DataQuery
from datatest.dataaccess.source import DataSource


class TestValidateCallChain(unittest.TestCase):
    def test_passing(self):
        _validate_call_chain([])
        _validate_call_chain(['foo'])
        _validate_call_chain(['sum', ((), {})])

    def test_container(self):
        with self.assertRaisesRegex(TypeError, "cannot be 'str'"):
            call_chain = 'bad container'
            _validate_call_chain(call_chain)

    def test_type(self):
        regex = "call_chain must be iterable"
        with self.assertRaisesRegex(TypeError, regex):
            call_chain = 123
            _validate_call_chain(call_chain)

    def test_len(self):
        regex = 'expected string or 2-tuple, found 3-tuple'
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([((), {}, {})])

    def test_first_item(self):
        regex = r"first item must be \*args 'tuple', found 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([(123, {})])

    def test_second_item(self):
        regex = r"second item must be \*\*kwds 'dict', found 'int'"
        with self.assertRaisesRegex(TypeError, regex):
            _validate_call_chain([((), 123)])


class TestBaseQuery(unittest.TestCase):
    def test_init(self):
        query = BaseQuery()
        self.assertEqual(query._data_source, None)
        self.assertEqual(query._call_chain, tuple())

    def test_from_source(self):
        """Test _from_parts() alternate constructor with source, only."""
        source = 'hello_world'
        query = BaseQuery._from_parts(data_source=source)
        self.assertIs(query._data_source, source, 'should be reference to source, not a copy')
        self.assertEqual(query._call_chain, tuple(), 'should be empty tuple')

    def test_from_source_and_chain(self):
        """Test _from_parts() alternate constructor with chain and source."""
        source = 'hello_world'
        chain = ['replace', (('_', ' '), {})]
        query = BaseQuery._from_parts(chain, source)

        self.assertIs(query._data_source, source)
        self.assertEqual(query._call_chain, tuple(chain), 'should be tuple, not list')

    def test_getattr(self):
        query_a = BaseQuery()
        query_b = query_a.upper  # <- Triggers __getattr__().
        self.assertIsInstance(query_b, BaseQuery, '__getattr__ should return BaseQuery')
        self.assertIsNot(query_a, query_b, 'should return copy, not mutate the original')
        self.assertEqual(query_b._call_chain, ('upper',))

        query = BaseQuery().foo.bar.baz
        expected = ('foo', 'bar', 'baz')
        self.assertEqual(query._call_chain, expected)

    def test_call(self):
        query_a = BaseQuery()
        query_b = query_a.upper()  # <- Triggers __call__().
        self.assertIsInstance(query_b, BaseQuery, '__call__ should return BaseQuery')
        self.assertIsNot(query_a, query_b, 'should return copy, not mutate the original')

        userfunc = lambda x: str(x).strip()
        query = BaseQuery().map(userfunc).replace('_', ' ')
        expected = (
            'map',
            ((userfunc,), {}),
            'replace',
            (('_', ' '), {}),
        )
        self.assertEqual(query._call_chain, expected, 'should use expected call chain format')

        query = BaseQuery().foo(bar='baz')  # Test keywords.
        expected = (
            'foo',
            ((), {'bar': 'baz'}),
        )
        self.assertEqual(query._call_chain, expected, 'should use expected call chain format')

    def test_repr_empty(self):
        query = BaseQuery()
        expected = """
            <BaseQuery object at {0}>
            steps: <empty>
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_source_only(self):
        query = BaseQuery._from_parts(data_source='hello_world')
        expected = """
            <BaseQuery object at {0}>
            steps: <empty>
            initial:
              'hello_world'
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_getattr(self):
        query = BaseQuery().upper
        expected = """
            <BaseQuery object at {0}>
            steps:
              upper
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_call(self):
        query = BaseQuery().upper()
        expected = """
            <BaseQuery object at {0}>
            steps:
              upper()
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_call_with_args(self):
        query = BaseQuery().replace('_', ' ')
        expected = """
            <BaseQuery object at {0}>
            steps:
              replace('_', ' ')
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_call_with_func_arg(self):
        def userfunc(x):
            return x
        query = BaseQuery().map(userfunc)
        expected = """
            <BaseQuery object at {0}>
            steps:
              map(userfunc)
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected, "Should use usefunc.__name__ not normal repr.")

        userlambda = lambda x: x
        query = BaseQuery().map(userlambda)  # <- Passes lambda!
        expected = """
            <BaseQuery object at {0}>
            steps:
              map(<lambda>)
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_call_with_kwds(self):
        query = BaseQuery().some_method(some_arg=123)
        expected = """
            <BaseQuery object at {0}>
            steps:
              some_method(some_arg=123)
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_indent(self):
        query = BaseQuery().replace('_', ' ').title()
        expected = """
            <BaseQuery object at {0}>
            steps:
              replace('_', ' ')
              title()
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_repr_integration(self):
        """Test all cases in single query."""
        query = BaseQuery().foo.bar().baz('_', ' ').qux(aa='AA').quux(10, bb='BB')('corge')
        expected = """
            <BaseQuery object at {0}>
            steps:
              foo
              bar()
              baz('_', ' ')
              qux(aa='AA')
              quux(10, bb='BB')
              ('corge')
            initial: <empty>
        """.format(hex(id(query)))
        expected = textwrap.dedent(expected).strip()
        self.assertEqual(repr(query), expected)

    def test_eval(self):
        query = BaseQuery().upper()
        self.assertEqual(query._eval('hello_world'), 'HELLO_WORLD')

        with self.assertRaisesRegex(ValueError, 'no preset found'):
            query._eval()

    def test_eval_preset(self):
        query = BaseQuery._from_parts(data_source='AAA123')
        query = query.isdigit()
        self.assertIs(query._eval(), False)

        query = BaseQuery._from_parts(data_source='AAA123')
        query = query.replace('A', '').isdigit()
        self.assertIs(query._eval(), True)

    def test_eval_overriding_preset(self):
        query = BaseQuery._from_parts(data_source='AAA123')
        query = query.replace('A', '').isdigit()
        self.assertIs(query._eval('BBB123'), False)  # <- 'BBB123' overrides preset


class Test_DataQuery_superclass(unittest.TestCase):
    """Tests for _DataQuery--the superclass for DataQuery."""
    def setUp(self):
        self.source = source = DataSource([
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value':  '5'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ])

    def test_empty(self):
        query = _DataQuery()
        self.assertIsInstance(query, BaseQuery)

    def test_from_parts(self):
        query = _DataQuery._from_parts(data_source=self.source)
        self.assertIsInstance(query, BaseQuery)

    def test_optimize_aggregate(self):
        """Known, wellformed, aggregate queries should be optimized."""
        unoptimized = (
            '_select',  # <- Must be '_select'.
            (({'label1': 'value'},), {'label2': 'x'}),  # <- Must be arg tuple.
            'avg',      # <- Must be known aggregate method.
            ((), {}),   # <- Must be empty.
        )
        output = _DataQuery._optimize(unoptimized)
        optimized = (
            '_select_aggregate',
            (('AVG', {'label1': 'value'},), {'label2': 'x'})
        )
        self.assertEqual(output, optimized)

    def test_optimize_unknown_method_one(self):
        """Call chains with unknown methods should not be optimized."""
        unoptimized = (
            'some_other_method',  # <- Not '_select'!
            (({'label1': 'value'},), {'label2': 'x'}),
            'avg',
            ((), {}),
        )
        output = _DataQuery._optimize(unoptimized)
        self.assertEqual(output, unoptimized)

    def test_optimize_unknown_method_two(self):
        """Call chains with unknown methods should not be optimized."""
        unoptimized = (
            '_select',
            (({'label1': 'value'},), {'label2': 'x'}),
            'other_method',  # <- Not a known aggregate method.
            ((), {}),
        )
        output = _DataQuery._optimize(unoptimized)
        self.assertEqual(output, unoptimized)

    def test_optimize_unexpected_args(self):
        """Call chains with unexpected arguments should not be optimized."""
        unoptimized = (
            '_select',
            (({'label1': 'value'},), {'label2': 'x'}),
            'avg',
            (('not empty'), {}),  # <- Expected to be empty.
        )
        output = _DataQuery._optimize(unoptimized)
        self.assertEqual(output, unoptimized)


class TestDataQuery(unittest.TestCase):
    def setUp(self):
        self.source = source = DataSource([
            {'label1': 'a', 'label2': 'x', 'value': '17'},
            {'label1': 'a', 'label2': 'x', 'value': '13'},
            {'label1': 'a', 'label2': 'y', 'value': '20'},
            {'label1': 'a', 'label2': 'z', 'value': '15'},
            {'label1': 'b', 'label2': 'z', 'value':  '5'},
            {'label1': 'b', 'label2': 'y', 'value': '40'},
            {'label1': 'b', 'label2': 'x', 'value': '25'},
        ])

    def test_from_parts(self):
        query = DataQuery._from_parts(data_source=self.source)
        self.assertIsInstance(query, BaseQuery)

        regex = "expected 'DataSource', got 'list'"
        with self.assertRaisesRegex(TypeError, regex):
            wrong_type = ['hello', 'world']
            query = DataQuery._from_parts(data_source=wrong_type)
