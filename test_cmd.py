#!/usr/bin/env python3

"""
# test_cmd.py

Perform unit testing for `cmd.py`.

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import cmd
import unittest


class TestCmd(unittest.TestCase):
  
  def test_is_cmd_file(self):
    self.assertTrue(cmd.is_cmd_file('file.cmd'))
    self.assertTrue(cmd.is_cmd_file('.cmd'))
    self.assertFalse(cmd.is_cmd_file('file/cmd'))
    self.assertFalse(cmd.is_cmd_file('file.'))
    self.assertFalse(cmd.is_cmd_file('file'))
  
  def test_to_normalised_name(self):
    
    self.assertEqual(cmd.extract_cmd_name('file.cmd'), 'file')
    self.assertEqual(cmd.extract_cmd_name('file.'), 'file')
    self.assertEqual(cmd.extract_cmd_name('file'), 'file')
    
    self.assertEqual(cmd.extract_cmd_name('./file.cmd'), 'file')
    self.assertEqual(cmd.extract_cmd_name('./file.'), 'file')
    self.assertEqual(cmd.extract_cmd_name('./file'), 'file')
    
    self.assertEqual(cmd.extract_cmd_name(r'a\b\file'), 'a/b/file')
    self.assertEqual(cmd.extract_cmd_name(r'.\dir\file.cmd'), 'dir/file')


if __name__ == '__main__':
  unittest.main()
