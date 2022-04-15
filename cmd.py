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
import textwrap
import traceback


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
  - syntax_type: BLOCK | INLINE (mandatory)
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
  
  ATTRIBUTE_NAMES = [
    'replacement_order',
    'syntax_type',
    # TODO: other attributes
  ]
  
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
  """
  Object governing the parsing and application of replacement rules.
  
  ## `legislate` ##
  
  Parse CMD replacement rule syntax. A line must be either:
  (1) whitespace-only,
  (2) a comment (beginning with `#`),
  (3) a rules inclusion (of the form `< /«rules_file_name»`),
  (4) the start of a class declaration (of the form `«ClassName»: #«id»`),
  (5) the start of an attribute declaration (beginning with `- `),
  (6) the start of a substitution declaration (beginning with `* `), or
  (7) a continuation (beginning with whitespace).
  «rules_file_name» is parsed relative to the working directory.
  An attribute declaration is of the form `- «name»: «value»`.
  A substitution declaration is of the form `* «pattern» --> «substitute»`,
  where the number of hyphens in the delimiter `-->`
  may be arbitrarily increased if «pattern» happens to contain
  a run of hyphens followed by a closing angle-bracket.
  
  Terminology:
  - Class declarations are _committed_.
  - Attribute and substitution declarations are _staged_.
  
  ## `execute` ##
  
  Applies the legislated replacements.
  """
  
  SYNTAX_HELP = textwrap.dedent(
    '''\
    In CMD replacement rule syntax, a line must be either:
    (1) whitespace-only,
    (2) a comment (beginning with `#`),
    (3) a rules inclusion (of the form `< /«rules_file_name»`),
    (4) the start of a class declaration (of the form `«ClassName»: #«id»`),
    (5) the start of an attribute declaration (beginning with `- `),
    (6) the start of a substitution declaration (beginning with `* `), or
    (7) a continuation (beginning with whitespace).
    '''
  )
  
  def __init__(self, cmd_file_name):
    
    self._included_file_names = []
    if cmd_file_name is not None:
      self._included_file_names.append(cmd_file_name)
    
    self._replacement_from_id = {}
    self._root_replacement_id = None
    self._replacement_queue = []
  
  @staticmethod
  def print_error(
    message,
    source_file,
    start_line_number,
    end_line_number=None,
  ):
    
    if end_line_number is None or start_line_number == end_line_number:
      line_number_range = f'line {start_line_number}'
    else:
      line_number_range = f'lines {start_line_number} to {end_line_number}'
    
    print(
      'error: '
      f'{source_file}, {line_number_range}: '
      f'{message}'
    )
  
  @staticmethod
  def print_traceback(exception):
    traceback.print_exception(
      type(exception),
      exception,
      exception.__traceback__,
    )
  
  @staticmethod
  def is_whitespace_only(line):
    return re.fullmatch(r'[\s]*', line, flags=re.ASCII)
  
  @staticmethod
  def is_comment(line):
    return line.startswith('#')
  
  @staticmethod
  def compute_rules_inclusion_match(line):
    return re.fullmatch(
      r'''
        [<][ ][/] (?P<rules_file_name> [\S][\s\S]* )
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  def process_rules_inclusion_line(
    self,
    rules_inclusion_match,
    source_file,
    line_number,
  ):
    
    rules_file_name = get_group('rules_file_name', rules_inclusion_match)
    try:
      with open(rules_file_name, 'r', encoding='utf-8') as rules_file:
        for file_name in self._included_file_names:
          if os.path.samefile(rules_file_name, file_name):
            self._included_file_names.append(rules_file_name)
            recursive_inclusion_string = \
                    ' includes '.join(
                      f'`{file_name}`'
                        for file_name in self._included_file_names
                    )
            ReplacementMaster.print_error(
              f'recursive inclusion: {recursive_inclusion_string}',
              source_file,
              line_number,
            )
            sys.exit(GENERIC_ERROR_EXIT_CODE)
        self._included_file_names.append(rules_file_name)
        replacement_rules = rules_file.read()
    except FileNotFoundError:
      ReplacementMaster.print_error(
        f'file `{rules_file_name}` not found',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    self.legislate(replacement_rules, f'`{rules_file_name}`')
  
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
  
  def process_class_declaration_line(
    self,
    class_declaration_match,
    source_file,
    line_number,
  ):
    
    class_name = get_group('class_name', class_declaration_match)
    id_ = get_group('id_', class_declaration_match)
    
    if class_name == 'ExtensibleFenceReplacement':
      replacement = ExtensibleFenceReplacement(id_)
    else:
      ReplacementMaster.print_error(
        f'unrecognised replacement class `{class_name}`',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if id_ in self._replacement_from_id:
      ReplacementMaster.print_error(
        f'replacement already declared with id `{id_}`',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    line_number_range_start = line_number
    
    return class_name, replacement, line_number_range_start
  
  @staticmethod
  def compute_attribute_declaration_match(line):
    return re.fullmatch(
      r'''
        [-][ ] (?P<attribute_name> [a-z_]+ ) [:]
        (?P<partial_attribute_value> [\s\S]* )
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def process_attribute_declaration_line(
    attribute_declaration_match,
    class_name,
    replacement,
    attribute_value,
    source_file,
    line_number,
  ):
    
    attribute_name = get_group('attribute_name', attribute_declaration_match)
    if attribute_name not in replacement.ATTRIBUTE_NAMES:
      ReplacementMaster.print_error(
        f'unrecognised attribute `{attribute_name}` for `{class_name}`',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    partial_attribute_value = \
            get_group('partial_attribute_value', attribute_declaration_match)
    attribute_value = \
            none_to_empty_string(attribute_value) + partial_attribute_value
    
    line_number_range_start = line_number
    
    return attribute_name, attribute_value, line_number_range_start
  
  @staticmethod
  def compute_substitution_declaration_match(line):
    return re.fullmatch(
      r'''
        [*][ ] (?P<partial_substitution> [\s\S]* )
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def process_substitution_declaration_line(
    substitution_declaration_match,
    substitution,
    line_number,
  ):
    
    partial_substitution = \
            get_group('partial_substitution', substitution_declaration_match)
    substitution = none_to_empty_string(substitution) + partial_substitution
    
    line_number_range_start = line_number
    
    return substitution, line_number_range_start
  
  @staticmethod
  def compute_continuation_match(line):
    return re.fullmatch(
      r'''
        (?P<continuation> [\s]+ [\S][\s\S]* )
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def process_continuation_line(
    continuation_match,
    attribute_name,
    attribute_value,
    substitution,
    source_file,
    line_number,
  ):
    
    continuation = get_group('continuation', continuation_match)
    
    if attribute_name is not None:
      attribute_value = none_to_empty_string(attribute_value) + continuation
    elif substitution is not None:
      substitution = substitution + continuation
    else:
      ReplacementMaster.print_error(
        'continuation only allowed for attribute or substitution declarations',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    return attribute_value, substitution
  
  @staticmethod
  def compute_replacement_order_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none> NONE )
            |
          (?P<root> ROOT )
            |
          (?P<replacement_order_type> BEFORE | AFTER )
          [ ]
          [#] (?P<replacement_order_id> [a-z-]+ )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_replacement_order(
    replacement,
    attribute_value,
    source_file,
    line_number_range_start,
    line_number,
  ):
    
    replacement_order_match = \
            ReplacementMaster.compute_replacement_order_match(attribute_value)
    if replacement_order_match is None:
      ReplacementMaster.print_error(
        f'invalid value `{attribute_value}` for attribute `replacement_order`',
        source_file,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if get_group('none', replacement_order_match) != '':
      return
    
    if get_group('root', replacement_order_match) != '':
      replacement.set_replacement_order('ROOT', None)
      return
    
    replacement_order_type = \
      get_group('replacement_order_type', replacement_order_match)
    replacement_order_id = \
      get_group('replacement_order_id', replacement_order_match)
    replacement.set_replacement_order(
      replacement_order_type,
      replacement_order_id,
    )
  
  @staticmethod
  def compute_syntax_type_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?P<syntax_type> BLOCK | INLINE )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_syntax_type(
    replacement,
    attribute_value,
    source_file,
    line_number_range_start,
    line_number,
  ):
    
    syntax_type_match = \
            ReplacementMaster.compute_syntax_type_match(attribute_value)
    if syntax_type_match is None:
      ReplacementMaster.print_error(
        f'invalid value `{attribute_value}` for attribute `syntax_type`',
        source_file,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    syntax_type = get_group('syntax_type', syntax_type_match)
    replacement.set_syntax_type(syntax_type == 'BLOCK')
  
  @staticmethod
  def compute_substitution_match(substitution):
    
    substitution_delimiters = re.findall('[-]{2,}[>]', substitution)
    longest_substitution_delimiter = max(substitution_delimiters, key=len)
    
    return re.fullmatch(
      fr'''
        [\s]*
          (?P<pattern> [\S][\s\S]* )
        [\s]*
          {re.escape(longest_substitution_delimiter)}
        [\s]*
          (?P<substitute> [\S][\s\S]* )
        [\s]*
      ''',
      substitution,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_ordinary_substitution(
    replacement,
    substitution,
    source_file,
    line_number_range_start,
    line_number,
  ):
    
    substitution_match = \
            ReplacementMaster.compute_substitution_match(substitution)
    if substitution_match is None:
      ReplacementMaster.print_error(
        f'missing delimiter in substitution `{substitution}`',
        source_file,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    pattern = get_group('pattern', substitution_match)
    substitute = get_group('substitute', substitution_match)
    
    replacement.add_substitution(pattern, substitute)
  
  @staticmethod
  def stage_regex_substitution(
    replacement,
    substitution,
    source_file,
    line_number_range_start,
    line_number,
  ):
    
    substitution_match = \
            ReplacementMaster.compute_substitution_match(substitution)
    if substitution_match is None:
      ReplacementMaster.print_error(
        f'missing delimiter in substitution `{substitution}`',
        source_file,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    pattern = get_group('pattern', substitution_match)
    substitute = get_group('substitute', substitution_match)
    
    try:
      re.sub(pattern, '', '', flags=re.ASCII | re.MULTILINE | re.VERBOSE)
    except re.error as pattern_exception:
      ReplacementMaster.print_error(
        f'bad regex pattern `{pattern}`',
        source_file,
        line_number_range_start,
        line_number,
      )
      ReplacementMaster.print_traceback(pattern_exception)
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    try:
      re.sub(
        pattern,
        substitute,
        '',
        flags=re.ASCII | re.MULTILINE | re.VERBOSE,
      )
    except re.error as substitute_exception:
      ReplacementMaster.print_error(
        f'bad regex substitute `{substitute}` for pattern `{pattern}`',
        source_file,
        line_number_range_start,
        line_number,
      )
      ReplacementMaster.print_traceback(substitute_exception)
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    replacement.add_substitution(pattern, substitute)
  
  @staticmethod
  def stage(
    class_name,
    replacement,
    attribute_name,
    attribute_value,
    substitution,
    source_file,
    line_number_range_start,
    line_number,
  ):
    
    if substitution is not None: # staging a substitution
      
      if class_name == 'OrdinaryDictionaryReplacement':
        ReplacementMaster.stage_ordinary_substitution(
          replacement,
          substitution,
          source_file,
          line_number_range_start,
          line_number,
        )
      elif class_name == 'RegexDictionaryReplacement':
        ReplacementMaster.stage_regex_substitution(
          replacement,
          substitution,
          source_file,
          line_number_range_start,
          line_number,
        )
      else:
        ReplacementMaster.print_error(
          f'class {class_name} does not allow substitutions',
          source_file,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
    else: # staging an attribute declaration
      
      if attribute_name == 'replacement_order':
        ReplacementMaster.stage_replacement_order(
          replacement,
          attribute_value,
          source_file,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'syntax_type':
        ReplacementMaster.stage_syntax_type(
          replacement,
          attribute_value,
          source_file,
          line_number_range_start,
          line_number,
        )
      
      # TODO: implement other attribute name cases
      # (I think we don't need to check the class_name is right ---
      # that should have already happened before we get to the staging stage)
    
    return None, None, None, None
    # attribute_name, attribute_value, substitution, line_number_range_start
  
  def commit(self, class_name, replacement, source_file, line_number):
    
    try:
      replacement.validate()
    except MissingAttributeException as exception:
      missing_attribute = exception.get_missing_attribute()
      ReplacementMaster.print_error(
        f'missing attribute `{missing_attribute}` for {class_name}',
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    id_ = replacement.get_id()
    self._replacement_from_id[id_] = replacement
    
    replacement_order_type = replacement.get_replacement_order_type()
    if replacement_order_type is None:
      pass
    elif replacement_order_type == 'ROOT':
      if self._root_replacement_id is not None:
        ReplacementMaster.print_error(
          f'root replacement already declared (#{self._root_replacement_id})',
          source_file,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      self._root_replacement_id = id_
      self._replacement_queue.append(replacement)
    else:
      reference_id = replacement.get_replacement_order_reference_id()
      reference_replacement = self._replacement_from_id[reference_id]
      reference_index = self._replacement_queue.index(reference_replacement)
      if replacement_order_type == 'BEFORE':
        insertion_index = reference_index
      elif replacement_order_type == 'AFTER':
        insertion_index = reference_index + 1
      else:
        insertion_index = None
      self._replacement_queue.insert(insertion_index, replacement)
    
    return None, None, None, None, None, None
    # class_name, replacement, attribute_name, attribute_value, substitution,
    # line_number_range_start
  
  def legislate(self, replacement_rules, source_file):
    
    class_name = None
    replacement = None
    attribute_name = None
    attribute_value = None
    substitution = None
    line_number_range_start = None
    line_number = 0
    
    for line_number, line \
    in enumerate(replacement_rules.splitlines(), start=1):
      
      if ReplacementMaster.is_whitespace_only(line) \
      or ReplacementMaster.is_comment(line):
        if attribute_name is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  ReplacementMaster.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    source_file,
                    line_number_range_start,
                    line_number,
                  )
        if replacement is not None:
          class_name, replacement, \
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.commit(
                    class_name,
                    replacement,
                    source_file,
                    line_number,
                  )
        continue
      
      rules_inclusion_match = \
              ReplacementMaster.compute_rules_inclusion_match(line)
      if rules_inclusion_match is not None:
        if attribute_name is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  ReplacementMaster.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    source_file,
                    line_number_range_start,
                    line_number,
                  )
        if replacement is not None:
          class_name, replacement, \
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.commit(
                    class_name,
                    replacement,
                    source_file,
                    line_number,
                  )
        self.process_rules_inclusion_line(
          rules_inclusion_match,
          source_file,
          line_number,
        )
        continue
      
      class_declaration_match = \
              ReplacementMaster.compute_class_declaration_match(line)
      if class_declaration_match is not None:
        if attribute_name is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  ReplacementMaster.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    source_file,
                    line_number_range_start,
                    line_number,
                  )
        if replacement is not None:
          class_name, replacement, \
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.commit(
                    class_name,
                    replacement,
                    source_file,
                    line_number,
                  )
        class_name, replacement, line_number_range_start = \
                self.process_class_declaration_line(
                  class_declaration_match,
                  source_file,
                  line_number,
                )
        continue
      
      attribute_declaration_match = \
              ReplacementMaster.compute_attribute_declaration_match(line)
      if attribute_declaration_match is not None:
        if attribute_name is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  ReplacementMaster.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    source_file,
                    line_number_range_start,
                    line_number,
                  )
        attribute_name, attribute_value, line_number_range_start = \
                ReplacementMaster.process_attribute_declaration_line(
                  attribute_declaration_match,
                  class_name,
                  replacement,
                  attribute_value,
                  source_file,
                  line_number,
                )
        continue
      
      substitution_declaration_match = \
              ReplacementMaster.compute_substitution_declaration_match(line)
      if substitution_declaration_match is not None:
        if attribute_name is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  ReplacementMaster.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    source_file,
                    line_number_range_start,
                    line_number,
                  )
        substitution, line_number_range_start = \
                ReplacementMaster.process_substitution_declaration_line(
                  substitution_declaration_match,
                  substitution,
                  line_number,
                )
        continue
      
      continuation_match = ReplacementMaster.compute_continuation_match(line)
      if continuation_match is not None:
        attribute_value, substitution = \
                ReplacementMaster.process_continuation_line(
                  continuation_match,
                  attribute_name,
                  attribute_value,
                  substitution,
                  source_file,
                  line_number,
                )
        continue
      
      ReplacementMaster.print_error(
        'invalid syntax\n\n' + ReplacementMaster.SYNTAX_HELP,
        source_file,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    # At end of file
    if attribute_name is not None:
      ReplacementMaster.stage(
        class_name,
        replacement,
        attribute_name,
        attribute_value,
        substitution,
        source_file,
        line_number_range_start,
        line_number,
      )
    if replacement is not None:
      self.commit(class_name, replacement, source_file, line_number + 1)
  
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


def compute_attribute_specification_matches(attribute_specifications):
  return re.finditer(
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
    ''',
    attribute_specifications,
    flags=re.ASCII | re.VERBOSE,
  )


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


def extract_attribute_name_and_value(attribute_specification_match):
  
  name = get_group('name', attribute_specification_match)
  if name != '':
    
    try:
      name = ATTRIBUTE_NAME_FROM_ABBREVIATION[name]
    except KeyError:
      pass
    
    quoted_value = get_group('quoted_value', attribute_specification_match)
    bare_value = get_group('bare_value', attribute_specification_match)
    value = quoted_value + bare_value # at most one will be non-empty
    
    return name, value
  
  id_ = get_group('id_', attribute_specification_match)
  if id_ != '':
    return 'id', id_
  
  class_ = get_group('class_', attribute_specification_match)
  if class_ != '':
    return 'class', class_
  
  rowspan = get_group('rowspan', attribute_specification_match)
  if rowspan != '':
    return 'rowspan', rowspan
  
  colspan = get_group('colspan', attribute_specification_match)
  if colspan != '':
    return 'colspan', colspan
  
  width = get_group('width', attribute_specification_match)
  if width != '':
    return 'width', width
  
  height = get_group('height', attribute_specification_match)
  if height != '':
    return 'height', height
  
  boolean_attribute = \
          get_group('boolean_attribute', attribute_specification_match)
  if boolean_attribute != '':
    return boolean_attribute, None
  
  return None, None


def build_attributes_sequence(attribute_specifications):
  """
  Convert CMD attribute specifications to an attribute sequence.
  
  CMD attribute specifications are of the following forms:
  ````
  name="«quoted_value»"
  name=«bare_value»
  #«id»
  .«class»
  r«rowspan»
  c«colspan»
  w«width»
  h«height»
  «boolean_attribute»
  ````
  In the two forms with an explicit equals sign,
  the following abbreviations are allowed for `name`:
  - # for id
  - . for class
  - l for lang
  - r for rowspan
  - c for colspan
  - w for width
  - h for height
  - s for style
  
  If an attribute of the same name is specified multiple times,
  the latest specification shall prevail,
  except when `class` is specified multiple times,
  in which case the values will be appended.
  For example, `id=x #y .a .b name=value .=c class="d"`
  shall be converted to the attrbute sequence
  ` id="y" class="a b c d" name="value"`.
  """
  
  attribute_value_from_name = {}
  
  for attribute_specification_match \
  in compute_attribute_specification_matches(attribute_specifications):
    
    name, value = \
            extract_attribute_name_and_value(attribute_specification_match)
    
    if name is None:
      continue
    
    if name == 'class':
      try:
        attribute_value_from_name['class'] += f' {value}'
      except KeyError:
        attribute_value_from_name['class'] = value
    else:
      attribute_value_from_name[name] = value
  
  attribute_sequence = ''
  
  for name, value in attribute_value_from_name.items():
    if value is None:
      attribute_sequence += f' {name}'
    else:
      attribute_sequence += f' {name}="{value}"'
  
  return attribute_sequence


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
  
  return replacement_rules, main_content


STANDARD_RULES = \
r'''# STANDARD_RULES

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
  
  replacement_master = ReplacementMaster(cmd_file_name)
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
