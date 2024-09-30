"""
# Conway-Markdown: test_authorities.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `authorities.py`.
"""

import unittest

from cmd.authorities import extract_basename, make_clean_url


class TestAuthorities(unittest.TestCase):
    def test_extract_basename(self):
        self.assertEqual(extract_basename('path/to/cmd_name'), 'cmd_name')

    def test_make_clean_url(self):
        self.assertEqual(make_clean_url('index'), '')
        self.assertEqual(make_clean_url('/index'), '/')
        self.assertEqual(make_clean_url('path/to/index'), 'path/to/')
        self.assertEqual(make_clean_url('/not-truly-index'), '/not-truly-index')


if __name__ == '__main__':
    unittest.main()
