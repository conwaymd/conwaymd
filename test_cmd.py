#!/usr/bin/env python3

"""
# test_cmd.py

Perform unit testing for `cmd.py`.
Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import cmd
import unittest


class TestCmd(unittest.TestCase):
  
  def test_extensible_fence_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.ExtensibleFenceReplacement.build_regex_pattern(
        syntax_is_block=False,
        allowed_flags={'u': 'KEEP_HTML_UNESCAPED', 'i': 'KEEP_INDENTED'},
        has_flags=True,
        opening_delimiter='{',
        extensible_delimiter_character='+',
        extensible_delimiter_min_count=2,
        attribute_specifications=None,
        closing_delimiter='}',
      ),
      '(?P<flags> [ui]* )'
      r'\{'
      r'(?P<extensible_delimiter> \+{2,} )'
      r'(?P<content> [\s\S]*? )'
      '(?P=extensible_delimiter)'
      r'\}'
    )
    
    self.assertEqual(
      cmd.ExtensibleFenceReplacement.build_regex_pattern(
        syntax_is_block=True,
        allowed_flags={},
        has_flags=False,
        opening_delimiter='',
        extensible_delimiter_character='$',
        extensible_delimiter_min_count=4,
        attribute_specifications='',
        closing_delimiter='',
      ),
      r'^[ \t]*'
      r'(?P<extensible_delimiter> \${4,} )'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'\n'
      r'(?P<content> [\s\S]*? )'
      r'^[ \t]*'
      '(?P=extensible_delimiter)'
    )
  
  def test_factorise_repeated_character(self):
    self.assertEqual(
      cmd.factorise_repeated_character('$$$$$$'),
      ('$', 6)
    )
    self.assertEqual(
      cmd.factorise_repeated_character('````'),
      ('`', 4)
    )
    self.assertRaises(
      cmd.NotCharacterRepeatedException,
      cmd.factorise_repeated_character, '$$$$$$````'
    )
    self.assertRaises(
      cmd.NotCharacterRepeatedException,
      cmd.factorise_repeated_character, 'ThisStringIsNotACharacterRepeated'
    )
  
  def test_to_attributes_sequence(self):
    self.assertEqual(
      cmd.to_attributes_sequence(''),
      ''
    )
    self.assertEqual(
      cmd.to_attributes_sequence('name="quoted value" name=bare-value'),
      ' name="quoted value" name="bare-value"'
    )
    self.assertEqual(
      cmd.to_attributes_sequence('#=top .=good    l=en    r=3    c=2'),
      ' id="top" class="good" lang="en" rowspan="3" colspan="2"'
    )
    self.assertEqual(
      cmd.to_attributes_sequence('w="320" h=16 s="font-weight: bold"'),
      ' width="320" height="16" style="font-weight: bold"'
    )
  
  def test_to_flags_regex(self):
    self.assertEqual(cmd.to_flags_regex({}, False), '')
    self.assertEqual(
      cmd.to_flags_regex(
        {
          'u': 'KEEP_HTML_UNESCAPED',
          'w': 'REDUCE_WHITESPACE',
          'i': 'KEEP_INDENTED',
        },
        True,
      ),
      '(?P<flags> [uwi]* )'
    )
  
  def test_extensible_delimiter_opening_regex(self):
    self.assertEqual(
      cmd.to_extensible_delimiter_opening_regex('$', 5),
      r'(?P<extensible_delimiter> \${5,} )'
    )
  
  def test_none_to_empty_string(self):
    self.assertEqual(cmd.none_to_empty_string(''), '')
    self.assertEqual(cmd.none_to_empty_string(None), '')
    self.assertEqual(cmd.none_to_empty_string('xyz'), 'xyz')
  
  def test_extract_rules_and_content(self):
    self.assertEqual(cmd.extract_rules_and_content(''), ('', ''))
    self.assertEqual(cmd.extract_rules_and_content('abc'), ('', 'abc'))
    self.assertEqual(cmd.extract_rules_and_content('%%%abc'), ('', '%%%abc'))
    self.assertEqual(cmd.extract_rules_and_content('abc%%%'), ('', 'abc%%%'))
    self.assertEqual(cmd.extract_rules_and_content('%%%\nabc'), ('', 'abc'))
    self.assertEqual(cmd.extract_rules_and_content('X%%\nY'), ('', 'X%%\nY'))
    self.assertEqual(
      cmd.extract_rules_and_content(
        'This be the preamble.\nEven two lines of preamble.\n%%%%%\nYea.\n'
      ),
      ('This be the preamble.\nEven two lines of preamble.\n', 'Yea.\n')
    )
    self.assertEqual(
      cmd.extract_rules_and_content(
        'ABC\n%%%\n123\n%%%%%%%\nXYZ'
      ),
      ('ABC\n', '123\n%%%%%%%\nXYZ')
    )
  
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
