"""Result objects for DataSource queries."""
from . import _unittest as unittest

from datatest.queryresult import _coerce_other
from datatest.queryresult import ResultSet
from datatest.queryresult import ResultMapping

from datatest import ExtraItem
from datatest import MissingItem
from datatest import InvalidItem


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
        a = ResultSet(['a','b','d'])
        b = ResultSet(['a','b','c'])
        expected = [ExtraItem('d'), MissingItem('c')]
        self.assertEqual(expected, a.compare(b))

        a = ResultSet(['a','b','c'])
        b = ResultSet(['a','b','c'])
        self.assertEqual([], a.compare(b), ('When there is no difference, '
                                            'compare should return an empty '
                                            'list.'))

        # Test callable other (all True).
        result = a.compare(lambda x: len(x) == 1)
        self.assertEqual([], result)

        # Test callable other (some False).
        result = a.compare(lambda x: x.startswith('b'))
        expected = set([InvalidItem('a'), InvalidItem('c')])
        self.assertEqual(expected, set(result))

    def test_all(self):
        a = ResultSet(['foo', 'bar', 'baz'])

        # Test True.
        result = a.all(lambda x: len(x) == 3)
        self.assertTrue(result)

        # Test False.
        result = a.all(lambda x: x.startswith('b'))
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
