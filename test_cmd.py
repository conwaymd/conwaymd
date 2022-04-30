#!/usr/bin/env python3

"""
# test_cmd.py

Perform unit testing for `cmd.py`.
Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import cmd
import os
import unittest


class TestCmd(unittest.TestCase):
  
  maxDiff = None
  
  def test_placeholder_master_protect(self):
    self.assertEqual(
      cmd.PlaceholderMaster.protect(''),
      '\uF8FF\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('$'),
      '\uF8FF\uE024\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('£'),
      '\uF8FF\uE0C2\uE0A3\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('ह'),
      '\uF8FF\uE0E0\uE0A4\uE0B9\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('€'),
      '\uF8FF\uE0E2\uE082\uE0AC\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('한'),
      '\uF8FF\uE0ED\uE095\uE09C\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('𐍈'),
      '\uF8FF\uE0F0\uE090\uE08D\uE088\uF8FF'
    )
    self.assertEqual(
      cmd.PlaceholderMaster.protect('一鿐'),
      '\uF8FF\uE0E4\uE0B8\uE080\uE0E9\uE0BF\uE090\uF8FF'
    )
  
  def test_ordinary_dictionary_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(
        substitute_from_pattern={},
      ),
      ''
    )
    self.assertEqual(
      cmd.OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(
        substitute_from_pattern={
          'a': 'b',
          'b': 'c',
          'c': 'd',
          r'#$&*+-.^\|~': 'COMPLICATED',
        },
      ),
      r'a|b|c|\#\$\&\*\+\-\.\^\\\|\~'
    )
  
  def test_fixed_delimiter_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.FixedDelimitersReplacement.build_regex_pattern(
        syntax_type_is_block=False,
        flag_name_from_letter={
          'u': 'KEEP_HTML_UNESCAPED',
          'i': 'KEEP_INDENTED',
        },
        has_flags=True,
        opening_delimiter='<|',
        attribute_specifications='',
        prohibited_content_regex=None,
        closing_delimiter='|>',
      ),
      '(?P<flags> [ui]* )'
      r'<\|'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'(?P<content> [\s\S]*? )'
      r'\|>'
    )
    
    self.assertEqual(
      cmd.FixedDelimitersReplacement.build_regex_pattern(
        syntax_type_is_block=True,
        flag_name_from_letter={},
        has_flags=False,
        opening_delimiter='($',
        attribute_specifications='',
        prohibited_content_regex=None,
        closing_delimiter='$)',
      ),
      r'^ [^\S\n]*'
      r'\(\$'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'\n'
      r'(?P<content> [\s\S]*? )'
      r'^ [^\S\n]*'
      r'\$\)'
    )
  
  def test_extensible_fence_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.ExtensibleFenceReplacement.build_regex_pattern(
        syntax_type_is_block=False,
        flag_name_from_letter={
          'u': 'KEEP_HTML_UNESCAPED',
          'i': 'KEEP_INDENTED',
        },
        has_flags=True,
        prologue_delimiter='{',
        extensible_delimiter_character='+',
        extensible_delimiter_min_length=2,
        attribute_specifications=None,
        prohibited_content_regex=None,
        epilogue_delimiter='}',
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
        syntax_type_is_block=True,
        flag_name_from_letter={},
        has_flags=False,
        prologue_delimiter='',
        extensible_delimiter_character='$',
        extensible_delimiter_min_length=4,
        attribute_specifications='',
        prohibited_content_regex=None,
        epilogue_delimiter='',
      ),
      r'^ [^\S\n]*'
      r'(?P<extensible_delimiter> \${4,} )'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'\n'
      r'(?P<content> [\s\S]*? )'
      r'^ [^\S\n]*'
      '(?P=extensible_delimiter)'
    )
  
  def test_partitioning_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.PartitioningReplacement.build_regex_pattern(
        starting_pattern='[-+*]',
        attribute_specifications='',
        ending_pattern='[-]',
      ),
      r'^ [^\S\n]*'
      '(?: [-+*] )'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} | [\s]+ )'
      r'(?P<content> [\s\S]*? )'
      r'(?= ^ [^\S\n]*(?: [-] )(?: \{ [^}]*? \} | [\s]+ ) | \Z )'
    )
    
    self.assertEqual(
      cmd.PartitioningReplacement.build_regex_pattern(
        starting_pattern='HELLO[:]',
        attribute_specifications=None,
        ending_pattern=None,
      ),
      r'^ [^\S\n]*'
      '(?: HELLO[:] )'
      r'[\s]+'
      r'(?P<content> [\s\S]*? )'
      r'(?= \Z )'
    )
  
  def test_reference_definition_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.ReferenceDefinitionReplacement.build_regex_pattern(
        attribute_specifications=None,
      ),
      r'^ (?P<anchoring_whitespace> [^\S\n]* )'
      r'\[ [\s]* (?P<label> [^\]]*? ) [\s]* \]'
      '[:]'
      r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
      '(?: '
        r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
          ' | '
        r'(?P<bare_uri> [\S]+ )'
      ' )'
      '(?: '
        r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
        '(?: '
          r'"(?P<double_quoted_title> [^"]*? )"'
            ' | '
          r"'(?P<single_quoted_title> [^']*? )'"
        ' )'
      ' )?'
      r'[^\S\n]* $'
    )
    
    self.assertEqual(
      cmd.ReferenceDefinitionReplacement.build_regex_pattern(
        attribute_specifications='',
      ),
      r'^ (?P<anchoring_whitespace> [^\S\n]* )'
      r'\[ [\s]* (?P<label> [^\]]*? ) [\s]* \]'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      '[:]'
      r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
      '(?: '
        r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
          ' | '
        r'(?P<bare_uri> [\S]+ )'
      ' )'
      '(?: '
        r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
        '(?: '
          r'"(?P<double_quoted_title> [^"]*? )"'
            ' | '
          r"'(?P<single_quoted_title> [^']*? )'"
        ' )'
      ' )?'
      r'[^\S\n]* $'
    )
  
  def test_specified_image_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.SpecifiedImageReplacement.build_regex_pattern(
        attribute_specifications=None,
        prohibited_content_regex=None,
      ),
      '[!]'
      r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
      r'\('
        fr'(?: [\s]* '
          '(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
              ' | '
            r'(?P<bare_uri> [\S]+ )'
          ' )'
        ' )?'
        fr'(?: [\s]* '
          '(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
              ' | '
            r"'(?P<single_quoted_title> [^']*? )'"
          ' )'
        ' )?'
        r'[\s]*'
      r'\)'
    )
    
    self.assertEqual(
      cmd.SpecifiedImageReplacement.build_regex_pattern(
        attribute_specifications='',
        prohibited_content_regex='a',
      ),
      '[!]'
      r'\[ [\s]* (?P<alt_text> (?: (?! a ) [^\]] )*? ) [\s]* \]'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'\('
        fr'(?: [\s]* '
          '(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
              ' | '
            r'(?P<bare_uri> [\S]+ )'
          ' )'
        ' )?'
        fr'(?: [\s]* '
          '(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
              ' | '
            r"'(?P<single_quoted_title> [^']*? )'"
          ' )'
        ' )?'
        r'[\s]*'
      r'\)'
    )
  
  def test_referenced_image_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.ReferencedImageReplacement.build_regex_pattern(
        attribute_specifications=None,
        prohibited_content_regex=None,
      ),
      '[!]'
      r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
      r'(?: \[ [\s]* (?P<label> [^\]]*? ) [\s]* \] )?'
    )
    
    self.assertEqual(
      cmd.ReferencedImageReplacement.build_regex_pattern(
        attribute_specifications='',
        prohibited_content_regex=None,
      ),
      '[!]'
      r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'(?: \[ [\s]* (?P<label> [^\]]*? ) [\s]* \] )?'
    )
  
  def test_inline_assorted_delimiters_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.InlineAssortedDelimitersReplacement.build_regex_pattern(
        tag_name_from_delimiter_length_from_character={
          '_': {1: 'i', 2: 'b'},
          '*': {1: 'em', 2: 'strong'},
        },
        attribute_specifications='',
        prohibited_content_regex='[<]div',
      ),
      '[|]?'
      '(?P<delimiter> '
        r'(?P<delimiter_character> (?P<either> [\*_] ) )'
        ' (?(either) (?P=either)? )'
      ' )'
      r'(?! [\s] | [<][/] )'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'[\s]*'
      r'(?P<content> (?: (?! (?P=delimiter_character) | [<]div ) [\s\S] )+? )'
      r'(?<! [\s] | [|] )'
      '(?P=delimiter)'
    )
    
    self.assertEqual(
      cmd.InlineAssortedDelimitersReplacement.build_regex_pattern(
        tag_name_from_delimiter_length_from_character={
          '_': {1: 'i'},
          '*': {1: 'em', 2: 'strong'},
          '"': {2: 'q'},
        },
        attribute_specifications=None,
        prohibited_content_regex='[<]div',
      ),
      '[|]?'
      '(?P<delimiter> '
        '(?P<delimiter_character> '
          r'(?P<double> ["] ) | (?P<either> [\*] ) | (?P<single> [_] )'
        ' )'
        ' (?(double) (?P=double) | (?(either) (?P=either)? ) )'
      ' )'
      r'(?! [\s] | [<][/] )'
      r'[\s]*'
      r'(?P<content> (?: (?! (?P=delimiter_character) | [<]div ) [\s\S] )+? )'
      r'(?<! [\s] | [|] )'
      '(?P=delimiter)'
    )
  
  def test_heading_replacement_build_regex_pattern(self):
    
    self.assertEqual(
      cmd.HeadingReplacement.build_regex_pattern(
        attribute_specifications=None,
      ),
      r'^ (?P<anchoring_whitespace> [^\S\n]* )'
      '(?P<opening_hashes> [#]{1,6} )'
      r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
      '(?P<content_continuation> '
        r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
      ' )'
      '[#]*'
      r'[^\S\n]* $'
    )
    
    self.assertEqual(
      cmd.HeadingReplacement.build_regex_pattern(attribute_specifications=''),
      r'^ (?P<anchoring_whitespace> [^\S\n]* )'
      '(?P<opening_hashes> [#]{1,6} )'
      r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
      r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
      '(?P<content_continuation> '
        r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
      ' )'
      '[#]*'
      r'[^\S\n]* $'
    )
  
  def test_compute_longest_common_prefix(self):
    self.assertEqual(
      cmd.compute_longest_common_prefix(['a', 'b', 'c', 'd']),
      ''
    )
    self.assertEqual(
      cmd.compute_longest_common_prefix(['  ', '  ', '   ', '      ']),
      '  '
    )
    self.assertEqual(
      cmd.compute_longest_common_prefix(['\t  ', '\t  3', '\t   \t \t']),
      '\t  '
    )
  
  def test_de_indent(self):
    self.assertEqual(
      cmd.de_indent(
'''
    4 spaces

      4 spaces + 2 spaces
      \t   4 spaces + 2 spaces, 1 tab, 3 spaces
     
     4 spaces + 1 space (this line and above)
'''
      ),
'''
4 spaces

  4 spaces + 2 spaces
  \t   4 spaces + 2 spaces, 1 tab, 3 spaces
 
 4 spaces + 1 space (this line and above)
'''
    )
    self.assertEqual(
      cmd.de_indent(
        '''
\t\t \t\t\t\t\t\t And,
\t\t \t\t\t\t\t\tWhitespace before closing delimiter:
        '''
      ),
'''
 And,
Whitespace before closing delimiter:
'''
    )
  
  def test_escape_attribute_value_html(self):
    self.assertEqual(
      cmd.escape_attribute_value_html('&<>"'),
      '&amp;&lt;&gt;&quot;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&amp;&lt;&gt;&quot;'),
      '&amp;&lt;&gt;&quot;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html(
        'https://en.wikipedia.org/w/index.php?title=Wikipedia&action=history'
      ),
      'https://en.wikipedia.org/w/index.php?title=Wikipedia&amp;action=history'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&ThisEntityNameHasTooManyCharacters;'),
      '&amp;ThisEntityNameHasTooManyCharacters;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&NotAValidNameButShortEnough;'),
      '&NotAValidNameButShortEnough;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&#1234567;'),
      '&#1234567;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&#12345678;'),
      '&amp;#12345678;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&#x123456;'),
      '&#x123456;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&#XAbCdeF;'),
      '&#XAbCdeF;'
    )
    self.assertEqual(
      cmd.escape_attribute_value_html('&#x1234567;'),
      '&amp;#x1234567;'
    )
  
  def test_build_attributes_sequence(self):
    self.assertEqual(
      cmd.build_attributes_sequence(''),
      ''
    )
    self.assertEqual(
      cmd.build_attributes_sequence('  '),
      ''
    )
    self.assertEqual(
      cmd.build_attributes_sequence('\t'),
      ''
    )
    self.assertEqual(
      cmd.build_attributes_sequence('   \n name=value\n    '),
      ' name="value"'
    )
    self.assertEqual(
      cmd.build_attributes_sequence(' empty1="" empty2=  boolean'),
      ' empty1="" empty2="" boolean'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('qv="quoted value" bv=bare-value'),
      ' qv="quoted value" bv="bare-value"'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('-before before after -after'),
      ' before'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('-before before=no after=yes -after'),
      ' before="no"'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('.1 .2 .3 .4 #a #b #c -id -class'),
      ''
    )
    self.assertEqual(
      cmd.build_attributes_sequence('#=top .=good    l=en    r=3    c=2'),
      ' id="top" class="good" lang="en" rowspan="3" colspan="2"'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('id=x #y .a .b name=value .=c class="d"'),
      ' id="y" class="a b c d" name="value"'
    )
    self.assertEqual(
      cmd.build_attributes_sequence('w="320" h=16 s="font-weight: bold"'),
      ' width="320" height="16" style="font-weight: bold"'
    )
  
  def test_build_flags_regex(self):
    self.assertEqual(cmd.build_flags_regex({}, False), '')
    self.assertEqual(
      cmd.build_flags_regex(
        {
          'u': 'KEEP_HTML_UNESCAPED',
          'w': 'REDUCE_WHITESPACE',
          'i': 'KEEP_INDENTED',
        },
        True,
      ),
      '(?P<flags> [uwi]* )'
    )
  
  def test_build_extensible_delimiter_opening_regex(self):
    self.assertEqual(
      cmd.build_extensible_delimiter_opening_regex('$', 5),
      r'(?P<extensible_delimiter> \${5,} )'
    )
  
  def test_none_to_empty_string(self):
    self.assertEqual(cmd.none_to_empty_string(''), '')
    self.assertEqual(cmd.none_to_empty_string(None), '')
    self.assertEqual(cmd.none_to_empty_string('xyz'), 'xyz')
  
  def test_extract_rules_and_content(self):
    self.assertEqual(cmd.extract_rules_and_content(''), (None, ''))
    self.assertEqual(cmd.extract_rules_and_content('abc'), (None, 'abc'))
    self.assertEqual(cmd.extract_rules_and_content('%%%abc'), (None, '%%%abc'))
    self.assertEqual(cmd.extract_rules_and_content('abc%%%'), (None, 'abc%%%'))
    self.assertEqual(cmd.extract_rules_and_content('%%%\nabc'), ('', 'abc'))
    self.assertEqual(cmd.extract_rules_and_content('X%%\nY'), (None, 'X%%\nY'))
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
  
  def test_extract_separator_normalised_cmd_name(self):
    self.assertEqual(
      cmd.extract_separator_normalised_cmd_name('path/to/cmd_name.cmd'),
      'path/to/cmd_name'
    )
    self.assertEqual(
      cmd.extract_separator_normalised_cmd_name(r'path\to\cmd_name.cmd'),
      'path/to/cmd_name'
    )
  
  def test_cmd_to_html(self):
    
    self.assertEqual(
      cmd.cmd_to_html('', 'test_cmd.py', verbose_mode_enabled=True),
'''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Title</title>
</head>
<body>
</body>
</html>
'''
    )
    
    self.assertEqual(
      cmd.cmd_to_html(
        ################################################################
        # START CMD
        ################################################################
r'''# Da Rules

OrdinaryDictionaryReplacement: #boilerplate-properties-override
- queue_position: BEFORE #boilerplate-properties
- apply_mode: SIMULTANEOUS
* %lang --> en-AU
* %title --> "This be a __test__ "
* %styles -->
    #good {
      font-family: sans-serif;
    }
    #bad {
      font-family: serif;
    }

FixedDelimitersReplacement: #comment-breaker
- queue_position: BEFORE #comments
- syntax_type: INLINE
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
- opening_delimiter: <|
- attribute_specifications: EMPTY
- content_replacements:
    #escape-html
    #trim-whitespace
    #placeholder-protect
- closing_delimiter: |>

OrdinaryDictionaryReplacement: #test-apply-mode-sequential
- queue_position: BEFORE #placeholder-unprotect
- apply_mode: SEQUENTIAL
* @1 --> @2
* @2 --> @3
* @3 --> @4
* @4 --> @5

OrdinaryDictionaryReplacement: #test-apply-mode-simultaneous
- queue_position: BEFORE #placeholder-unprotect
- apply_mode: SIMULTANEOUS
* !1 --> !2
* !2 --> !3
* !3 --> !4
* !4 --> !5

%%%

# `test_cmd_to_html`

Sequential `OrdinaryDictionaryReplacement` result: @1, @2, @3, @4
Simultaneous `OrdinaryDictionaryReplacement` result: !1, !2, !3, !4
``{title=&<>"} Attribute specification escape test. ``
``{title='"'} Attribute specification double-quote escape test. ``
``{title="`?` <`` <`!`> ``>"}
  Attribute specification prevail test.
``

## `#placeholder-markers`

If implemented properly, the following shall confound not:
  `'\uF8FF\uE069\uE420\uE000\uF8FE\uE064\uF8FF'`: 

## `#literals`

BEFORE{ <`` Literal & < > ``> }AFTER
    <```
      No indent,
          yet four more spaces hence?
    ```>
   u<```` Flag `u`: unescaped HTML, <b>&amp; for ampersand!</b> ````>
   i<```
          Flag `i`: whitespace stripped on this line,
      but indent preserved on lines thereafter.
    ```>
   uw<````````
      Flag `w`: whitespace trimmed on all lines,
        even trailing whitespace,  
          and even whitespace before a break element:        <br>
    ````````>

## `#display-code`

  ```
    for (int index = 0; index < count; index++)
    {
      // etc. etc.
    }
  ```
  ````{#display-code-1 .class-2 l=en lang=en-AU .class-3}
    :(
    u<``<strong>LITERALS PREVAIL OVER DISPLAY CODE</strong>``>
        <```<``(unless restrained by an outer literal)``>```>
  ````
  i```
    Retained indentation:
      a lot.
   ```

## `#comment-breaker` (custom)

<| <## Sundered |> be <| this. ##> |>
u<| <strong>Unescaped!</strong> |>

## `#comments`

`Code prevails not <## over comments ##>.`
`Literals may aid code to prevail <`<# over comments #>`>`
Comments can remove code. <# `Like so.` #>

## `#divisions`

||||{.top-level}
  Parent.
  ||{.elder}
  Child 1.
  ||
  ||{.younger}
  Child 2.
  ||
||||

## `#blockquotes`

""""{.four}
"""{.three}
""{.two}
||
"One is not a blockquote"
||
""
"""
""""

## `#unordered-lists`
===={.four}
-
  ==={.three}
  - Dash.
  + Plus.
  * Asterisk.
  1. Not number.
    =={.two}
    - Yes.
    ==
  ===
- Hello!
====
Empty list:
======
======

## `#ordered-lists`
++++
0. Yes.
00. Yep.
000000000000000000000000000. Yeah.
- Nah.
======
- Try.
  +++
  123456789. Still 1.
  2. Indeed 2.
     ++{start=50}
     50. 50/50?
     ++
  +++
======
++++
'''
"""
## `#tables`

''''
<caption>Why the hell would you have table inception?</caption>
|^
  //
    ; `starting_match`
    ; `tag_name`
|:
  //
    , `|^`
    , `thead`
  //
    , `|:`
    , `tbody`
  //
    , `|_`
    , `tfoot`
|_
  //
    ,{}
      ''{.nested-with-parts}
        |^
          //
            ; No
            ; Logic
        |:
          //
            ,{r2} A
            , 1
          //
            , 2
          //
            ,{c2}
      ''
    ,{style="background: yellow"}
      ''{.nested-without-parts}
        //
          ; Who
          , Me
        //
          ; What
          , Yes
        //
          ;{style="font-weight: bold"} When
          , Didn't Ask
      ''
''''
Empty:
''
''
Head:
''
|^
''
Body:
''
|:
''
Foot:
''
|_
''
Head-body:
''
|^
|:
''
Head-foot:
''
|^
|_
''
Body-foot:
''
|:
|_
''
Header-after-data (seriously, why would you have this?):
'''
//
  , Data
  ; Header
  ; Header2
//
  , Data
  ; Header
  , Data2
'''
"""
r'''
## `#headings`

### Level 3
#### Level 4
##### Level 5
###### Level 6

###
### Non-empty
### Insufficient closing hashes #
### Excessive closing hashes #######
###{}
###{} Non-empty
###{.class-1 title="This be fancy"} Fancy
### Trailing whitespace     	
### Trailing whitespace after hashes #  	

### Below be
  continuation
  lines

  ### And this also
    hath a continuation

### But this
hath insufficient indentation

###
  Starter line may be empty

#missing-whitespace
####### Excessive opening hashes

## `#paragraphs`

--------{.eight}
This be a paragraph.
--
NOTE: nested paragraphs are illegal.
--
--------
--{.two}
This be another paragraph.
--
||
----
A paragraph cannot contain a <div>block</div>.
----
||

## `#inline-code`

This be `inline code`.
u``{.classy} Whitespace stripped, and <b>unescaped</b>. ``
Even ```inline with ``backticks within`` ```.

Inline code may not contain anchored block tags.
(1) `This code
  <p>will not work`</p>.
(2)
--
Neither will `this
--
code`.
||
(3) But if the block tag be not anchored,
then it `<p>will work</p>`.
||

## `#cmd-properties`

CMD version is <code>v%cmd-version</code>.
CMD name is <code>%cmd-name</code>.
CMD basename is <code>%cmd-basename</code>.

## `#backslash-escapes`

\\ \# \& \( \) \* \< \> \[ \] \_ \{ \| \}
\\\3 \\\\4 \\\\\5 \\\\\\6
[space]\ [space]
[tab]\t[tab]

## `#backslash-continuations`

This be \
    continuation.
This be not \\
    continuation, for the backslash is escaped.

## `#reference-definitions`

[good]: https://example.com
[good double]: https://example.com "Yes"
[good angle-bracketed single]: <https://example.com> 'Yes'

  [good continued]:
    https://example.com
    "Yes"

[some good]: https://example.com
  [more good]: https://example.com

  [good except title]:
    https://example.com
  "No"

  [bad]:
https://example.com

[missing uri]:
  [indented]: https://example.com

## `#specified-images`

![](decoration/image)
![]{-alt}("omitting alt is bad")
![Alt text.]()
![Alt text.](/src/only)
![Alt text.]("title only")
![
  Spacious alt.
](
  <spacious/src>
  'spacious title'
)
![alt]{alt=A src=S title=T}(src "title")

""
  ![Images/links cannot
""
--
  span](across/blocks)
--

## `#referenced-images`

[label]{.test}: file.svg "title"
[Hooray!]{.test2}: yay.png

![Alt text.][label]
![ Space & case test   ][  LaBEl  ]
![Hooray!]{class="no-label"}
![Class dismissed.]{-class .dismissed}[label]

![Untouched][Nonexistent label]


""
  ![Images/links cannot
""
--
  span across blocks][label]
--
(but note that the trailing `[label]` will be consumed by itself).

## `#explicit-links`

<https://example.com>
b<https://example.com>
s<https://example.com>
bs<https://example.com>

bs<mailto:mail@example.com>

s<{href='https://evil.com'}https://example.com>

## `#specified-links`

[](empty/content)
[Empty href](<>)
[No href]{-href}()
[Text]("title only")
[
  Spacious text.
](
  <spacious/href>
  'spacious title'
)
[Link]{href=H title=T}(href "title")

[![alt](src "title")](href 'title2')

## `#referenced-links`

[label2]{.test}: /file "title"
[Rejoice]{.test2}: yay.html

[Content.][label2]
[ Space & case test   ][  LabEL2  ]
[Rejoice]{class="no-label"}
[Class dismissed.]{-class .dismissed}[label2]

[Untouched][Nonexistent label]

## `#inline-semantics`

11 *em*
22 **strong**
33 ***em(strong)***
44 ****strong(strong)****
55 *****em(strong(strong))*****
123 *em **em(strong)***
213 **strong *strong(em)***
312 ***strong(em)* strong**
321 ***em(strong)** em*
1221 *em **em(strong)** em*
2112 **strong *strong(em)* strong**

___foo___ vs __|_bar___

_i_ __b__
*em* **strong**
''cite''
""q""

'not enough single-quotes for cite'
"not enough double-quotes for q"

"""1+"""
""""2""""
"""""2+"""""
""""""3""""""

----
No __spanning
----
----
across block elements__.
----
Yes __spanning
across lines__.
'''
        ################################################################
        # END CMD
        ################################################################
        ,
        'test_cmd.py',
        verbose_mode_enabled=True,
      ),
      ################################################################
      # START HTML
      ################################################################
r'''<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>This be a __test__ </title>
<style>
#good {
font-family: sans-serif;
}
#bad {
font-family: serif;
}
</style>
</head>
<body>
<h1><code>test_cmd_to_html</code></h1>
Sequential <code>OrdinaryDictionaryReplacement</code> result: @5, @5, @5, @5
Simultaneous <code>OrdinaryDictionaryReplacement</code> result: !2, !3, !4, !5
<code title="&amp;&lt;&gt;&quot;">Attribute specification escape test.</code>
<code title="&quot;">Attribute specification double-quote escape test.</code>
<pre title="`?` &lt;`!`&gt;"><code>Attribute specification prevail test.
</code></pre>
<h2><code>#placeholder-markers</code></h2>
If implemented properly, the following shall confound not:
<code>'\uF8FF\uE069\uE420\uE000\uF8FE\uE064\uF8FF'</code>: 
<h2><code>#literals</code></h2>
BEFORE{ Literal &amp; &lt; &gt; }AFTER
No indent,
    yet four more spaces hence?
Flag `u`: unescaped HTML, <b>&amp; for ampersand!</b>
Flag `i`: whitespace stripped on this line,
      but indent preserved on lines thereafter.
Flag `w`: whitespace trimmed on all lines,
even trailing whitespace,
and even whitespace before a break element:<br>
<h2><code>#display-code</code></h2>
<pre><code>for (int index = 0; index &lt; count; index++)
{
  // etc. etc.
}
</code></pre>
<pre id="display-code-1" class="class-2 class-3" lang="en-AU"><code>:(
<strong>LITERALS PREVAIL OVER DISPLAY CODE</strong>
    &lt;``(unless restrained by an outer literal)``&gt;
</code></pre>
<pre><code>    Retained indentation:
      a lot.
</code></pre>
<h2><code>#comment-breaker</code> (custom)</h2>
&lt;## Sundered be this. ##&gt;
<strong>Unescaped!</strong>
<h2><code>#comments</code></h2>
<code>Code prevails not.</code>
<code>Literals may aid code to prevail &lt;# over comments #&gt;</code>
Comments can remove code.
<h2><code>#divisions</code></h2>
<div class="top-level">
Parent.
<div class="elder">
Child 1.
</div>
<div class="younger">
Child 2.
</div>
</div>
<h2><code>#blockquotes</code></h2>
<blockquote class="four">
<blockquote class="three">
<blockquote class="two">
<div>
"One is not a blockquote"
</div>
</blockquote>
</blockquote>
</blockquote>
<h2><code>#unordered-lists</code></h2>
<ul class="four">
<li>
<ul class="three">
<li>
Dash.
</li>
<li>
Plus.
</li>
<li>
Asterisk.
1. Not number.
<ul class="two">
<li>
Yes.
</li>
</ul>
</li>
</ul>
</li>
<li>
Hello!
</li>
</ul>
Empty list:
<ul>
</ul>
<h2><code>#ordered-lists</code></h2>
<ol>
<li>
Yes.
</li>
<li>
Yep.
</li>
<li>
Yeah.
- Nah.
<ul>
<li>
Try.
<ol>
<li>
Still 1.
</li>
<li>
Indeed 2.
<ol start="50">
<li>
50/50?
</li>
</ol>
</li>
</ol>
</li>
</ul>
</li>
</ol>
<h2><code>#tables</code></h2>
<table>
<caption>Why the hell would you have table inception?</caption>
<thead>
<tr>
<th><code>starting_match</code></th>
<th><code>tag_name</code></th>
</tr>
</thead>
<tbody>
<tr>
<td><code>|^</code></td>
<td><code>thead</code></td>
</tr>
<tr>
<td><code>|:</code></td>
<td><code>tbody</code></td>
</tr>
<tr>
<td><code>|_</code></td>
<td><code>tfoot</code></td>
</tr>
</tbody>
<tfoot>
<tr>
<td><table class="nested-with-parts">
<thead>
<tr>
<th>No</th>
<th>Logic</th>
</tr>
</thead>
<tbody>
<tr>
<td rowspan="2">A</td>
<td>1</td>
</tr>
<tr>
<td>2</td>
</tr>
<tr>
<td colspan="2"></td>
</tr>
</tbody>
</table></td>
<td style="background: yellow"><table class="nested-without-parts">
<tr>
<th>Who</th>
<td>Me</td>
</tr>
<tr>
<th>What</th>
<td>Yes</td>
</tr>
<tr>
<th style="font-weight: bold">When</th>
<td>Didn't Ask</td>
</tr>
</table></td>
</tr>
</tfoot>
</table>
Empty:
<table>
</table>
Head:
<table>
<thead>
</thead>
</table>
Body:
<table>
<tbody>
</tbody>
</table>
Foot:
<table>
<tfoot>
</tfoot>
</table>
Head-body:
<table>
<thead>
</thead>
<tbody>
</tbody>
</table>
Head-foot:
<table>
<thead>
</thead>
<tfoot>
</tfoot>
</table>
Body-foot:
<table>
<tbody>
</tbody>
<tfoot>
</tfoot>
</table>
Header-after-data (seriously, why would you have this?):
<table>
<tr>
<td>Data</td>
<th>Header</th>
<th>Header2</th>
</tr>
<tr>
<td>Data</td>
<th>Header</th>
<td>Data2</td>
</tr>
</table>
<h2><code>#headings</code></h2>
<h3>Level 3</h3>
<h4>Level 4</h4>
<h5>Level 5</h5>
<h6>Level 6</h6>
<h3></h3>
<h3>Non-empty</h3>
<h3>Insufficient closing hashes</h3>
<h3>Excessive closing hashes</h3>
<h3></h3>
<h3>Non-empty</h3>
<h3 class="class-1" title="This be fancy">Fancy</h3>
<h3>Trailing whitespace</h3>
<h3>Trailing whitespace after hashes</h3>
<h3>Below be
continuation
lines</h3>
<h3>And this also
hath a continuation</h3>
<h3>But this</h3>
hath insufficient indentation
<h3>
Starter line may be empty</h3>
#missing-whitespace
####### Excessive opening hashes
<h2><code>#paragraphs</code></h2>
<p class="eight">
This be a paragraph.
--
NOTE: nested paragraphs are illegal.
--
</p>
<p class="two">
This be another paragraph.
</p>
<div>
----
A paragraph cannot contain a <div>block</div>.
----
</div>
<h2><code>#inline-code</code></h2>
This be <code>inline code</code>.
<code class="classy">Whitespace stripped, and <b>unescaped</b>.</code>
Even <code>inline with ``backticks within``</code>.
Inline code may not contain anchored block tags.
(1) `This code
<p>will not work`</p>.
(2)
<p>
Neither will `this
</p>
code`.
<div>
(3) But if the block tag be not anchored,
then it <code>&lt;p&gt;will work&lt;/p&gt;</code>.
</div>
<h2><code>#cmd-properties</code></h2>
CMD version is <code>v3.999...</code>.
CMD name is <code>test_cmd.py</code>.
CMD basename is <code>test_cmd.py</code>.
<h2><code>#backslash-escapes</code></h2>
\ # &amp; ( ) * &lt; &gt; [ ] _ { | }
\\3 \\4 \\\5 \\\6
[space] [space]
[tab]	[tab]
<h2><code>#backslash-continuations</code></h2>
This be continuation.
This be not \
continuation, for the backslash is escaped.
<h2><code>#reference-definitions</code></h2>
"No"
[bad]:
https://example.com
[missing uri]:
<h2><code>#specified-images</code></h2>
<img alt="" src="decoration/image">
<img src="" title="omitting alt is bad">
<img alt="Alt text." src="">
<img alt="Alt text." src="/src/only">
<img alt="Alt text." src="" title="title only">
<img alt="Spacious alt." src="spacious/src" title="spacious title">
<img alt="A" src="S" title="T">
<blockquote>
![Images/links cannot
</blockquote>
<p>
span](across/blocks)
</p>
<h2><code>#referenced-images</code></h2>
<img alt="Alt text." src="file.svg" title="title" class="test">
<img alt="Space &amp; case test" src="file.svg" title="title" class="test">
<img alt="Hooray!" src="yay.png" class="test2 no-label">
<img alt="Class dismissed." src="file.svg" title="title" class="dismissed">
![Untouched][Nonexistent label]
<blockquote>
![Images/links cannot
</blockquote>
<p>
span across blocks]<a href="file.svg" title="title" class="test">label</a>
</p>
(but note that the trailing <code>[label]</code> will be consumed by itself).
<h2><code>#explicit-links</code></h2>
<a href="https://example.com">https://example.com</a>
&lt;<a href="https://example.com">https://example.com</a>&gt;
<a href="https://example.com">example.com</a>
&lt;<a href="https://example.com">example.com</a>&gt;
&lt;<a href="mailto:mail@example.com">mail@example.com</a>&gt;
<a href="https://evil.com">example.com</a>
<h2><code>#specified-links</code></h2>
<a href="empty/content"></a>
<a href="">Empty href</a>
<a>No href</a>
<a title="title only">Text</a>
<a href="spacious/href" title="spacious title">Spacious text.</a>
<a href="H" title="T">Link</a>
<a href="href" title="title2"><img alt="alt" src="src" title="title"></a>
<h2><code>#referenced-links</code></h2>
<a href="/file" title="title" class="test">Content.</a>
<a href="/file" title="title" class="test">Space &amp; case test</a>
<a href="yay.html" class="test2 no-label">Rejoice</a>
<a href="/file" title="title" class="dismissed">Class dismissed.</a>
[Untouched][Nonexistent label]
<h2><code>#inline-semantics</code></h2>
11 <em>em</em>
22 <strong>strong</strong>
33 <em><strong>em(strong)</strong></em>
44 <strong><strong>strong(strong)</strong></strong>
55 <em><strong><strong>em(strong(strong))</strong></strong></em>
123 <em>em <strong>em(strong)</strong></em>
213 <strong>strong <em>strong(em)</em></strong>
312 <strong><em>strong(em)</em> strong</strong>
321 <em><strong>em(strong)</strong> em</em>
1221 <em>em <strong>em(strong)</strong> em</em>
2112 <strong>strong <em>strong(em)</em> strong</strong>
<i><b>foo</b></i> vs <b><i>bar</i></b>
<i>i</i> <b>b</b>
<em>em</em> <strong>strong</strong>
<cite>cite</cite>
<q>q</q>
'not enough single-quotes for cite'
"not enough double-quotes for q"
"<q>1+</q>"
<q><q>2</q></q>
"<q><q>2+</q></q>"
<q><q><q>3</q></q></q>
<p>
No __spanning
</p>
<p>
across block elements__.
</p>
Yes <b>spanning
across lines</b>.
</body>
</html>
'''
      ################################################################
      # END HTML
      ################################################################
    )
    
    self.assertEqual(
      cmd.cmd_to_html(
r'''
RegexDictionaryReplacement: #delete-everything
- queue_position: AFTER #placeholder-unprotect
* [\s\S]* -->

%%%

The quick brown fox jumps over the lazy dog.
Everything is everything, and everything is dumb.
'''
        ,
        'test_cmd.py',
      ),
      ''
    )
  
  def test_is_cmd_file(self):
    self.assertTrue(cmd.is_cmd_file('file.cmd'))
    self.assertTrue(cmd.is_cmd_file('.cmd'))
    self.assertFalse(cmd.is_cmd_file('file/cmd'))
    self.assertFalse(cmd.is_cmd_file('file.'))
    self.assertFalse(cmd.is_cmd_file('file'))
  
  def test_extract_cmd_name(self):
    
    self.assertEqual(cmd.extract_cmd_name('file.cmd'), 'file')
    self.assertEqual(cmd.extract_cmd_name('file.'), 'file')
    self.assertEqual(cmd.extract_cmd_name('file'), 'file')
    
    if os.sep == '/':
      self.assertEqual(cmd.extract_cmd_name('./././file.cmd'), 'file')
      self.assertEqual(cmd.extract_cmd_name('./dir/../file.cmd'), 'file')
      self.assertEqual(cmd.extract_cmd_name('./file.'), 'file')
      self.assertEqual(cmd.extract_cmd_name('./file'), 'file')
    elif os.sep == '\\':
      self.assertEqual(cmd.extract_cmd_name(r'.\.\.\file.cmd'), 'file')
      self.assertEqual(cmd.extract_cmd_name(r'.\dir\..\file.cmd'), 'file')
      self.assertEqual(cmd.extract_cmd_name(r'.\file.'), 'file')
      self.assertEqual(cmd.extract_cmd_name(r'.\file'), 'file')


if __name__ == '__main__':
  unittest.main()
