#!/usr/bin/env python3

"""
# cmd.py

Convert Conway-Markdown (CMD) to HTML.
Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

## Structure

CMD files are parsed as
````
«replacement_rules»
«delimiter»
«main_content»
````
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


class RootReplacementAlreadyExistsException(Exception):
  pass


class ExtensibleFenceReplacement:
  """
  A generalised extensible-fence-style replacement rule.
  
  Inspired by the repeatable backticks of John Gruber's Markdown.
  CMD replacement rule syntax:
  ````
  ExtensibleFenceReplacement: #«id»
  - replacement_order: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
  - syntax_type: DISPLAY | INLINE (mandatory)
  - allowed_flags:
      (def) NONE
        |
      «letter»=KEEP_HTML_UNESCAPED | REDUCE_WHITESPACE | KEEP_INDENTED [...]
  - opening_delimiter: (def) NONE | «string»
  - extensible_delimiter: «character_repeated» (mandatory)
  - attribute_specifications: (def) NONE | EMPTY | «string»
  - content_replacements: (def) NONE | #«id» [...]
  - closing_delimiter: (def) NONE | «string»
  - tag_name: (def) NONE | «name»
  ````
  """
  
  def __init__(self, id_):
    
    self._id = id_
    self._replacement_order_type = None
    self._replacement_order_reference_id = None
    self._syntax_type_is_block = None
    self._flag_setting_from_letter = {}
    self._has_flags = False
    self._opening_delimiter = ''
    self._extensible_delimiter_character = None
    self._extensible_delimiter_min_count = None
    self._attribute_specifications = None
    self._content_replacement_id_list = []
    self._closing_delimiter = ''
    self._tag_name = None
    self._regex_pattern = None
    self._substitute_function = None
  
  def get_id(self):
    return self._id
  
  def set_replacement_order(
    self,
    replacement_order_type,
    replacement_order_reference_id,
  ):
    self._replacement_order_type = replacement_order_type
    self._replacement_order_reference_id = replacement_order_reference_id
  
  def get_replacement_order_type(self):
    return self._replacement_order_type
  
  def get_replacement_order_reference_id(self):
    return self._replacement_order_reference_id
  
  def set_syntax_type(self, syntax_type_is_block):
    self._syntax_type_is_block = syntax_type_is_block
  
  def set_allowed_flags(self, flag_setting_from_letter, has_flags):
    self._flag_setting_from_letter = flag_setting_from_letter
    self._has_flags = has_flags
  
  def set_opening_delimiter(self, opening_delimiter):
    self._opening_delimiter = opening_delimiter
  
  def set_extensible_delimiter(
    self,
    extensible_delimiter_character,
    extensible_delimiter_min_count,
  ):
    self._extensible_delimiter_character = extensible_delimiter_character
    self._extensible_delimiter_min_count = extensible_delimiter_min_count
  
  def set_attribute_specifications(self, attribute_specifications):
    self._attribute_specifications = attribute_specifications
  
  def set_content_replacements(self, content_replacement_id_list):
    self._content_replacement_id_list = content_replacement_id_list
  
  def set_closing_delimiter(self, closing_delimiter):
    self._closing_delimiter = closing_delimiter
  
  def set_tag_name(self, tag_name):
    self._tag_name = tag_name
  
  def validate(self):
    
    if self._syntax_type_is_block is None:
      raise MissingAttributeException('syntax_type')
    
    if self._extensible_delimiter_character is None:
      raise MissingAttributeException('extensible_delimiter')
    
    self._regex_pattern = \
            ExtensibleFenceReplacement.build_regex_pattern(
              self._syntax_type_is_block,
              self._flag_setting_from_letter,
              self._has_flags,
              self._opening_delimiter,
              self._extensible_delimiter_character,
              self._extensible_delimiter_min_count,
              self._attribute_specifications,
              self._closing_delimiter,
            )
    self._substitute_function = \
            ExtensibleFenceReplacement.build_substitute_function(
              self._flag_setting_from_letter,
              self._has_flags,
              self._attribute_specifications,
              self._tag_name,
            )
  
  def apply(self, string):
    return re.sub(
      self._regex_pattern,
      self._substitute_function,
      string,
      flags=re.ASCII | re.MULTILINE | re.VERBOSE,
    )
  
  @staticmethod
  def build_regex_pattern(
    syntax_is_block,
    flag_setting_from_letter,
    has_flags,
    opening_delimiter,
    extensible_delimiter_character,
    extensible_delimiter_min_count,
    attribute_specifications,
    closing_delimiter,
  ):
    
    block_anchoring_regex = \
            build_block_anchoring_regex(syntax_is_block)
    flags_regex = build_flags_regex(flag_setting_from_letter, has_flags)
    opening_delimiter_regex = re.escape(opening_delimiter)
    extensible_delimiter_opening_regex = \
            build_extensible_delimiter_opening_regex(
              extensible_delimiter_character,
              extensible_delimiter_min_count,
            )
    attribute_specifications_regex = \
            build_attribute_specifications_regex(
              attribute_specifications,
              syntax_is_block,
            )
    content_regex = build_content_regex()
    extensible_delimiter_closing_regex = \
            build_extensible_delimiter_closing_regex()
    closing_delimiter_regex = re.escape(closing_delimiter)
    
    return ''.join(
      [
        block_anchoring_regex,
        flags_regex,
        opening_delimiter_regex,
        extensible_delimiter_opening_regex,
        attribute_specifications_regex,
        content_regex,
        block_anchoring_regex,
        extensible_delimiter_closing_regex,
        closing_delimiter_regex,
      ]
    )
  
  @staticmethod
  def build_substitute_function(
    flag_setting_from_letter,
    has_flags,
    attribute_specifications,
    tag_name,
  ):
    
    def substitute_function(match):
      
      enabled_flag_settings = set()
      if has_flags:
        flags = get_group('flags', match)
        for flag_letter, flag_setting in flag_setting_from_letter.items():
          if flag_letter in flags:
            enabled_flag_settings.add(flag_setting)
      
      if attribute_specifications is not None:
        matched_attribute_specifications = \
                get_group('attribute_specifications', match)
        combined_attribute_specifications = \
                ' '.join(
                  [attribute_specifications, matched_attribute_specifications]
                )
        attributes_sequence = \
                build_attributes_sequence(combined_attribute_specifications)
      else:
        attributes_sequence = ''
      
      content = get_group('content', match)
      # TODO: content replacements
      
      if tag_name is None:
        return content
      else:
        return f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'
    
    return substitute_function


class ReplacementMaster:
  
  def __init__(self):
    self._replacement_from_id = {}
    self._replacement_queue = []
  
  @staticmethod
  def is_whitespace_only(line):
    return re.fullmatch(r'[\s]*', line, flags=re.ASCII)
  
  @staticmethod
  def is_comment(line):
    return line.startswith('#')
  
  @staticmethod
  def compute_class_declaration_match(line):
    return re.fullmatch(
      r'''
        (?P<class_name> [A-Za-z]+ ) [:]
        [\s]+
        [#] (?P<id_> [a-z-]+ )
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  def commit(self, replacement, source_file, line_number, class_name):
    
    try:
      replacement.validate()
    except MissingAttributeException as exception:
      missing_attribute = exception.get_missing_attribute()
      print(
        'error: '
        f'{source_file} line {line_number}: '
        f'missing attribute `{missing_attribute}` for {class_name}'
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    id_ = replacement.get_id()
    self._replacement_from_id[id_] = replacement
    
    replacement_order_type = replacement.get_replacement_order_type()
    if replacement_order_type is None:
      return
    
    # TODO: insert replacement at appropriate spot in queue
  
  def legislate(self, replacement_rules, source_file):
    
    class_name = None
    replacement = None
    
    for line_number, line \
    in enumerate(replacement_rules.splitlines(), start=1):
      
      if ReplacementMaster.is_whitespace_only(line):
        continue
      
      if ReplacementMaster.is_comment(line):
        continue
      
      class_declaration_match = \
              ReplacementMaster.compute_class_declaration_match(line)
      if class_declaration_match is not None:
        
        if replacement is not None:
          self.commit(replacement, source_file, line_number, class_name)
        
        class_name = get_group('class_name', class_declaration_match)
        id_ = get_group('id_', class_declaration_match)
        
        if class_name == 'ExtensibleFenceReplacement':
          replacement = ExtensibleFenceReplacement(id_)
        else:
          print(
            'error: '
            f'{source_file} line {line_number}: '
            f'unrecognised replacement class `{class_name}`'
          )
          sys.exit(GENERIC_ERROR_EXIT_CODE)
        
        if id_ in self._replacement_from_id:
          print(
            'error: '
            f'{source_file} line {line_number}: '
            f'replacement already declared with id `{id_}'
          )
          sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      # TODO: other cases
    
    return
  
  def execute(self, string):
    
    for replacement in self._replacement_queue:
      string = replacement.apply(string)
    
    return string


def factorise_repeated_character(string):
  
  first_character = string[0]
  string_length = len(string)
  
  if string != first_character * string_length:
    raise NotCharacterRepeatedException
  
  return first_character, string_length


ATTRIBUTE_NAME_FROM_ABBREVIATION = \
        {
          '#': 'id',
          '.': 'class',
          'l': 'lang',
          'r': 'rowspan',
          'c': 'colspan',
          'w': 'width',
          'h': 'height',
          's': 'style',
        }
BUILD_ATTRIBUTES_SEQUENCE_REGEX_PATTERN = \
        r'''
          [\s]*
          (?:
            (?P<name> [^\s=]+ ) =
                    (?:
                      "(?P<quoted_value> [\s\S]*? )"
                        |
                      (?P<bare_value> [\S]* )
                    )
              |
            [#] (?P<id_> [^\s"]+ )
              |
            [.] (?P<class_> [^\s"]+ )
              |
            [r] (?P<rowspan> [0-9]+ )
              |
            [c] (?P<colspan> [0-9]+ )
              |
            [w] (?P<width> [0-9]+ )
              |
            [h] (?P<height> [0-9]+ )
              |
            (?P<boolean_attribute> [\S]+ )
          ) ?
          [\s]*
        '''


def build_attributes_sequence_substitute_function(match):
  
  name = get_group('name', match)
  if name != '':
    
    try:
      name = ATTRIBUTE_NAME_FROM_ABBREVIATION[name]
    except KeyError:
      pass
    
    quoted_value = get_group('quoted_value', match)
    bare_value = get_group('bare_value', match)
    value = quoted_value + bare_value # at most one will be non-empty
    
    return f' {name}="{value}"'
  
  id_ = get_group('id_', match)
  if id_ != '':
    return f' id="{id_}"'
  
  class_ = get_group('class_', match)
  if class_ != '':
    return f' class="{class_}"'
  
  rowspan = get_group('rowspan', match)
  if rowspan != '':
    return f' rowspan={rowspan}'
  
  colspan = get_group('colspan', match)
  if colspan != '':
    return f' colspan={colspan}'
  
  width = get_group('width', match)
  if width != '':
    return f' width={width}'
  
  height = get_group('height', match)
  if height != '':
    return f' height={height}'
  
  boolean_attribute = get_group('boolean_attribute', match)
  if boolean_attribute != '':
    return f' {boolean_attribute}'
  
  return ''


def build_attributes_sequence(attribute_specifications):
  
  return re.sub(
    BUILD_ATTRIBUTES_SEQUENCE_REGEX_PATTERN,
    build_attributes_sequence_substitute_function,
    attribute_specifications,
    flags=re.ASCII | re.MULTILINE | re.VERBOSE,
  )


def build_block_anchoring_regex(syntax_type_is_block):
  
  if syntax_type_is_block:
    return r'^[^\S\n]*'
  
  return ''


def build_flags_regex(allowed_flags, has_flags):
  
  if not has_flags:
    return ''
  
  flag_letters = \
          ''.join(
            re.escape(flag_letter)
              for flag_letter in allowed_flags.keys()
          )
  return f'(?P<flags> [{flag_letters}]* )'


def build_extensible_delimiter_opening_regex(
  extensible_delimiter_character,
  extensible_delimiter_min_count,
):
  
  character_regex = re.escape(extensible_delimiter_character)
  repetition_regex = f'{{{extensible_delimiter_min_count},}}'
  
  return f'(?P<extensible_delimiter> {character_regex}{repetition_regex} )'


def build_attribute_specifications_regex(
  attribute_specifications,
  syntax_type_is_block,
):
  
  if attribute_specifications is not None:
    optional_braced_sequence_regex = \
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
  else:
    optional_braced_sequence_regex = ''
  
  if syntax_type_is_block:
    block_newline_regex = r'\n'
  else:
    block_newline_regex = ''
  
  return optional_braced_sequence_regex + block_newline_regex


def build_content_regex():
  return r'(?P<content> [\s\S]*? )'


def build_extensible_delimiter_closing_regex():
  return '(?P=extensible_delimiter)'


def none_to_empty_string(string):
  
  if string is not None:
    return string
  
  return ''


def get_group(group_name, match):
  """
  Retrieve as string a named capture group from a match object.
  
  Ensures the result is not None.
  """
  
  string = match.group(group_name)
  
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
  
  match = \
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
  
  replacement_rules = get_group('replacement_rules', match)
  main_content = get_group('main_content', match)
  
  return (replacement_rules, main_content)


STANDARD_RULES = \
r'''# STANDARD_RULES

OrdinaryReplacement: #escape-html
- & --> &amp;
- < --> &lt;
- > --> &gt;

RegexReplacement: #trim-whitespace
- \A[\s]+ | [\s]+\Z  -->

RegexReplacement: #reduce-whitespace
- [\n]+  -->  \n
- [\s]+(?=<br>)  -->

DeIndentReplacement: #de-indent

PlaceholderReplacement: #placeholder-protect

ExtensibleFenceReplacement: #literals
- replacement_order: ROOT
- syntax_type: INLINE
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
    w=REDUCE_WHITESPACE
    i=KEEP_INDENTED
- opening_delimiter: <
- extensible_delimiter: `
- content_replacements:
    #escape-html
    #trim-whitespace
    #reduce-whitespace
    #de-indent
    #placeholder-protect
- closing_delimiter: >
'''


def cmd_to_html(cmd, cmd_file_name=None):
  """
  Convert CMD to HTML.
  """
  
  replacement_rules, main_content = extract_rules_and_content(cmd)
  
  replacement_master = ReplacementMaster()
  replacement_master.legislate(STANDARD_RULES, 'STANDARD_RULES')
  replacement_master.legislate(replacement_rules, f'`{cmd_file_name}`')
  html = replacement_master.execute(main_content)
  
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
      print(
        'error: '
        f'argument `{cmd_file_name_argument}`: '
        f'file `{cmd_file_name}` not found'
      )
      sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)
    else:
      error_message = \
              (
                f'file `{cmd_file_name}` not found '
                f'for `{cmd_file_name}` in cmd_file_name_list'
              )
      raise FileNotFoundError(error_message) from file_not_found_error
  
  html = cmd_to_html(cmd, cmd_file_name)
  
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
