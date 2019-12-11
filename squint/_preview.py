# -*- coding: utf-8 -*-
import sys
try:
    import builtins
except ImportError:
    builtins = __builtins__

try:
    u = unicode
except NameError:
    u = str

from .select import Query
from .result import Result


def build_preview(query):
    """Take *query* and return a formatted preview string."""
    result = query.execute()

    if isinstance(result, Result):
        while len(result._preview()) < 80 * 5:
            try:
                result._next_cache()
            except StopIteration:
                break
        preview = result._preview()
    else:
        preview = repr(result)

    return '---- preview ----\n{0}'.format(preview)


existing_displayhook = sys.displayhook


def displayhook(value):
    if not isinstance(value, Query):
        return existing_displayhook(value)

    try:
        builtins._ = None  # Set to None to avoid recursion.
    except AttributeError:
        pass

    text = '{0!r}\n{1}'.format(value, build_preview(value))
    text = u(text)  # Convert to Unicode (for Python 2.x).

    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        bytes = text.encode(sys.stdout.encoding, 'backslashreplace')
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(bytes)
        else:
            text = bytes.decode(sys.stdout.encoding, 'strict')
            sys.stdout.write(text)
    sys.stdout.write(u('\n'))

    try:
        builtins._ = value
    except AttributeError:
        pass
