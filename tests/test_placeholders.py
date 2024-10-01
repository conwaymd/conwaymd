"""
# Conway-Markdown: test_placeholders.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `placeholders.py`.
"""

import unittest

from cmd.placeholders import PlaceholderMaster


class TestPlaceholders(unittest.TestCase):
    def test_placeholder_master_protect(self):
        self.assertEqual(PlaceholderMaster.protect(''), '\uF8FF\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('$'), '\uF8FF\uE024\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('£'), '\uF8FF\uE0C2\uE0A3\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('ह'), '\uF8FF\uE0E0\uE0A4\uE0B9\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('€'), '\uF8FF\uE0E2\uE082\uE0AC\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('한'), '\uF8FF\uE0ED\uE095\uE09C\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('𐍈'), '\uF8FF\uE0F0\uE090\uE08D\uE088\uF8FF')
        self.assertEqual(PlaceholderMaster.protect('一鿐'), '\uF8FF\uE0E4\uE0B8\uE080\uE0E9\uE0BF\uE090\uF8FF')

    def test_placeholder_master_unprotect(self):
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uF8FF'), '')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE024\uF8FF'), '$')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0C2\uE0A3\uF8FF'), '£')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0E0\uE0A4\uE0B9\uF8FF'), 'ह')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0E2\uE082\uE0AC\uF8FF'), '€')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0ED\uE095\uE09C\uF8FF'), '한')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0F0\uE090\uE08D\uE088\uF8FF'), '𐍈')
        self.assertEqual(PlaceholderMaster.unprotect('\uF8FF\uE0E4\uE0B8\uE080\uE0E9\uE0BF\uE090\uF8FF'), '一鿐')


if __name__ == '__main__':
    unittest.main()
