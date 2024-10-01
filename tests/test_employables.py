"""
# Conway-Markdown: test_employables.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `employables.py`.
"""

import unittest

from conwaymd.employables import (
    ExtensibleFenceReplacement,
    FixedDelimitersReplacement,
    HeadingReplacement,
    InlineAssortedDelimitersReplacement,
    OrdinaryDictionaryReplacement,
    PartitioningReplacement,
    ReferenceDefinitionReplacement,
    ReferencedImageReplacement,
    SpecifiedImageReplacement,
)


class TestEmployables(unittest.TestCase):
    def test_extensible_fence_replacement_build_regex_pattern(self):
        self.assertEqual(
            ExtensibleFenceReplacement.build_regex_pattern(
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
            r'\}',
        )
        self.assertEqual(
            ExtensibleFenceReplacement.build_regex_pattern(
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
            r'(?P=extensible_delimiter)',
        )

    def test_fixed_delimiter_replacement_build_regex_pattern(self):
        self.assertEqual(
            FixedDelimitersReplacement.build_regex_pattern(
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
            r'\|>',
        )
        self.assertEqual(
            FixedDelimitersReplacement.build_regex_pattern(
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
            r'\$\)',
        )

    def test_heading_replacement_build_regex_pattern(self):
        self.assertEqual(
            HeadingReplacement.build_regex_pattern(attribute_specifications=None),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'(?P<opening_hashes> [#]{1,6} )'
            r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
            r'(?P<content_continuation> '
            r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
            r' )'
            r'[#]*'
            r'[^\S\n]* $',
        )
        self.assertEqual(
            HeadingReplacement.build_regex_pattern(attribute_specifications=''),
            r'^ (?P<anchoring_whitespace> [^\S\n]* )'
            r'(?P<opening_hashes> [#]{1,6} )'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
            r'(?P<content_continuation> '
            r'(?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )*'
            r' )'
            r'[#]*'
            r'[^\S\n]* $',
        )

    def test_inline_assorted_delimiters_replacement_build_regex_pattern(self):
        self.assertEqual(
            InlineAssortedDelimitersReplacement.build_regex_pattern(
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
            r'(?P=delimiter)',
        )
        self.assertEqual(
            InlineAssortedDelimitersReplacement.build_regex_pattern(
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
            r'(?P=delimiter)',
        )

    def test_ordinary_dictionary_replacement_build_regex_pattern(self):
        self.assertEqual(
            OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(substitute_from_pattern={}),
            '',
        )
        self.assertEqual(
            OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(
                substitute_from_pattern={
                    'a': 'b',
                    'b': 'c',
                    'c': 'd',
                    r'#$&*+-.^\|~': 'COMPLICATED',
                },
            ),
            r'a|b|c|\#\$\&\*\+\-\.\^\\\|\~',
        )

    def test_partitioning_replacement_build_regex_pattern(self):
        self.assertEqual(
            PartitioningReplacement.build_regex_pattern(
                starting_pattern='[-+*]',
                attribute_specifications='',
                ending_pattern='[-]',
            ),
            r'^ [^\S\n]*'
            r'(?: [-+*] )'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} | [\s]+? )'
            r'(?P<content> [\s\S]*? )'
            r'(?= ^ [^\S\n]*(?: [-] )(?: \{ [^}]*? \} | [\s]+ ) | \Z )',
        )
        self.assertEqual(
            PartitioningReplacement.build_regex_pattern(
                starting_pattern='HELLO[:]',
                attribute_specifications=None,
                ending_pattern=None,
            ),
            r'^ [^\S\n]*'
            r'(?: HELLO[:] )'
            r'[\s]+?'
            r'(?P<content> [\s\S]*? )'
            r'(?= \Z )',
        )

    def test_reference_definition_replacement_build_regex_pattern(self):
        self.assertEqual(
            ReferenceDefinitionReplacement.build_regex_pattern(attribute_specifications=None),
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
            r'[^\S\n]* $',
        )
        self.assertEqual(
            ReferenceDefinitionReplacement.build_regex_pattern(attribute_specifications=''),
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
            r'[^\S\n]* $',
        )

    def test_referenced_image_replacement_build_regex_pattern(self):
        self.assertEqual(
            ReferencedImageReplacement.build_regex_pattern(
                attribute_specifications=None,
                prohibited_content_regex=None,
            ),
            r'[!]'
            r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
            r'(?: \[ [\s]* (?P<label> [^\]]*? ) [\s]* \] )?',
        )
        self.assertEqual(
            ReferencedImageReplacement.build_regex_pattern(
                attribute_specifications='',
                prohibited_content_regex=None,
            ),
            r'[!]'
            r'\[ [\s]* (?P<alt_text> [^\]]*? ) [\s]* \]'
            r'(?: \{ (?P<attribute_specifications> [^}]*? ) \} )?'
            r'(?: \[ [\s]* (?P<label> [^\]]*? ) [\s]* \] )?',
        )

    def test_specified_image_replacement_build_regex_pattern(self):
        self.assertEqual(
            SpecifiedImageReplacement.build_regex_pattern(
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
            r'\)',
        )
        self.assertEqual(
            SpecifiedImageReplacement.build_regex_pattern(
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
            r'\)',
        )


if __name__ == '__main__':
    unittest.main()
