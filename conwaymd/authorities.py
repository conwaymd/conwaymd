"""
# Conway-Markdown: authorities.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

The higher power that governs the conversion logic.
"""

import os
import re
import sys
import traceback
from typing import Iterable, NamedTuple, Optional

from conwaymd._version import __version__
from conwaymd.bases import Replacement, ReplacementWithSubstitutions
from conwaymd.constants import CMD_REPLACEMENT_SYNTAX_HELP, GENERIC_ERROR_EXIT_CODE
from conwaymd.employables import (
    DeIndentationReplacement,
    ExplicitLinkReplacement,
    ExtensibleFenceReplacement,
    FixedDelimitersReplacement,
    HeadingReplacement,
    InlineAssortedDelimitersReplacement,
    OrdinaryDictionaryReplacement,
    PartitioningReplacement,
    PlaceholderMarkerReplacement,
    PlaceholderProtectionReplacement,
    PlaceholderUnprotectionReplacement,
    ReferenceDefinitionReplacement,
    ReferencedImageReplacement,
    ReferencedLinkReplacement,
    RegexDictionaryReplacement,
    ReplacementSequence,
    SpecifiedImageReplacement,
    SpecifiedLinkReplacement,
)
from conwaymd.exceptions import MissingAttributeException
from conwaymd.idioms import build_block_tag_regex
from conwaymd.references import ReferenceMaster
from conwaymd.utilities import none_to_empty_string


class ReplacementAuthority:
    """
    Object governing the parsing and application of replacement rules.

    ## `legislate`

    Parses CMD replacement rule syntax.
    See the constant `CMD_REPLACEMENT_SYNTAX_HELP` in `constants.py`.

    Terminology:
    - Class declarations are _committed_.
    - Attribute and substitution declarations are _staged_.

    ## `execute`

    Applies the legislated replacements.
    """
    _opened_file_names: list[str]
    _replacement_from_id: dict[str, 'Replacement']
    _root_replacement_id: Optional[str]
    _replacement_queue: list['Replacement']
    _reference_master: 'ReferenceMaster'
    _verbose_mode_enabled: bool

    def __init__(self, cmd_file_name: str, verbose_mode_enabled: bool):
        self._opened_file_names = [cmd_file_name]
        self._replacement_from_id = {}
        self._root_replacement_id = None
        self._replacement_queue = []
        self._reference_master = ReferenceMaster()
        self._verbose_mode_enabled = verbose_mode_enabled

    @staticmethod
    def print_error(message: str, rules_file_name: str, start_line_number: int, end_line_number: Optional[int] = None):
        source_file = f'`{rules_file_name}`'

        if end_line_number is None or start_line_number == end_line_number - 1:
            line_number_range = f'line {start_line_number}'
        else:
            line_number_range = f'lines {start_line_number} to {end_line_number - 1}'

        print(f'error: {source_file}, {line_number_range}: {message}', file=sys.stderr)

    @staticmethod
    def print_traceback(exception: Exception):
        traceback.print_exception(type(exception), exception, exception.__traceback__)

    @staticmethod
    def is_whitespace_only(line: str) -> bool:
        return bool(re.fullmatch(pattern=r'[\s]*', string=line, flags=re.ASCII))

    @staticmethod
    def is_comment(line: str) -> bool:
        return line.startswith('#')

    @staticmethod
    def compute_rules_inclusion_match(line: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [<][ ]
                    (?:
                        [/] (?P<included_file_name> [\S][\s\S]*? )
                            |
                        (?P<included_file_name_relative> [\S][\s\S]*? )
                    )
                [\s]*
            ''',
            string=line,
            flags=re.ASCII | re.VERBOSE,
        )

    def process_rules_inclusion_line(self, rules_inclusion_match: re.Match,
                                     rules_file_name: str, cmd_name: str, line_number: int):
        included_file_name_relative = rules_inclusion_match.group('included_file_name_relative')
        if included_file_name_relative is not None:
            included_file_name = os.path.join(os.path.dirname(rules_file_name), included_file_name_relative)
        else:
            included_file_name = rules_inclusion_match.group('included_file_name')

        included_file_name = os.path.normpath(included_file_name)

        try:
            with open(included_file_name, 'r', encoding='utf-8') as included_file:
                replacement_rules = included_file.read()
        except FileNotFoundError:
            ReplacementAuthority.print_error(f'file `{included_file_name}` (relative to terminal) not found',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        for opened_file_name in self._opened_file_names:
            if os.path.samefile(opened_file_name, included_file_name):
                recursive_inclusion_string = ' includes '.join(
                    f'`{opened_file_name}`'
                    for opened_file_name in [*self._opened_file_names, included_file_name]
                )
                ReplacementAuthority.print_error(f'recursive inclusion: {recursive_inclusion_string}',
                                                 rules_file_name, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

        self._opened_file_names.append(included_file_name)
        self.legislate(replacement_rules, rules_file_name=included_file_name, cmd_name=cmd_name)

    @staticmethod
    def compute_class_declaration_match(line: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                (?P<class_name> [A-Za-z]+ ) [:]
                [\s]+
                [#] (?P<id_> [a-z0-9-.]+ )
            ''',
            string=line,
            flags=re.ASCII | re.VERBOSE,
        )

    def process_class_declaration_line(self, class_declaration_match: re.Match,
                                       rules_file_name: str, line_number: int) -> 'PostClassDeclarationState':
        class_name = class_declaration_match.group('class_name')
        id_ = class_declaration_match.group('id_')

        if class_name == 'ReplacementSequence':
            replacement = ReplacementSequence(id_, self._verbose_mode_enabled)
        elif class_name == 'PlaceholderMarkerReplacement':
            replacement = PlaceholderMarkerReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'PlaceholderProtectionReplacement':
            replacement = PlaceholderProtectionReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'PlaceholderUnprotectionReplacement':
            replacement = PlaceholderUnprotectionReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'DeIndentationReplacement':
            replacement = DeIndentationReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'OrdinaryDictionaryReplacement':
            replacement = OrdinaryDictionaryReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'RegexDictionaryReplacement':
            replacement = RegexDictionaryReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'FixedDelimitersReplacement':
            replacement = FixedDelimitersReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'ExtensibleFenceReplacement':
            replacement = ExtensibleFenceReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'PartitioningReplacement':
            replacement = PartitioningReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'InlineAssortedDelimitersReplacement':
            replacement = InlineAssortedDelimitersReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'HeadingReplacement':
            replacement = HeadingReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'ReferenceDefinitionReplacement':
            replacement = ReferenceDefinitionReplacement(id_, self._reference_master, self._verbose_mode_enabled)
        elif class_name == 'SpecifiedImageReplacement':
            replacement = SpecifiedImageReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'ReferencedImageReplacement':
            replacement = ReferencedImageReplacement(id_, self._reference_master, self._verbose_mode_enabled)
        elif class_name == 'ExplicitLinkReplacement':
            replacement = ExplicitLinkReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'SpecifiedLinkReplacement':
            replacement = SpecifiedLinkReplacement(id_, self._verbose_mode_enabled)
        elif class_name == 'ReferencedLinkReplacement':
            replacement = ReferencedLinkReplacement(id_, self._reference_master, self._verbose_mode_enabled)
        else:
            ReplacementAuthority.print_error(f'unrecognised replacement class `{class_name}`',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if id_ in self._replacement_from_id:
            ReplacementAuthority.print_error(f'replacement already declared with id `{id_}`',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        line_number_range_start = line_number

        return PostClassDeclarationState(class_name, replacement, line_number_range_start)

    @staticmethod
    def compute_attribute_declaration_match(line: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [-][ ] (?P<attribute_name> [a-z_]+ ) [:]
                (?P<partial_attribute_value> [\s\S]* )
            ''',
            string=line,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def process_attribute_declaration_line(attribute_declaration_match: re.Match, class_name: str,
                                           replacement: 'Replacement', attribute_value: Optional[str],
                                           rules_file_name: str, line_number: int,
                                           ) -> 'PostAttributeDeclarationState':
        if replacement is None:
            ReplacementAuthority.print_error(f'attribute declaration without an active class declaration',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        attribute_name = attribute_declaration_match.group('attribute_name')
        if attribute_name not in replacement.attribute_names:
            ReplacementAuthority.print_error(f'unrecognised attribute `{attribute_name}` for `{class_name}`',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        partial_attribute_value = attribute_declaration_match.group('partial_attribute_value')
        attribute_value = none_to_empty_string(attribute_value) + partial_attribute_value

        line_number_range_start = line_number

        return PostAttributeDeclarationState(attribute_name, attribute_value, line_number_range_start)

    @staticmethod
    def compute_substitution_declaration_match(line: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'[*][ ] (?P<partial_substitution> [\s\S]* )',
            string=line,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def process_substitution_declaration_line(replacement: Optional['Replacement'],
                                              substitution_declaration_match: re.Match, substitution: Optional[str],
                                              rules_file_name: str, line_number: int,
                                              ) -> 'PostSubstitutionDeclarationState':
        if replacement is None:
            ReplacementAuthority.print_error(f'substitution declaration without an active class declaration',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        partial_substitution = substitution_declaration_match.group('partial_substitution')
        substitution = none_to_empty_string(substitution) + partial_substitution

        line_number_range_start = line_number

        return PostSubstitutionDeclarationState(substitution, line_number_range_start)

    @staticmethod
    def compute_continuation_match(line: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'(?P<continuation> [\s]+ [\S][\s\S]* )',
            string=line,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def process_continuation_line(continuation_match: re.Match, attribute_name: Optional[str],
                                  attribute_value: Optional[str], substitution: Optional[str],
                                  rules_file_name: str, line_number: int,
                                  ) -> 'PostContinuationState':
        continuation = continuation_match.group('continuation')

        if attribute_name is not None:
            attribute_value = none_to_empty_string(attribute_value) + '\n' + continuation
        elif substitution is not None:
            substitution = substitution + '\n' + continuation
        else:
            ReplacementAuthority.print_error('continuation only allowed for attribute or substitution declarations',
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        return PostContinuationState(attribute_value, substitution)

    @staticmethod
    def compute_allowed_flag_matches(attribute_value: str) -> Iterable[re.Match]:
        return re.finditer(
            pattern=r'''
                (?P<whitespace_only> \A [\s]* \Z )
                    |
                (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
                    |
                [\s]*
                (?:
                    (?P<flag_letter> [a-z] ) = (?P<flag_name> [A-Z_]+ ) (?= [\s] | \Z )
                        |
                    (?P<invalid_syntax> [\S]+ )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_allowed_flags(replacement: 'Replacement', attribute_value: str,
                            rules_file_name: str, line_number_range_start: int, line_number: int):
        flag_name_from_letter: dict[str, str] = {}

        for allowed_flag_match in ReplacementAuthority.compute_allowed_flag_matches(attribute_value):
            if allowed_flag_match.group('whitespace_only') is not None:
                ReplacementAuthority.print_error(f'invalid specification `` for attribute `allowed_flags`',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            invalid_syntax = allowed_flag_match.group('invalid_syntax')
            if invalid_syntax is not None:
                ReplacementAuthority.print_error(
                    f'invalid specification `{invalid_syntax}` for attribute `allowed_flags`',
                    rules_file_name, line_number_range_start, line_number,
                )
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            if allowed_flag_match.group('none_keyword') is not None:
                return

            flag_letter = allowed_flag_match.group('flag_letter')
            flag_name = allowed_flag_match.group('flag_name')
            flag_name_from_letter[flag_letter] = flag_name

        replacement.flag_name_from_letter = flag_name_from_letter

    @staticmethod
    def compute_apply_mode_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<apply_mode> SIMULTANEOUS | SEQUENTIAL )
                        |
                    (?P<invalid_value> [\s\S]*? )
                    )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE
        )

    @staticmethod
    def stage_apply_mode(replacement: 'Replacement', attribute_value: str,
                         rules_file_name: str, line_number_range_start: int, line_number: int):
        apply_mode_match = ReplacementAuthority.compute_apply_mode_match(attribute_value)

        invalid_value = apply_mode_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `apply_mode`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        apply_mode = apply_mode_match.group('apply_mode')
        replacement.apply_substitutions_simultaneously = apply_mode == 'SIMULTANEOUS'

    @staticmethod
    def compute_attribute_specifications_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
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
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_attribute_specifications(replacement: 'Replacement', attribute_value: str,
                                       rules_file_name: str, line_number_range_start: int, line_number: int):
        attribute_specifications_match = ReplacementAuthority.compute_attribute_specifications_match(attribute_value)

        invalid_value = attribute_specifications_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(
                f'invalid value `{invalid_value}` for attribute `attribute_specifications`',
                rules_file_name, line_number_range_start, line_number,
            )
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if attribute_specifications_match.group('none_keyword') is not None:
            return

        if attribute_specifications_match.group('empty_keyword') is not None:
            replacement.attribute_specifications = ''
            return

        attribute_specifications = attribute_specifications_match.group('attribute_specifications')
        replacement.attribute_specifications = attribute_specifications

    @staticmethod
    def compute_closing_delimiter_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<closing_delimiter> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_closing_delimiter(replacement: 'Replacement', attribute_value: str,
                                rules_file_name: str, line_number_range_start: int, line_number: int):
        closing_delimiter_match = ReplacementAuthority.compute_closing_delimiter_match(attribute_value)

        invalid_value = closing_delimiter_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `closing_delimiter`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        closing_delimiter = closing_delimiter_match.group('closing_delimiter')
        replacement.closing_delimiter = closing_delimiter

    @staticmethod
    def compute_concluding_replacement_matches(attribute_value: str) -> Iterable[re.Match]:
        return re.finditer(
            pattern=r'''
                (?P<whitespace_only> \A [\s]* \Z )
                    |
                (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
                    |
                (?:
                    [#] (?P<id_> [a-z0-9-.]+ ) (?= [\s] | \Z )
                        |
                    (?P<invalid_syntax> [\S]+ )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    def stage_concluding_replacements(self, replacement: 'Replacement', attribute_value: str,
                                      rules_file_name: str, line_number_range_start: int, line_number: int):
        concluding_replacements: list['Replacement'] = []

        concluding_replacement_matches = ReplacementAuthority.compute_concluding_replacement_matches(attribute_value)
        for concluding_replacement_match in concluding_replacement_matches:
            if concluding_replacement_match.group('whitespace_only') is not None:
                ReplacementAuthority.print_error(f'invalid specification `` for attribute `concluding_replacements`',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            invalid_syntax = concluding_replacement_match.group('invalid_syntax')
            if invalid_syntax is not None:
                ReplacementAuthority.print_error(
                    f'invalid specification `{invalid_syntax}` for attribute `concluding_replacements`',
                    rules_file_name, line_number_range_start, line_number,
                )
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            if concluding_replacement_match.group('none_keyword') is not None:
                return

            concluding_replacement_id = concluding_replacement_match.group('id_')
            if concluding_replacement_id == replacement.id_:
                concluding_replacement = replacement
            else:
                try:
                    concluding_replacement = self._replacement_from_id[concluding_replacement_id]
                except KeyError:
                    ReplacementAuthority.print_error(f'undefined replacement `#{concluding_replacement_id}`',
                                                     rules_file_name, line_number_range_start, line_number)
                    sys.exit(GENERIC_ERROR_EXIT_CODE)

            concluding_replacements.append(concluding_replacement)

        replacement.concluding_replacements = concluding_replacements

    @staticmethod
    def compute_content_replacement_matches(attribute_value: str) -> Iterable[re.Match]:
        return re.finditer(
            pattern=r'''
                (?P<whitespace_only> \A [\s]* \Z )
                    |
                (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
                    |
                (?:
                    [#] (?P<id_> [a-z0-9-.]+ ) (?= [\s] | \Z )
                        |
                    (?P<invalid_syntax> [\S]+ )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    def stage_content_replacements(self, replacement: 'Replacement', attribute_value: str,
                                   rules_file_name: str, line_number_range_start: int, line_number: int):
        content_replacements: list['Replacement'] = []

        for content_replacement_match in ReplacementAuthority.compute_content_replacement_matches(attribute_value):
            if content_replacement_match.group('whitespace_only') is not None:
                ReplacementAuthority.print_error(f'invalid specification `` for attribute `content_replacements`',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            invalid_syntax = content_replacement_match.group('invalid_syntax')
            if invalid_syntax is not None:
                ReplacementAuthority.print_error(
                    f'invalid specification `{invalid_syntax}` for attribute `content_replacements`',
                    rules_file_name, line_number_range_start, line_number,
                )
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            if content_replacement_match.group('none_keyword') is not None:
                return

            content_replacement_id = content_replacement_match.group('id_')
            if content_replacement_id == replacement.id_:
                content_replacement = replacement
            else:
                try:
                    content_replacement = self._replacement_from_id[content_replacement_id]
                except KeyError:
                    ReplacementAuthority.print_error(f'undefined replacement `#{content_replacement_id}`',
                                                     rules_file_name, line_number_range_start, line_number)
                    sys.exit(GENERIC_ERROR_EXIT_CODE)

            content_replacements.append(content_replacement)

        replacement.content_replacements = content_replacements

    @staticmethod
    def compute_delimiter_conversion_matches(attribute_value: str) -> Iterable[re.Match]:
        return re.finditer(
            pattern=r'''
                (?P<whitespace_only> \A [\s]* \Z )
                    |
                [\s]*
                (?:
                    (?P<delimiter>
                    (?P<delimiter_character> [\S] ) (?P=delimiter_character)?
                )
                    = (?P<tag_name> [a-z0-9]+ ) (?= [\s] | \Z )
                    |
                (?P<invalid_syntax> [\S]+ )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_delimiter_conversion(replacement: 'Replacement', attribute_value: str,
                                   rules_file_name: str, line_number_range_start: int, line_number: int):
        tag_name_from_delimiter_length_from_character: dict[str, dict[int, str]] = {}

        for delimiter_conversion_match in ReplacementAuthority.compute_delimiter_conversion_matches(attribute_value):
            if delimiter_conversion_match.group('whitespace_only') is not None:
                ReplacementAuthority.print_error(f'invalid specification `` for attribute `delimiter_conversion`',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            invalid_syntax = delimiter_conversion_match.group('invalid_syntax')
            if invalid_syntax is not None:
                ReplacementAuthority.print_error(
                    f'invalid specification `{invalid_syntax}` for attribute `delimiter_conversion`',
                    rules_file_name, line_number_range_start, line_number,
                )
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            character = delimiter_conversion_match.group('delimiter_character')
            length = len(delimiter_conversion_match.group('delimiter'))
            tag_name = delimiter_conversion_match.group('tag_name')

            if character not in tag_name_from_delimiter_length_from_character:
                tag_name_from_delimiter_length_from_character[character]: dict[int, str] = {}

            tag_name_from_delimiter_length_from_character[character][length] = tag_name

        replacement.tag_name_from_delimiter_length_from_character = tag_name_from_delimiter_length_from_character

    @staticmethod
    def compute_ending_pattern_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<ending_pattern> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_ending_pattern(replacement: 'Replacement', attribute_value: str,
                             rules_file_name: str, line_number_range_start: int, line_number: int):
        ending_pattern_match = ReplacementAuthority.compute_ending_pattern_match(attribute_value)

        invalid_value = ending_pattern_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `ending_pattern`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if ending_pattern_match.group('none_keyword') is not None:
            return

        ending_pattern = ending_pattern_match.group('ending_pattern')

        try:
            ending_pattern_compiled = re.compile(pattern=ending_pattern, flags=re.ASCII | re.MULTILINE | re.VERBOSE)
        except re.error as pattern_exception:
            ReplacementAuthority.print_error(f'bad regex pattern `{ending_pattern}`',
                                             rules_file_name, line_number_range_start, line_number)
            ReplacementAuthority.print_traceback(pattern_exception)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if len(ending_pattern_compiled.groupindex) > 0:
            ReplacementAuthority.print_error(f'named capture groups not allowed in `ending_pattern`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        replacement.ending_pattern = ending_pattern

    @staticmethod
    def compute_epilogue_delimiter_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<epilogue_delimiter> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_epilogue_delimiter(replacement: 'Replacement', attribute_value: str,
                                 rules_file_name: str, line_number_range_start: int, line_number: int):
        epilogue_delimiter_match = ReplacementAuthority.compute_epilogue_delimiter_match(attribute_value)

        invalid_value = epilogue_delimiter_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `epilogue_delimiter`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if epilogue_delimiter_match.group('none_keyword') is not None:
            return

        epilogue_delimiter = epilogue_delimiter_match.group('epilogue_delimiter')
        replacement.epilogue_delimiter = epilogue_delimiter

    @staticmethod
    def compute_extensible_delimiter_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
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
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_extensible_delimiter(replacement: 'Replacement', attribute_value: str,
                                   rules_file_name: str, line_number_range_start: int, line_number: int):
        extensible_delimiter_match = ReplacementAuthority.compute_extensible_delimiter_match(attribute_value)

        invalid_value = extensible_delimiter_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(
                f'invalid value `{invalid_value}` not a character repeated for attribute `extensible_delimiter`',
                rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        extensible_delimiter_character = extensible_delimiter_match.group('extensible_delimiter_character')
        extensible_delimiter = extensible_delimiter_match.group('extensible_delimiter')
        extensible_delimiter_min_length = len(extensible_delimiter)

        replacement.extensible_delimiter_character = extensible_delimiter_character
        replacement.extensible_delimiter_min_length = extensible_delimiter_min_length

    @staticmethod
    def compute_negative_flag_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<negative_flag_name> [A-Z_]+ )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_negative_flag(replacement: 'Replacement', attribute_value: str,
                            rules_file_name: str, line_number_range_start: int, line_number: int):
        negative_flag_match = ReplacementAuthority.compute_negative_flag_match(attribute_value)

        invalid_value = negative_flag_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `negative_flag`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if negative_flag_match.group('none_keyword') is not None:
            return

        negative_flag_name = negative_flag_match.group('negative_flag_name')
        replacement.negative_flag_name = negative_flag_name

    @staticmethod
    def compute_opening_delimiter_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<opening_delimiter> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_opening_delimiter(replacement: 'Replacement', attribute_value: str,
                                rules_file_name: str, line_number_range_start: int, line_number: int):
        opening_delimiter_match = ReplacementAuthority.compute_opening_delimiter_match(attribute_value)

        invalid_value = opening_delimiter_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `opening_delimiter`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        opening_delimiter = opening_delimiter_match.group('opening_delimiter')
        replacement.opening_delimiter = opening_delimiter

    @staticmethod
    def compute_positive_flag_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<positive_flag_name> [A-Z_]+ )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_positive_flag(replacement: 'Replacement', attribute_value: str,
                            rules_file_name: str, line_number_range_start: int, line_number: int):
        positive_flag_match = ReplacementAuthority.compute_positive_flag_match(attribute_value)

        invalid_value = positive_flag_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `positive_flag`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if positive_flag_match.group('none_keyword') is not None:
            return

        positive_flag_name = positive_flag_match.group('positive_flag_name')
        replacement.positive_flag_name = positive_flag_name

    @staticmethod
    def compute_prohibited_content_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<prohibited_content> BLOCKS | ANCHORED_BLOCKS )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_prohibited_content(replacement: 'Replacement', attribute_value: str,
                                 rules_file_name: str, line_number_range_start: int, line_number: int):
        prohibited_content_match = ReplacementAuthority.compute_prohibited_content_match(attribute_value)

        invalid_value = prohibited_content_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `prohibited_content`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if prohibited_content_match.group('none_keyword') is not None:
            return

        prohibited_content = prohibited_content_match.group('prohibited_content')
        require_anchoring = prohibited_content == 'ANCHORED_BLOCKS'
        prohibited_content_regex = build_block_tag_regex(require_anchoring)
        replacement.prohibited_content_regex = prohibited_content_regex

    @staticmethod
    def compute_prologue_delimiter_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<prologue_delimiter> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_prologue_delimiter(replacement: 'Replacement', attribute_value: str,
                                 rules_file_name: str, line_number_range_start: int, line_number: int):
        prologue_delimiter_match = ReplacementAuthority.compute_prologue_delimiter_match(attribute_value)

        invalid_value = prologue_delimiter_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `prologue_delimiter`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if prologue_delimiter_match.group('none_keyword') is not None:
            return

        prologue_delimiter = prologue_delimiter_match.group('prologue_delimiter')
        replacement.prologue_delimiter = prologue_delimiter

    @staticmethod
    def compute_queue_position_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<root_keyword> ROOT )
                        |
                    (?P<queue_position_type> BEFORE | AFTER )
                    [ ]
                    [#] (?P<queue_reference_id> [a-z-.]+ )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    def stage_queue_position(self, replacement: 'Replacement', attribute_value: str,
                             rules_file_name: str, line_number_range_start: int, line_number: int):
        queue_position_match = ReplacementAuthority.compute_queue_position_match(attribute_value)

        invalid_value = queue_position_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `queue_position`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if queue_position_match.group('none_keyword') is not None:
            return

        if queue_position_match.group('root_keyword') is not None:
            if self._root_replacement_id is not None:
                ReplacementAuthority.print_error(f'root replacement already declared (`#{self._root_replacement_id}`)',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            replacement.queue_position_type = 'ROOT'
            replacement.queue_reference_replacement = None
            return

        queue_position_type = queue_position_match.group('queue_position_type')
        queue_reference_id = queue_position_match.group('queue_reference_id')

        if queue_reference_id == replacement.id_:
            ReplacementAuthority.print_error(f'self-referential `queue_position`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        try:
            queue_reference_replacement = self._replacement_from_id[queue_reference_id]
        except KeyError:
            ReplacementAuthority.print_error(f'undefined replacement `#{queue_reference_id}`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if queue_reference_replacement not in self._replacement_queue:
            ReplacementAuthority.print_error(f'replacement `#{queue_reference_id}` not in queue',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        replacement.queue_position_type = queue_position_type
        replacement.queue_reference_replacement = queue_reference_replacement

    @staticmethod
    def compute_replacement_matches(attribute_value: str) -> Iterable[re.Match]:
        return re.finditer(
            pattern=r'''
                (?P<whitespace_only> \A [\s]* \Z )
                    |
                (?P<none_keyword> \A [\s]* NONE [\s]* \Z )
                    |
                (?:
                    [#] (?P<id_> [a-z0-9-.]+ ) (?= [\s] | \Z )
                        |
                    (?P<invalid_syntax> [\S]+ )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    def stage_replacements(self, replacement: 'Replacement', attribute_value: str,
                           rules_file_name: str, line_number_range_start: int, line_number: int):
        matched_replacements: list['Replacement'] = []

        for replacement_match in ReplacementAuthority.compute_replacement_matches(attribute_value):
            if replacement_match.group('whitespace_only') is not None:
                ReplacementAuthority.print_error(f'invalid specification `` for attribute `replacements`',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            invalid_syntax = replacement_match.group('invalid_syntax')
            if invalid_syntax is not None:
                ReplacementAuthority.print_error(
                    f'invalid specification `{invalid_syntax}` for attribute `replacements`',
                    rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

            if replacement_match.group('none_keyword') is not None:
                return

            matched_replacement_id = replacement_match.group('id_')
            if matched_replacement_id == replacement.id_:
                matched_replacement = replacement
            else:
                try:
                    matched_replacement = self._replacement_from_id[matched_replacement_id]
                except KeyError:
                    ReplacementAuthority.print_error(f'undefined replacement `#{matched_replacement_id}`',
                                                     rules_file_name, line_number_range_start, line_number)
                    sys.exit(GENERIC_ERROR_EXIT_CODE)

            matched_replacements.append(matched_replacement)

        replacement.replacements = matched_replacements

    @staticmethod
    def compute_starting_pattern_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<starting_pattern> [\S][\s\S]*? )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_starting_pattern(replacement: 'Replacement', attribute_value: str,
                               rules_file_name: str, line_number_range_start: int, line_number: int):
        starting_pattern_match = ReplacementAuthority.compute_starting_pattern_match(attribute_value)

        invalid_value = starting_pattern_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `starting_pattern`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        starting_pattern = starting_pattern_match.group('starting_pattern')

        try:
            starting_pattern_compiled = re.compile(pattern=starting_pattern, flags=re.ASCII | re.MULTILINE | re.VERBOSE)
        except re.error as pattern_exception:
            ReplacementAuthority.print_error(f'bad regex pattern `{starting_pattern}`',
                                             rules_file_name, line_number_range_start, line_number)
            ReplacementAuthority.print_traceback(pattern_exception)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if len(starting_pattern_compiled.groupindex) > 0:
            ReplacementAuthority.print_error(f'named capture groups not allowed in `starting_pattern`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        replacement.starting_pattern = starting_pattern

    @staticmethod
    def compute_syntax_type_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<syntax_type> BLOCK | INLINE )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_syntax_type(replacement: 'Replacement', attribute_value: str,
                          rules_file_name: str, line_number_range_start: int, line_number: int):
        syntax_type_match = ReplacementAuthority.compute_syntax_type_match(attribute_value)

        invalid_value = syntax_type_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `syntax_type`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        syntax_type = syntax_type_match.group('syntax_type')
        replacement.syntax_type_is_block = syntax_type == 'BLOCK'

    @staticmethod
    def compute_tag_name_match(attribute_value: str) -> Optional[re.Match]:
        return re.fullmatch(
            pattern=r'''
                [\s]*
                (?:
                    (?P<none_keyword> NONE )
                        |
                    (?P<tag_name> [a-z0-9]+ )
                        |
                    (?P<invalid_value> [\s\S]*? )
                )
                [\s]*
            ''',
            string=attribute_value,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_tag_name(replacement: 'Replacement', attribute_value: str,
                       rules_file_name: str, line_number_range_start: int, line_number: int):
        tag_name_match = ReplacementAuthority.compute_tag_name_match(attribute_value)

        invalid_value = tag_name_match.group('invalid_value')
        if invalid_value is not None:
            ReplacementAuthority.print_error(f'invalid value `{invalid_value}` for attribute `tag_name`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        if tag_name_match.group('none_keyword') is not None:
            return

        tag_name = tag_name_match.group('tag_name')
        replacement.tag_name = tag_name

    @staticmethod
    def compute_substitution_match(substitution: str) -> Optional[re.Match]:
        substitution_delimiters: list[str] = re.findall(pattern='[-]{2,}[>]', string=substitution)
        if len(substitution_delimiters) == 0:
            return None

        longest_substitution_delimiter = max(substitution_delimiters, key=len)
        return re.fullmatch(
            pattern=fr'''
                [\s]*
                    (?:
                        "(?P<double_quoted_pattern> [\s\S]*? )"
                            |
                        '(?P<single_quoted_pattern> [\s\S]*? )'
                            |
                        (?P<bare_pattern> [\s\S]*? )
                    )
                [\s]*
                    {re.escape(longest_substitution_delimiter)}
                    [\s]*
                    (?:
                        (?P<cmd_version_keyword> CMD_VERSION )
                            |
                        (?P<cmd_name_keyword> CMD_NAME )
                            |
                        (?P<cmd_basename_keyword> CMD_BASENAME )
                            |
                        (?P<clean_url_keyword> CLEAN_URL )
                            |
                        "(?P<double_quoted_substitute> [\s\S]*? )"
                            |
                        '(?P<single_quoted_substitute> [\s\S]*? )'
                            |
                        (?P<bare_substitute> [\s\S]*? )
                    )
                [\s]*
            ''',
            string=substitution,
            flags=re.ASCII | re.VERBOSE,
        )

    @staticmethod
    def stage_ordinary_substitution(replacement: 'ReplacementWithSubstitutions', substitution: str,
                                    rules_file_name: str, cmd_name: str,
                                    line_number_range_start: int, line_number: int):
        substitution_match = ReplacementAuthority.compute_substitution_match(substitution)
        if substitution_match is None:
            ReplacementAuthority.print_error(f'missing delimiter `-->` in substitution `{substitution}`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        double_quoted_pattern = substitution_match.group('double_quoted_pattern')
        if double_quoted_pattern is not None:
            pattern = double_quoted_pattern
        else:
            single_quoted_pattern = substitution_match.group('single_quoted_pattern')
            if single_quoted_pattern is not None:
                pattern = single_quoted_pattern
            else:
                pattern = substitution_match.group('bare_pattern')

        if substitution_match.group('cmd_version_keyword') is not None:
            substitute = __version__
        elif substitution_match.group('cmd_name_keyword') is not None:
            substitute = cmd_name
        elif substitution_match.group('cmd_basename_keyword') is not None:
            substitute = extract_basename(cmd_name)
        elif substitution_match.group('clean_url_keyword') is not None:
            substitute = make_clean_url(cmd_name)
        else:
            double_quoted_substitute = substitution_match.group('double_quoted_substitute')
            if double_quoted_substitute is not None:
                substitute = double_quoted_substitute
            else:
                single_quoted_substitute = substitution_match.group('single_quoted_substitute')
                if single_quoted_substitute is not None:
                    substitute = single_quoted_substitute
                else:
                    substitute = substitution_match.group('bare_substitute')

        replacement.add_substitution(pattern, substitute)

    @staticmethod
    def stage_regex_substitution(replacement: 'ReplacementWithSubstitutions', substitution: str,
                                 rules_file_name: str, cmd_name: str, line_number_range_start: int, line_number: int):
        substitution_match = ReplacementAuthority.compute_substitution_match(substitution)
        if substitution_match is None:
            ReplacementAuthority.print_error(f'missing delimiter `-->` in substitution `{substitution}`',
                                             rules_file_name, line_number_range_start, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        double_quoted_pattern = substitution_match.group('double_quoted_pattern')
        if double_quoted_pattern is not None:
            pattern = double_quoted_pattern
        else:
            single_quoted_pattern = substitution_match.group('single_quoted_pattern')
            if single_quoted_pattern is not None:
                pattern = single_quoted_pattern
            else:
                pattern = substitution_match.group('bare_pattern')

        if substitution_match.group('cmd_version_keyword') is not None:
            substitute = escape_regex_substitute(__version__)
        elif substitution_match.group('cmd_name_keyword') is not None:
            substitute = escape_regex_substitute(cmd_name)
        elif substitution_match.group('cmd_basename_keyword') is not None:
            substitute = escape_regex_substitute(extract_basename(cmd_name))
        elif substitution_match.group('clean_url_keyword') is not None:
            substitute = escape_regex_substitute(make_clean_url(cmd_name))
        else:
            double_quoted_substitute = substitution_match.group('double_quoted_substitute')
            if double_quoted_substitute is not None:
                substitute = double_quoted_substitute
            else:
                single_quoted_substitute = substitution_match.group('single_quoted_substitute')
                if single_quoted_substitute is not None:
                    substitute = single_quoted_substitute
                else:
                    substitute = substitution_match.group('bare_substitute')

        try:
            pattern_compiled = re.compile(pattern=pattern, flags=re.ASCII | re.MULTILINE | re.VERBOSE)
        except re.error as pattern_exception:
            ReplacementAuthority.print_error(f'bad regex pattern `{pattern}`',
                                             rules_file_name, line_number_range_start, line_number)
            ReplacementAuthority.print_traceback(pattern_exception)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        try:
            re.sub(pattern=pattern_compiled, repl=substitute, string='')
        except re.error as substitute_exception:
            ReplacementAuthority.print_error(f'bad regex substitute `{substitute}` for pattern `{pattern}`',
                                             rules_file_name, line_number_range_start, line_number)
            ReplacementAuthority.print_traceback(substitute_exception)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        replacement.add_substitution(pattern, substitute)

    def stage(self, class_name: str, replacement: 'Replacement',
              attribute_name: str, attribute_value: str, substitution: str,
              rules_file_name: str, cmd_name: str, line_number_range_start: int, line_number: int) -> 'PostStageState':
        if substitution is not None:  # staging a substitution
            if class_name == 'OrdinaryDictionaryReplacement':
                assert isinstance(replacement, ReplacementWithSubstitutions)
                ReplacementAuthority.stage_ordinary_substitution(replacement, substitution,
                                                                 rules_file_name, cmd_name,
                                                                 line_number_range_start, line_number)
            elif class_name == 'RegexDictionaryReplacement':
                assert isinstance(replacement, ReplacementWithSubstitutions)
                ReplacementAuthority.stage_regex_substitution(replacement, substitution,
                                                              rules_file_name, cmd_name,
                                                              line_number_range_start, line_number)
            else:
                ReplacementAuthority.print_error(f'class `{class_name}` does not allow substitutions',
                                                 rules_file_name, line_number_range_start, line_number)
                sys.exit(GENERIC_ERROR_EXIT_CODE)

        else:  # staging an attribute declaration
            if attribute_name == 'allowed_flags':
                ReplacementAuthority.stage_allowed_flags(replacement, attribute_value,
                                                         rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'apply_mode':
                ReplacementAuthority.stage_apply_mode(replacement, attribute_value,
                                                      rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'attribute_specifications':
                ReplacementAuthority.stage_attribute_specifications(replacement, attribute_value,
                                                                    rules_file_name,
                                                                    line_number_range_start, line_number)
            elif attribute_name == 'closing_delimiter':
                self.stage_closing_delimiter(replacement, attribute_value,
                                             rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'concluding_replacements':
                self.stage_concluding_replacements(replacement, attribute_value,
                                                   rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'content_replacements':
                self.stage_content_replacements(replacement, attribute_value,
                                                rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'delimiter_conversion':
                ReplacementAuthority.stage_delimiter_conversion(replacement, attribute_value,
                                                                rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'ending_pattern':
                ReplacementAuthority.stage_ending_pattern(replacement, attribute_value,
                                                          rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'epilogue_delimiter':
                ReplacementAuthority.stage_epilogue_delimiter(replacement, attribute_value,
                                                              rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'extensible_delimiter':
                ReplacementAuthority.stage_extensible_delimiter(replacement, attribute_value,
                                                                rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'negative_flag':
                ReplacementAuthority.stage_negative_flag(replacement, attribute_value,
                                                         rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'opening_delimiter':
                ReplacementAuthority.stage_opening_delimiter(replacement, attribute_value,
                                                             rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'positive_flag':
                ReplacementAuthority.stage_positive_flag(replacement, attribute_value,
                                                         rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'prohibited_content':
                ReplacementAuthority.stage_prohibited_content(replacement, attribute_value,
                                                              rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'prologue_delimiter':
                ReplacementAuthority.stage_prologue_delimiter(replacement, attribute_value,
                                                              rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'queue_position':
                self.stage_queue_position(replacement, attribute_value,
                                          rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'replacements':
                self.stage_replacements(replacement, attribute_value,
                                        rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'starting_pattern':
                ReplacementAuthority.stage_starting_pattern(replacement, attribute_value,
                                                            rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'syntax_type':
                ReplacementAuthority.stage_syntax_type(replacement, attribute_value,
                                                       rules_file_name, line_number_range_start, line_number)
            elif attribute_name == 'tag_name':
                ReplacementAuthority.stage_tag_name(replacement, attribute_value,
                                                    rules_file_name, line_number_range_start, line_number)

        return PostStageState(attribute_name=None, attribute_value=None, substitution=None,
                              line_number_range_start=None)

    def commit(self, class_name: str, replacement: 'Replacement',
               rules_file_name: str, line_number: int) -> 'PostCommitState':
        try:
            replacement.commit()
        except MissingAttributeException as exception:
            missing_attribute = exception.missing_attribute
            ReplacementAuthority.print_error(f'missing attribute `{missing_attribute}` for {class_name}',
                                             rules_file_name, line_number)
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
            queue_reference_index = self._replacement_queue.index(queue_reference_replacement)
            if queue_position_type == 'BEFORE':
                insertion_index = queue_reference_index
            elif queue_position_type == 'AFTER':
                insertion_index = queue_reference_index + 1
            else:
                insertion_index = None
            self._replacement_queue.insert(insertion_index, replacement)

        return PostCommitState(class_name=None, replacement=None, attribute_name=None, attribute_value=None,
                               substitution=None, line_number_range_start=None)

    def legislate(self, replacement_rules: str, rules_file_name: str, cmd_name: str):
        if replacement_rules is None:
            return

        class_name: Optional[str] = None
        replacement: Optional['Replacement'] = None
        attribute_name: Optional[str] = None
        attribute_value: Optional[str] = None
        substitution: Optional[str] = None
        line_number_range_start: Optional[int] = None
        line_number: int = 0

        for line_number, line in enumerate(replacement_rules.splitlines(), start=1):
            if ReplacementAuthority.is_whitespace_only(line):
                if attribute_name is not None or substitution is not None:
                    attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                                   rules_file_name, cmd_name, line_number_range_start, line_number)
                    )
                if replacement is not None:
                    class_name, replacement, attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.commit(class_name, replacement, rules_file_name, line_number)
                    )
                continue

            if ReplacementAuthority.is_comment(line):
                continue

            rules_inclusion_match = ReplacementAuthority.compute_rules_inclusion_match(line)
            if rules_inclusion_match is not None:
                if attribute_name is not None or substitution is not None:
                    attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                                   rules_file_name, cmd_name, line_number_range_start, line_number)
                    )
                if replacement is not None:
                    class_name, replacement, attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.commit(class_name, replacement, rules_file_name, line_number)
                    )
                self.process_rules_inclusion_line(rules_inclusion_match, rules_file_name, cmd_name, line_number)
                continue

            class_declaration_match = ReplacementAuthority.compute_class_declaration_match(line)
            if class_declaration_match is not None:
                if attribute_name is not None or substitution is not None:
                    attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                                   rules_file_name, cmd_name, line_number_range_start, line_number)
                    )
                if replacement is not None:
                    class_name, replacement, attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.commit(class_name, replacement, rules_file_name, line_number)
                    )
                class_name, replacement, line_number_range_start = (
                    self.process_class_declaration_line(class_declaration_match, rules_file_name, line_number)
                )
                continue

            attribute_declaration_match = ReplacementAuthority.compute_attribute_declaration_match(line)
            if attribute_declaration_match is not None:
                if attribute_name is not None or substitution is not None:
                    attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                                   rules_file_name, cmd_name, line_number_range_start, line_number)
                    )
                attribute_name, attribute_value, line_number_range_start = (
                    ReplacementAuthority.process_attribute_declaration_line(
                        attribute_declaration_match, class_name, replacement, attribute_value,
                        rules_file_name, line_number,
                    )
                )
                continue

            substitution_declaration_match = ReplacementAuthority.compute_substitution_declaration_match(line)
            if substitution_declaration_match is not None:
                if attribute_name is not None or substitution is not None:
                    attribute_name, attribute_value, substitution, line_number_range_start = (
                        self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                                   rules_file_name, cmd_name, line_number_range_start, line_number)
                    )
                substitution, line_number_range_start = (
                    ReplacementAuthority.process_substitution_declaration_line(
                        replacement, substitution_declaration_match, substitution,
                        rules_file_name, line_number,
                    )
                )
                continue

            continuation_match = ReplacementAuthority.compute_continuation_match(line)
            if continuation_match is not None:
                attribute_value, substitution = (
                    ReplacementAuthority.process_continuation_line(
                        continuation_match, attribute_name, attribute_value, substitution,
                        rules_file_name, line_number,
                    )
                )
                continue

            ReplacementAuthority.print_error('invalid syntax\n\n' + CMD_REPLACEMENT_SYNTAX_HELP,
                                             rules_file_name, line_number)
            sys.exit(GENERIC_ERROR_EXIT_CODE)

        # At end of file
        if attribute_name is not None or substitution is not None:
            self.stage(class_name, replacement, attribute_name, attribute_value, substitution,
                       rules_file_name, cmd_name, line_number_range_start, line_number)
        if replacement is not None:
            self.commit(class_name, replacement, rules_file_name, line_number + 1)

    def execute(self, string: str) -> str:
        if self._verbose_mode_enabled:
            replacement_queue_ids = [
                f'#{replacement.id_}'
                for replacement in self._replacement_queue
            ]
            print(f'Replacement queue: {replacement_queue_ids}\n\n\n\n')

        for replacement in self._replacement_queue:
            string = replacement.apply(string)

        return string  # HTMl


class PostClassDeclarationState(NamedTuple):
    class_name: str
    replacement: 'Replacement'
    line_number_range_start: int


class PostAttributeDeclarationState(NamedTuple):
    attribute_name: str
    attribute_value: str
    line_number_range_start: int


class PostSubstitutionDeclarationState(NamedTuple):
    substitution: str
    line_number_range_start: int


class PostContinuationState(NamedTuple):
    attribute_value: str
    substitution: str


class PostStageState(NamedTuple):
    attribute_name: Optional[str]
    attribute_value: Optional[str]
    substitution: Optional[str]
    line_number_range_start: Optional[int]


class PostCommitState(NamedTuple):
    class_name: Optional[str]
    replacement: Optional['Replacement']
    attribute_name: Optional[str]
    attribute_value: Optional[str]
    substitution: Optional[str]
    line_number_range_start: Optional[int]


def escape_regex_substitute(substitute: str) -> str:
    return substitute.replace('\\', r'\\')


def extract_basename(name: str) -> str:
    return re.sub(pattern=r'\A .* [/]', repl='', string=name, flags=re.VERBOSE)


def make_clean_url(cmd_name: str) -> str:
    return re.sub(
        pattern=r'(?P<last_separator> \A | [/] ) index \Z',
        repl=r'\g<last_separator>',
        string=cmd_name,
        flags=re.VERBOSE,
    )
