"""
# Conway-Markdown: test_cli.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `cli.py`.
"""

import os
import unittest

from conwaymd.cli import extract_cmd_name, is_cmd_file


class TestCli(unittest.TestCase):
    def test_extract_cmd_name(self):
        self.assertEqual(extract_cmd_name('file.cmd'), 'file')
        self.assertEqual(extract_cmd_name('file.'), 'file')
        self.assertEqual(extract_cmd_name('file'), 'file')

        if os.sep == '/':
            self.assertEqual(extract_cmd_name('./././file.cmd'), 'file')
            self.assertEqual(extract_cmd_name('./dir/../file.cmd'), 'file')
            self.assertEqual(extract_cmd_name('./file.'), 'file')
            self.assertEqual(extract_cmd_name('./file'), 'file')
        elif os.sep == '\\':
            self.assertEqual(extract_cmd_name(r'.\.\.\file.cmd'), 'file')
            self.assertEqual(extract_cmd_name(r'.\dir\..\file.cmd'), 'file')
            self.assertEqual(extract_cmd_name(r'.\file.'), 'file')
            self.assertEqual(extract_cmd_name(r'.\file'), 'file')

    def test_is_cmd_file(self):
        self.assertTrue(is_cmd_file('file.cmd'))
        self.assertTrue(is_cmd_file('.cmd'))
        self.assertFalse(is_cmd_file('file/cmd'))
        self.assertFalse(is_cmd_file('file.'))
        self.assertFalse(is_cmd_file('file'))


if __name__ == '__main__':
    unittest.main()
