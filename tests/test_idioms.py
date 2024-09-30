"""
# Conway-Markdown: test_idioms.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `idioms.py`.
"""

import os
import unittest

from cmd.idioms import build_attributes_sequence


class TestIdioms(unittest.TestCase):
    def test_build_attributes_sequence(self):
        self.assertEqual(build_attributes_sequence(''), '')
        self.assertEqual(build_attributes_sequence('  '), '')
        self.assertEqual(build_attributes_sequence('\t'), '')
        self.assertEqual(build_attributes_sequence('   \n name=value\n    '), ' name="value"')
        self.assertEqual(build_attributes_sequence(' empty1="" empty2=  boolean'), ' empty1="" empty2="" boolean')
        self.assertEqual(
            build_attributes_sequence('qv="quoted value" bv=bare-value'),
            ' qv="quoted value" bv="bare-value"',
        )
        self.assertEqual(build_attributes_sequence('-before before after -after'), ' before')
        self.assertEqual(build_attributes_sequence('-before before=no after=yes -after'), ' before="no"')
        self.assertEqual(build_attributes_sequence('.1 .2 .3 .4 #a #b #c -id -class'), '')
        self.assertEqual(
            build_attributes_sequence('#=top .=good    l=en    r=3    c=2'),
            ' id="top" class="good" lang="en" rowspan="3" colspan="2"',
        )
        self.assertEqual(
            build_attributes_sequence('id=x #y .a .b name=value .=c class="d"'),
            ' id="y" class="a b c d" name="value"',
        )
        self.assertEqual(
            build_attributes_sequence('w="320" h=16 s="font-weight: bold"'),
            ' width="320" height="16" style="font-weight: bold"',
        )



if __name__ == '__main__':
    unittest.main()
