#!/usr/bin/env python3

"""
# cmd.py

Convert Conway-Markdown (CMD) to HTML.
Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

## Structure

CMD files are parsed as
        «replacement_rules»
        «delimiter»
        «main_content»
where «delimiter» is the first occurrence of
3-or-more percent signs on its own line.
If the file is free of «delimiter»,
thw whole file is parsed is parsed as «main_content».

## Replacement rules

TODO

## Main content

TODO
"""


import argparse
import os
import re
import sys


GENERIC_ERROR_EXIT_CODE = 1
COMMAND_LINE_ERROR_EXIT_CODE = 2


class NotCharacterRepeatedException(Exception):
  pass


class MissingAttributeException(Exception):
  
  def __init__(self, missing_attribute):
    self._missing_attribute = missing_attribute
  
  def get_missing_attribute(self):
    return self._missing_attribute


class ExtensibleDelimiterException(Exception):
  
  def __init__(self, extensible_delimiter):
    self._extensible_delimiter = extensible_delimiter
  
  def get_extensible_delimiter(self):
    return self._extensible_delimiter


class ExtensibleFenceReplacement:
  """
  A generalised extensible-fence-style replacement rule.
  
  Inspired by the repeatable backticks of John Gruber's Markdown.
  CMD replacement rule syntax:
          ExtensibleFenceReplacement: #«id»
          - replacement_order: ROOT | BEFORE #«id» | AFTER #«id» | (def) NONE
          - syntax_type: DISPLAY | INLINE
          - allowed_flags:
            - «letter»: KEEP_HTML_UNESCAPED | REDUCE_WHITESPACE | KEEP_INDENTED
            [...]
            (def «none»)
          - opening_delimiter: «string» (def «empty»)
          - extensible_delimiter: «character_repeated»
          - attribute_specifications: (def) NONE | EMPTY | «string»
          - content_replacements: #«id» [...] (def «none»)
          - closing_delimiter: «string» (def «empty»)
  """
  
  def __init__(self, id_):
    self._id = id_
    self._replacement_order = 'NONE'
    self._syntax_type = None
    self._allowed_flags = {}
    self._opening_delimiter = ''
    self._extensible_delimiter = None
    self._attribute_specifications = 'NONE'
    self._content_replacements = []
    self._closing_delimiter = ''
    self._regex = None
  
  def set_replacement_order(self, replacement_order):
    self._replacement_order = replacement_order
  
  def set_syntax_type(self, syntax_type):
    self._syntax_type = syntax_type
  
  def set_allowed_flags(self, flag_setting_from_letter):
    self._allowed_flags = flag_setting_from_letter
  
  def set_opening_delimiter(self, opening_delimiter):
    self._opening_delimiter = opening_delimiter
  
  def set_extensible_delimiter(self, extensible_delimiter):
    self._extensible_delimiter = extensible_delimiter
  
  def set_attribute_specifications(self, attribute_specifications):
    self._attribute_specifications = attribute_specifications
  
  def set_content_replacements(self, content_replacements):
    self._content_replacements = content_replacements
  
  def set_closing_delimiter(self, closing_delimiter):
    self._closing_delimiter = closing_delimiter
  
  def validate(self):
    
    if self._syntax_type is None:
      raise MissingAttributeException('syntax_type')
    if self._extensible_delimiter is None:
      raise MissingAttributeException('extensible_delimiter')
    
    try:
      extensible_delimiter_character, extensible_delimiter_min_count = \
              factorise_repeated_character(self._extensible_delimiter)
    except NotCharacterRepeatedException:
      raise ExtensibleDelimiterException(self._extensible_delimiter)
    
    self._regex = \
            self.build_regex(
              extensible_delimiter_character,
              extensible_delimiter_min_count
            )
  
  def build_regex(
    self,
    extensible_delimiter_character,
    extensible_delimiter_min_count,
  ):
    
    type_is_block = self._syntax_type == 'BLOCK'
    has_attribute_specifications = self._attribute_specifications != 'NONE'
    
    block_anchoring_regex = to_block_anchoring_regex(type_is_block)
    flags_regex = to_flags_regex(self._allowed_flags)
    opening_delimiter_regex = re.escape(self._opening_delimiter)
    extensible_delimiter_opening_regex = \
            to_extensible_delimiter_opening_regex(
              extensible_delimiter_character,
              extensible_delimiter_min_count,
            )
    attribute_specifications_regex = \
            to_attribute_specifications_regex(
              has_attribute_specifications,
              type_is_block,
            )
    content_regex = to_content_regex()
    extensible_delimiter_closing_regex = \
            to_extensible_delimiter_closing_regex()
    closing_delimiter_regex = re.escape(self._closing_delimiter)
    
    return ''.join(
      [
        block_anchoring_regex,
        flags_regex,
        opening_delimiter_regex,
        extensible_delimiter_opening_regex,
        attribute_specifications_regex,
        content_regex,
        extensible_delimiter_closing_regex,
        closing_delimiter_regex,
      ]
    )


def factorise_repeated_character(string):
  
  first_character = string[0]
  string_length = len(string)
  
  if string != first_character * string_length:
    raise NotCharacterRepeatedException
  
  return first_character, string_length


def to_block_anchoring_regex(type_is_block):
  
  if type_is_block:
    return r'^[ \t]*'
  
  return ''


def to_flags_regex(allowed_flags):
  
  if len(allowed_flags) == 0:
    return ''
  
  flag_letters = \
          ''.join(
            re.escape(flag_letter)
              for flag_letter in allowed_flags.keys()
          )
  return f'(?P<flags> [{flag_letters}]* )'


def to_extensible_delimiter_opening_regex(
  extensible_delimiter_character,
  extensible_delimiter_min_count,
):
  
  character_regex = re.escape(extensible_delimiter_character)
  repetition_regex = f'{{{extensible_delimiter_min_count},}}'
  
  return f'(?P<extensible_delimiter> {character_regex}{repetition_regex} )'


def to_attribute_specifications_regex(
  has_attribute_specifications,
  type_is_block,
):
  
  if has_attribute_specifications:
    optional_braced_sequence_regex = \
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
  else:
    optional_braced_sequence_regex = ''
  
  if type_is_block:
    block_newline_regex = r'\n'
  else:
    block_newline_regex = ''
  
  return optional_braced_sequence_regex + block_newline_regex


def to_content_regex():
  return r'(?P<content> [\s\S]*? )'


def to_extensible_delimiter_closing_regex():
  return '(?P=extensible_delimiter)'


def none_to_empty_string(string):
  
  if string is not None:
    return string
  
  return ''


def get_group(group_name, match_object):
  """
  Retrieve as string a named capture group from a match object.
  
  Ensures the result is not None.
  """
  
  string = match_object.group(group_name)
  
  return none_to_empty_string(string)


def extract_rules_and_content(cmd):
  """
  Extract replacement rules and main content from CMD file content.
  
  «delimiter» shall be 3-or-more percent signs on its own line.
  If the CMD file content is free of «delimiter»,
  all of it shall be parsed as «main_content».
  If the CMD file content contains «delimiter»,
  it shall be parsed as
          «replacement_rules»
          «delimiter»
          «main_content»
  according to the first occurrence of «delimiter».
  """
  
  match_object = \
          re.fullmatch(
            r'''
              (?:
                (?P<replacement_rules> [\s\S]*? )
                (?P<delimiter> ^ [%]{3,} )
                \n
              ) ?
              (?P<main_content> [\s\S]* )
            ''',
            cmd,
            flags=re.MULTILINE | re.VERBOSE,
          )
  
  replacement_rules = get_group('replacement_rules', match_object)
  main_content = get_group('main_content', match_object)
  
  return (replacement_rules, main_content)


def cmd_to_html(cmd):
  """
  Convert CMD to HTML.
  """
  
  replacement_rules, main_content = extract_rules_and_content(cmd)
  
  html = main_content # TODO: implement conversion properly
  
  return html


def is_cmd_file(file_name):
  return file_name.endswith('.cmd')


def extract_cmd_name(cmd_file_name_argument):
  """
  Extract name-without-extension from a CMD file name argument.
  
  The argument received from the command line can be either
  `«cmd_name».cmd`, `«cmd_name».`, or `«cmd_name»`,
  or even `./«cmd_name».cmd` if the user is being dumb.
  If no argument be received from the command line,
  we loop through the file names, which are `./«cmd_name».cmd`.
  If the operating system be Windows,
  the directory separators will be backslashes
  instead of forward slashes (as in URLs).
  In all cases we want `«cmd_name»` with forward slashes.
  """
  
  cmd_file_name_argument = re.sub(r'\\', '/', cmd_file_name_argument)
  cmd_file_name_argument = re.sub(r'\A[.][/]', '', cmd_file_name_argument)
  cmd_name = re.sub(r'[.](cmd)?\Z', '', cmd_file_name_argument)
  
  return cmd_name


def generate_html_file(cmd_file_name_argument, uses_command_line_argument):
  
  cmd_name = extract_cmd_name(cmd_file_name_argument)
  cmd_file_name = f'{cmd_name}.cmd'
  try:
    with open(cmd_file_name, 'r', encoding='utf-8') as cmd_file:
      cmd = cmd_file.read()
  except FileNotFoundError as file_not_found_error:
    if uses_command_line_argument:
      error_message = \
              (
                'error: '
                f'argument `{cmd_file_name_argument}`: '
                f'file `{cmd_file_name}` not found'
              )
      print(error_message)
      sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)
    else:
      error_message = \
              (
                f'file `{cmd_file_name}` not found '
                f'for `{cmd_file_name}` in cmd_file_name_list'
              )
      raise FileNotFoundError(error_message) from file_not_found_error
  
  html = cmd_to_html(cmd)
  
  html_file_name = f'{cmd_name}.html'
  try:
    with open(html_file_name, 'w', encoding='utf-8') as html_file:
      html_file.write(html)
      print(f'success: wrote to `{html_file_name}`')
  except IOError:
    print(f'error: cannot write to `{html_file_name}`')
    sys.exit(GENERIC_ERROR_EXIT_CODE)


DESCRIPTION = '''
  Convert Conway-Markdown (CMD) to HTML.
'''
CMD_FILE_NAME_HELP = '''
  Name of CMD file to be converted.
  Abbreviate as `file` or `file.` for increased productivity.
  Omit to convert all CMD files under the working directory.
'''


def parse_command_line_arguments():
  
  argument_parser = argparse.ArgumentParser(description=DESCRIPTION)
  argument_parser.add_argument(
    'cmd_file_name_argument',
    default='',
    help=CMD_FILE_NAME_HELP,
    metavar='file.cmd',
    nargs='?',
  )
  
  return argument_parser.parse_args()


def main():
  
  parsed_arguments = parse_command_line_arguments()
  cmd_file_name_argument = parsed_arguments.cmd_file_name_argument
  
  if cmd_file_name_argument != '':
    generate_html_file(cmd_file_name_argument, uses_command_line_argument=True)
    return
  else:
    for path, _, file_names in os.walk('./'):
      for file_name in file_names:
        if is_cmd_file(file_name):
          cmd_file_name = os.path.join(path, file_name)
          generate_html_file(cmd_file_name, uses_command_line_argument=False)


if __name__ == '__main__':
  main()
