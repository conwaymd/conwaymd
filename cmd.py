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


import abc
import argparse
import os
import re
import sys
import traceback
import warnings


__version__ = 'v3.999...'


GENERIC_ERROR_EXIT_CODE = 1
COMMAND_LINE_ERROR_EXIT_CODE = 2


class CommittedMutateException(Exception):
  pass


class UncommittedApplyException(Exception):
  pass


class MissingAttributeException(Exception):
  
  def __init__(self, missing_attribute):
    self._missing_attribute = missing_attribute
  
  def get_missing_attribute(self):
    return self._missing_attribute


class PlaceholderMaster:
  """
  Object providing placeholder protection to strings.
  
  There are many instances in which the result of a replacement
  should not be altered further by replacements to follow.
  To protect a string from further alteration,
  it is temporarily replaced by a placeholder
  consisting of code points in the main Unicode Private Use Area.
  Specifically, the placeholder shall be of the form
  `«marker»«encoded_counter»«marker»`, where «marker» is `U+F8FF`,
  and «encoded_counter» is base-6399 `U+E000` through `U+F8FE`,
  incrementing every time a new string is protected.
  
  The very first call to PlaceholderMaster should be to
  protect occurrences of «marker» in the text with a placeholder,
  lest those occurrences of «marker» be confounding.
  The very last call to PlaceholderMaster should be to unprotect
  the text (restoring the strings were protected with a placeholder).
  
  It is assumed the user will not define replacements rules
  that alter strings of the form `«marker»«encoded_counter»«marker»`,
  or generate strings of the form `«marker»«encoded_counter»«marker»`.
  In fact the user should not be using Private Use Area code points
  in the first place, see <https://www.w3.org/TR/charmod/#C073>.
  """
  
  _COUNTER_CODE_POINT_MIN = 0xE000
  _COUNTER_CODE_POINT_MAX = 0xF8FE
  _COUNTER_BASE = _COUNTER_CODE_POINT_MAX - _COUNTER_CODE_POINT_MIN + 1
  _MARKER_CODE_POINT = 0xF8FF
  
  _COUNTER_ENCODED_DIGIT_MIN = chr(_COUNTER_CODE_POINT_MIN)
  _COUNTER_ENCODED_DIGIT_MAX = chr(_COUNTER_CODE_POINT_MAX)
  _MARKER = chr(_MARKER_CODE_POINT)
  
  _PLACEHOLDER_PATTERN = \
          re.compile(
            f'''
              {_MARKER}
              (?P<encoded_counter>
                [{_COUNTER_ENCODED_DIGIT_MIN}-{_COUNTER_ENCODED_DIGIT_MAX}]+
              )
              {_MARKER}
            ''',
            flags=re.VERBOSE
          )
  
  def _unprotect_substitute_function(self, placeholder_match):
    
    placeholder = placeholder_match.group()
    try:
      return self._string_from_placeholder[placeholder]
    except KeyError:
      encoded_counter = placeholder_match.group('encoded_counter')
      counter = PlaceholderMaster.decode(encoded_counter)
      warnings.warn(
        'warning: placeholder encountered with unrecognised counter '
        f'`{encoded_counter}`, denoting {counter}, '
        f'which is greater than the current counter ({self._counter})\n\n'
        'Possible causes:\n'
        '- Confounding occurrences of «marker» have not been removed '
          'by calling protect_marker_occurrences(...)\n'
        '- A replacement rule alters or generates strings of the form '
          '`«marker»«encoded_counter»«marker»`'
      )
      return placeholder
  
  def __init__(self):
    self._counter = 0
    self._string_from_placeholder = {}
    self._placeholder_from_string = {}
    self._marker_placeholder = self.protect(PlaceholderMaster._MARKER)
  
  def protect_marker_occurrences(self, string):
    """
    Ensure that occurrences of «marker» will not be confounding.
    """
    
    return re.sub(PlaceholderMaster._MARKER, self._marker_placeholder, string)
  
  def protect(self, string):
    """
    Protect a string by allocating it a placeholder.
    
    Reuses existing placeholders where possible.
    """
    
    string = self.unprotect(string)
    if string in self._placeholder_from_string:
      return self._placeholder_from_string[string]
    
    placeholder = PlaceholderMaster.build_placeholder(self._counter)
    self._counter += 1
    self._string_from_placeholder[placeholder] = string
    self._placeholder_from_string[string] = placeholder
    
    return placeholder
  
  def unprotect(self, string):
    """
    Unprotect a string by restoring placeholders to their strings.
    """
    
    return re.sub(
      PlaceholderMaster._PLACEHOLDER_PATTERN,
      self._unprotect_substitute_function,
      string,
    )
  
  @staticmethod
  def encode_digit(digit):
    
    if digit < 0:
      raise ValueError('error: digit must be non-negative')
    
    if digit >= PlaceholderMaster._COUNTER_BASE:
      raise ValueError(
        f'error: digit too large for base {PlaceholderMaster._COUNTER_BASE}'
      )
    
    return chr(PlaceholderMaster._COUNTER_CODE_POINT_MIN + digit)
  
  @staticmethod
  def decode_encoded_digit(encoded_digit):
    return ord(encoded_digit) - PlaceholderMaster._COUNTER_CODE_POINT_MIN
  
  @staticmethod
  def encode(counter):
    
    if counter < 0:
      raise ValueError('error: counter to be encoded must be non-negative')
    
    if counter == 0:
      return PlaceholderMaster.encode_digit(0)
    
    encoded_digits = []
    while counter > 0:
      quotient, last_digit = divmod(counter, PlaceholderMaster._COUNTER_BASE)
      encoded_last_digit = PlaceholderMaster.encode_digit(last_digit)
      encoded_digits.append(encoded_last_digit)
      counter = quotient
    
    return ''.join(reversed(encoded_digits))
  
  @staticmethod
  def decode(encoded_counter):
    
    counter = 0
    for encoded_digit in encoded_counter:
      digit = PlaceholderMaster.decode_encoded_digit(encoded_digit)
      counter = counter * PlaceholderMaster._COUNTER_BASE + digit
    
    return counter
  
  @staticmethod
  def build_placeholder(counter):
    
    marker = PlaceholderMaster._MARKER
    encoded_counter = PlaceholderMaster.encode(counter)
    
    return f'{marker}{encoded_counter}{marker}'


class Replacement(abc.ABC):
  """
  Base class for a replacement rule.
  
  Not to be used when authoring CMD documents.
  (Hypothetical) CMD replacement rule syntax:
  ````
  Replacement: #«id»
  - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
  ````
  """
  
  def __init__(self, id_):
    self._is_committed = False
    self._id = id_
    self._queue_position_type = None
    self._queue_reference_replacement = None
  
  @property
  @abc.abstractmethod
  def attribute_names(self):
    raise NotImplementedError
  
  @property
  def id_(self):
    return self._id
  
  @property
  def queue_position_type(self):
    return self._queue_position_type
  
  @queue_position_type.setter
  def queue_position_type(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `queue_position_type` after `commit()`'
      )
    self._queue_position_type = value
  
  @property
  def queue_reference_replacement(self):
    return self._queue_reference_replacement
  
  @queue_reference_replacement.setter
  def queue_reference_replacement(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `queue_reference_replacement` after `commit()`'
      )
    self._queue_reference_replacement = value
  
  def commit(self):
    self._validate_mandatory_attributes()
    self._set_apply_method_variables()
    self._is_committed = True
  
  def apply(self, string):
    if not self._is_committed:
      raise UncommittedApplyException(
        'error: cannot call `apply(string)` before `commit()`'
      )
    return self._apply(string)
  
  @abc.abstractmethod
  def _validate_mandatory_attributes(self):
    """
    Ensure all mandatory attributes have been set.
    """
    raise NotImplementedError
  
  @abc.abstractmethod
  def _set_apply_method_variables(self):
    """
    Set variables used in `self._apply(string)`.
    """
    raise NotImplementedError
  
  @abc.abstractmethod
  def _apply(self, string):
    """
    Apply the defined replacement to a string.
    """
    raise NotImplementedError


class PlaceholderMarkerReplacement(Replacement):
  """
  A replacement rule replacing the placeholder marker with a placeholder.
  
  To be used before PlaceholderProtectionReplacement,
  see class PlaceholderMaster (especially `protect_marker_occurrences`).
  Ensures that occurrences of «marker» will not be confounding.
  """
  
  def __init__(self, id_, replacement_master):
    super().__init__(id_)
    self._replacement_master = replacement_master
  
  def attribute_names(self):
    return ()
  
  def _validate_mandatory_attributes(self):
    pass
  
  def _set_apply_method_variables(self):
    pass
  
  def _apply(self, string):
    return self._replacement_master.protect_marker_occurrences(string)


class DeIndentationReplacement(Replacement):
  """
  A replacement rule for de-indentation.
  
  CMD replacement rule syntax:
  ````
  DeIndentationReplacement: #«id»
  - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
  ````
  """
  
  def __init__(self, id_):
    super().__init__(id_)
  
  def attribute_names(self):
    return ()
  
  def _validate_mandatory_attributes(self):
    pass
  
  def _set_apply_method_variables(self):
    pass
  
  def _apply(self, string):
    return de_indent(string)


class OrdinaryDictionaryReplacement(Replacement):
  """
  A replacement rule for a dictionary of ordinary substitutions.
  
  Substitutions shall be applied simultaneously,
  that earlier substitutions be not sabotaged by newer ones.
  
  CMD replacement rule syntax:
  ````
  OrdinaryDictionaryReplacement: #«id»
  - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
  * «pattern» --> «substitute»
  [...]
  ````
  """
  
  def __init__(self, id_):
    super().__init__(id_)
    self._substitute_from_pattern = {}
    self._regex_pattern = None
    self._substitute_function = None
  
  def attribute_names(self):
    return (
      'queue_position',
    )
  
  def add_substitution(self, pattern, substitute):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot call `add_substitution(...)` after `commit()`'
      )
    self._substitute_from_pattern[pattern] = substitute
  
  def _validate_mandatory_attributes(self):
    pass
  
  def _set_apply_method_variables(self):
    self._regex_pattern = \
            OrdinaryDictionaryReplacement.build_regex_pattern(
              self._substitute_from_pattern,
            )
    self._substitute_function = \
            OrdinaryDictionaryReplacement.build_substitute_function(
              self._substitute_from_pattern,
            )
  
  def _apply(self, string):
    
    if self._regex_pattern != '':
      string = re.sub(self._regex_pattern, self._substitute_function, string)
    
    return string
  
  @staticmethod
  def build_regex_pattern(substitute_from_pattern):
    return '|'.join(re.escape(pattern) for pattern in substitute_from_pattern)
  
  @staticmethod
  def build_substitute_function(substitute_from_pattern):
    
    def substitute_function(match):
      pattern = match.group()
      substitute = substitute_from_pattern[pattern]
      return substitute
    
    return substitute_function


class RegexDictionaryReplacement(Replacement):
  """
  A replacement rule for a dictionary of regex substitutions.
  
  Substitutions are applied in order.
  Python regex syntax is used,
  with `flags=re.ASCII | re.MULTILINE | re.VERBOSE`.
  
  CMD replacement rule syntax:
  ````
  RegexDictionaryReplacement: #«id»
  - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
  * «pattern» --> «substitute»
  [...]
  ````
  """
  
  def __init__(self, id_):
    super().__init__(id_)
    self._substitute_from_pattern = {}
  
  def attribute_names(self):
    return (
      'queue_position',
    )
  
  def add_substitution(self, pattern, substitute):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot call `add_substitution(...)` after `commit()`'
      )
    self._substitute_from_pattern[pattern] = substitute
  
  def _validate_mandatory_attributes(self):
    pass
  
  def _set_apply_method_variables(self):
    pass
  
  def _apply(self, string):
    for pattern, substitute in self._substitute_from_pattern.items():
      string = \
              re.sub(
                pattern,
                substitute,
                string,
                flags=re.ASCII | re.MULTILINE | re.VERBOSE,
              )
    return string


class ExtensibleFenceReplacement(Replacement):
  """
  A generalised extensible-fence-style replacement rule.
  
  Inspired by the repeatable backticks of John Gruber's Markdown.
  CMD replacement rule syntax:
  ````
  ExtensibleFenceReplacement: #«id»
  - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
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
  
  def __init__(self, id_):
    super().__init__(id_)
    self._syntax_type_is_block = None
    self._flag_setting_from_letter = {}
    self._has_flags = False
    self._opening_delimiter = ''
    self._extensible_delimiter_character = None
    self._extensible_delimiter_min_count = None
    self._attribute_specifications = None
    self._content_replacement_list = []
    self._closing_delimiter = ''
    self._tag_name = None
    self._regex_pattern = None
    self._substitute_function = None
  
  def attribute_names(self):
    return (
      'queue_position',
      'syntax_type',
      'allowed_flags',
      'opening_delimiter',
      'extensible_delimiter',
      'attribute_specifications',
      'content_replacements',
      'closing_delimiter',
      'tag_name',
    )
  
  @property
  def syntax_type_is_block(self):
    return self._syntax_type_is_block
  
  @syntax_type_is_block.setter
  def syntax_type_is_block(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `syntax_type_is_block` after `commit()`'
      )
    self._syntax_type_is_block = value
  
  @property
  def flag_setting_from_letter(self):
    return self._flag_setting_from_letter
  
  @flag_setting_from_letter.setter
  def flag_setting_from_letter(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `flag_setting_from_letter` after `commit()`'
      )
    self._flag_setting_from_letter = value
  
  @property
  def opening_delimiter(self):
    return self._opening_delimiter
  
  @opening_delimiter.setter
  def opening_delimiter(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `flag_setting_from_letter` after `commit()`'
      )
    self._opening_delimiter = value
  
  @property
  def extensible_delimiter_character(self):
    return self._extensible_delimiter_character
  
  @extensible_delimiter_character.setter
  def extensible_delimiter_character(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `extensible_delimiter_character` after `commit()`'
      )
    self._extensible_delimiter_character = value
  
  @property
  def extensible_delimiter_min_count(self):
    return self._extensible_delimiter_min_count
  
  @extensible_delimiter_min_count.setter
  def extensible_delimiter_min_count(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `extensible_delimiter_min_count` after `commit()`'
      )
    self._extensible_delimiter_min_count = value
  
  @property
  def attribute_specifications(self):
    return self._attribute_specifications
  
  @attribute_specifications.setter
  def attribute_specifications(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `attribute_specifications` after `commit()`'
      )
    self._attribute_specifications = value
  
  @property
  def content_replacement_list(self):
    return self._content_replacement_list
  
  @content_replacement_list.setter
  def content_replacement_list(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `content_replacement_list` after `commit()`'
      )
    self._content_replacement_list = value
  
  @property
  def closing_delimiter(self):
    return self._closing_delimiter
  
  @closing_delimiter.setter
  def closing_delimiter(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `closing_delimiter` after `commit()`'
      )
    self._closing_delimiter = value
  
  @property
  def tag_name(self):
    return self._tag_name
  
  @tag_name.setter
  def tag_name(self, value):
    if self._is_committed:
      raise CommittedMutateException(
        'error: cannot set `tag_name` after `commit()`'
      )
    self._tag_name = value
  
  def _validate_mandatory_attributes(self):
    
    if self._syntax_type_is_block is None:
      raise MissingAttributeException('syntax_type')
    
    if self._extensible_delimiter_character is None:
      raise MissingAttributeException('extensible_delimiter')
  
  def _set_apply_method_variables(self):
    
    self._has_flags = len(self._flag_setting_from_letter) > 0
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
            self.build_substitute_function(
              self._flag_setting_from_letter,
              self._has_flags,
              self._attribute_specifications,
              self._tag_name,
            )
  
  def _apply(self, string):
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
  
  def build_substitute_function(
    self,
    flag_setting_from_letter,
    has_flags,
    attribute_specifications,
    tag_name,
  ):
    
    def substitute_function(match):
      
      enabled_flag_settings = set()
      if has_flags:
        flags = match.group('flags')
        for flag_letter, flag_setting in flag_setting_from_letter.items():
          if flag_letter in flags:
            enabled_flag_settings.add(flag_setting)
      
      if attribute_specifications is not None:
        matched_attribute_specifications = \
                match.group('attribute_specifications')
        combined_attribute_specifications = \
                ' '.join(
                  [attribute_specifications, matched_attribute_specifications]
                )
        attributes_sequence = \
                build_attributes_sequence(combined_attribute_specifications)
      else:
        attributes_sequence = ''
      
      content = match.group('content')
      for replacement in self._content_replacement_list:
        replacement_id = replacement.id_
        if replacement_id == 'escape-html':
          if 'KEEP_HTML_UNESCAPED' in enabled_flag_settings:
            continue
        elif replacement_id == 'reduce-whitespace':
          if 'REDUCE_WHITESPACE' not in enabled_flag_settings:
            continue
        elif replacement_id == 'de-indent':
          if 'KEEP_INDENTED' in enabled_flag_settings:
            continue
        content = replacement.apply(content)
      
      if tag_name is None:
        return content
      else:
        return f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'
    
    return substitute_function


CMD_REPLACEMENT_SYNTAX_HELP = \
'''\
In CMD replacement rule syntax, a line must be one of the following:
(1) whitespace-only;
(2) a comment (beginning with `#`);
(3) a rules inclusion (`< «included_file_name»`);
(4) a class declaration (`«ClassName»: #«id»`);
(5) the start of an attribute declaration (`- «name»: «value»`);
(6) the start of a substitution declaration (`* «pattern» --> «substitute»`);
(7) a continuation (beginning with whitespace).
- Note for (3): if «included_file_name» begins with a slash,
  it is parsed relative to the working directory;
  otherwise it is parsed relative to the current file.
- Note for (6): the number of hyphens in the delimiter `-->`
  may be arbitrarily increased should «pattern» contain
  a run of hyphens followed by a closing angle-bracket.
- Note for (7): continuations are only allowed for attribute declarations
  and for substitution declarations.
'''


class ReplacementMaster:
  """
  Object governing the parsing and application of replacement rules.
  
  ## `legislate` ##
  
  Parses CMD replacement rule syntax.
  See the constant `CMD_REPLACEMENT_SYNTAX_HELP` above.
  
  Terminology:
  - Class declarations are _committed_.
  - Attribute and substitution declarations are _staged_.
  
  ## `execute` ##
  
  Applies the legislated replacements.
  """
  
  def __init__(self, cmd_file_name):
    
    self._opened_file_names = [cmd_file_name]
    self._replacement_from_id = {}
    self._root_replacement_id = None
    self._replacement_queue = []
  
  @staticmethod
  def print_error(
    message,
    rules_file_name,
    start_line_number,
    end_line_number=None,
  ):
    
    if rules_file_name is None:
      source_file = 'STANDARD_RULES'
    else:
      source_file = f'`{rules_file_name}`'
    
    if end_line_number is None or start_line_number == end_line_number - 1:
      line_number_range = f'line {start_line_number}'
    else:
      line_number_range = f'lines {start_line_number} to {end_line_number - 1}'
    
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
        [<][ ]
          (?:
            [/] (?P<included_file_name> [\S][\s\S]*? )
              |
            (?P<included_file_name_relative> [\S][\s\S]*? )
          )
        [\s]*
      ''',
      line,
      flags=re.ASCII | re.VERBOSE,
    )
  
  def process_rules_inclusion_line(
    self,
    rules_inclusion_match,
    rules_file_name,
    line_number,
  ):
    
    included_file_name_relative = \
            rules_inclusion_match.group('included_file_name_relative')
    if included_file_name_relative is not None:
      included_file_name = \
              os.path.join(
                os.path.dirname(rules_file_name),
                included_file_name_relative,
              )
    else:
      included_file_name = rules_inclusion_match.group('included_file_name')
    included_file_name = os.path.normpath(included_file_name)
    
    try:
      with open(included_file_name, 'r', encoding='utf-8') as included_file:
        for opened_file_name in self._opened_file_names:
          if os.path.samefile(opened_file_name, included_file_name):
            self._opened_file_names.append(included_file_name)
            recursive_inclusion_string = \
                    ' includes '.join(
                      f'`{opened_file_name}`'
                        for opened_file_name in self._opened_file_names
                    )
            ReplacementMaster.print_error(
              f'recursive inclusion: {recursive_inclusion_string}',
              rules_file_name,
              line_number,
            )
            sys.exit(GENERIC_ERROR_EXIT_CODE)
        self._opened_file_names.append(included_file_name)
        replacement_rules = included_file.read()
    except FileNotFoundError:
      ReplacementMaster.print_error(
        f'file `{included_file_name}` (relative to terminal) not found',
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    self.legislate(replacement_rules, included_file_name)
  
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
    rules_file_name,
    line_number,
  ):
    
    class_name = class_declaration_match.group('class_name')
    id_ = class_declaration_match.group('id_')
    
    if class_name == 'DeIndentationReplacement':
      replacement = DeIndentationReplacement(id_)
    elif class_name == 'OrdinaryDictionaryReplacement':
      replacement = OrdinaryDictionaryReplacement(id_)
    elif class_name == 'ExtensibleFenceReplacement':
      replacement = ExtensibleFenceReplacement(id_)
    elif class_name == 'RegexDictionaryReplacement':
      replacement = RegexDictionaryReplacement(id_)
    else:
      ReplacementMaster.print_error(
        f'unrecognised replacement class `{class_name}`',
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if id_ in self._replacement_from_id:
      ReplacementMaster.print_error(
        f'replacement already declared with id `{id_}`',
        rules_file_name,
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
    rules_file_name,
    line_number,
  ):
    
    attribute_name = attribute_declaration_match.group('attribute_name')
    if attribute_name not in replacement.attribute_names():
      ReplacementMaster.print_error(
        f'unrecognised attribute `{attribute_name}` for `{class_name}`',
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    partial_attribute_value = \
            attribute_declaration_match.group('partial_attribute_value')
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
            substitution_declaration_match.group('partial_substitution')
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
    rules_file_name,
    line_number,
  ):
    
    continuation = continuation_match.group('continuation')
    
    if attribute_name is not None:
      attribute_value = \
              none_to_empty_string(attribute_value) + '\n' + continuation
    elif substitution is not None:
      substitution = substitution + '\n' + continuation
    else:
      ReplacementMaster.print_error(
        'continuation only allowed for attribute or substitution declarations',
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    return attribute_value, substitution
  
  @staticmethod
  def compute_allowed_flag_matches(attribute_value):
    return re.finditer(
      r'''
        (?P<whitespace_only> \A [\s]* \Z )
          |
        (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
          |
        [\s]*
        (?:
          (?P<flag_letter> [a-z] ) =
                  (?P<flag_setting>
                    KEEP_HTML_UNESCAPED
                      |
                    REDUCE_WHITESPACE
                      |
                    KEEP_INDENTED
                  )
                  (?= [\s] | \Z )
            |
          (?P<invalid_syntax> [\S]+ )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_allowed_flags(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    flag_setting_from_letter = {}
    
    for allowed_flag_match \
    in ReplacementMaster.compute_allowed_flag_matches(attribute_value):
      
      if allowed_flag_match.group('whitespace_only') is not None:
        ReplacementMaster.print_error(
          f'invalid specification `` for attribute `allowed_flags`',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      invalid_syntax = allowed_flag_match.group('invalid_syntax')
      if invalid_syntax is not None:
        ReplacementMaster.print_error(
          f'invalid specification `{invalid_syntax}`'
          ' for attribute `allowed_flags`',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      if allowed_flag_match.group('none_keyword') is not None:
        return
      
      flag_letter = allowed_flag_match.group('flag_letter')
      flag_setting = allowed_flag_match.group('flag_setting')
      flag_setting_from_letter[flag_letter] = flag_setting
    
    replacement.flag_setting_from_letter = flag_setting_from_letter
  
  @staticmethod
  def compute_attribute_specifications_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none_keyword> NONE )
            |
          (?P<empty_keyword> EMPTY )
            |
          (?P<attribute_specifications> [\S][\s\S]*? )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_attribute_specifications(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    attribute_specifications_match = \
            ReplacementMaster.compute_attribute_specifications_match(
              attribute_value
            )
    
    invalid_value = attribute_specifications_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}`'
        ' for attribute `attribute_specifications`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if attribute_specifications_match.group('none_keyword') is not None:
      return
    
    if attribute_specifications_match.group('empty_keyword') is not None:
      replacement.attribute_specifications = ''
    
    attribute_specifications = \
            attribute_specifications_match.group('attribute_specifications')
    replacement.attribute_specifications = attribute_specifications
  
  @staticmethod
  def compute_closing_delimiter_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none_keyword> NONE )
            |
          (?P<closing_delimiter> [\S][\s\S]*? )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_closing_delimiter(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    closing_delimiter_match = \
            ReplacementMaster.compute_closing_delimiter_match(attribute_value)
    
    invalid_value = closing_delimiter_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` for attribute `closing_delimiter`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if closing_delimiter_match.group('none_keyword') is not None:
      return
    
    closing_delimiter = closing_delimiter_match.group('closing_delimiter')
    replacement.closing_delimiter = closing_delimiter
  
  @staticmethod
  def compute_content_replacement_matches(attribute_value):
    return re.finditer(
      r'''
        (?P<whitespace_only> \A [\s]* \Z )
          |
        (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
          |
        (?:
          [#] (?P<id_> [a-z-]+ ) (?= [\s] | \Z )
            |
          (?P<invalid_syntax> [\S]+ )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  def stage_content_replacements(
    self,
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    content_replacement_list = []
    
    for content_replacement_match \
    in ReplacementMaster.compute_content_replacement_matches(attribute_value):
      
      if content_replacement_match.group('whitespace_only') is not None:
        ReplacementMaster.print_error(
          f'invalid specification `` for attribute `content_replacements`',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      invalid_syntax = content_replacement_match.group('invalid_syntax')
      if invalid_syntax is not None:
        ReplacementMaster.print_error(
          f'invalid specification `{invalid_syntax}`'
          ' for attribute `content_replacements`',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      if content_replacement_match.group('none_keyword') is not None:
        return
      
      content_replacement_id = content_replacement_match.group('id_')
      if content_replacement_id == replacement.id_:
        content_replacement = replacement
      else:
        try:
          content_replacement = \
                  self._replacement_from_id[content_replacement_id]
        except KeyError:
          ReplacementMaster.print_error(
            f'undefined replacement `#{content_replacement_id}`',
            rules_file_name,
            line_number_range_start,
            line_number,
          )
          sys.exit(GENERIC_ERROR_EXIT_CODE)
      
      content_replacement_list.append(content_replacement)
    
    replacement.content_replacements = content_replacement_list
  
  @staticmethod
  def compute_extensible_delimiter_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<extensible_delimiter>
            (?P<extensible_delimiter_character> [\S] )
            (?P=extensible_delimiter_character)*
          )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_extensible_delimiter(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    extensible_delimiter_match = \
            ReplacementMaster.compute_extensible_delimiter_match(
              attribute_value
            )
    
    invalid_value = extensible_delimiter_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` not a character repeated'
        ' for attribute `extensible_delimiter`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    extensible_delimiter_character = \
            extensible_delimiter_match.group('extensible_delimiter_character')
    extensible_delimiter = \
            extensible_delimiter_match.group('extensible_delimiter')
    extensible_delimiter_min_count = len(extensible_delimiter)
    
    replacement.extensible_delimiter_character = extensible_delimiter_character
    replacement.extensible_delimiter_min_count = extensible_delimiter_min_count
  
  @staticmethod
  def compute_opening_delimiter_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none_keyword> NONE )
            |
          (?P<opening_delimiter> [\S][\s\S]*? )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_opening_delimiter(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    opening_delimiter_match = \
            ReplacementMaster.compute_opening_delimiter_match(attribute_value)
    
    invalid_value = opening_delimiter_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` for attribute `opening_delimiter`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if opening_delimiter_match.group('none_keyword') is not None:
      return
    
    opening_delimiter = opening_delimiter_match.group('opening_delimiter')
    replacement.opening_delimiter = opening_delimiter
  
  @staticmethod
  def compute_queue_position_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none_keyword> NONE )
            |
          (?P<root_keyword> ROOT )
            |
          (?P<queue_position_type> BEFORE | AFTER )
          [ ]
          [#] (?P<queue_reference_id> [a-z-]+ )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  def stage_queue_position(
    self,
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    queue_position_match = \
            ReplacementMaster.compute_queue_position_match(attribute_value)
    
    invalid_value = queue_position_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` for attribute `queue_position`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if queue_position_match.group('none_keyword') is not None:
      return
    
    if queue_position_match.group('root_keyword') is not None:
      if self._root_replacement_id is not None:
        ReplacementMaster.print_error(
          'root replacement already declared'
          f' (`#{self._root_replacement_id}`)',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      replacement.queue_position_type = 'ROOT'
      replacement.queue_reference_replacement = None
      return
    
    queue_position_type = \
            queue_position_match.group('queue_position_type')
    queue_reference_id = \
            queue_position_match.group('queue_reference_id')
    
    if queue_reference_id == replacement.id_:
      ReplacementMaster.print_error(
        f'self-referential `queue_position`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    try:
      queue_reference_replacement = \
              self._replacement_from_id[queue_reference_id]
    except KeyError:
      ReplacementMaster.print_error(
        f'undefined replacement `#{queue_reference_id}`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    replacement.queue_position_type = queue_position_type
    replacement.queue_reference_replacement = queue_reference_replacement
  
  @staticmethod
  def compute_syntax_type_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<syntax_type> BLOCK | INLINE )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_syntax_type(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    syntax_type_match = \
            ReplacementMaster.compute_syntax_type_match(attribute_value)
    
    invalid_value = syntax_type_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` for attribute `syntax_type`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    syntax_type = syntax_type_match.group('syntax_type')
    replacement.syntax_type_is_block = syntax_type == 'BLOCK'
  
  @staticmethod
  def compute_tag_name_match(attribute_value):
    return re.fullmatch(
      r'''
        [\s]*
        (?:
          (?P<none_keyword> NONE )
            |
          (?P<tag_name> [a-z]+ )
            |
          (?P<invalid_value> [\s\S]*? )
        )
        [\s]*
      ''',
      attribute_value,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_tag_name(
    replacement,
    attribute_value,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    tag_name_match = ReplacementMaster.compute_tag_name_match(attribute_value)
    
    invalid_value = tag_name_match.group('invalid_value')
    if invalid_value is not None:
      ReplacementMaster.print_error(
        f'invalid value `{invalid_value}` for attribute `tag_name`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    if tag_name_match.group('none_keyword') is not None:
      return
    
    tag_name = tag_name_match.group('tag_name')
    replacement.tag_name = tag_name
  
  @staticmethod
  def compute_substitution_match(substitution):
    
    substitution_delimiters = re.findall('[-]{2,}[>]', substitution)
    if len(substitution_delimiters) == 0:
      return None
    
    longest_substitution_delimiter = max(substitution_delimiters, key=len)
    return re.fullmatch(
      fr'''
        [\s]*
          (?P<pattern> [\S][\s\S]*? )
        [\s]*
          {re.escape(longest_substitution_delimiter)}
        [\s]*
          (?P<substitute> [\s\S]*? )
        [\s]*
      ''',
      substitution,
      flags=re.ASCII | re.VERBOSE,
    )
  
  @staticmethod
  def stage_ordinary_substitution(
    replacement,
    substitution,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    substitution_match = \
            ReplacementMaster.compute_substitution_match(substitution)
    if substitution_match is None:
      ReplacementMaster.print_error(
        f'missing delimiter `-->` in substitution `{substitution}`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    pattern = substitution_match.group('pattern')
    substitute = substitution_match.group('substitute')
    
    replacement.add_substitution(pattern, substitute)
  
  @staticmethod
  def stage_regex_substitution(
    replacement,
    substitution,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    substitution_match = \
            ReplacementMaster.compute_substitution_match(substitution)
    if substitution_match is None:
      ReplacementMaster.print_error(
        f'missing delimiter `-->` in substitution `{substitution}`',
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    pattern = substitution_match.group('pattern')
    substitute = substitution_match.group('substitute')
    
    try:
      re.sub(pattern, '', '', flags=re.ASCII | re.MULTILINE | re.VERBOSE)
    except re.error as pattern_exception:
      ReplacementMaster.print_error(
        f'bad regex pattern `{pattern}`',
        rules_file_name,
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
        rules_file_name,
        line_number_range_start,
        line_number,
      )
      ReplacementMaster.print_traceback(substitute_exception)
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    replacement.add_substitution(pattern, substitute)
  
  def stage(
    self,
    class_name,
    replacement,
    attribute_name,
    attribute_value,
    substitution,
    rules_file_name,
    line_number_range_start,
    line_number,
  ):
    
    if substitution is not None: # staging a substitution
      
      if class_name == 'OrdinaryDictionaryReplacement':
        ReplacementMaster.stage_ordinary_substitution(
          replacement,
          substitution,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif class_name == 'RegexDictionaryReplacement':
        ReplacementMaster.stage_regex_substitution(
          replacement,
          substitution,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      else:
        ReplacementMaster.print_error(
          f'class `{class_name}` does not allow substitutions',
          rules_file_name,
          line_number_range_start,
          line_number,
        )
        sys.exit(GENERIC_ERROR_EXIT_CODE)
      
    else: # staging an attribute declaration
      
      if attribute_name == 'allowed_flags':
        ReplacementMaster.stage_allowed_flags(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'attribute_specifications':
        ReplacementMaster.stage_attribute_specifications(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'closing_delimiter':
        ReplacementMaster.stage_closing_delimiter(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'content_replacements':
        self.stage_content_replacements(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'extensible_delimiter':
        ReplacementMaster.stage_extensible_delimiter(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'opening_delimiter':
        ReplacementMaster.stage_opening_delimiter(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'queue_position':
        self.stage_queue_position(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'syntax_type':
        ReplacementMaster.stage_syntax_type(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
      elif attribute_name == 'tag_name':
        ReplacementMaster.stage_tag_name(
          replacement,
          attribute_value,
          rules_file_name,
          line_number_range_start,
          line_number,
        )
    
    return None, None, None, None
    # attribute_name, attribute_value, substitution, line_number_range_start
  
  def commit(self, class_name, replacement, rules_file_name, line_number):
    
    try:
      replacement.commit()
    except MissingAttributeException as exception:
      missing_attribute = exception.get_missing_attribute()
      ReplacementMaster.print_error(
        f'missing attribute `{missing_attribute}` for {class_name}',
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    id_ = replacement.id_
    self._replacement_from_id[id_] = replacement
    
    queue_position_type = replacement.queue_position_type
    if queue_position_type is None:
      pass
    elif queue_position_type == 'ROOT':
      self._root_replacement_id = id_
      self._replacement_queue.append(replacement)
    else:
      queue_reference_replacement = replacement.queue_reference_replacement
      queue_reference_index = \
              self._replacement_queue.index(queue_reference_replacement)
      if queue_position_type == 'BEFORE':
        insertion_index = queue_reference_index
      elif queue_position_type == 'AFTER':
        insertion_index = queue_reference_index + 1
      else:
        insertion_index = None
      self._replacement_queue.insert(insertion_index, replacement)
    
    return None, None, None, None, None, None
    # class_name, replacement, attribute_name, attribute_value, substitution,
    # line_number_range_start
  
  def legislate(self, replacement_rules, rules_file_name=None):
    
    if replacement_rules is None:
      return
    
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
        if attribute_name is not None or substitution is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    rules_file_name,
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
                    rules_file_name,
                    line_number,
                  )
        continue
      
      rules_inclusion_match = \
              ReplacementMaster.compute_rules_inclusion_match(line)
      if rules_inclusion_match is not None:
        if attribute_name is not None or substitution is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    rules_file_name,
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
                    rules_file_name,
                    line_number,
                  )
        self.process_rules_inclusion_line(
          rules_inclusion_match,
          rules_file_name,
          line_number,
        )
        continue
      
      class_declaration_match = \
              ReplacementMaster.compute_class_declaration_match(line)
      if class_declaration_match is not None:
        if attribute_name is not None or substitution is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    rules_file_name,
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
                    rules_file_name,
                    line_number,
                  )
        class_name, replacement, line_number_range_start = \
                self.process_class_declaration_line(
                  class_declaration_match,
                  rules_file_name,
                  line_number,
                )
        continue
      
      attribute_declaration_match = \
              ReplacementMaster.compute_attribute_declaration_match(line)
      if attribute_declaration_match is not None:
        if attribute_name is not None or substitution is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    rules_file_name,
                    line_number_range_start,
                    line_number,
                  )
        attribute_name, attribute_value, line_number_range_start = \
                ReplacementMaster.process_attribute_declaration_line(
                  attribute_declaration_match,
                  class_name,
                  replacement,
                  attribute_value,
                  rules_file_name,
                  line_number,
                )
        continue
      
      substitution_declaration_match = \
              ReplacementMaster.compute_substitution_declaration_match(line)
      if substitution_declaration_match is not None:
        if attribute_name is not None or substitution is not None:
          attribute_name, attribute_value, \
          substitution, \
          line_number_range_start = \
                  self.stage(
                    class_name,
                    replacement,
                    attribute_name,
                    attribute_value,
                    substitution,
                    rules_file_name,
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
                  rules_file_name,
                  line_number,
                )
        continue
      
      ReplacementMaster.print_error(
        'invalid syntax\n\n' + CMD_REPLACEMENT_SYNTAX_HELP,
        rules_file_name,
        line_number,
      )
      sys.exit(GENERIC_ERROR_EXIT_CODE)
    
    # At end of file
    if attribute_name is not None or substitution is not None:
      self.stage(
        class_name,
        replacement,
        attribute_name,
        attribute_value,
        substitution,
        rules_file_name,
        line_number_range_start,
        line_number,
      )
    if replacement is not None:
      self.commit(class_name, replacement, rules_file_name, line_number + 1)
  
  def execute(self, string):
    
    for replacement in self._replacement_queue:
      string = replacement.apply(string)
    
    return string


def compute_longest_common_prefix(strings):
  
  shortest_string = min(strings, key=len)
  
  prefix = shortest_string
  while len(prefix) > 0:
    if all(string.startswith(prefix) for string in strings):
      break
    prefix = prefix[:-1]
  
  return prefix


def de_indent(string):
  """
  De-indent a string.
  
  Empty lines do not count towards the longest common indentation.
  Whitespace-only lines do count towards the longest common indentation,
  except for the last line, which, if whitespace-only,
  will have its whitespace erased.
  
  In contrast, `textwrap.dedent` will perform blank erasure
  of whitespace on all whitespace-only lines,
  even those lines which are not the last line.
  """
  
  string = \
          re.sub(
            r'''
              ^ [^\S\n]+ \Z
            ''',
            '',
            string,
            flags=re.ASCII | re.MULTILINE | re.VERBOSE
          )
  indentations = \
          re.findall(
            r'''
              ^ [^\S\n]+
                |
              ^ (?! $ )
            ''',
            string,
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
          )
  longest_common_indentation = compute_longest_common_prefix(indentations)
  string = \
          re.sub(
            f'''
              ^ {re.escape(longest_common_indentation)}
            ''',
            '',
            string,
            flags=re.MULTILINE | re.VERBOSE,
          )
  
  return string


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
  
  name = attribute_specification_match.group('name')
  if name is not None:
    
    try:
      name = ATTRIBUTE_NAME_FROM_ABBREVIATION[name]
    except KeyError:
      pass
    
    quoted_value = attribute_specification_match.group('quoted_value')
    if quoted_value is not None:
      return name, quoted_value
    
    bare_value = attribute_specification_match.group('bare_value')
    if bare_value is not None:
      return name, bare_value
  
  id_ = attribute_specification_match.group('id_')
  if id_ is not None:
    return 'id', id_
  
  class_ = attribute_specification_match.group('class_')
  if class_ is not None:
    return 'class', class_
  
  rowspan = attribute_specification_match.group('rowspan')
  if rowspan is not None:
    return 'rowspan', rowspan
  
  colspan = attribute_specification_match.group('colspan')
  if colspan is not None:
    return 'colspan', colspan
  
  width = attribute_specification_match.group('width')
  if width is not None:
    return 'width', width
  
  height = attribute_specification_match.group('height')
  if height is not None:
    return 'height', height
  
  boolean_attribute = attribute_specification_match.group('boolean_attribute')
  if boolean_attribute is not None:
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
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
          )
  
  replacement_rules = match.group('replacement_rules')
  main_content = match.group('main_content')
  
  return replacement_rules, main_content


STANDARD_RULES = \
r'''# STANDARD_RULES

DeIndentationReplacement: #de-indent

OrdinaryDictionaryReplacement: #escape-html
* & --> &amp;
* < --> &lt;
* > --> &gt;

RegexDictionaryReplacement: #trim-whitespace
* \A [\s]* -->
* [\s]* \Z -->

RegexDictionaryReplacement: #reduce-whitespace
* [\n]+ --> \n
* ^ [^\S\n]+ -->
* [^\S\n]+ $ -->
* [\s]+ (?= <br> ) -->

ExtensibleFenceReplacement: #literals
- queue_position: ROOT
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
  replacement_master.legislate(STANDARD_RULES)
  replacement_master.legislate(replacement_rules, cmd_file_name)
  html = replacement_master.execute(main_content)
  
  return html


def is_cmd_file(file_name):
  return file_name.endswith('.cmd')


def extract_cmd_name(cmd_file_name_argument):
  """
  Extract name-without-extension from a CMD file name argument.
  
  The path is normalised by resolving `./` and `../`.
  """
  
  cmd_file_name_argument = os.path.normpath(cmd_file_name_argument)
  cmd_name = \
          re.sub(
            r'''
              [.] (cmd)?
              \Z
            ''',
            '',
            cmd_file_name_argument,
            flags=re.VERBOSE,
          )
  
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
    '-v', '--version',
    action='version',
    version=f'{argument_parser.prog} {__version__}',
  )
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
    for path, _, file_names in os.walk(os.curdir):
      for file_name in file_names:
        if is_cmd_file(file_name):
          cmd_file_name = os.path.join(path, file_name)
          generate_html_file(cmd_file_name, uses_command_line_argument=False)


if __name__ == '__main__':
  main()
