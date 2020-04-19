#!/usr/bin/python

"""
----------------------------------------------------------------
cmd.py
----------------------------------------------------------------

A converter from Conway's markdown (CMD) to HTML,
written for the sole purpose of building his site
<https://yawnoc.github.io/>.

Conversion is done entirely using regular expression replacements
and placeholder dictionaries.
Unlike John Gruber's markdown, I use fence-style constructs
to avoid the need for proper parsing.

You   : Why the hell would you use regex to do this?
Conway: It works, really!
You   : You're crazy.
Conway: Oh shut up, I already know that.

Documentation: <https://conway-markdown.github.io/>
GitHub: <https://github.com/conway-markdown/conway-markdown>

Released into the public domain (CC0):
  <https://creativecommons.org/publicdomain/zero/1.0/>
ABSOLUTELY NO WARRANTY, i.e. "GOD SAVE YOU"

"""


import argparse
import fnmatch
import functools
import os
import re


################################################################
# String processing
################################################################


ANY_CHARACTER_REGEX = r'[\s\S]'
ANYTHING_MINIMAL_REGEX = f'{ANY_CHARACTER_REGEX}*?'
NON_EMPTY_MINIMAL_REGEX = f'{ANY_CHARACTER_REGEX}+?'

NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX = r'[^]]*?'
NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX = r'[^}]*?'

NOT_QUOTE_MINIMAL_REGEX = r'[^"]*?'

HORIZONTAL_WHITESPACE_CHARACTER_REGEX = r'[^\S\n]'
LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX = (
  f'^{HORIZONTAL_WHITESPACE_CHARACTER_REGEX}*'
)

NOT_WHITESPACE_MINIMAL_REGEX = r'[\S]*?'

NOT_NEWLINE_CHARACTER_REGEX = r'[^\n]'


def de_indent(string):
  """
  De-indent string.
  
  Trailing horizontal whitespace on the last line is removed.
  Empty lines do not count towards the longest common indentation.
  
  By contrast, textwrap.dedent will remove horizontal whitespace
  from *any* whitespace-only line, even in the middle of the string,
  which is undesirable.
  """
  
  # Remove trailing horizontal whitespace on the last line
  string = re.sub(
    f'''
      {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} *  $
    ''',
    '',
    string,
    flags=re.VERBOSE
  )
  
  # Get list of all indentations, either
  # (1) non-empty leading horizontal whitespace, or
  # (2) the leading empty string on a non-empty line.
  indentation_list = re.findall(
    f'''
      ^  {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +
        |
      ^  (?=  {NOT_NEWLINE_CHARACTER_REGEX}  )
    ''',
    string,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  # Remove longest common indentation
  longest_common_indentation = os.path.commonprefix(indentation_list)
  string = re.sub(
    f'''
      ^  {re.escape(longest_common_indentation)}
    ''',
    '',
    string,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return string


def escape_python_backslash(string):
  r"""
  Escape a Python backslash into a double backslash.
    \ becomes \\
  """
  
  string = re.sub(r'\\', r'\\\\', string)
  
  return string


def escape_html_syntax_characters(string):
  """
  Escape the three HTML syntax characters &, <, >.
    & becomes &amp;
    < becomes &lt;
    > becomes &gt;
  """
  
  string = re.sub('&', '&amp;', string)
  string = re.sub('<', '&lt;', string)
  string = re.sub('>', '&gt;', string)
  
  return string


def escape_html_quotes(string):
  """
  Escape the HTML double quote ".
    " becomes &quot;
  """
  
  string = re.sub('"', '&quot;', string)
  
  return string


def escape_html_attribute_value(placeholder_storage, string):
  """
  Escape the characters &, <, >, " in an attribute value.
  Surrounding whitespace not protected by a placeholder is stripped.
  
  Since the string may contain placeholder strings
  (for instance from CMD literals),
  in which the three HTML syntax characters &, <, >
  are already escaped, but the quote " is not:
  (1) Leading and trailing whitespace is stripped.
  (2) Line continuations are processed.
  (3) The three HTML syntax characters &, <, > are escaped.
  (4) The placeholder strings are replaced with their markup.
  (5) If the string is empty, an empty string is returned.
  (6) The quote " is escaped.
  (7) The string is stored into a new placeholder.
  
  CMD shall always delimit attribute values by double quotes " ",
  never single quotes ' '.
  Therefore single quotes are not escaped as &apos;
  """
  
  string = string.strip()
  string = process_line_continuations(string)
  string = escape_html_syntax_characters(string)
  string = placeholder_storage.replace_placeholders_with_markup(string)
  if string == '':
    return string
  string = escape_html_quotes(string)
  
  return placeholder_storage.create_placeholder_store_markup(string)


def build_html_attribute(
  placeholder_storage, attribute_name, attribute_value
):
  """
  Build an HTML attribute {attribute name}="{attribute value}",
  with a leading space and the necessary escaping for {attribute value}.
  If {attribute value} is None or empty, the empty string is returned.
  """
  
  if (
    attribute_value is None
      or
    placeholder_storage
      .replace_placeholders_with_markup(attribute_value)
      .strip()
      == ''
  ):
    return ''
  
  attribute_value = escape_html_attribute_value(
    placeholder_storage, attribute_value
  )
  attribute = f' {attribute_name}="{attribute_value}"'
  
  return attribute


################################################################
# Temporary storage
################################################################


def replace_by_ordinary_dictionary(
  dictionary, string, placeholder_storage=None
):
  """
  Apply a dictionary of ordinary replacements to a string.
  """
  
  for pattern in dictionary:
    
    replacement = dictionary[pattern]
    replacement = escape_python_backslash(replacement)
    if placeholder_storage is not None:
      replacement = (
        placeholder_storage.create_placeholder_store_markup(replacement)
      )
    
    string = re.sub(
      re.escape(pattern),
      replacement,
      string
    )
  
  return string


def replace_by_regex_dictionary(dictionary, string):
  """
  Apply a dictionary of regex replacements to a string.
  """
  
  for pattern in dictionary:
    
    replacement = dictionary[pattern]
    
    string = re.sub(
      pattern,
      replacement,
      string,
      flags=re.MULTILINE|re.VERBOSE
    )
  
  return string


def process_match_by_ordinary_dictionary(dictionary, match_object):
  """
  Process a match object using a dictionary of ordinary replacements.
  To be passed in the form
    functools.partial(process_match_by_ordinary_dictionary, dictionary)
  as the replacement-function argument to re.sub,
  so that an ordinary replacement dictionary can be used
  to process a regex match object.
  
  If the entire string for the match object
  is a key (pattern) in the dictionary,
  the corresponding value (replacement) is returned;
  otherwise the string is returned as is.
  """
  
  match_string = match_object.group()
  replacement = dictionary.get(match_string, match_string)
  
  return replacement


class PlaceholderStorage:
  """
  Placeholder storage class for managing temporary replacements.
  
  There are many instances in which
  a portion of the markup should not be altered
  by any replacements in the processing to follow.
  To protect these portions of markup from further alteration,
  they are temporarily replaced by placeholder strings of the form
    X{n}X
  where
  (a) X is U+E000, the first "Private Use Area" code point,
      referred to as the "placeholder marker", and
  (b) {n} is an integer counter which is incremented.
  Actual occurrences of X in the original markup
  are themselves to be replaced with a placeholder;
  this ensures that those actual occurrences
  are not confounded with the placeholder strings X{n}X.
  
  Assuming that the user does not supply regex or ordinary replacements
  which alter strings of the form X{n}X,
  the placeholder strings will reliably protect portions of markup
  from any further processing.
  
  Each portion of markup which is to be protected
  from alteration by further processing
  is stored in a dictionary of ordinary replacements, with
    KEYS: the placeholder strings (X{n}X), and
    VALUES: the respective portions of markup.
  """
  
  PLACEHOLDER_MARKER = '\uE000'
  PLACEHOLDER_STRING_COMPILED_REGEX = re.compile(
    f'''
      {PLACEHOLDER_MARKER}
      [0-9] +
      {PLACEHOLDER_MARKER}
    ''',
    flags=re.VERBOSE
  )
  
  def __init__(self):
    """
    Initialise placeholder storage.
    A placeholder is created for the placeholder marker X itself.
    """
    
    self.dictionary = {}
    self.counter = 0
    
    self.PLACEHOLDER_MARKER_PLACEHOLDER_STRING = (
      self.create_placeholder_store_markup(self.PLACEHOLDER_MARKER)
    )
  
  def create_placeholder(self):
    """
    Create a placeholder string for the current counter value.
    """
    
    placeholder_string = (
      f'{self.PLACEHOLDER_MARKER}{self.counter}{self.PLACEHOLDER_MARKER}'
    )
    
    return placeholder_string
  
  def create_placeholder_store_markup(self, markup_portion):
    """
    Create a placeholder string for, and store, a markup portion.
    Then increment the counter.
    
    Existing placeholder strings in the markup portion
    are substituted with their corresponding markup portions
    before being stored in the dictionary.
    This ensures that all markup portions in the dictionary
    are free of placeholder strings.
    """
    
    placeholder_string = self.create_placeholder()
    self.dictionary[placeholder_string] = (
      self.replace_placeholders_with_markup(markup_portion)
    )
    self.counter += 1
    
    return placeholder_string
  
  def replace_marker_with_placeholder(self, string):
    """
    Replace the placeholder marker X with its own placeholder string.
    This ensures that actual occurrences of X in a string
    are not confounded with the placeholder strings X{n}X.
    """
    
    string = re.sub(
      self.PLACEHOLDER_MARKER,
      self.PLACEHOLDER_MARKER_PLACEHOLDER_STRING,
      string
    )
    
    return string
  
  def replace_placeholders_with_markup(self, string):
    """
    Replace all placeholder strings with their markup portions.
    X{n}X becomes its markup portion as stored in the dictionary.
    """
    
    string = re.sub(
      self.PLACEHOLDER_STRING_COMPILED_REGEX,
      functools.partial(process_match_by_ordinary_dictionary, self.dictionary),
      string
    )
    
    return string


PROPERTY_NAME_REGEX = '[a-zA-Z0-9-]+'


class PropertyStorage:
  """
  Property storage class.
  
  Properties are specified in the content of the preamble,
  which is split according to leading occurrences of %{property name}
  (i.e. occurrences preceded only by whitespace on their lines),
  where {property name} may only contain letters, digits, and hyphens.
  Property specifications end at the next property specification,
  or at the end of the (preamble) content being split.
  
  Properties are stored in a dictionary of ordinary replacements,
  with
    KEYS: %{property name}
    VALUES: {property markup}
  
  These may be referenced by writing %{property name},
  called a property string, anywhere else in the document.
  """
  
  def __init__(self):
    """
    Initialise property storage.
    """
    
    self.dictionary = {}
  
  def store_property_markup(self, property_name, property_markup):
    """
    Store markup for a property.
    """
    
    property_string = f'%{property_name}'
    self.dictionary[property_string] = property_markup
  
  def get_property_markup(self, property_name):
    """
    Get property markup for a property.
    """
    
    property_string = f'%{property_name}'
    property_markup = self.dictionary[property_string]
    property_markup = (
      self.replace_property_strings_with_markup(property_markup)
    )
    
    return property_markup
  
  def read_specifications_store_markup(self, preamble_content):
    """
    Read and store property specifications.
    """
    
    re.sub(
      f'''
        {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
        %
        (?P<property_name>  {PROPERTY_NAME_REGEX}  )
          (?P<property_markup>
            (
              (?!
                {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
                %
                {PROPERTY_NAME_REGEX}
              )
              {ANY_CHARACTER_REGEX}
            ) *
          )
      ''',
      self.process_specification_match,
      preamble_content,
      flags=re.MULTILINE|re.VERBOSE
    )
  
  def process_specification_match(self, match_object):
    """
    Process a single property-specification match object.
    """
    
    property_name = match_object.group('property_name')
    
    property_markup = match_object.group('property_markup')
    property_markup = de_indent(property_markup)
    property_markup = property_markup.strip()
    
    self.store_property_markup(property_name, property_markup)
    
    return ''
  
  def replace_property_strings_with_markup(self, string):
    """
    Replace all property strings with their markup.
    """
    
    string = re.sub(
      f'%{PROPERTY_NAME_REGEX}',
      functools.partial(process_match_by_ordinary_dictionary, self.dictionary),
      string
    )
    
    return string


class RegexReplacementStorage:
  """
  Regex replacement storage class.
  
  Regex replacements are specified in the form
  {% {pattern} % {replacement} %},
  and are stored in a dictionary with
    KEYS: {pattern}
    VALUES: {replacement}
  """
  
  def __init__(self):
    """
    Initialise regex replacement storage.
    """
    
    self.dictionary = {}
  
  def store_replacement(self, pattern, replacement):
    """
    Store a replacement.
    """
    
    self.dictionary[pattern] = replacement
  
  def replace_patterns(self, string):
    """
    Replace all patterns with their replacements.
    """
    
    string = replace_by_regex_dictionary(self.dictionary, string)
    
    return string


class OrdinaryReplacementStorage:
  """
  Ordinary replacement storage class.
  
  Ordinary replacements are specified in the form
  {: {pattern} : {replacement} :},
  and are stored in a dictionary with
    KEYS: {pattern}
    VALUES: {replacement}
  """
  
  def __init__(self):
    """
    Initialise ordinary replacement storage.
    """
    
    self.dictionary = {}
  
  def store_replacement(self, pattern, replacement):
    """
    Store a replacement.
    """
    
    self.dictionary[pattern] = replacement
  
  def replace_patterns(self, string):
    """
    Replace all patterns with their replacements.
    """
    
    string = replace_by_ordinary_dictionary(self.dictionary, string)
    
    return string


class ImageDefinitionStorage:
  """
  Image definition storage class.
  
  Definitions for reference-style images are specified in the form
  @@![{label}]{[class]}↵ {src} [title] @@[width],
  and are stored in a dictionary with
    KEYS: {label}
    VALUES: {attributes}
  where {attributes} is the sequence of attributes
  built from [class], {src}, [title], and [width].
  {label} is case insensitive,
  and is stored canonically in lower case.
  """
  
  def __init__(self):
    """
    Initialise image definition storage.
    """
    
    self.dictionary = {}
  
  def store_definition_attributes(self,
    placeholder_storage, label, class_, src, title, width
  ):
    """
    Store attributes for an image definition.
    """
    
    label = label.lower()
    
    class_attribute = build_html_attribute(
      placeholder_storage, 'class', class_
    )
    src_attribute = build_html_attribute(
      placeholder_storage, 'src', src
    )
    title_attribute = build_html_attribute(
      placeholder_storage, 'title', title
    )
    width_attribute = build_html_attribute(
      placeholder_storage, 'width', width
    )
    
    attributes = (
      class_attribute + src_attribute + title_attribute + width_attribute
    )
    
    self.dictionary[label] = attributes
  
  def get_definition_attributes(self, label):
    """
    Get attributes for an image definition.
    
    If no image is defined for the given label, return None.
    """
    
    label = label.lower()
    
    attributes = self.dictionary.get(label, None)
    
    return attributes


class LinkDefinitionStorage:
  """
  Link definition storage class.
  
  Definitions for reference-style links are specified in the form
  @@[{label}]{[class]}↵ {href} [title] @@,
  and are stored in a dictionary with
    KEYS: {label}
    VALUES: {attributes}
  where {attributes} is the sequence of attributes
  built from [class], {href}, and [title].
  {label} is case insensitive,
  and is stored canonically in lower case.
  """
  
  def __init__(self):
    """
    Initialise link definition storage.
    """
    
    self.dictionary = {}
  
  def store_definition_attributes(self,
    placeholder_storage, label, class_, href, title
  ):
    """
    Store attributes for a link definition.
    """
    
    label = label.lower()
    
    class_attribute = build_html_attribute(
      placeholder_storage, 'class', class_
    )
    href_attribute = build_html_attribute(
      placeholder_storage, 'href', href
    )
    title_attribute = build_html_attribute(
      placeholder_storage, 'title', title
    )
    
    attributes = class_attribute + href_attribute + title_attribute
    
    self.dictionary[label] = attributes
  
  def get_definition_attributes(self, label):
    """
    Get attributes for a link definition.
    
    If no link is defined for the given label, return None.
    """
    
    label = label.lower()
    
    attributes = self.dictionary.get(label, None)
    
    return attributes


################################################################
# Literals
################################################################


def process_literals(placeholder_storage, markup):
  """
  Process CMD literals (! {content} !).
  
  (! {content} !) becomes {content}, literally,
  with HTML syntax-character escaping
  and de-indentation for {content}.
  Whitespace around {content} is stripped.
  For {content} containing one or more consecutive exclamation marks
  followed by a closing round bracket,
  use a longer run of exclamation marks in the delimiters,
  e.g. "(!! (! blah !) !!)" for "(! blah !)".
  """
  
  markup = re.sub(
    fr'''
      \(
        (?P<exclamation_marks>  [!] +  )
          (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=exclamation_marks)
      \)
    ''',
    functools.partial(process_literal_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_literal_match(placeholder_storage, match_object):
  """
  Process a single CMD-literal match object.
  """
  
  content = match_object.group('content')
  content = de_indent(content)
  content = content.strip()
  content = escape_html_syntax_characters(content)
  
  literal = content
  literal = placeholder_storage.create_placeholder_store_markup(literal)
  
  return literal


################################################################
# Display code
################################################################


def process_display_code(placeholder_storage, markup):
  """
  Process display code ``[id]{[class]}↵ {content} ``.
  The delimiting backticks must be the first
  non-whitespace characters on their lines.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  
  ``[id]{[class]}↵ {content} `` becomes
  <pre id="[id]" class="[class]"><code>{content}</code></pre>,
  with HTML syntax-character escaping
  and de-indentation for {content}.
  For {content} containing two or more consecutive backticks
  which are not protected by CMD literals,
  use a longer run of backticks in the delimiters.
  """
  
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<backticks>  [`] {{2,}}  )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=backticks)
    ''',
    functools.partial(process_display_code_match, placeholder_storage),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return markup


def process_display_code_match(placeholder_storage, match_object):
  """
  Process a single display-code match object.
  """
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  content = match_object.group('content')
  content = de_indent(content)
  content = escape_html_syntax_characters(content)
  
  display_code = (
    f'<pre{id_attribute}{class_attribute}><code>{content}</code></pre>'
  )
  display_code = (
    placeholder_storage.create_placeholder_store_markup(display_code)
  )
  
  return display_code


################################################################
# Inline code
################################################################


def process_inline_code(placeholder_storage, markup):
  """
  Process inline code ` {content} `.
  
  ` {content} ` becomes <code>{content}</code>,
  with HTML syntax-character escaping for {content}.
  Whitespace around {content} is stripped.
  For {content} containing one or more consecutive backticks
  which are not protected by CMD literals,
  use a longer run of backticks in the delimiters.
  """
  
  markup = re.sub(
    f'''
      (?P<backticks>  [`] +  )
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      (?P=backticks)
    ''',
    functools.partial(process_inline_code_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_inline_code_match(placeholder_storage, match_object):
  """
  Process a single inline-code match object.
  """
  
  content = match_object.group('content')
  content = content.strip()
  content = escape_html_syntax_characters(content)
  
  inline_code = f'<code>{content}</code>'
  inline_code = (
    placeholder_storage.create_placeholder_store_markup(inline_code)
  )
  
  return inline_code


################################################################
# Comments
################################################################


def process_comments(markup):
  """
  Process comments <!-- {content} -->.
  
  <!-- {content} --> is removed,
  along with any preceding horizontal whitespace.
  Although comments are weaker than literals and code
  they may still be used to remove them, e.g.
    (! A <!-- B --> !) becomes A <!-- B --> with HTML escaping,
  but
    <!-- A (! B !) --> is removed entirely.
  In this sense they are stronger than literals and code.
  Therefore, while the comment syntax is not placeholder-protected,
  it is nevertheless accorded this status.
  """
  
  markup = re.sub(
    f'''
      {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} *
      <!
        [-] {{2}}
          (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
        [-] {{2}}
      >
    ''',
    '',
    markup,
    flags=re.VERBOSE
  )
  
  return markup


################################################################
# Display maths
################################################################


def process_display_maths(placeholder_storage, markup):
  r"""
  Process display maths $$[id]{[class]}↵ {content} $$.
  The delimiting dollar signs must be the first
  non-whitespace characters on their lines.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  
  $$[id]{[class]}↵ {content} $$ becomes
  <div id="[id]" class="js-maths [class]">{content}</div>,
  with HTML syntax-character escaping
  and de-indentation for {content}.
  For {content} containing two or more consecutive dollar signs
  which are not protected by CMD literals,
  e.g. \text{\$$d$, i.e.~$d$~dollars},
  use a longer run of dollar signs in the delimiters.
  
  This is to be used with some sort of JavaScript code
  which renders equations based on the class "js-maths".
  If MathML support becomes widespread in the future,
  this ought to be replaced with some MathML converter.
  """
  
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<dollar_signs>  [$] {{2,}}  )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=dollar_signs)
    ''',
    functools.partial(process_display_maths_match, placeholder_storage),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return markup


def process_display_maths_match(placeholder_storage, match_object):
  """
  Process a single display-maths match object.
  """
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  if class_ is None:
    class_ = ''
  class_ = class_.strip()
  class_attribute = build_html_attribute(
    placeholder_storage, 'class', f'js-maths {class_}'
  )
  
  content = match_object.group('content')
  content = de_indent(content)
  content = escape_html_syntax_characters(content)
  
  display_maths = f'<div{id_attribute}{class_attribute}>{content}</div>'
  display_maths = (
    placeholder_storage.create_placeholder_store_markup(display_maths)
  )
  
  return display_maths


################################################################
# Inline maths
################################################################


def process_inline_maths(placeholder_storage, markup):
  r"""
  Process inline maths $ {content} $.
  
  ` {content} ` becomes <span class="js-maths">{content}</span>,
  with HTML syntax-character escaping for {content}.
  Whitespace around {content} is stripped.
  For {content} containing one or more consecutive dollar signs
  which are not protected by CMD literals,
  e.g. \text{$x = \infinity$ is very big},
  use a longer run of dollar signs in the delimiters.
  
  This is to be used with some sort of JavaScript code
  which renders equations based on the class "js-maths".
  If MathML support becomes widespread in the future,
  this ought to be replaced with some MathML converter.
  """
  
  markup = re.sub(
    f'''
      (?P<dollar_signs> [$] +  )
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      (?P=dollar_signs)
    ''',
    functools.partial(process_inline_maths_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_inline_maths_match(placeholder_storage, match_object):
  """
  Process a single inline-maths match object.
  """
  
  content = match_object.group('content')
  content = content.strip()
  content = escape_html_syntax_characters(content)
  
  inline_maths = f'<span class="js-maths">{content}</span>'
  inline_maths = (
    placeholder_storage.create_placeholder_store_markup(inline_maths)
  )
  
  return inline_maths


################################################################
# Inclusions
################################################################


def process_inclusions(placeholder_storage, markup):
  r"""
  Process inclusions (+ {file name} +).
  
  (+ {file name} +) includes the content of the file {file name}.
  For {file name} containing one or more consecutive plus signs
  followed by a closing round bracket,
  use a longer run of plus signs in the delimiters.
  
  All of the syntax above (CMD literals through to inline maths)
  is processed.
  Unlike nested \input in LaTeX,
  nested inclusions are not processed.
  """
  
  markup = re.sub(
    fr'''
      \(
        (?P<plus_signs>  [+] +  )
          (?P<file_name>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=plus_signs)
      \)
    ''',
    functools.partial(process_inclusion_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_inclusion_match(placeholder_storage, match_object):
  """
  Process a single inclusion match object.
  """
  
  file_name = match_object.group('file_name')
  file_name = file_name.strip()
  
  with open(file_name, 'r', encoding='utf-8') as file:
    content = file.read()
  
  content = placeholder_storage.replace_marker_with_placeholder(content)
  
  content = process_literals(placeholder_storage, content)
  content = process_display_code(placeholder_storage, content)
  content = process_inline_code(placeholder_storage, content)
  content = process_comments(content)
  content = process_display_maths(placeholder_storage, content)
  content = process_inline_maths(placeholder_storage, content)
  
  inclusion = content
  
  return inclusion


################################################################
# Regex replacements
################################################################


def process_regex_replacements(
  placeholder_storage, regex_replacement_storage, markup
):
  """
  Process regex replacements {% {pattern} % {replacement} %}.
  Python regex syntax is used,
  and the flags re.MULTILINE and re.VERBOSE are enabled.
  
  Whitespace around {pattern} and {replacement} is stripped.
  For {pattern} or {replacement} containing
  one or more consecutive percent signs,
  use a longer run of percent signs in the delimiters.
  For {pattern} matching any of the syntax above,
  which should not be processed using that syntax, use CMD literals.
  
  All regex replacement specifications are read and stored
  using the regex replacement storage class
  before being applied in order.
  If the same pattern is specified more than once,
  the latest specification shall prevail.
  
  WARNING:
    Malicious or careless user-defined regex replacements
    will break the normal CMD syntax.
    To avoid breaking placeholder storage,
    do not use replacements to alter placeholder strings.
    To avoid breaking properties,
    do not use replacements to alter property strings.
  """
  
  markup = re.sub(
    fr'''
      \{{
        (?P<percent_signs>  [%] +  )
          (?P<pattern>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=percent_signs)
          (?P<replacement>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=percent_signs)
      \}}
    ''',
    functools.partial(process_regex_replacement_match,
      placeholder_storage,
      regex_replacement_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  markup = regex_replacement_storage.replace_patterns(markup)
  
  return markup


def process_regex_replacement_match(
  placeholder_storage, regex_replacement_storage, match_object
):
  """
  Process a single regex-replacement match object.
  """
  
  pattern = match_object.group('pattern')
  pattern = pattern.strip()
  pattern = placeholder_storage.replace_placeholders_with_markup(pattern)
  
  replacement = match_object.group('replacement')
  replacement = replacement.strip()
  
  regex_replacement_storage.store_replacement(pattern, replacement)
  
  return ''


################################################################
# Ordinary replacements
################################################################


def process_ordinary_replacements(ordinary_replacement_storage, markup):
  """
  Process ordinary replacements {: {pattern} : {replacement} :}.
  
  Whitespace around {pattern} and {replacement} is stripped.
  For {pattern} or {replacement} containing
  one or more consecutive colons,
  use a longer run of colons in the delimiters.
  
  All ordinary replacement specifications are read and stored
  using the ordinary replacement storage class
  before being applied in order.
  If the same pattern is specified more than once,
  the latest specification shall prevail.
  
  WARNING:
    Malicious or careless user-defined ordinary replacements
    will break the normal CMD syntax.
    To avoid breaking placeholder storage,
    do not use replacements to alter placeholder strings.
    To avoid breaking properties,
    do not use replacements to alter property strings.
  """
  
  markup = re.sub(
    fr'''
      \{{
        (?P<colons>  [:] +  )
          (?P<pattern>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=colons)
          (?P<replacement>  {ANYTHING_MINIMAL_REGEX}  )
        (?P=colons)
      \}}
    ''',
    functools.partial(process_ordinary_replacement_match,
      ordinary_replacement_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  markup = ordinary_replacement_storage.replace_patterns(markup)
  
  return markup


def process_ordinary_replacement_match(
  ordinary_replacement_storage, match_object
):
  """
  Process a single ordinary-replacement match object.
  """
  
  pattern = match_object.group('pattern')
  pattern = pattern.strip()
  
  replacement = match_object.group('replacement')
  replacement = replacement.strip()
  
  ordinary_replacement_storage.store_replacement(pattern, replacement)
  
  return ''


################################################################
# Preamble
################################################################


def process_preamble(
  placeholder_storage, property_storage, cmd_name, markup
):
  """
  Process the preamble %%↵ {content} %%.
  The delimiting percent signs must be the first
  non-whitespace characters on their lines.
  
  %%↵ {content} %% becomes the HTML preamble,
  i.e. everything from <!DOCTYPE html> through to <body>.
  {content} is split into property specifications
  according to leading occurrences of %{property name}
  (i.e. occurrences preceded only by whitespace on their lines),
  where {property name} may only contain letters, digits, and hyphens.
  Property specifications end at the next property specification,
  or at the end of the (preamble) content being split.
  
  Each property is then stored using the property storage class
  and may be referenced by writing %{property name},
  called a property string, anywhere else in the document.
  
  If the same property is specified more than once,
  the latest specification shall prevail.
  
  For {content} containing two or more consecutive percent signs
  which are not protected by CMD literals,
  use a longer run of percent signs in the delimiters.
  
  Only the first occurrence in the markup is processed.
  
  The following properties, called original properties,
  are accorded special treatment.
  If omitted from a preamble,
  they take the default values shown beside them:
    %lang en
    %title Title
    %title-suffix
    %author
    %date-created yyyy-mm-dd
    %date-modified yyyy-mm-dd
    %resources
    %description
    %css
    %onload-js
    %footer-copyright-remark
    %footer-remark
  
  The following properties, called derived properties,
  are computed based on the supplied original properties:
    %html-lang-attribute
    %meta-element-author
    %meta-element-description
    %title-element
    %style-element
    %body-onload-attribute
    %year-created
    %year-modified
    %year-modified-next
    %footer-element
    %url
  In particular, the year properties are taken
  from the first 4 characters of the appropriate date properties.
  (NOTE: This will break come Y10K.)
  The property %url is computed from the CMD-name argument.
  It is assumed that the current directory
  is the root directory of the website being built,
  so that %url is the URL of the resulting page relative to root.
  """
  
  markup, preamble_count = re.subn(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<percent_signs>  [%] {{2,}}  )
      \n
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=percent_signs)
    ''',
    functools.partial(process_preamble_match,
      placeholder_storage, property_storage, cmd_name
    ),
    markup,
    count=1,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  if preamble_count > 0:
    
    markup = f'''\
      <!DOCTYPE html>
      <html%html-lang-attribute>
        <head>
          <meta charset="utf-8">
          %meta-element-author
          %meta-element-description
          %resources
          %title-element
          %style-element
        </head>
        <body%body-onload-attribute>
          {markup}
        </body>
      </html>
    '''
    markup = property_storage.replace_property_strings_with_markup(markup)
  
  return markup


DEFAULT_ORIGINAL_PROPERTY_SPECIFICATIONS = '''
  %lang en
  %title Title
  %title-suffix
  %author
  %date-created yyyy-mm-dd
  %date-modified yyyy-mm-dd
  %resources
  %description
  %css
  %onload-js
  %footer-copyright-remark
  %footer-remark
'''


def process_preamble_match(
  placeholder_storage, property_storage, cmd_name, match_object
):
  """
  Process a single preamble match object.
  
  (1) The default property specifications
      for original properties are prepended as defaults
      (which will be overwritten by the supplied properties).
  (2) The properties are stored.
  (3) The derived properties are computed and stored.
  (4) Finally the preamble is removed.
  """
  
  content = match_object.group('content')
  content = DEFAULT_ORIGINAL_PROPERTY_SPECIFICATIONS + content
  
  property_storage.read_specifications_store_markup(content)
  
  # Derived property %html-lang-attribute
  lang = property_storage.get_property_markup('lang')
  html_lang_attribute = build_html_attribute(
    placeholder_storage, 'lang', lang
  )
  property_storage.store_property_markup(
    'html-lang-attribute', html_lang_attribute
  )
  
  # Derived property %meta-element-author
  author = property_storage.get_property_markup('author')
  author = escape_html_attribute_value(placeholder_storage, author)
  if author == '':
    meta_element_author = ''
  else:
    meta_element_author = f'<meta name="author" content="{author}">'
  property_storage.store_property_markup(
    'meta-element-author', meta_element_author
  )
  
  # Derived property %meta-element-description
  description = property_storage.get_property_markup('description')
  description = escape_html_attribute_value(placeholder_storage, description)
  if description == '':
    meta_element_description = ''
  else:
    meta_element_description = (
      f'<meta name="description" content="{description}">'
    )
  property_storage.store_property_markup(
    'meta-element-description', meta_element_description
  )
  
  # Derived property %title-element
  title = property_storage.get_property_markup('title')
  title_suffix = property_storage.get_property_markup('title-suffix')
  title_element = f'<title>{title}{title_suffix}</title>'
  property_storage.store_property_markup('title-element', title_element)
  
  # Derived property %style-element
  css = property_storage.get_property_markup('css')
  if css == '':
    style_element = ''
  else:
    style_element = f'<style>{css}</style>'
  property_storage.store_property_markup(
    'style-element', style_element
  )
  
  # Derived property %body-onload-attribute
  onload_js = property_storage.get_property_markup('onload-js')
  onload_js = escape_html_attribute_value(placeholder_storage, onload_js)
  if onload_js == '':
    body_onload_attribute = ''
  else:
    body_onload_attribute = f' onload="{onload_js}"'
  property_storage.store_property_markup(
    'body-onload-attribute', body_onload_attribute
  )
  
  # Derived property %year-created
  date_created = property_storage.get_property_markup('date-created')
  year_created = date_created[:4]
  property_storage.store_property_markup(
    'year-created', year_created
  )
  
  # Derived property %year-modified
  date_modified = property_storage.get_property_markup('date-modified')
  year_modified = date_modified[:4]
  property_storage.store_property_markup(
    'year-modified', year_modified
  )
  
  # Derived property %year-modified-next
  try:
    year_modified_next = f'{int(year_modified) + 1}'
  except ValueError:
    year_modified_next = '????'
  property_storage.store_property_markup(
    'year-modified-next', year_modified_next
  )
  
  # Derived property %footer-element
  year_range = year_created
  try:
    if int(year_modified) > int(year_created):
      year_range += f'--{year_modified}'
  except ValueError:
    pass
  if author == '':
    author_markup = ''
  else:
    author_markup = f'~{author}'
  footer_copyright_remark = (
    property_storage.get_property_markup('footer-copyright-remark')
  )
  if footer_copyright_remark == '':
    footer_copyright_remark_markup = ''
  else:
    footer_copyright_remark_markup = f', {footer_copyright_remark}'
  footer_remark = property_storage.get_property_markup('footer-remark')
  if footer_remark == '':
    footer_remark_markup = ''
  else:
    footer_remark_markup = fr'''
      \\
      {footer_remark}
    '''
  footer_element = f'''
    <footer>
      ©~{year_range}{author_markup}{footer_copyright_remark_markup}.
      {footer_remark_markup}
    </footer>
  '''
  property_storage.store_property_markup(
    'footer-element', footer_element
  )
  
  # Derived property %url
  url = f'{cmd_name}.html'
  url = re.sub('(^|(?<=/))index[.]html', '', url)
  property_storage.store_property_markup(
    'url', url
  )
  
  return ''


################################################################
# Protected elements
################################################################


PROTECTED_ELEMENT_TAG_NAME_REGEX = '(script|style)'


def process_protected_elements(placeholder_storage, markup):
  """
  Process protected elements <script> and <style>.
  
  These elements are protected from any further processing
  (i.e. kept as is) using the placeholder storage class.
  """
  
  markup = re.sub(
    f'''
      <
        (?P<tag_name>  {PROTECTED_ELEMENT_TAG_NAME_REGEX}  )
      >
        {ANYTHING_MINIMAL_REGEX}
      </
        (?P=tag_name)
      >
    ''',
    functools.partial(process_protected_element_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_protected_element_match(placeholder_storage, match_object):
  """
  Process a single protected-element match object.
  """
  
  match_string = match_object.group()
  
  protected_element = match_string
  protected_element = (
    placeholder_storage.create_placeholder_store_markup(protected_element)
  )
  
  return protected_element


################################################################
# Headings
################################################################


def process_headings(placeholder_storage, markup):
  """
  Process headings #[id] {content} #.
  The opening hash must be the first
  non-whitespace character of its line.
  
  #[id] {content} # becomes <h1 id="[id]">{content}</h1>.
  Whitespace around {content} is stripped.
  For <h2> to <h6>, use 2 to 6 delimiting hashes respectively.
  For {content} containing the delimiting number of
  or more consecutive hashes, use CMD literals.
  """
  
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<hashes>
        [#] {{1,6}}
        (?!  [#]  )
      )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
      [\s] +
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      (?P=hashes)
    ''',
    functools.partial(process_heading_match, placeholder_storage),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return markup


def process_heading_match(placeholder_storage, match_object):
  """
  Process a single heading match object.
  """
  
  hashes = match_object.group('hashes')
  level = len(hashes)
  tag_name = f'h{level}'
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  content = match_object.group('content')
  content = content.strip()
  
  heading = f'<{tag_name}{id_attribute}>{content}</{tag_name}>'
  
  return heading


################################################################
# Blocks
################################################################


BLOCK_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY = {
  '-': 'p',
  '|': 'div',
  '"': 'blockquote',
  '=': 'ul',
  '+': 'ol',
}
BLOCK_DELIMITER_CHARACTERS_STRING = (
  ''.join(BLOCK_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY.keys())
)
BLOCK_DELIMITER_CHARACTER_REGEX = f'[{BLOCK_DELIMITER_CHARACTERS_STRING}]'

LIST_TAG_NAMES = ['ul', 'ol']


def process_blocks(placeholder_storage, markup):
  """
  Process blocks cccc[id]{[class]}↵ {content} cccc.
  The delimiting characters (c) must be the first
  non-whitespace characters on their lines.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  
  The following delimiting characters (c) are used:
    Non-lists
      -  <p>
      |  <div>
      "  <blockquote>
    Lists
      =  <ul>
      +  <ol>
  cccc[id]{[class]}↵ {content} cccc becomes
  <{tag name} id="[id]" class="[class]">↵{content}</{tag name}>.
  For {content} containing four or more
  consecutive delimiting characters
  which are not protected by CMD literals,
  use a longer run of delimiting characters in the delimiters.
  
  A recursive call is used to process nested blocks.
  
  For list blocks, {content} is split into list items <li>
  according to list item processing.
  """
  
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<delimiter>
        (?P<delimiter_character>  {BLOCK_DELIMITER_CHARACTER_REGEX}  )
        (?P=delimiter_character) {{3,}}
      )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=delimiter)
    ''',
    functools.partial(process_block_match, placeholder_storage),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return markup


def process_block_match(placeholder_storage, match_object):
  """
  Process a single block match object.
  """
  
  delimiter_character = match_object.group('delimiter_character')
  tag_name = (
    BLOCK_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY[delimiter_character]
  )
  block_is_list = tag_name in LIST_TAG_NAMES
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  content = match_object.group('content')
  
  # Process nested blocks
  content = process_blocks(placeholder_storage, content)
  
  if block_is_list:
    content = process_list_items(placeholder_storage, content)
  
  block = (
    f'<{tag_name}{id_attribute}{class_attribute}>\n{content}</{tag_name}>'
  )
  
  return block


LIST_ITEM_DELIMITER_REGEX = '([*+-]|[0-9]+[.])'


def process_list_items(placeholder_storage, content):
  """
  Process list items.
  
  Content is split into list items <li>
  according to leading occurrences of Y[id]{[class]}
  (i.e. occurrences preceded only by whitespace on their lines),
  with the following delimiters (Y):
    *
    +
    -
    1. (or any run of digits followed by a full stop)
  List items end at the next list item,
  or at the end of the content being split.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  """
  
  content = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      {LIST_ITEM_DELIMITER_REGEX}
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
      [\s] +
      (?P<list_item_content>
        (
          (?!
            {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
            {LIST_ITEM_DELIMITER_REGEX}
          )
          {ANY_CHARACTER_REGEX}
        ) *
      )
    ''',
    functools.partial(process_list_item_match, placeholder_storage),
    content,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return content


def process_list_item_match(placeholder_storage, match_object):
  """
  Process a single list-item match object.
  """
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  list_item_content = match_object.group('list_item_content')
  list_item_content = list_item_content.strip()
  
  list_item = f'''
    <li{id_attribute}{class_attribute}>{list_item_content}
    </li>
  '''
  
  return list_item


################################################################
# Tables
################################################################


TABLE_CELL_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY = {
  ';': 'th',
  ',': 'td',
}
TABLE_CELL_DELIMITER_CHARACTERS_STRING = (
  ''.join(TABLE_CELL_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY.keys())
)
TABLE_CELL_DELIMITER_CHARACTER_REGEX = (
  f'[{TABLE_CELL_DELIMITER_CHARACTERS_STRING}]'
)


TABLE_ROW_DELIMITER_CHARACTER_REGEX = '/'


TABLE_PART_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY = {
  '^': 'thead',
  '~': 'tbody',
  '_': 'tfoot',
}
TABLE_PART_DELIMITER_CHARACTERS_STRING = (
  ''.join(TABLE_PART_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY.keys())
)
TABLE_PART_DELIMITER_CHARACTER_REGEX = (
  f'[{re.escape(TABLE_PART_DELIMITER_CHARACTERS_STRING)}]'
)


def process_tables(placeholder_storage, markup):
  """
  Process tables ''''[id]{[class]}↵ {content} ''''.
  The delimiting apostrophes must be the first
  non-whitespace characters on their lines.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  
  ''''[id]{[class]}↵ {content} '''' becomes
  <table id="[id]" class="[class]">↵{content}</table>.
  For {content} containing four or more consecutive apostrophes
  which are not protected by CMD literals,
  use a longer run of apostrophes in the delimiters.
  
  A recursive call is used to process nested tables.
  
  {content} is
  (1) split into table cells <th>, <td>
      according to table cell processing,
  (2) split into table rows <tr>
      according to table row processing, and
  (3) split into table parts <thead>, <tbody>, <tfoot>
      according to table part processing.
  """
  
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<apostrophes>  ['] {{4,}}  )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (?P<content>  {ANYTHING_MINIMAL_REGEX}  )
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=apostrophes)
    ''',
    functools.partial(process_table_match, placeholder_storage),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return markup


def process_table_match(placeholder_storage, match_object):
  """
  Process a single table match object.
  """
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  content = match_object.group('content')
  
  # Process nested tables
  content = process_tables(placeholder_storage, content)
  
  content = process_table_cells(placeholder_storage, content)
  content = process_table_rows(placeholder_storage, content)
  content = process_table_parts(placeholder_storage, content)
  
  table = f'<table{id_attribute}{class_attribute}>\n{content}</table>'
  
  return table


def process_table_cells(placeholder_storage, content):
  """
  Process table cells.
  
  Content is split into table cells <th>, <td> according to
  leading occurrences of Z[id]{[class]}[[rowspan],[colspan]]
  (i.e. occurrences preceded only by whitespace on their lines),
  with the following delimiters (Z):
    ; (or any run of semicolons)  <th>
    , (or any run of commas)      <td>
  Table cells end at the next table cell, table row, or table part,
  or at the end of the content being split.
  Non-empty [rowspan] and [colspan] must consist of digits only.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  If [colspan] is empty, the comma before it may be omitted.
  If both [rowspan] and [colspan] are empty,
  the comma between them and the square brackets surrounding them
  may be omitted.
  """
  
  content = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<delimiter>
        (?P<delimiter_character>  {TABLE_CELL_DELIMITER_CHARACTER_REGEX}
        ) +
      )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (
          \[
            (?P<rowspan>  [0-9] *?  )
            (
              [,]
              (?P<colspan>  [0-9] *?  )
            ) ?
          \]
        ) ?
      (
        {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +
          |
        \n
      )
      (?P<table_cell_content>
        (
          (?!
            {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
            (
              {TABLE_CELL_DELIMITER_CHARACTER_REGEX}
                |
              {TABLE_ROW_DELIMITER_CHARACTER_REGEX}
                |
              {TABLE_PART_DELIMITER_CHARACTER_REGEX}
            ) +
          )
          {ANY_CHARACTER_REGEX}
        ) *
      )
    ''',
    functools.partial(process_table_cell_match, placeholder_storage),
    content,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return content


def process_table_cell_match(placeholder_storage, match_object):
  """
  Process a single table-cell match object.
  """
  
  delimiter_character = match_object.group('delimiter_character')
  tag_name = (
    TABLE_CELL_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY[delimiter_character]
  )
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  rowspan = match_object.group('rowspan')
  rowspan_attribute = (
    build_html_attribute(placeholder_storage, 'rowspan', rowspan)
  )
  
  colspan = match_object.group('colspan')
  colspan_attribute = (
    build_html_attribute(placeholder_storage, 'colspan', colspan)
  )
  
  table_cell_content = match_object.group('table_cell_content')
  table_cell_content = table_cell_content.strip()
  
  attributes = (
    id_attribute + class_attribute + rowspan_attribute + colspan_attribute
  )
  
  table_cell = f'<{tag_name}{attributes}>{table_cell_content}</{tag_name}>\n'
  
  return table_cell


def process_table_rows(placeholder_storage, content):
  """
  Process table rows.
  
  Content is split into table rows <tr>
  according to leading occurrences of /[id]{[class]}
  (i.e. occurrences preceded only by whitespace on their lines).
  The slash may instead be any run of slashes.
  Table rows end at the next table row or table part,
  or at the end of the content being split.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  """
  
  content = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<delimiter>  {TABLE_ROW_DELIMITER_CHARACTER_REGEX} +  )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
      (
        {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +
          |
        \n
      )
      (?P<table_row_content>
        (
          (?!
            {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
            (
              {TABLE_ROW_DELIMITER_CHARACTER_REGEX}
                |
              {TABLE_PART_DELIMITER_CHARACTER_REGEX}
            ) +
          )
          {ANY_CHARACTER_REGEX}
        ) *
      )
    ''',
    functools.partial(process_table_row_match, placeholder_storage),
    content,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return content


def process_table_row_match(placeholder_storage, match_object):
  """
  Process a single table-row match object.
  """
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  table_row_content = match_object.group('table_row_content')
  table_row_content = table_row_content.strip()
  
  table_row = f'''
    <tr{id_attribute}{class_attribute}>
      {table_row_content}
    </tr>
  '''
  
  return table_row


def process_table_parts(placeholder_storage, content):
  """
  Process table parts.
  
  Content is split into table parts <thead>, <tbody>, <tfoot>
  according to leading occurrences of Y[id]{[class]}
  (i.e. occurrences preceded only by whitespace on their lines),
  with the following delimiters (Y):
    ^ (or any run of carets)      <thead>
    ~ (or any run of tildes)      <tbody>
    _ (or any run of underscores) <tfoot>
  Table parts end at the next table part,
  or at the end of the content being split.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  """
  
  content = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<delimiter>
        (?P<delimiter_character>  {TABLE_PART_DELIMITER_CHARACTER_REGEX}
        ) +
      )
        (?P<id_>  {NOT_WHITESPACE_MINIMAL_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
      (
        {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +
          |
        \n
      )
      (?P<table_part_content>
        (
          (?!
            {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
            {TABLE_PART_DELIMITER_CHARACTER_REGEX} +
          )
          {ANY_CHARACTER_REGEX}
        ) *
      )
    ''',
    functools.partial(process_table_part_match, placeholder_storage),
    content,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  return content


def process_table_part_match(placeholder_storage, match_object):
  """
  Process a single table-part match object.
  """
  
  delimiter_character = match_object.group('delimiter_character')
  tag_name = (
    TABLE_PART_DELIMITER_CHARACTER_TAG_NAME_DICTIONARY[delimiter_character]
  )
  
  id_ = match_object.group('id_')
  id_attribute = build_html_attribute(placeholder_storage, 'id', id_)
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  table_part_content = match_object.group('table_part_content')
  table_part_content = table_part_content.strip()
  
  table_part = f'''
    <{tag_name}{id_attribute}{class_attribute}>
      {table_part_content}
    </{tag_name}>
  '''
  
  return table_part


################################################################
# Punctuation (or, escapes)
################################################################


PUNCTUATION_REPLACEMENT_DICTIONARY = {
  r'\/': '',
  r'\ /': ' ',
  r'\ ': ' ',
  r'\~': '~',
  '~': '&nbsp;',
  r'\0': '&numsp;',
  r'\,': '&thinsp;',
  r'\&': escape_html_syntax_characters('&'),
  r'\<': escape_html_syntax_characters('<'),
  r'\>': escape_html_syntax_characters('>'),
  '---': '—',
  '--': '–',
  r'\P': '¶',
  r'\#': '#',
  r'\[': '[',
  r'\]': ']',
  r'\(': '(',
  r'\)': ')',
  r'\*': '*',
  r'\_': '_',
}


def process_punctuation(placeholder_storage, markup):
  r"""
  Process punctuation.
    \\  becomes <br>
    \/  becomes the empty string
    \ / becomes   U+0020 SPACE
    \   becomes   U+0020 SPACE
    \~  becomes ~
    ~   becomes &nbsp;
    \0  becomes &numsp;
    \,  becomes &thinsp;
    \&  becomes &amp;
    \<  becomes &lt;
    \>  becomes &gt;
    --- becomes — U+2014 EM DASH
    --  becomes – U+2013 EN DASH
    \P  becomes ¶ U+00B6 PILCROW SIGN
    \#  becomes #
    \[  becomes [
    \]  becomes ]
    \(  becomes (
    \)  becomes )
    \*  becomes *
    \_  becomes _
  Most of these are based on LaTeX syntax.
  
  Some of the resulting strings (*, _) must be protected
  from further replacements using placeholder storage,
  but <br> resulting from \\ must not be protected so
  since whitespace before it will be removed later;
  for the remaining strings it does not matter.
  For simplicity in the implementation,
  <br> alone is left unprotected
  whilst everything else is protected.
  """
  
  markup = re.sub(r'\\\\', '<br>', markup)
  
  markup = replace_by_ordinary_dictionary(
    PUNCTUATION_REPLACEMENT_DICTIONARY, markup, placeholder_storage
  )
  
  return markup


################################################################
# Line continuations
################################################################


def process_line_continuations(markup):
  """
  Process backslash line continuations.
  """
  
  markup = re.sub(
    fr'''
      \\
      \n
      {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} *
    ''',
    '',
    markup,
    flags=re.VERBOSE
  )
  
  return markup


################################################################
# Images
################################################################


def process_images(placeholder_storage, image_definition_storage, markup):
  """
  Process images.
  
  Reference-style:
    DEFINITION: @@![{label}]{[class]}↵ {src} [title] @@[width]
    IMAGE: ![{alt}][[label]]
  The delimiting at signs in a definition must be the first
  non-whitespace characters on their lines.
  A single space may be included
  between [{alt}] and [[label]] in an image.
  The referencing strings {label} and [label] are case insensitive
  (this is handled by the image definition storage class).
  Non-empty [width] in a definition must consist of digits only.
  If [class] in a definition is empty,
  the curly brackets surrounding it may be omitted.
  If [label] in an image is empty,
  the square brackets surrounding it may be omitted,
  and {alt} is used as the label for that image.
  
  ![{alt}][[label]] becomes <img alt="alt"{attributes}>,
  where {attributes} is the sequence of attributes
  built from [class], {src}, [title], and [width].
  
  Whitespace around [label] is stripped.
  For definitions whose {label}, [class], {src}, or [title]
  contains two or more consecutive at signs
  which are not protected by CMD literals,
  use a longer run of at signs in the delimiters.
  For images whose {alt} or [label] contains
  one or more closing square brackets, use CMD literals.
  
  All (reference-style) image definitions are read and stored
  using the image definition storage class.
  If the same label (which is case insensitive)
  is specified more than once,
  the latest specification shall prevail.
  
  Inline-style:
    IMAGE: ![{alt}]( {src} [title] )
  (NOTE:
    Unlike John Gruber's markdown, [title] is not surrounded by quotes.
    If quotes are supplied to [title],
    they are automatically escaped as &quot;.
  )
  
  ![{alt}]( {src} [title] ) becomes
  <img alt="{alt}" src="{src}" title="[title]">.
  
  For {alt}, {src}, or [title] containing
  one or more closing square or round brackets, use CMD literals.
  """
  
  # Reference-style image definitions
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<at_signs>  [@] {{2,}})
        !
        \[
          (?P<label>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
        \]
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (
          [\s] *
          (?P<src>  {ANYTHING_MINIMAL_REGEX}  )
          (
            [\s] +?
            (?P<title>  {ANYTHING_MINIMAL_REGEX}  )
          ) ??
        ) ??
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=at_signs)
        (?P<width>  [0-9] *  )
    ''',
    functools.partial(process_image_definition_match,
      placeholder_storage,
      image_definition_storage
    ),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  # Reference-style images
  markup = re.sub(
    fr'''
      !
      \[
        (?P<alt>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
      \]
      [ ] ??
      (
        \[
          (?P<label>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
        \]
      ) ?
    ''',
    functools.partial(process_reference_image_match,
      placeholder_storage,
      image_definition_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  # Inline-style images
  markup = re.sub(
    fr'''
      !
      \[
        (?P<alt>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
      \]
      \(
        [\s] *
        (?P<src>  {ANYTHING_MINIMAL_REGEX}  )
        (
          [\s] +?
          (?P<title>  {ANYTHING_MINIMAL_REGEX}  )
        ) ??
      \)
    ''',
    functools.partial(process_inline_image_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_image_definition_match(
  placeholder_storage, image_definition_storage, match_object
):
  """
  Process a single image-definition match object.
  """
  
  label = match_object.group('label')
  class_ = match_object.group('class_')
  src = match_object.group('src')
  title = match_object.group('title')
  width = match_object.group('width')
  
  image_definition_storage.store_definition_attributes(
    placeholder_storage, label, class_, src, title, width
  )
  
  return ''


def process_reference_image_match(
  placeholder_storage, image_definition_storage, match_object
):
  """
  Process a single reference-style-image match object.
  
  If no image is defined for the given label,
  returned the entire string for the matched object as is.
  """
  
  alt = match_object.group('alt')
  alt_attribute = build_html_attribute(placeholder_storage, 'alt', alt)
  
  label = match_object.group('label')
  if label is None or label.strip() == '':
    label = alt
  
  attributes = image_definition_storage.get_definition_attributes(label)
  if attributes is None:
    match_string = match_object.group()
    return match_string
  
  image = f'<img{alt_attribute}{attributes}>'
  
  return image


def process_inline_image_match(placeholder_storage, match_object):
  """
  Process a single inline-style-image match object.
  """
  
  alt = match_object.group('alt')
  alt_attribute = build_html_attribute(placeholder_storage, 'alt', alt)
  
  src = match_object.group('src')
  src_attribute = build_html_attribute(placeholder_storage, 'src', src)
  
  title = match_object.group('title')
  title_attribute = build_html_attribute(placeholder_storage, 'title', title)
  
  image = f'<img{alt_attribute}{src_attribute}{title_attribute}>'
  
  return image


################################################################
# Links
################################################################


def process_links(placeholder_storage, link_definition_storage, markup):
  """
  Process links.
  
  Reference-style:
    DEFINITION: @@[{label}]{[class]}↵ {href} [title] @@
    LINK: [{content}][[label]]
  The delimiting at signs in a definition must be the first
  non-whitespace characters on their lines.
  A single space may be included
  between [{content}] and [[label]] in a link.
  The referencing strings {label} and [label] are case insensitive
  (this is handled by the link definition storage class).
  If [class] in a definition is empty,
  the curly brackets surrounding it may be omitted.
  If [label] in a link is empty,
  the square brackets surrounding it may be omitted,
  and {content} is used as the label for that link.
  
  [{content}][[label]] becomes <a{attributes}>{content}</a>,
  where {attributes} is the sequence of attributes
  built from [class], {href}, and [title].
  
  Whitespace around {content} and [label] is stripped.
  For definitions whose {label}, [class], {href}, or [title]
  contains two or more consecutive at signs
  which are not protected by CMD literals,
  use a longer run of at signs in the delimiters.
  For links whose {content} or [label] contains
  one or more closing square brackets, use CMD literals.
  
  All (reference-style) link definitions are read and stored
  using the link definition storage class.
  If the same label (which is case insensitive)
  is specified more than once,
  the latest specification shall prevail.
  
  Inline-style:
    LINK: [{content}]( {href} [title] )
  (NOTE:
    Unlike John Gruber's markdown, [title] is not surrounded by quotes.
    If quotes are supplied to [title],
    they are automatically escaped as &quot;.
  )
  
  [{content}]( {href} [title] ) becomes
  <a href="{href}" title="[title]">{content}</a>.
  
  Whitespace around {content} is stripped.
  For {content}, {href}, or [title] containing
  one or more closing square or round brackets, use CMD literals.
  """
  
  # Reference-style link definitions
  markup = re.sub(
    fr'''
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P<at_signs>  [@] {{2,}})
        \[
          (?P<label>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
        \]
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}} ?
        ) ?
      \n
        (
          [\s] *
          (?P<href>  {ANYTHING_MINIMAL_REGEX}  )
          (
            [\s] +?
            (?P<title>  {ANYTHING_MINIMAL_REGEX}  )
          ) ??
        ) ??
      {LEADING_HORIZONTAL_WHITESPACE_MAXIMAL_REGEX}
      (?P=at_signs)
    ''',
    functools.partial(process_link_definition_match,
      placeholder_storage,
      link_definition_storage
    ),
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  
  # Reference-style links
  markup = re.sub(
    fr'''
      \[
        (?P<content>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
      \]
      [ ] ??
      (
        \[
          (?P<label>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
        \]
      ) ?
    ''',
    functools.partial(process_reference_link_match, link_definition_storage),
    markup,
    flags=re.VERBOSE
  )
  
  # Inline-style links
  markup = re.sub(
    fr'''
      \[
        (?P<content>  {NOT_CLOSING_SQUARE_BRACKET_MINIMAL_REGEX}  )
      \]
      \(
        [\s] *
        (?P<href>  {ANYTHING_MINIMAL_REGEX}  )
        (
          [\s] +?
          (?P<title>  {ANYTHING_MINIMAL_REGEX}  )
        ) ??
      \)
    ''',
    functools.partial(process_inline_link_match, placeholder_storage),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_link_definition_match(
  placeholder_storage, link_definition_storage, match_object
):
  """
  Process a single link-definition match object.
  """
  
  label = match_object.group('label')
  class_ = match_object.group('class_')
  href = match_object.group('href')
  title = match_object.group('title')
  
  link_definition_storage.store_definition_attributes(
    placeholder_storage, label, class_, href, title
  )
  
  return ''


def process_reference_link_match(link_definition_storage, match_object):
  """
  Process a single reference-style-link match object.
  
  If no link is defined for the given label,
  returned the entire string for the matched object as is.
  """
  
  content = match_object.group('content')
  content = content.strip()
  
  label = match_object.group('label')
  if label is None or label.strip() == '':
    label = content
  
  attributes = link_definition_storage.get_definition_attributes(label)
  if attributes is None:
    match_string = match_object.group()
    return match_string
  
  link = f'<a{attributes}>{content}</a>'
  
  return link


def process_inline_link_match(placeholder_storage, match_object):
  """
  Process a single inline-style-link match object.
  """
  
  content = match_object.group('content')
  content = content.strip()
  
  href = match_object.group('href')
  href_attribute = build_html_attribute(placeholder_storage, 'href', href)
  
  title = match_object.group('title')
  title_attribute = build_html_attribute(placeholder_storage, 'title', title)
  
  link = f'<a{href_attribute}{title_attribute}>{content}</a>'
  
  return link


################################################################
# Inline semantics
################################################################


INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY = {
  '*': 'em',
  '**': 'strong',
  '_' : 'i',
  '__': 'b',
}
INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX = '[*_]'


def process_inline_semantics(placeholder_storage, markup):
  r"""
  Process inline semantics X{[class]} {content} X.
  {content} must be non-empty.
  If [class] is empty,
  the curly brackets surrounding it may be omitted.
  
  The following delimiters (X) are used:
    *   <em>
    **  <strong>
    _   <i>
    __  <b>
  X{[class]} {content} X (c or cc) becomes
  <{tag name} class="[class]">{content}</{tag name}>.
  Whitespace around {content} is stripped.
  For {content} containing one or more occurrences of c (* or _),
  use CMD literals or \* and \_.
  
  Separate patterns are required
  for the following groupings of delimiting characters (c)
  so that the processing is performed in this order:
    33    ccc{[inner class]} {inner content} ccc
    312   ccc{[inner class]} {inner content} c {outer content} cc
    321   ccc{[inner class]} {inner content} cc {outer content} c
    22    cc{[class]} {content} cc
    11    c{[class]} {content} c
  33 is effectively 312 with empty {outer content}.
  However, once such a pattern has been matched,
  only three cases need to be handled for the resulting match object:
    2-layer special (for 33)
      XY{[inner class]} {inner content} YX
    2-layer general (for 312, 321):
      XY{[inner class]} {inner content} Y {outer content} X
    1-layer (for 22, 11):
      X{[class]} {content} X
  
  Recursive calls are used to process nested inline semantics.
  """
  
  # 33
  markup = re.sub(
    fr'''
      (?P<delimiter>
        (?P<delimiter_character>
          {INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX}
        )
        (?P=delimiter_character) {{2}}
      )
        (
          \{{
            (?P<inner_class>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (?P<inner_content>
          (
            (?!  (?P=delimiter_character)  )
            {ANY_CHARACTER_REGEX}
          ) +?
        )
      (?P=delimiter)
    ''',
    functools.partial(process_inline_semantic_match_2_layer_special,
      placeholder_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  # 312
  markup = re.sub(
    fr'''
      (
        (?P<delimiter_character>
          {INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX}
        )
        (?P=delimiter_character) {{2}}
      )
        (
          \{{
            (?P<inner_class>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (?P<inner_content>
          (
            (?!  (?P=delimiter_character)  )
            {ANY_CHARACTER_REGEX}
          ) +?
        )
      (?P<inner_delimiter>  (?P=delimiter_character) {{1}}  )
        (?P<outer_content>
          (
            (?!  (?P=delimiter_character)  )
            {ANY_CHARACTER_REGEX}
          ) +?
        )
      (?P<outer_delimiter>  (?P=delimiter_character) {{2}}  )
    ''',
    functools.partial(process_inline_semantic_match_2_layer_general,
      placeholder_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  # 321
  markup = re.sub(
    fr'''
      (
        (?P<delimiter_character>
          {INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX}
        )
        (?P=delimiter_character) {{2}}
      )
        (
          \{{
            (?P<inner_class>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (?P<inner_content>
          (
            (?!  (?P=delimiter_character)  )
            {ANY_CHARACTER_REGEX}
          ) +?
        )
      (?P<inner_delimiter>  (?P=delimiter_character) {{2}}  )
        (?P<outer_content>
          (
            (?!  (?P=delimiter_character)  )
            {ANY_CHARACTER_REGEX}
          ) +?
        )
      (?P<outer_delimiter>  (?P=delimiter_character) {{1}}  )
    ''',
    functools.partial(process_inline_semantic_match_2_layer_general,
      placeholder_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  # 22
  markup = re.sub(
    fr'''
      (?P<delimiter>
        (?P<delimiter_character>
          {INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX}
        )
        (?P=delimiter_character)
      )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (?P<content>  {NON_EMPTY_MINIMAL_REGEX}  )
      (?P=delimiter)
    ''',
    functools.partial(process_inline_semantic_match_1_layer,
      placeholder_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  # 11
  markup = re.sub(
    f'''
      (?P<delimiter>  {INLINE_SEMANTIC_DELIMITER_CHARACTER_REGEX}  )
        (
          \{{
            (?P<class_>  {NOT_CLOSING_CURLY_BRACKET_MINIMAL_REGEX}  )
          \}}
        ) ?
        (?P<content>  {NON_EMPTY_MINIMAL_REGEX}  )
      (?P=delimiter)
    ''',
    functools.partial(process_inline_semantic_match_1_layer,
      placeholder_storage
    ),
    markup,
    flags=re.VERBOSE
  )
  
  return markup


def process_inline_semantic_match_2_layer_special(
  placeholder_storage, match_object
):
  """
  Process a single 2-layer special inline-semantic match object.
  """
  
  inner_class = match_object.group('inner_class')
  inner_class_attribute = build_html_attribute(
    placeholder_storage, 'class', inner_class
  )
  
  inner_content = match_object.group('inner_content')
  inner_content = inner_content.strip()
  
  # Process nested inline semantics (inner)
  inner_content = process_inline_semantics(placeholder_storage, inner_content)
  
  delimiter_character = match_object.group('delimiter_character')
  
  inner_delimiter = delimiter_character
  inner_tag_name = (
    INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY[inner_delimiter]
  )
  
  outer_delimiter = delimiter_character * 2
  outer_tag_name = (
    INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY[outer_delimiter]
  )
  
  inline_semantic = (
    f'<{outer_tag_name}>'
      f'<{inner_tag_name}{inner_class_attribute}>'
        f'{inner_content}'
      f'</{inner_tag_name}>'
    f'</{outer_tag_name}>'
  )
  
  return inline_semantic


def process_inline_semantic_match_2_layer_general(
  placeholder_storage, match_object
):
  """
  Process a single 2-layer general inline-semantic match object.
  """
  
  inner_class = match_object.group('inner_class')
  inner_class_attribute = build_html_attribute(
    placeholder_storage, 'class', inner_class
  )
  
  inner_content = match_object.group('inner_content')
  inner_content = inner_content.strip()
  
  # Process nested inline semantics (inner)
  inner_content = process_inline_semantics(placeholder_storage, inner_content)
  
  inner_delimiter = match_object.group('inner_delimiter')
  inner_tag_name = (
    INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY[inner_delimiter]
  )
  
  outer_content = match_object.group('outer_content')
  outer_content = outer_content.rstrip()
  
  outer_delimiter = match_object.group('outer_delimiter')
  outer_tag_name = (
    INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY[outer_delimiter]
  )
  
  # Process nested inline semantics (outer)
  outer_content = process_inline_semantics(placeholder_storage, outer_content)
  
  inline_semantic = (
    f'<{outer_tag_name}>'
      f'<{inner_tag_name}{inner_class_attribute}>'
        f'{inner_content}'
      f'</{inner_tag_name}>'
      f'{outer_content}'
    f'</{outer_tag_name}>'
  )
  
  return inline_semantic


def process_inline_semantic_match_1_layer(placeholder_storage, match_object):
  """
  Process a single 1-layer inline-semantic match object.
  """
  
  delimiter = match_object.group('delimiter')
  tag_name = INLINE_SEMANTIC_DELIMITER_TAG_NAME_DICTIONARY[delimiter]
  
  class_ = match_object.group('class_')
  class_attribute = build_html_attribute(placeholder_storage, 'class', class_)
  
  content = match_object.group('content')
  content = content.strip()
  
  # Process nested inline semantics
  content = process_inline_semantics(placeholder_storage, content)
  
  inline_semantic = f'<{tag_name}{class_attribute}>{content}</{tag_name}>'
  
  return inline_semantic


################################################################
# Whitespace
################################################################


def process_whitespace(markup):
  """
  Process whitespace.
  
  (1) Leading and trailing horizontal whitespace is removed.
  (2) Empty lines are removed.
      (In the implementation, consecutive newlines
      are normalised to a single newline.)
  (3) Whitespace before line break elements <br> is removed.
  (4) Whitespace for attributes is canonicalised:
      (a) a single space is used before the attribute name, and
      (b) no whitespace is used around the equals sign.
  """
  
  markup = re.sub(
    f'''
      ^  {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +
        |
      {HORIZONTAL_WHITESPACE_CHARACTER_REGEX} +  $
    ''',
    '',
    markup,
    flags=re.MULTILINE|re.VERBOSE
  )
  markup = re.sub(r'[\n]+', r'\n', markup)
  markup = re.sub(r'[\s]+(?=<br>)', '', markup)
  markup = re.sub(
    fr'''
      [\s] +?
        (?P<attribute_name>  [\S] +?  )
      [\s] *?
        =
      [\s] *?
        (?P<quoted_attribute_value>  "  {NOT_QUOTE_MINIMAL_REGEX}  ")
    ''',
    r' \g<attribute_name>=\g<quoted_attribute_value>',
    markup,
    flags=re.VERBOSE
  )
  
  return markup


################################################################
# Converter
################################################################


def cmd_to_html(cmd, cmd_name):
  """
  Convert CMD to HTML.
  
  The CMD-name argument determines the URL of the resulting page,
  which is stored in the property %url.
  It is assumed that the current directory
  is the root directory of the website being built,
  so that %url is the URL of the resulting page relative to root.
  
  During the conversion, the string is neither CMD nor HTML,
  and is referred to as "markup".
  """
  
  markup = cmd
  
  ################################################
  # START of conversion
  ################################################
  
  # Initialise placeholder storage
  placeholder_storage = PlaceholderStorage()
  markup = placeholder_storage.replace_marker_with_placeholder(markup)
  
  # Process placeholder-protected syntax
  # (i.e. syntax where the content is protected by a placeholder)
  markup = process_literals(placeholder_storage, markup)
  markup = process_display_code(placeholder_storage, markup)
  markup = process_inline_code(placeholder_storage, markup)
  markup = process_comments(markup)
  markup = process_display_maths(placeholder_storage, markup)
  markup = process_inline_maths(placeholder_storage, markup)
  markup = process_inclusions(placeholder_storage, markup)
  
  # Process regex replacements
  regex_replacement_storage = RegexReplacementStorage()
  markup = process_regex_replacements(
    placeholder_storage, regex_replacement_storage, markup
  )
  
  # Process ordinary replacements
  ordinary_replacement_storage = OrdinaryReplacementStorage()
  markup = process_ordinary_replacements(ordinary_replacement_storage, markup)
  
  # Process preamble
  property_storage = PropertyStorage()
  markup = process_preamble(
    placeholder_storage, property_storage, cmd_name, markup
  )
  
  # Process protected elements
  markup = process_protected_elements(placeholder_storage, markup)
  
  # Process headings
  markup = process_headings(placeholder_storage, markup)
  
  # Process blocks
  markup = process_blocks(placeholder_storage, markup)
  
  # Process tables
  markup = process_tables(placeholder_storage, markup)
  
  # Process punctuation
  markup = process_punctuation(placeholder_storage, markup)
  
  # Process line continuations
  markup = process_line_continuations(markup)
  
  # Process images
  image_definition_storage = ImageDefinitionStorage()
  markup = process_images(
    placeholder_storage, image_definition_storage, markup
  )
  
  # Process links
  link_definition_storage = LinkDefinitionStorage()
  markup = process_links(placeholder_storage, link_definition_storage, markup)
  
  # Process inline semantics
  markup = process_inline_semantics(placeholder_storage, markup)
  
  # Process whitespace
  markup = process_whitespace(markup)
  
  # Replace placeholders strings with markup portions
  markup = placeholder_storage.replace_placeholders_with_markup(markup)
  
  ################################################
  # END of conversion
  ################################################
  
  html = markup
  
  return html


################################################################
# Wrappers
################################################################


def cmd_file_to_html_file(cmd_name):
  """
  Run converter on CMD file and generate HTML file.
  """
  
  # Canonicalise file name:
  # (1) Convert Windows backslashes to forward slashes
  # (2) Remove leading dot-slash for current directory
  # (3) Remove trailing "." or ".cmd" extension if given
  cmd_name = re.sub(r'\\', '/', cmd_name)
  cmd_name = re.sub(r'^[.]/', '', cmd_name)
  cmd_name = re.sub(r'[.](cmd)?$', '', cmd_name)
  
  # Read CMD from CMD file
  with open(f'{cmd_name}.cmd', 'r', encoding='utf-8') as cmd_file:
    cmd = cmd_file.read()
  
  # Convert CMD to HTML
  html = cmd_to_html(cmd, cmd_name)
  
  # Write HTML to HTML file
  with open(f'{cmd_name}.html', 'w', encoding='utf-8') as html_file:
    html_file.write(html)


def main(cmd_name):
  
  # Read CMD ignore patterns from .cmdignore
  try:
    with open('.cmdignore', 'r', encoding='utf-8') as cmd_ignore_file:
      cmd_ignore_content = cmd_ignore_file.read()
  except FileNotFoundError:
    cmd_ignore_content = ''
  
  # Convert to a list and ensure leading ./
  cmd_ignore_pattern_list = cmd_ignore_content.split()
  cmd_ignore_pattern_list = [
    re.sub('^(?![.]/)', './', cmd_ignore_pattern)
      for cmd_ignore_pattern in cmd_ignore_pattern_list
  ]
  
  # Get list of CMD files to be converted
  if cmd_name == '':
    # Get list of all CMD files
    cmd_name_list = [
      os.path.join(path, name)
        for path, _, files in os.walk('.')
          for name in files
            if fnmatch.fnmatch(name, '*.cmd')
    ]
    # Filter out ignored CMD files
    cmd_name_list = [
      cmd_name
        for cmd_name in cmd_name_list
          if not any(
            fnmatch.fnmatch(cmd_name, cmd_ignore_pattern)
              for cmd_ignore_pattern in cmd_ignore_pattern_list
          )
    ]
  else:
    cmd_name_list = [cmd_name]
  
  # Convert CMD files
  for cmd_name in cmd_name_list:
    cmd_file_to_html_file(cmd_name)


if __name__ == '__main__':
  
  DESCRIPTION_TEXT = '''
    Convert Conway's markdown (CMD) to HTML.
  '''
  parser = argparse.ArgumentParser(description=DESCRIPTION_TEXT)
  
  CMD_NAME_HELP_TEXT = '''
    Name of CMD file to be converted.
    Output is cmd_name.html.
    Omit to convert all CMD files,
    except those listed in .cmdignore.
  '''
  parser.add_argument(
    'cmd_name',
    help=CMD_NAME_HELP_TEXT,
    metavar='cmd_name[.[cmd]]',
    nargs='?',
    default=''
  )
  
  arguments = parser.parse_args()
  
  cmd_name = arguments.cmd_name
  
  main(cmd_name)
