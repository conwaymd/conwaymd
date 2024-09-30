#!/usr/bin/env python3

"""
# test_cmd.py

Perform unit testing for `cmd.py`.
Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""

import cmd
import unittest


class TestCmd(unittest.TestCase):
    maxDiff = None

    def test_placeholder_master_protect(self):
        self.assertEqual(cmd.PlaceholderMaster.protect(''), '\uF8FF\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('$'), '\uF8FF\uE024\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('£'), '\uF8FF\uE0C2\uE0A3\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('ह'), '\uF8FF\uE0E0\uE0A4\uE0B9\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('€'), '\uF8FF\uE0E2\uE082\uE0AC\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('한'), '\uF8FF\uE0ED\uE095\uE09C\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('𐍈'), '\uF8FF\uE0F0\uE090\uE08D\uE088\uF8FF')
        self.assertEqual(cmd.PlaceholderMaster.protect('一鿐'), '\uF8FF\uE0E4\uE0B8\uE080\uE0E9\uE0BF\uE090\uF8FF')

    def test_ordinary_dictionary_replacement_build_regex_pattern(self):

        self.assertEqual(
            cmd.OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(substitute_from_pattern={}),
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
            r'(?P<flags> [ui]* )'
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
            r'(?P<flags> [ui]* )'
            r'\{'
            r'(?P<extensible_delimiter> \+{2,} )'
            r'(?P<content> [\s\S]*? )'
            r'(?P=extensible_delimiter)'
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
            r'(?P=extensible_delimiter)'
        )

    def test_partitioning_replacement_build_regex_pattern(self):
        self.assertEqual(
            cmd.PartitioningReplacement.build_regex_pattern(
                starting_pattern='[-+*]',
                attribute_specifications='',
                ending_pattern='[-]',
            ),
            r'^ [^\S\n]*'
            r'(?: [-+*] )'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} | [\s]+? )'
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
            r'(?: HELLO[:] )'
            r'[\s]+?'
            r'(?P<content> [\s\S]*? )'
            r'(?= \Z )'
        )

    def test_reference_definition_replacement_build_regex_pattern(self):
        self.assertEqual(
            cmd.ReferenceDefinitionReplacement.build_regex_pattern(attribute_specifications=None),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'\[ [\s]* (?P<label> [^\]]*? ) [\s]* \]'
            r'[:]'
            r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
            r'(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
            r' | '
            r'(?P<bare_uri> [\S]+ )'
            r' )'
            r'(?: '
            r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
            r'(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
            r' | '
            r"'(?P<single_quoted_title> [^']*? )'"
            r' )'
            r' )?'
            r'[^\S\n]* $'
        )

        self.assertEqual(
            cmd.ReferenceDefinitionReplacement.build_regex_pattern(attribute_specifications=''),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'\[ [\s]* (?P<label> [^\]]*? ) [\s]* \]'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'[:]'
            r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
            r'(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
            r' | '
            r'(?P<bare_uri> [\S]+ )'
            r' )'
            r'(?: '
            r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'
            r'(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
            r' | '
            r"'(?P<single_quoted_title> [^']*? )'"
            r' )'
            r' )?'
            r'[^\S\n]* $'
        )

    def test_specified_image_replacement_build_regex_pattern(self):

        self.assertEqual(
            cmd.SpecifiedImageReplacement.build_regex_pattern(
                attribute_specifications=None,
                prohibited_content_regex=None,
            ),
            r'[!]'
            r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
            r'\('
            r'(?: [\s]* '
            r'(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
            r' | '
            r'(?P<bare_uri> [\S]+? )'
            r' )'
            r' )?'
            r'(?: [\s]* '
            r'(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
            r' | '
            r"'(?P<single_quoted_title> [^']*? )'"
            r' )'
            r' )?'
            r'[\s]*'
            r'\)'
        )

        self.assertEqual(
            cmd.SpecifiedImageReplacement.build_regex_pattern(
                attribute_specifications='',
                prohibited_content_regex='a',
            ),
            r'[!]'
            r'\[ [\s]* (?P<alt_text> (?: (?! a ) [^\]] )*? ) [\s]* \]'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'\('
            r'(?: [\s]* '
            r'(?: '
            r'[<] (?P<angle_bracketed_uri> [^>]*? ) [>]'
            r' | '
            r'(?P<bare_uri> [\S]+? )'
            r' )'
            r' )?'
            r'(?: [\s]* '
            r'(?: '
            r'"(?P<double_quoted_title> [^"]*? )"'
            r' | '
            r"'(?P<single_quoted_title> [^']*? )'"
            r' )'
            r' )?'
            r'[\s]*'
            r'\)'
        )

    def test_referenced_image_replacement_build_regex_pattern(self):
        self.assertEqual(
            cmd.ReferencedImageReplacement.build_regex_pattern(
                attribute_specifications=None,
                prohibited_content_regex=None,
            ),
            r'[!]'
            r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
            r'(?: \[ [\s]* (?P<label> [^\]]*? ) [\s]* \] )?'
        )

        self.assertEqual(
            cmd.ReferencedImageReplacement.build_regex_pattern(
                attribute_specifications='',
                prohibited_content_regex=None,
            ),
            r'[!]'
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
            r'[|]?'
            r'(?P<delimiter> '
            r'(?P<delimiter_character> (?P<either> [\*_] ) )'
            r' (?(either) (?P=either)? )'
            r' )'
            r'(?! [\s] | [<][/] )'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'[\s]*'
            r'(?P<content> (?: (?! (?P=delimiter_character) | [<]div ) [\s\S] )+? )'
            r'(?<! [\s] | [|] )'
            r'(?P=delimiter)'
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
            r'[|]?'
            r'(?P<delimiter> '
            r'(?P<delimiter_character> '
            r'(?P<double> ["] ) | (?P<either> [\*] ) | (?P<single> [_] )'
            r' )'
            r' (?(double) (?P=double) | (?(either) (?P=either)? ) )'
            r' )'
            r'(?! [\s] | [<][/] )'
            r'[\s]*'
            r'(?P<content> (?: (?! (?P=delimiter_character) | [<]div ) [\s\S] )+? )'
            r'(?<! [\s] | [|] )'
            r'(?P=delimiter)'
        )

    def test_heading_replacement_build_regex_pattern(self):
        self.assertEqual(
            cmd.HeadingReplacement.build_regex_pattern(
                attribute_specifications=None,
            ),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'(?P<opening_hashes> [#]{1,6} )'
            r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
            r'(?P<content_continuation> '
            r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
            r' )'
            r'[#]*'
            r'[^\S\n]* $'
        )

        self.assertEqual(
            cmd.HeadingReplacement.build_regex_pattern(attribute_specifications=''),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'(?P<opening_hashes> [#]{1,6} )'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
            r'(?P<content_continuation> '
            r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
            r' )'
            r'[#]*'
            r'[^\S\n]* $'
        )

    def test_compute_longest_common_prefix(self):
        self.assertEqual(cmd.compute_longest_common_prefix([]), '')
        self.assertEqual(cmd.compute_longest_common_prefix(['a', 'b', 'c', 'd']), '')
        self.assertEqual(cmd.compute_longest_common_prefix(['  ', '  ', '   ', '      ']), '  ')
        self.assertEqual(cmd.compute_longest_common_prefix(['\t  ', '\t  3', '\t   \t \t']), '\t  ')

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
        self.assertEqual(cmd.escape_attribute_value_html('&<>"'), '&amp;&lt;&gt;&quot;')
        self.assertEqual(cmd.escape_attribute_value_html('&amp;&lt;&gt;&quot;'), '&amp;&lt;&gt;&quot;')
        self.assertEqual(
            cmd.escape_attribute_value_html('https://en.wikipedia.org/w/index.php?title=Wikipedia&action=history'),
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
        self.assertEqual(cmd.escape_attribute_value_html('&#1234567;'), '&#1234567;')
        self.assertEqual(cmd.escape_attribute_value_html('&#12345678;'), '&amp;#12345678;')
        self.assertEqual(cmd.escape_attribute_value_html('&#x123456;'), '&#x123456;')
        self.assertEqual(cmd.escape_attribute_value_html('&#XAbCdeF;'), '&#XAbCdeF;')
        self.assertEqual(cmd.escape_attribute_value_html('&#x1234567;'), '&amp;#x1234567;')

    def test_build_attributes_sequence(self):
        self.assertEqual(cmd.build_attributes_sequence(''), '')
        self.assertEqual(cmd.build_attributes_sequence('  '), '')
        self.assertEqual(cmd.build_attributes_sequence('\t'), '')
        self.assertEqual(cmd.build_attributes_sequence('   \n name=value\n    '), ' name="value"')
        self.assertEqual(cmd.build_attributes_sequence(' empty1="" empty2=  boolean'), ' empty1="" empty2="" boolean')
        self.assertEqual(
            cmd.build_attributes_sequence('qv="quoted value" bv=bare-value'),
            ' qv="quoted value" bv="bare-value"'
        )
        self.assertEqual(cmd.build_attributes_sequence('-before before after -after'), ' before')
        self.assertEqual(cmd.build_attributes_sequence('-before before=no after=yes -after'), ' before="no"')
        self.assertEqual(cmd.build_attributes_sequence('.1 .2 .3 .4 #a #b #c -id -class'), '')
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
        self.assertEqual(cmd.build_extensible_delimiter_opening_regex('$', 5), r'(?P<extensible_delimiter> \${5,} )')

    def test_none_to_empty_string(self):
        self.assertEqual(cmd.none_to_empty_string(''), '')
        self.assertEqual(cmd.none_to_empty_string(None), '')
        self.assertEqual(cmd.none_to_empty_string('xyz'), 'xyz')


if __name__ == '__main__':
    unittest.main()
