# -*- coding: utf-8 -*-
import sys
try:
    import builtins
except ImportError:
    builtins = __builtins__

from .select import Query


existing_displayhook = sys.displayhook


def preview_query(value):
    if not isinstance(value, Query):
        return existing_displayhook(value)

    builtins._ = None  # Set to None to avoid recursion.

    result = value.execute()
    while len(result._preview()) < 80 * 5:
        try:
            result._next_cache()
        except StopIteration:
            break
    text = '{0!r}\n----- preview -----\n{1}'.format(value, result._preview())

    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        bytes = text.encode(sys.stdout.encoding, 'backslashreplace')
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write(bytes)
        else:
            text = bytes.decode(sys.stdout.encoding, 'strict')
            sys.stdout.write(text)
    sys.stdout.write('\n')
    builtins._ = value
