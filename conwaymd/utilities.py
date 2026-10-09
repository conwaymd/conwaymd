"""
# Conway-Markdown: utilities.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Common utility functions.
"""

import functools
import re
from typing import Optional


def compute_longest_common_prefix(strings: list[str]) -> str:
    shortest_string = min(strings, key=len, default='')

    prefix = shortest_string
    while len(prefix) > 0:
        if all(string.startswith(prefix) for string in strings):
            break

        prefix = prefix[:-1]

    return prefix


WHITESPACE_ONLY_FINAL_LINE_PATTERN = re.compile(
    pattern=r'^ [^\S\n]+ \Z',
    flags=re.ASCII | re.MULTILINE | re.VERBOSE,
)
NON_EMPTY_INITIAL_WHITESPACE_PATTERN = re.compile(
    pattern=r'^ [^\S\n]+ | ^ (?! $ )',
    flags=re.ASCII | re.MULTILINE | re.VERBOSE,
)


@functools.lru_cache(maxsize=None)
def initial_indentation_pattern(longest_common_indentation: str) -> re.Pattern:
    return re.compile(pattern=f'^ {re.escape(longest_common_indentation)}', flags=re.MULTILINE | re.VERBOSE)


def de_indent(string: str) -> str:
    """
    De-indent a string.

    Empty lines do not count towards the longest common indentation.
    Whitespace-only lines do count towards the longest common indentation,
    except for the last line, which, if whitespace-only, will have its whitespace erased.

    In contrast, `textwrap.dedent` will perform blank erasure
    of whitespace on all whitespace-only lines,
    even those lines which are not the last line.
    """
    string = WHITESPACE_ONLY_FINAL_LINE_PATTERN.sub(repl='', string=string)
    indentations = NON_EMPTY_INITIAL_WHITESPACE_PATTERN.findall(string)
    longest_common_indentation = compute_longest_common_prefix(indentations)

    string = initial_indentation_pattern(longest_common_indentation).sub(repl='', string=string)

    return string


def escape_attribute_value_html(value: str) -> str:
    """
    Escape an attribute value that will be delimited by double quotes.

    For speed, we make the following assumptions:
    - Entity names are any run of up to 31 letters. At the time of writing (2022-04-18), the longest entity name is
      `CounterClockwiseContourIntegral` according to <https://html.spec.whatwg.org/entities.json>.
      Actually checking is slow for very little return.
    - Decimal code points are any run of up to 7 digits.
    - Hexadecimal code points are any run of up to 6 digits.
    """
    value = re.sub(
        pattern='''
            [&]
            (?!
                (?:
                    [a-zA-Z]{1,31}
                        |
                    [#] (?: [0-9]{1,7} | [xX] [0-9a-fA-F]{1,6} )
                )
                [;]
            )
        ''',
        repl='&amp;',
        string=value,
        flags=re.VERBOSE,
    )
    value = re.sub(pattern='<', repl='&lt;', string=value)
    value = re.sub(pattern='>', repl='&gt;', string=value)
    value = re.sub(pattern='"', repl='&quot;', string=value)

    return value


def none_to_empty_string(string: Optional[str]) -> str:
    if string is None:
        return ''

    return string
