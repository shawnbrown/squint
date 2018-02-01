# -*- coding: utf-8 -*-
import csv
import io
import sys

from .._compatibility.collections import Iterable
from .._compatibility.itertools import chain
from .._utils import string_types
from .._utils import file_types


########################################################################
# From Dictionaries.
########################################################################
def from_dicts(records):
    records = iter(records)
    first_record = next(records, None)
    header_row = list(first_record.keys())

    yield header_row
    for row in chain([first_record], records):
        yield [row.get(key, None) for key in header_row]


########################################################################
# From Namedtuples.
########################################################################
def from_namedtuples(records):
    records = iter(records)
    first_record = next(records, None)
    if first_record:
        yield first_record._fields  # Header row.
        yield first_record

    for record in records:
        yield record


########################################################################
# CSV Reader.
########################################################################
if sys.version_info[0] >= 3:

    def _from_csv_iterable(iterable, encoding, **kwds):
        return csv.reader(iterable, **kwds)
        # Above, the *encoding* arg is not used but is included so
        # that the csv-helper functions have the same signature.

    def _from_csv_path(path, encoding, **kwds):
        with open(path, 'rt', encoding=encoding, newline='') as f:
            for row in csv.reader(f, **kwds):
                yield row

else:
    import codecs

    class UTF8Recoder(object):
        """Iterator that reads an encoded stream and reencodes the
        input to UTF-8.

        This class is adapted from example code in Python 2.7 docs
        for the csv module.
        """
        def __init__(self, f, encoding):
            if isinstance(f, io.IOBase):
                stream_reader = codecs.getreader(encoding)
                self.reader = stream_reader(f)
            elif isinstance(f, Iterable):
                self.reader = (row.decode(encoding) for row in f)
            else:
                cls_name = f.__class__.__name__
                raise TypeError('unsupported type {0}'.format(cls_name))

        def __iter__(self):
            return self

        def next(self):
            return next(self.reader).encode('utf-8')


    class UnicodeReader(object):
        """A CSV reader which will iterate over lines in the CSV
        file *f*, which is encoded in the given encoding.

        This class is adapted from example code in Python 2.7 docs
        for the csv module.
        """
        def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
            f = UTF8Recoder(f, encoding)
            self.reader = csv.reader(f, dialect=dialect, **kwds)

        @property
        def line_num(self):
            return self.reader.line_num

        @line_num.setter
        def line_num(self, value):
            self.reader.line_num = value

        def next(self):
            row = next(self.reader)
            return [unicode(s, 'utf-8') for s in row]

        def __iter__(self):
            return self

    def _from_csv_iterable(iterable, encoding, **kwds):
        # Check that iterable is expected to return bytes (not strings).
        try:
            if isinstance(iterable, file):
                assert 'b' in iterable.mode
            elif isinstance(iterable, io.IOBase):
                assert not isinstance(iterable, io.TextIOBase)
            else:
                pass
                # If *iterable* is a generic iterator, we just have to
                # trust that the user knows what they're doing. Because
                # in Python 2, there's no reliable way to tell the
                # difference between encoded bytes and decoded strings:
                #
                #   >>> b'x' == 'x'
                #   True
                #
        except AssertionError:
            msg = ('Python 2 unicode compatibility expects bytes, not '
                   'strings (did you open the file in binary mode?)')
            raise TypeError(msg)

        return UnicodeReader(iterable, encoding=encoding, **kwds)


    def _from_csv_path(path, encoding, **kwds):
        with open(path, 'rb') as f:
            for row in UnicodeReader(f, encoding=encoding, **kwds):
                yield row


def from_csv(csvfile, encoding='utf-8', **kwds):
    if isinstance(csvfile, string_types):
        return _from_csv_path(csvfile, encoding, **kwds)
    return _from_csv_iterable(csvfile, encoding, **kwds)


########################################################################
# Pandas DataFrame Reader.
########################################################################
def from_pandas(df, index=True):
    if index:
        yield list(df.index.names) + list(df.columns)
    else:
        yield list(df.columns)

    records = df.to_records(index=index)
    for record in records:
        yield list(record)


########################################################################
# MS Excel Reader.
########################################################################
def from_excel(path, worksheet=0):
    try:
        import xlrd
    except ImportError:
        raise ImportError(
            "No module named 'xlrd'\n"
            "\n"
            "This is an optional constructor that requires the "
            "third-party library 'xlrd'."
        )
    book = xlrd.open_workbook(path, on_demand=True)
    try:
        if isinstance(worksheet, int):
            sheet = book.sheet_by_index(worksheet)
        else:
            sheet = book.sheet_by_name(worksheet)

        for index in range(sheet.nrows):
            yield sheet.row_values(index)

    finally:
        book.release_resources()


########################################################################
# DBF Reader.
########################################################################
def from_dbf(filename, encoding=None, **kwds):
    try:
        import dbfread
    except ImportError:
        raise ImportError(
            "No module named 'dbfread'\n"
            "\n"
            "This is an optional constructor that requires the "
            "third-party library 'dbfread'."
        )
    if 'load' not in kwds:
        kwds['load'] = False
    def recfactory(record):
        return [x[1] for x in record]
    kwds['recfactory'] = recfactory
    table = dbfread.DBF(filename, encoding, **kwds)

    yield table.field_names  # <- Header row.

    for record in table:
        yield record


########################################################################
# Function Dispatching.
########################################################################
def get_reader(obj, *args, **kwds):
    if isinstance(obj, string_types):
        lowercase = obj.lower()

        if lowercase.endswith('.csv'):
            return from_csv(obj, *args, **kwds)

        if lowercase.endswith('.xlsx') or lowercase.endswith('.xls'):
            return from_excel(obj, *args, **kwds)

        if lowercase.endswith('.dbf'):
            return from_dbf(obj, *args, **kwds)

    else:
        if isinstance(obj, file_types) \
                and getattr(obj, 'name', '').lower().endswith('.csv'):
            return from_csv(obj, *args, **kwds)

        if 'pandas' in sys.modules:
            if isinstance(obj, sys.modules['pandas'].DataFrame):
                return from_pandas(obj, *args, **kwds)

        if isinstance(obj, Iterable):
            iterator = iter(obj)
            first_value = next(iterator, None)
            iterator = chain([first_value], iterator)

            if isinstance(first_value, dict):
                return from_dicts(iterator, *args, **kwds)

            if hasattr(first_value, '_fields'):
                return from_namedtuples(iterator, *args, **kwds)

            if isinstance(first_value, (list, tuple)):
                return iterator  # obj already seems reader-like.

    msg = ('unable to determine constructor for {0!r}, specify a '
           'constructor to load - for example: get_reader.from_csv(...), '
           'get_reader.from_pandas(...), etc.')
    raise TypeError(msg.format(obj))


# Add specific constructor functions as properties of the get_reader()
# function--this mimics how alternate constructors look on classes.
get_reader.from_dicts = from_dicts
get_reader.from_namedtuples = from_namedtuples
get_reader.from_csv = from_csv
get_reader.from_pandas = from_pandas
get_reader.from_excel = from_excel
get_reader.from_dbf = from_dbf
