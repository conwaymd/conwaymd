#!/usr/bin/env python3

"""
# test_cmd.py

Perform unit testing for `cmd.py`.

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import cmd
import unittest


class TestCmd(unittest.TestCase):
  
  def test_to_normalised_name(self):
    
    self.assertEqual(cmd.to_normalised_name('file.cmd'), 'file')
    self.assertEqual(cmd.to_normalised_name('file.'), 'file')
    self.assertEqual(cmd.to_normalised_name('file'), 'file')


if __name__ == '__main__':
  unittest.main()
