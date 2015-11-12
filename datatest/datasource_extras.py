
from . import _itertools as itertools
from .datasource import BaseSource
from .datasource import SqliteSource


def _version_info(module):
    """Helper function returns a tuple containing the version number
    components for a given module.

    """
    version = module.__version__
    return tuple(int(i) for i in version.split('.'))


class PandasSource(BaseSource):
    """Loads pandas DataFrame as a data source:
    ::
        subjectData = datatest.PandasSource(df)

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

    @classmethod
    def from_records(cls, data, columns=None):
        """Alternate constructor to load an existing collection of
        records.  Loads *data* (an iterable of lists, tuples, or dicts)
        as a DataFrame with the given *columns*::

            subjectData = datatest.PandasSource.from_records(records, columns)

        """
        try:
            import pandas
            try:
                assert _version_info(pandas) >= (0, 13, 0)
            except AssertionError:
                raise AssertionError("Requires 'pandas' version 0.13.0 "
                                     "or greater.")
        except ImportError:
            raise ImportError(
                "No module named 'pandas'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party libraries 'pandas' (0.13.0 or greater) "
                "and 'numpy' (1.7.1 or greater)."
            )

        data = iter(data)
        if not columns:
            first_row = next(data)
            if hasattr(first_row, 'keys'):  # Dict-like rows.
                columns = tuple(first_row.keys())
            elif hasattr(first_row, '_fields'):  # Namedtuple-like rows.
                columns = first_row._fields
            else:
                msg = ('columns argument can only be omitted if data '
                       'contains dict-rows or namedtuple-rows')
                raise TypeError(msg)
            data = itertools.chain([first_row], data)  # Rebuild original.

        df = pandas.DataFrame.from_records(data, columns=columns)
        return cls(df)


class ExcelSource(BaseSource):
    """Loads first worksheet from XLSX or XLS file *path*::

        subjectData = datatest.ExcelSource('mydata.xlsx')

    Specific worksheets can be accessed by name::

        subjectData = datatest.ExcelSource('mydata.xlsx', 'Sheet 2')

    """

    def __init__(self, path, worksheet=None, in_memory=False):
        """Initialize self."""
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "No module named 'xlrd'\n"
                "\n"
                "This is an optional data source that requires the "
                "third-party library 'xlrd'."
            )

        self._file_repr = repr(path)

        # Open Excel file and get worksheet.
        book = xlrd.open_workbook(path, on_demand=True)
        if worksheet:
            sheet = book.sheet_by_name(worksheet)
        else:
            sheet = book.sheet_by_index(0)

        # Build iterable for worksheet.
        iterrows = (sheet.row(i) for i in range(sheet.nrows))
        iterrows = ([x.value for x in row] for row in iterrows)

        # Build source from records, release resources.
        columns = next(iterrows)
        self._source = SqliteSource.from_records(iterrows, columns)
        book.release_resources()

    def __repr__(self):
        """Return a string representation of the data source."""
        cls_name = self.__class__.__name__
        src_file = self._file_repr
        return '{0}({1})'.format(cls_name, src_file)

    def __iter__(self):
        """Return iterable of dictionary rows (like csv.DictReader)."""
        return iter(self._source)

    def columns(self):
        """Return list of column names."""
        return self._source.columns()

    def sum(self, column, group_by=None, **filter_by):
        return self._source.sum(column, group_by, **filter_by)

    def count(self, group_by=None, **filter_by):
        return self._source.count(group_by, **filter_by)

    def aggregate(self, function, column, group_by=None, **filter_by):
        return self._source.aggregate(function, column, group_by, **filter_by)

    def distinct(self, column, **filter_by):
        return self._source.distinct(column, **filter_by)
