from __future__ import absolute_import

from .base import BaseSource
from .sqlite import SqliteSource


def _version_info(module):
    """Helper function returns a tuple containing the version number
    components for a given module.
    """
    version = module.__version__
    return tuple(int(i) for i in version.split('.'))


class PandasSource(BaseSource):
    """Loads pandas DataFrame as a data source:

    .. code-block:: python

        subjectData = datatest.PandasSource(df)

    This is an optional data source that requires the third-party
    library `pandas <https://pypi.python.org/pypi/pandas>`_.

    .. todo::

        Optimize.  PandasSource is not yet optimized for speed (although
        it will be in the future).  Testing large DataFrames will be
        slow---it is faster to use CsvSource or SqliteSource.
    """
    def __init__(self, df):
        """Initialize self."""
        self._df = df
        self._default_index = (df.index.names == [None])
        try:
            import numpy
            try:
                assert _version_info(numpy) >= (1, 7, 1)
            except AssertionError:
                raise AssertionError("Requires 'numpy' version 1.7.1 "
                                     "or greater.")
        except ImportError:
            raise ImportError(
                "No module named 'numpy'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party library 'numpy' (1.7.1 or greater)."
            )
        self._np = numpy

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        hex_id = hex(id(self._df))
        return "{0}(<pandas.DataFrame object at {1}>)".format(cls_name, hex_id)

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        columns = self.columns()
        if self._default_index:
            for row in self._df.itertuples(index=not self._default_index):
                yield dict(zip(columns, row))
        else:
            gettup = lambda x: x if isinstance(x, tuple) else tuple([x])
            addtup = lambda x: gettup(x[0]) + gettup(x[1:])
            for row in self._df.itertuples(index=not self._default_index):
                yield dict(zip(columns, addtup(row)))

    def columns(self):
        """Return list of column names."""
        if self._default_index:
            return list(self._df.columns)
        return list(self._df.index.names) + list(self._df.columns)

    #def unique(self, *column, **filter_by):
    #    """Return iterable of unique tuples of column values."""
    #    df = self.__filter_by(self._df, self._default_index, **filter_by)
    #    df = df[list(column)].drop_duplicates()
    #    for row in df.itertuples(index=False):
    #        yield row

    #def sum(self, column, **filter_by):
    #    """Return sum of values in column."""
    #    df = self.__filter_by(self._df, self._default_index, **filter_by)
    #    s = df[column].replace('', self._np.nan)
    #    return s.astype(self._np.float).sum()

    #def count(self, **filter_by):
    #    """Return count of rows."""
    #    df = self.__filter_by(self._df, self._default_index, **filter_by)
    #    return len(df)

    @staticmethod
    def __filter_by(df, default_index, **filter_by):
        """Filter iterable by keywords (column=value, etc.)."""
        if not default_index:
            df = df.reset_index()

        for col, val in filter_by.items():
            if isinstance(val, (list, tuple)):
                df = df[df[col].isin(val)]
            else:
                df = df[df[col] == val]
        return df
