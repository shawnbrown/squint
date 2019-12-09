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


existing_displayhook = sys.displayhook


def preview_query(value):
    if not isinstance(value, Query):
        return existing_displayhook(value)

    try:
        builtins._ = None  # Set to None to avoid recursion.
    except AttributeError:
        pass

    result = value.execute()
    while len(result._preview()) < 80 * 5:
        try:
            result._next_cache()
        except StopIteration:
            break

    text = '{0!r}\n----- preview -----\n{1}'
    text = u(text.format(value, result._preview()))

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
