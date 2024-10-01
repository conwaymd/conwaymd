"""
# Conway-Markdown: test_utilities.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `utilities.py`.
"""

import unittest

from conwaymd.utilities import (
    compute_longest_common_prefix,
    de_indent,
    escape_attribute_value_html,
    none_to_empty_string,
)


class TestUtilities(unittest.TestCase):
    def test_compute_longest_common_prefix(self):
        self.assertEqual(compute_longest_common_prefix([]), '')
        self.assertEqual(compute_longest_common_prefix(['a', 'b', 'c', 'd']), '')
        self.assertEqual(compute_longest_common_prefix(['  ', '  ', '   ', '      ']), '  ')
        self.assertEqual(compute_longest_common_prefix(['\t  ', '\t  3', '\t   \t \t']), '\t  ')

    def test_de_indent(self):
        self.assertEqual(
            de_indent(
                '''
    4 spaces

      4 spaces + 2 spaces
      \t   4 spaces + 2 spaces, 1 tab, 3 spaces
     
     4 spaces + 1 space (this line and above)
'''
            ),
            '''
4 spaces

  4 spaces + 2 spaces
  \t   4 spaces + 2 spaces, 1 tab, 3 spaces
 
 4 spaces + 1 space (this line and above)
''',
        )
        self.assertEqual(
            de_indent(
                '''
\t\t \t\t\t\t\t\t And,
\t\t \t\t\t\t\t\tWhitespace before closing delimiter:
        '''
            ),
            '''
 And,
Whitespace before closing delimiter:
''',
        )

    def test_escape_attribute_value_html(self):
        self.assertEqual(escape_attribute_value_html('&<>"'), '&amp;&lt;&gt;&quot;')
        self.assertEqual(escape_attribute_value_html('&amp;&lt;&gt;&quot;'), '&amp;&lt;&gt;&quot;')
        self.assertEqual(
            escape_attribute_value_html('https://en.wikipedia.org/w/index.php?title=Wikipedia&action=history'),
            'https://en.wikipedia.org/w/index.php?title=Wikipedia&amp;action=history'
        )
        self.assertEqual(
            escape_attribute_value_html('&ThisEntityNameHasTooManyCharacters;'),
            '&amp;ThisEntityNameHasTooManyCharacters;'
        )
        self.assertEqual(
            escape_attribute_value_html('&NotAValidNameButShortEnough;'),
            '&NotAValidNameButShortEnough;'
        )
        self.assertEqual(escape_attribute_value_html('&#1234567;'), '&#1234567;')
        self.assertEqual(escape_attribute_value_html('&#12345678;'), '&amp;#12345678;')
        self.assertEqual(escape_attribute_value_html('&#x123456;'), '&#x123456;')
        self.assertEqual(escape_attribute_value_html('&#XAbCdeF;'), '&#XAbCdeF;')
        self.assertEqual(escape_attribute_value_html('&#x1234567;'), '&amp;#x1234567;')

    def test_none_to_empty_string(self):
        self.assertEqual(none_to_empty_string(''), '')
        self.assertEqual(none_to_empty_string(None), '')
        self.assertEqual(none_to_empty_string('xyz'), 'xyz')


if __name__ == '__main__':
    unittest.main()
