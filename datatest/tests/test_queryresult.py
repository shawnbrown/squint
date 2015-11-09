"""Result objects for DataSource queries."""
from . import _unittest as unittest

from datatest.queryresult import _coerce_other
from datatest.queryresult import ResultSet
from datatest.queryresult import ResultMapping

from datatest import ExtraItem
from datatest import MissingItem
from datatest import InvalidItem
from datatest import InvalidNumber
from datatest import NotProperSubset
from datatest import NotProperSuperset


class TestMethodDecorator(unittest.TestCase):
    """Test decorator to coerce *other* for comparison magic methods."""
    def test_coerce_other(self):
        # Mock comparison method.
        def fn(self, other):
            return other
        decorator = _coerce_other(ResultSet)
        wrapped = decorator(fn)

        values = set([1, 2, 3, 4])

        other = wrapped(None, values)            # Values set.
        self.assertIsInstance(other, ResultSet)

        other = wrapped(None, list(values))      # Values list.
        self.assertIsInstance(other, ResultSet)

        other = wrapped(None, tuple(values))     # Values tuple.
        self.assertIsInstance(other, ResultSet)

        values_gen = (v for v in values)         # Values generator.
        other = wrapped(None, values_gen)
        self.assertIsInstance(other, ResultSet)

        # Values mapping (not implemented).
        other = wrapped(None, dict(enumerate(values)))
        self.assertEqual(NotImplemented, other)


class TestResultSet(unittest.TestCase):
    def test_init(self):
        values = set([1, 2, 3, 4])

        x = ResultSet(values)               # Values set.
        self.assertEqual(values, x.values)

        x = ResultSet(list(values))         # Values list.
        self.assertEqual(values, x.values)

        x = ResultSet(tuple(values))        # Values tuple.
        self.assertEqual(values, x.values)

        values_gen = (v for v in values)    # Values generator.
        x = ResultSet(values_gen)
        self.assertEqual(values, x.values)

        # Values mapping (type error).
        values_dict = dict(enumerate(values))
        with self.assertRaises(TypeError):
            x = ResultSet(values_dict)

        x = ResultSet(set())
        self.assertEqual(set(), x.values)

    def test_eq(self):
        values = set([1, 2, 3, 4])

        a = ResultSet(values)
        b = ResultSet(values)
        self.assertEqual(a, b)

        # Test coersion.
        a = ResultSet(values)
        b = [1, 2, 3, 4]  # <- Should be coerced into ResultSet internally.
        self.assertEqual(a, b)

    def test_ne(self):
        a = ResultSet(set([1, 2, 3]))
        b = ResultSet(set([1, 2, 3, 4]))
        self.assertTrue(a != b)

    def test_compare(self):
        a = ResultSet(['aaa','bbb','ddd'])
        b = ResultSet(['aaa','bbb','ccc'])
        expected = [ExtraItem('ddd'), MissingItem('ccc')]
        self.assertEqual(expected, a.compare(b))

        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        # Test callable other (all True).
        result = a.compare(lambda x: len(x) == 3)
        self.assertEqual([], result)

        # Test callable other (some False).
        result = a.compare(lambda x: x.startswith('b'))
        expected = set([InvalidItem('aaa'), InvalidItem('ccc')])
        self.assertEqual(expected, set(result))

        # Test subset (less-than-or-equal).
        a = ResultSet(['aaa','bbb','ddd'])
        b = ResultSet(['aaa','bbb','ccc'])
        expected = [ExtraItem('ddd')]
        self.assertEqual(expected, a.compare(b, op='<='))

        # Test strict subset (less-than).
        a = ResultSet(['aaa','bbb'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([], a.compare(b, op='<'))

        # Test strict subset (less-than) assertion violation.
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSubset()], a.compare(b, op='<'))

        # Test superset (greater-than-or-equal).
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ddd'])
        expected = [MissingItem('ddd')]
        self.assertEqual(expected, a.compare(b, op='>='))

        # Test superset subset (greater-than).
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb'])
        self.assertEqual([], a.compare(b, op='>'))

        # Test superset subset (greater-than) assertion violation.
        a = ResultSet(['aaa','bbb','ccc'])
        b = ResultSet(['aaa','bbb','ccc'])
        self.assertEqual([NotProperSuperset()], a.compare(b, op='>'))

    def test_all(self):
        a = ResultSet(['foo', 'bar', 'baz'])

        # Test True.
        result = a.all(lambda x: len(x) == 3)
        self.assertTrue(result)

        # Test False.
        result = a.all(lambda x: x.startswith('b'))
        self.assertFalse(result)


class TestResultMapping(unittest.TestCase):
    def test_init(self):
        values = {'a': 1, 'b': 2, 'c': 3, 'd': 4}

        x = ResultMapping(values, 'foo')                # dict.
        self.assertEqual(values, x.values)

        x = ResultMapping(list(values.items()), 'foo')  # list of tuples.
        self.assertEqual(values, x.values)

        # Non-mapping values (values error).
        values_list = ['a', 'b', 'c', 'd']
        with self.assertRaises(ValueError):
            x = ResultMapping(values_list, 'foo')

        # Single-item wrapped in collection.
        values = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        x = ResultMapping(values, ['foo'])
        unwrapped = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.assertEqual(unwrapped, x.values)

        # IMPLEMENT THIS?
        # Mis-matched group_by and keys.
        #with self.assertRaises(ValueError):
        #    values = {('a',): 1, ('b',): 2, ('c',): 3, ('d',): 4}
        #    x = ResultMapping(values, 'foo')

    def test_eq(self):
        values1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(values1, 'foo')
        b = ResultMapping(values1, 'foo')
        self.assertTrue(a == b)

        values2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = ResultMapping(values1, 'foo')
        b = ResultMapping(values2, 'foo')
        self.assertFalse(a == b)

        # Test coersion of mapping.
        values1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(values1, 'foo')
        self.assertTrue(a == {'a': 1, 'b': 2, 'c': 3, 'd': 4})

        # Test coersion of list of tuples.
        values1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        values2 = [('a', 1),  # <- Should be coerced
                   ('b', 2),  #    into ResultMapping
                   ('c', 3),  #    internally.
                   ('d', 4)]
        a = ResultMapping(values1, 'foo')
        b = values2
        self.assertTrue(a == b)

    def test_ne(self):
        values1 = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        a = ResultMapping(values1, 'foo')
        b = ResultMapping(values1, 'foo')
        self.assertFalse(a != b)

        values2 = {'a': 1, 'b': 2.5, 'c': 3, 'd': 4}
        a = ResultMapping(values1, 'foo')
        b = ResultMapping(values2, 'foo')
        self.assertTrue(a != b)

    def test_compare_numbers(self):
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in self/subject.
        a = ResultMapping({'aaa': 1, 'bbb':   0, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is missing from self/subject.
        a = ResultMapping({'aaa': 1,             'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(-2.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is zero in other/reference.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1, 'bbb': 0, 'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(+2, 0, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # 'b' is missing from other/reference.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = ResultMapping({'aaa': 1,           'ccc': 3, 'ddd': 4}, 'foo')
        expected = [InvalidNumber(+2, None, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

        # Test coersion of *other*.
        a = ResultMapping({'aaa': 1, 'bbb': 2, 'ccc': 3, 'ddd': 4}, 'foo')
        b = {'aaa': 1, 'bbb': 2.5, 'ccc': 3, 'ddd': 4}
        expected = [InvalidNumber(-0.5, 2.5, foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_strings(self):
        a = ResultMapping({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')
        b = ResultMapping({'aaa': 'x', 'bbb': 'z', 'ccc': 'z'}, 'foo')
        expected = [InvalidItem('y', 'z', foo='bbb')]
        self.assertEqual(expected, a.compare(b))

    def test_compare_function(self):
        a = ResultMapping({'aaa': 'x', 'bbb': 'y', 'ccc': 'z'}, 'foo')

        # All True.
        result = a.compare(lambda x: len(x) == 1)
        self.assertEqual([], result)

        # Some False.
        result = a.compare(lambda a: a in ('x', 'y'))
        expected = [InvalidItem('z', foo='ccc')]
        self.assertEqual(expected, result)

    def test_compare_mixed_types(self):
        a = ResultMapping({'aaa':  2,  'bbb': 3,   'ccc': 'z'}, 'foo')
        b = ResultMapping({'aaa': 'y', 'bbb': 4.0, 'ccc':  5 }, 'foo')
        expected = set([
            InvalidItem(2, 'y', foo='aaa'),
            InvalidNumber(-1, 4, foo='bbb'),
            InvalidItem('z', 5, foo='ccc'),
        ])
        self.assertEqual(expected, set(a.compare(b)))


if __name__ == '__main__':
    unittest.main()
