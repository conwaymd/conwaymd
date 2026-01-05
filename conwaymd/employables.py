"""
# Conway-Markdown: employables.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Classes for CMD replacement rules that are actually exposed to the user via CMD replacement rule syntax.
"""

import copy
import re
from typing import Callable, Optional

from conwaymd.bases import (
    Replacement,
    ReplacementWithAllowedFlags,
    ReplacementWithAttributeSpecifications,
    ReplacementWithConcludingReplacements,
    ReplacementWithContentReplacements,
    ReplacementWithProhibitedContent,
    ReplacementWithSubstitutions,
    ReplacementWithSyntaxType,
    ReplacementWithTagName,
)
from conwaymd.exceptions import CommittedMutateException, MissingAttributeException, UnrecognisedLabelException
from conwaymd.idioms import (
    build_attribute_specifications_regex,
    build_attributes_sequence,
    build_block_anchoring_regex,
    build_captured_character_class_regex,
    build_content_regex,
    build_extensible_delimiter_closing_regex,
    build_extensible_delimiter_opening_regex,
    build_flags_regex,
    build_maybe_hanging_whitespace_regex,
    build_title_regex,
    build_uri_regex,
)
from conwaymd.placeholders import PlaceholderMaster
from conwaymd.references import ReferenceMaster
from conwaymd.utilities import de_indent, none_to_empty_string


class ReplacementSequence(Replacement):
    """
    A replacement rule that applies a sequence of replacement rules.

    CMD replacement rule syntax:
    ````
    ReplacementSequence: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - replacements: (def) NONE | #«id» [...]
    ````
    """
    _replacements: list['Replacement']

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._replacements = []

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'replacements',
        )

    @property
    def replacements(self) -> list['Replacement']:
        return self._replacements

    @replacements.setter
    def replacements(self, value: list['Replacement']):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `replacements` after `commit()`')

        self._replacements = copy.copy(value)

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        pass

    def _apply(self, string: str) -> str:
        for replacement in self._replacements:
            string = replacement.apply(string)

        return string


class PlaceholderMarkerReplacement(Replacement):
    """
    A rule for replacing the placeholder marker with a placeholder.

    Ensures that occurrences of «marker» will not be confounding.
    To be used before PlaceholderProtectionReplacement.
    See class PlaceholderMaster, especially `replace_marker_occurrences`.

    CMD replacement rule syntax:
    ````
    PlaceholderMarkerReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    ````
    """
    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        pass

    def _apply(self, string: str) -> str:
        return PlaceholderMaster.replace_marker_occurrences(string)


class PlaceholderProtectionReplacement(Replacement):
    """
    A replacement rule for protecting strings with a placeholder.

    CMD replacement rule syntax:
    ````
    PlaceholderProtectionReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    ````
    """
    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        pass

    def _apply(self, string: str) -> str:
        return PlaceholderMaster.protect(string)


class PlaceholderUnprotectionReplacement(Replacement):
    """
    A replacement rule for restoring placeholders to their strings.

    CMD replacement rule syntax:
    ````
    PlaceholderUnprotectionReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    """
    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        pass

    def _apply(self, string: str) -> str:
        return PlaceholderMaster.unprotect(string)


class DeIndentationReplacement(Replacement):
    """
    A replacement rule for de-indentation.

    CMD replacement rule syntax:
    ````
    DeIndentationReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - positive_flag: (def) NONE | «FLAG_NAME»
    - negative_flag: (def) NONE | «FLAG_NAME»
    ````
    """
    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'positive_flag',
            'negative_flag',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        pass

    def _apply(self, string: str) -> str:
        return de_indent(string)


class OrdinaryDictionaryReplacement(
    ReplacementWithSubstitutions,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A replacement rule for a dictionary of ordinary substitutions.

    CMD replacement rule syntax:
    ````
    OrdinaryDictionaryReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - positive_flag: (def) NONE | «FLAG_NAME»
    - negative_flag: (def) NONE | «FLAG_NAME»
    - apply_mode: (def) SIMULTANEOUS | SEQUENTIAL
    * "«pattern»" | '«pattern»' | «pattern»
        -->
      CMD_VERSION | CMD_NAME | CMD_BASENAME | CLEAN_URL |
              "«substitute»" | '«substitute»' | «substitute»
    [...]
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _apply_substitutions_simultaneously: bool
    _simultaneous_regex_pattern_compiled: Optional[re.Pattern]
    _simultaneous_substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._apply_substitutions_simultaneously = True
        self._simultaneous_regex_pattern_compiled = None
        self._simultaneous_substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'positive_flag',
            'negative_flag',
            'apply_mode',
            'concluding_replacements',
        )

    @property
    def apply_substitutions_simultaneously(self) -> bool:
        return self._apply_substitutions_simultaneously

    @apply_substitutions_simultaneously.setter
    def apply_substitutions_simultaneously(self, value: bool):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `apply_mode` after `commit()`')

        self._apply_substitutions_simultaneously = value

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        if self._apply_substitutions_simultaneously:
            self.set_simultaneous_apply_method_variables()

    def _apply(self, string: str) -> str:
        if self._apply_substitutions_simultaneously:
            return self.simultaneous_apply(string)
        else:
            return self.sequential_apply(string)

    def set_simultaneous_apply_method_variables(self):
        self._simultaneous_regex_pattern_compiled = re.compile(
            pattern=OrdinaryDictionaryReplacement.build_simultaneous_regex_pattern(self._substitute_from_pattern),
        )
        self._simultaneous_substitute_function = (
            self.build_simultaneous_substitute_function(self._substitute_from_pattern)
        )

    @staticmethod
    def build_simultaneous_regex_pattern(substitute_from_pattern: dict[str, str]) -> str:
        return '|'.join(
            re.escape(pattern)
            for pattern in substitute_from_pattern
        )

    def build_simultaneous_substitute_function(self, substitute_from_pattern: dict[str, str],
                                               ) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            pattern = match.group()
            substitute = substitute_from_pattern[pattern]

            for replacement in self._concluding_replacements:
                substitute = replacement.apply(substitute)

            return substitute

        return substitute_function

    def simultaneous_apply(self, string: str) -> str:
        if len(self._substitute_from_pattern) > 0:
            string = re.sub(
                pattern=self._simultaneous_regex_pattern_compiled,
                repl=self._simultaneous_substitute_function,
                string=string,
            )

        return string

    def sequential_apply(self, string: str) -> str:
        for pattern, substitute in self._substitute_from_pattern.items():
            string = string.replace(pattern, substitute)

        for replacement in self._concluding_replacements:
            string = replacement.apply(string)

        return string


class RegexDictionaryReplacement(
    ReplacementWithSubstitutions,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A replacement rule for a dictionary of regex substitutions.

    Substitutions are applied in order.
    Python regex syntax is used,
    with `flags=re.ASCII | re.MULTILINE | re.VERBOSE`.

    CMD replacement rule syntax:
    ````
    RegexDictionaryReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - positive_flag: (def) NONE | «FLAG_NAME»
    - negative_flag: (def) NONE | «FLAG_NAME»
    * "«pattern»" | '«pattern»' | «pattern»
        -->
      CMD_VERSION | CMD_NAME | CMD_BASENAME | CLEAN_URL |
              "«substitute»" | '«substitute»' | «substitute»
    [...]
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _substitute_function_from_pattern: dict[str, Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._substitute_function_from_pattern = {}

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'positive_flag',
            'negative_flag',
            'concluding_replacements',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        for pattern, substitute in self._substitute_from_pattern.items():
            substitute_function = self.build_substitute_function(substitute)
            self._substitute_function_from_pattern[pattern] = substitute_function

    def _apply(self, string: str) -> str:
        for pattern, substitute_function in self._substitute_function_from_pattern.items():
            string = re.sub(
                pattern=pattern,
                repl=substitute_function,
                string=string,
                flags=re.ASCII | re.MULTILINE | re.VERBOSE,
            )

        return string

    def build_substitute_function(self, substitute: str) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            substitute_result = match.expand(substitute)

            for replacement in self._concluding_replacements:
                substitute_result = replacement.apply(substitute_result)

            return substitute_result

        return substitute_function


class FixedDelimitersReplacement(
    ReplacementWithSyntaxType,
    ReplacementWithAllowedFlags,
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    ReplacementWithContentReplacements,
    ReplacementWithTagName,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A fixed-delimiters replacement rule.

    ````
    FixedDelimitersReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - syntax_type: BLOCK | INLINE (mandatory)
    - allowed_flags: (def) NONE | «letter»=«FLAG_NAME» [...]
    - opening_delimiter: «string» (mandatory)
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    - content_replacements: (def) NONE | #«id» [...]
    - closing_delimiter: «string» (mandatory)
    - tag_name: (def) NONE | «name»
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _opening_delimiter: Optional[str]
    _closing_delimiter: Optional[str]
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._opening_delimiter = None
        self._closing_delimiter = None
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'syntax_type',
            'allowed_flags',
            'opening_delimiter',
            'attribute_specifications',
            'prohibited_content',
            'content_replacements',
            'closing_delimiter',
            'tag_name',
            'concluding_replacements',
        )

    @property
    def opening_delimiter(self) -> Optional[str]:
        return self._opening_delimiter

    @opening_delimiter.setter
    def opening_delimiter(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `opening_delimiter` after `commit()`')

        self._opening_delimiter = value

    @property
    def closing_delimiter(self) -> Optional[str]:
        return self._closing_delimiter

    @closing_delimiter.setter
    def closing_delimiter(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `closing_delimiter` after `commit()`')

        self._closing_delimiter = value

    def _validate_mandatory_attributes(self):
        if self._syntax_type_is_block is None:
            raise MissingAttributeException('syntax_type')

        if self._opening_delimiter is None:
            raise MissingAttributeException('opening_delimiter')

        if self._closing_delimiter is None:
            raise MissingAttributeException('closing_delimiter')

    def _set_apply_method_variables(self):
        self._has_flags = len(self._flag_name_from_letter) > 0
        self._regex_pattern_compiled = re.compile(
            pattern=FixedDelimitersReplacement.build_regex_pattern(self._syntax_type_is_block,
                                                                   self._flag_name_from_letter, self._has_flags,
                                                                   self._opening_delimiter,
                                                                   self._attribute_specifications,
                                                                   self._prohibited_content_regex,
                                                                   self._closing_delimiter),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(self._flag_name_from_letter, self._has_flags,
                                                                   self._attribute_specifications, self._tag_name)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(syntax_type_is_block: bool, flag_name_from_letter: dict[str, str], has_flags: bool,
                            opening_delimiter: str, attribute_specifications: Optional[str],
                            prohibited_content_regex: Optional[str], closing_delimiter: str,
                            ) -> str:
        block_anchoring_regex = build_block_anchoring_regex(syntax_type_is_block)
        flags_regex = build_flags_regex(flag_name_from_letter, has_flags)
        opening_delimiter_regex = re.escape(opening_delimiter)
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=syntax_type_is_block)
        content_regex = build_content_regex(prohibited_content_regex)
        closing_delimiter_regex = re.escape(closing_delimiter)

        return ''.join([
            block_anchoring_regex,
            flags_regex,
            opening_delimiter_regex,
            attribute_specifications_regex,
            content_regex,
            block_anchoring_regex,
            closing_delimiter_regex
        ])

    def build_substitute_function(self, flag_name_from_letter: dict[str, str], has_flags: bool,
                                  attribute_specifications: Optional[str], tag_name: Optional[str],
                                  ) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            enabled_flag_names = ReplacementWithAllowedFlags.get_enabled_flag_names(match, flag_name_from_letter,
                                                                                    has_flags)

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
                attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)
            else:
                attributes_sequence = ''

            content = match.group('content')
            for replacement in self._content_replacements:
                content = replacement.apply(content, enabled_flag_names)

            if tag_name is None:
                substitute = content
            else:
                substitute = f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'

            for replacement in self._concluding_replacements:
                substitute = replacement.apply(substitute, enabled_flag_names)

            return substitute

        return substitute_function


class ExtensibleFenceReplacement(
    ReplacementWithSyntaxType,
    ReplacementWithAllowedFlags,
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    ReplacementWithContentReplacements,
    ReplacementWithTagName,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A generalised extensible-fence-style replacement rule.

    Inspired by the repeatable backticks of John Gruber's Markdown.
    CMD replacement rule syntax:
    ````
    ExtensibleFenceReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - syntax_type: BLOCK | INLINE (mandatory)
    - allowed_flags: (def) NONE | «letter»=«FLAG_NAME» [...]
    - prologue_delimiter: (def) NONE | «string»
    - extensible_delimiter: «character_repeated» (mandatory)
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    - content_replacements: (def) NONE | #«id» [...]
    - epilogue_delimiter: (def) NONE | «string»
    - tag_name: (def) NONE | «name»
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _prologue_delimiter: str
    _extensible_delimiter_character: Optional[str]
    _extensible_delimiter_min_length: Optional[int]
    _epilogue_delimiter: str
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._prologue_delimiter = ''
        self._extensible_delimiter_character = None
        self._extensible_delimiter_min_length = None
        self._epilogue_delimiter = ''
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'syntax_type',
            'allowed_flags',
            'prologue_delimiter',
            'extensible_delimiter',
            'attribute_specifications',
            'prohibited_content',
            'content_replacements',
            'epilogue_delimiter',
            'tag_name',
            'concluding_replacements',
        )

    @property
    def prologue_delimiter(self) -> str:
        return self._prologue_delimiter

    @prologue_delimiter.setter
    def prologue_delimiter(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `prologue_delimiter` after `commit()`')

        self._prologue_delimiter = value

    @property
    def extensible_delimiter_character(self) -> Optional[str]:
        return self._extensible_delimiter_character

    @extensible_delimiter_character.setter
    def extensible_delimiter_character(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `extensible_delimiter_character` after `commit()`')

        self._extensible_delimiter_character = value

    @property
    def extensible_delimiter_min_length(self) -> Optional[int]:
        return self._extensible_delimiter_min_length

    @extensible_delimiter_min_length.setter
    def extensible_delimiter_min_length(self, value: int):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `extensible_delimiter_min_length` after `commit()`')

        self._extensible_delimiter_min_length = value

    @property
    def epilogue_delimiter(self) -> str:
        return self._epilogue_delimiter

    @epilogue_delimiter.setter
    def epilogue_delimiter(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `epilogue_delimiter` after `commit()`')

        self._epilogue_delimiter = value

    def _validate_mandatory_attributes(self):
        if self._syntax_type_is_block is None:
            raise MissingAttributeException('syntax_type')

        if self._extensible_delimiter_character is None:
            raise MissingAttributeException('extensible_delimiter')

    def _set_apply_method_variables(self):
        self._has_flags = len(self._flag_name_from_letter) > 0
        self._regex_pattern_compiled = re.compile(
            pattern=ExtensibleFenceReplacement.build_regex_pattern(
                self._syntax_type_is_block,
                self._flag_name_from_letter,
                self._has_flags,
                self._prologue_delimiter,
                self._extensible_delimiter_character,
                self._extensible_delimiter_min_length,
                self._attribute_specifications,
                self._prohibited_content_regex,
                self._epilogue_delimiter,
            ),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(
            self._flag_name_from_letter,
            self._has_flags,
            self._attribute_specifications,
            self._tag_name,
        )

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(syntax_type_is_block: bool, flag_name_from_letter: dict[str, str], has_flags: bool,
                            prologue_delimiter: str,
                            extensible_delimiter_character: str, extensible_delimiter_min_length: int,
                            attribute_specifications: Optional[str], prohibited_content_regex: Optional[str],
                            epilogue_delimiter: str,
                            ) -> str:
        block_anchoring_regex = build_block_anchoring_regex(syntax_type_is_block)
        flags_regex = build_flags_regex(flag_name_from_letter, has_flags)
        prologue_delimiter_regex = re.escape(prologue_delimiter)
        extensible_delimiter_opening_regex = build_extensible_delimiter_opening_regex(extensible_delimiter_character,
                                                                                      extensible_delimiter_min_length)
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=syntax_type_is_block)
        content_regex = build_content_regex(prohibited_content_regex)
        extensible_delimiter_closing_regex = build_extensible_delimiter_closing_regex()
        epilogue_delimiter_regex = re.escape(epilogue_delimiter)

        return ''.join([
            block_anchoring_regex,
            flags_regex,
            prologue_delimiter_regex,
            extensible_delimiter_opening_regex,
            attribute_specifications_regex,
            content_regex,
            block_anchoring_regex,
            extensible_delimiter_closing_regex,
            epilogue_delimiter_regex,
        ])

    def build_substitute_function(self, flag_name_from_letter: dict[str, str], has_flags: bool,
                                  attribute_specifications: Optional[str], tag_name: Optional[str],
                                  ) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            enabled_flag_names = ReplacementWithAllowedFlags.get_enabled_flag_names(match,
                                                                                    flag_name_from_letter, has_flags)

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
                attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)
            else:
                attributes_sequence = ''

            content = match.group('content')
            for replacement in self._content_replacements:
                content = replacement.apply(content, enabled_flag_names)

            if tag_name is None:
                substitute = content
            else:
                substitute = f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'

            for replacement in self._concluding_replacements:
                substitute = replacement.apply(substitute, enabled_flag_names)

            return substitute

        return substitute_function


class PartitioningReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithContentReplacements,
    ReplacementWithTagName,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A generalised partitioning replacement rule.

    Does partitioning by consuming everything from a
    starting pattern up to but not including an ending pattern.
    CMD replacement rule syntax:
    ````
    PartitioningReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - starting_pattern: «regex» (mandatory)
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - content_replacements: (def) NONE | #«id» [...]
    - ending_pattern: (def) NONE | «regex»
    - tag_name: (def) NONE | «name»
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _starting_pattern: Optional[str]
    _ending_pattern: Optional[str]
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._starting_pattern = None
        self._ending_pattern = None
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'starting_pattern',
            'attribute_specifications',
            'content_replacements',
            'ending_pattern',
            'tag_name',
            'concluding_replacements',
        )

    @property
    def starting_pattern(self) -> Optional[str]:
        return self._starting_pattern

    @starting_pattern.setter
    def starting_pattern(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `starting_pattern` after `commit()`')

        self._starting_pattern = value

    @property
    def ending_pattern(self) -> Optional[str]:
        return self._ending_pattern

    @ending_pattern.setter
    def ending_pattern(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `ending_pattern` after `commit()`')

        self._ending_pattern = value

    def _validate_mandatory_attributes(self):
        if self._starting_pattern is None:
            raise MissingAttributeException('starting_pattern')

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=PartitioningReplacement.build_regex_pattern(
                self._starting_pattern,
                self._attribute_specifications,
                self._ending_pattern,
            ),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(self._attribute_specifications, self._tag_name)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(starting_pattern: str, attribute_specifications: Optional[str],
                            ending_pattern: Optional[str]) -> str:
        anchoring_regex = build_block_anchoring_regex(syntax_type_is_block=True)

        starting_regex = f'(?: {starting_pattern} )'

        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False,
                                                                              allow_omission=False)
        if attribute_specifications_regex == '':
            attribute_specifications_or_whitespace_regex = r'[\s]+?'
        else:
            attribute_specifications_or_whitespace_regex = fr'(?: {attribute_specifications_regex} | [\s]+? )'

        content_regex = build_content_regex()

        attribute_specifications_no_capture_regex = (
            build_attribute_specifications_regex(attribute_specifications,
                                                 require_newline=False, capture_attribute_specifications=False,
                                                 allow_omission=False)
        )
        if attribute_specifications_no_capture_regex == '':
            attribute_specifications_no_capture_or_whitespace_regex = r'[\s]+'
        else:
            attribute_specifications_no_capture_or_whitespace_regex = (
                fr'(?: {attribute_specifications_no_capture_regex} | [\s]+ )'
            )

        if ending_pattern is None:
            ending_lookahead_regex = r'(?= \Z )'
        else:
            ending_regex = f'(?: {ending_pattern} )'
            ending_lookahead_regex = (
                '(?= '
                + anchoring_regex
                + ending_regex
                + attribute_specifications_no_capture_or_whitespace_regex
                + r' | \Z )'
            )

        return ''.join([
            anchoring_regex,
            starting_regex,
            attribute_specifications_or_whitespace_regex,
            content_regex,
            ending_lookahead_regex,
        ])

    def build_substitute_function(self, attribute_specifications: Optional[str], tag_name: Optional[str],
                                  ) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
                attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)
            else:
                attributes_sequence = ''

            content = match.group('content')
            for replacement in self._content_replacements:
                content = replacement.apply(content)

            if tag_name is None:
                substitute = content
            else:
                substitute = f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>\n'

            for replacement in self._concluding_replacements:
                substitute = replacement.apply(substitute)

            return substitute

        return substitute_function


class InlineAssortedDelimitersReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    Replacement
):
    """
    An inline assorted-delimiters replacement rule.

    CMD replacement rule syntax:
    ````
    InlineAssortedDelimitersReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - delimiter_conversion:
      «character» | «character_doubled»=«tag_name» [...] (mandatory)
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _tag_name_from_delimiter_length_from_character: dict[str, dict[int, str]]
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._tag_name_from_delimiter_length_from_character = {}
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'delimiter_conversion',
            'attribute_specifications',
            'prohibited_content',
        )

    @property
    def tag_name_from_delimiter_length_from_character(self) -> dict[str, dict[int, str]]:
        return self._tag_name_from_delimiter_length_from_character

    @tag_name_from_delimiter_length_from_character.setter
    def tag_name_from_delimiter_length_from_character(self, value: dict[str, dict[int, str]]):
        if self._is_committed:
            raise CommittedMutateException('error: cannot call `add_delimiter_conversion(...)` after `commit()`')

        self._tag_name_from_delimiter_length_from_character = copy.deepcopy(value)

    def _validate_mandatory_attributes(self):
        if len(self._tag_name_from_delimiter_length_from_character) == 0:
            raise MissingAttributeException('delimiter_conversion')

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=InlineAssortedDelimitersReplacement.build_regex_pattern(
                self._tag_name_from_delimiter_length_from_character,
                self._attribute_specifications,
                self._prohibited_content_regex,
            ),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(
            self._tag_name_from_delimiter_length_from_character,
            self._attribute_specifications,
        )

    def _apply(self, string: str) -> str:
        string_has_changed = True

        while string_has_changed:
            new_string = re.sub(pattern=self._regex_pattern_compiled, repl=self._substitute_function, string=string)
            string_has_changed = new_string != string
            string = new_string

        return string

    def build_substitute_function(self, tag_name_from_delimiter_length_from_character: dict[str, dict[int, str]],
                                  attribute_specifications: Optional[str],
                                  ) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            character = match.group('delimiter_character')
            delimiter = match.group('delimiter')
            length = len(delimiter)
            tag_name = tag_name_from_delimiter_length_from_character[character][length]

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
                attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)
            else:
                attributes_sequence = ''

            content = match.group('content')
            content = self.apply(content)

            substitute = f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'

            return substitute

        return substitute_function

    @staticmethod
    def build_regex_pattern(tag_name_from_delimiter_length_from_character: dict[str, dict[int, str]],
                            attribute_specifications: Optional[str], prohibited_content_regex: Optional[str],
                            ) -> str:
        optional_pipe_regex = '[|]?'

        single_characters = set()
        either_characters = set()
        double_characters = set()
        all_characters = set()

        for character in tag_name_from_delimiter_length_from_character:
            tag_name_from_delimiter_length = tag_name_from_delimiter_length_from_character[character]
            delimiter_lengths = tag_name_from_delimiter_length.keys()
            if delimiter_lengths == {1}:
                single_characters.add(character)
                all_characters.add(character)
            elif delimiter_lengths == {1, 2}:
                either_characters.add(character)
                all_characters.add(character)
            elif delimiter_lengths == {2}:
                double_characters.add(character)
                all_characters.add(character)

        single_class_regex = build_captured_character_class_regex(single_characters, 'single')
        either_class_regex = build_captured_character_class_regex(either_characters, 'either')
        double_class_regex = build_captured_character_class_regex(double_characters, 'double')
        class_regexes = [double_class_regex, either_class_regex, single_class_regex]
        delimiter_character_alternatives = ' | '.join(
            class_regex
            for class_regex in class_regexes
            if class_regex is not None
        )
        delimiter_character_regex = f'(?P<delimiter_character> {delimiter_character_alternatives} )'

        if either_class_regex is not None:
            if double_class_regex is not None:
                repetition_regex = '(?(double) (?P=double) | (?(either) (?P=either)? ) )'
            else:
                repetition_regex = '(?(either) (?P=either)? )'
        else:
            if double_class_regex is not None:
                repetition_regex = '(?(double) (?P=double) )'
            else:
                repetition_regex = ''

        opening_delimiter_regex = f'(?P<delimiter> {delimiter_character_regex} {repetition_regex} )'

        after_opening_delimiter_regex = r'(?! [\s] | [<][/] )'
        attribute_specifications_regex = (
            build_attribute_specifications_regex(attribute_specifications, require_newline=False)
        )
        before_content_whitespace_regex = r'[\s]*'

        if prohibited_content_regex is None:
            prohibited_content_regex = '(?P=delimiter_character)'
        else:
            prohibited_content_regex = f'(?P=delimiter_character) | {prohibited_content_regex}'

        content_regex = build_content_regex(prohibited_content_regex, permit_empty=False)

        before_closing_delimiter_regex = r'(?<! [\s] | [|] )'
        closing_delimiter_regex = '(?P=delimiter)'

        return ''.join([
            optional_pipe_regex,
            opening_delimiter_regex,
            after_opening_delimiter_regex,
            attribute_specifications_regex,
            before_content_whitespace_regex,
            content_regex,
            before_closing_delimiter_regex,
            closing_delimiter_regex,
        ])


class HeadingReplacement(
    ReplacementWithAttributeSpecifications,
    Replacement,
):
    """
    A replacement rule for headings.

    CMD replacement rule syntax:
    ````
    HeadingReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    ````
    """
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=HeadingReplacement.build_regex_pattern(self._attribute_specifications),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = HeadingReplacement.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str]) -> str:
        block_anchoring_regex = build_block_anchoring_regex(syntax_type_is_block=True,
                                                            capture_anchoring_whitespace=True)
        opening_hashes_regex = '(?P<opening_hashes> [#]{1,6} )'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        content_starter_regex = r'(?: [^\S\n]+ (?P<content_starter> [^\n]*? ) )? [^\S\n]*'
        content_continuation_regex = (
            r'(?P<content_continuation> (?: \n (?P=anchoring_whitespace) [^\S\n]+ [^\n]* )* )'
        )
        closing_hashes_regex = '[#]*'
        trailing_horizontal_whitespace_regex = r'[^\S\n]* $'

        return ''.join([
            block_anchoring_regex,
            opening_hashes_regex,
            attribute_specifications_regex,
            content_starter_regex,
            content_continuation_regex,
            closing_hashes_regex,
            trailing_horizontal_whitespace_regex,
        ])

    @staticmethod
    def build_substitute_function(attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            opening_hashes = match.group('opening_hashes')
            heading_level = len(opening_hashes)
            tag_name = f'h{heading_level}'

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
                attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)
            else:
                attributes_sequence = ''

            content_starter = match.group('content_starter')
            content_continuation = match.group('content_continuation')
            content = none_to_empty_string(content_starter) + content_continuation

            substitute = f'<{tag_name}{attributes_sequence}>{content}</{tag_name}>'

            return substitute

        return substitute_function


class ReferenceDefinitionReplacement(
    ReplacementWithAttributeSpecifications,
    Replacement,
):
    """
    A replacement rule for consuming reference definitions.

    CMD replacement rule syntax:
    ````
    ReferenceDefinitionReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    ````
    """
    _reference_master: 'ReferenceMaster'
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, reference_master: 'ReferenceMaster', verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._reference_master = reference_master
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=ReferenceDefinitionReplacement.build_regex_pattern(self._attribute_specifications),
            flags=re.ASCII | re.MULTILINE | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str]) -> str:
        block_anchoring_regex = build_block_anchoring_regex(syntax_type_is_block=True,
                                                            capture_anchoring_whitespace=True)
        label_regex = r'\[ [\s]* (?P<label> [^\]]*? ) [\s]* \]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        colon_regex = '[:]'
        maybe_hanging_whitespace_regex = build_maybe_hanging_whitespace_regex()
        uri_regex = build_uri_regex(be_greedy=True)
        whitespace_then_uri_regex = f'{maybe_hanging_whitespace_regex}{uri_regex}'
        title_regex = build_title_regex()
        whitespace_then_title_regex = f'(?: {maybe_hanging_whitespace_regex}{title_regex} )?'
        trailing_horizontal_whitespace_regex = r'[^\S\n]* $'

        return ''.join([
            block_anchoring_regex,
            label_regex,
            attribute_specifications_regex,
            colon_regex,
            whitespace_then_uri_regex,
            whitespace_then_title_regex,
            trailing_horizontal_whitespace_regex,
        ])

    def build_substitute_function(self, attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            label = match.group('label')

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = (
                    attribute_specifications
                    + ' '
                    + none_to_empty_string(matched_attribute_specifications)
                )
            else:
                combined_attribute_specifications = ''

            angle_bracketed_uri = match.group('angle_bracketed_uri')
            if angle_bracketed_uri is not None:
                uri = angle_bracketed_uri
            else:
                uri = match.group('bare_uri')

            double_quoted_title = match.group('double_quoted_title')
            if double_quoted_title is not None:
                title = double_quoted_title
            else:
                title = match.group('single_quoted_title')

            self._reference_master.store_definition(label, combined_attribute_specifications, uri, title)

            return ''

        return substitute_function


class SpecifiedImageReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    Replacement,
):
    """
    A replacement rule for specified images.

    CMD replacement rule syntax:
    ````
    SpecifiedImageReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
            'prohibited_content',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=SpecifiedImageReplacement.build_regex_pattern(
                self._attribute_specifications,
                self._prohibited_content_regex,
            ),
            flags=re.ASCII | re.VERBOSE,
        )
        self._substitute_function = SpecifiedImageReplacement.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str], prohibited_content_regex: Optional[str]) -> str:
        exclamation_mark_regex = '[!]'
        alt_text_regex = build_content_regex(prohibited_content_regex,
                                             permitted_content_regex=r'[^\]]', capture_group_name='alt_text')
        bracketed_alt_text_regex = fr'\[ [\s]* {alt_text_regex} [\s]* \]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        opening_parenthesis_regex = r'\('
        uri_regex = build_uri_regex(be_greedy=False)
        whitespace_then_uri_regex = fr'(?: [\s]* {uri_regex} )?'
        title_regex = build_title_regex()
        whitespace_then_title_regex = fr'(?: [\s]* {title_regex} )?'
        whitespace_regex = r'[\s]*'
        closing_parenthesis_regex = r'\)'

        return ''.join([
            exclamation_mark_regex,
            bracketed_alt_text_regex,
            attribute_specifications_regex,
            opening_parenthesis_regex,
            whitespace_then_uri_regex,
            whitespace_then_title_regex,
            whitespace_regex,
            closing_parenthesis_regex,
        ])

    @staticmethod
    def build_substitute_function(attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            alt = match.group('alt_text')
            alt_protected = PlaceholderMaster.protect(alt)
            alt_attribute_specification = f'alt={alt_protected}'

            angle_bracketed_uri = match.group('angle_bracketed_uri')
            if angle_bracketed_uri is not None:
                src = angle_bracketed_uri
            else:
                src = match.group('bare_uri')

            src_protected = PlaceholderMaster.protect(none_to_empty_string(src))
            src_attribute_specification = f'src={src_protected}'

            double_quoted_title = match.group('double_quoted_title')
            if double_quoted_title is not None:
                title = double_quoted_title
            else:
                title = match.group('single_quoted_title')

            if title is not None:
                title_protected = PlaceholderMaster.protect(title)
                title_attribute_specification = f'title={title_protected}'
            else:
                title_attribute_specification = ''

            alt_src_title_attribute_specifications = ' '.join([
                alt_attribute_specification,
                src_attribute_specification,
                title_attribute_specification,
            ])

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = ' '.join([
                    alt_src_title_attribute_specifications,
                    attribute_specifications,
                    none_to_empty_string(matched_attribute_specifications),
                ])
            else:
                combined_attribute_specifications = alt_src_title_attribute_specifications

            attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)

            substitute = f'<img{attributes_sequence}>'

            return substitute

        return substitute_function


class ReferencedImageReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    Replacement,
):
    """
    A replacement rule for referenced images.

    CMD replacement rule syntax:
    ````
    ReferencedImageReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _reference_master: 'ReferenceMaster'
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, reference_master: 'ReferenceMaster', verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._reference_master = reference_master
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
            'prohibited_content',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=ReferencedImageReplacement.build_regex_pattern(
                self._attribute_specifications,
                self._prohibited_content_regex,
            ),
            flags=re.ASCII | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str], prohibited_content_regex: Optional[str]) -> str:
        exclamation_mark_regex = '[!]'
        alt_text_regex = build_content_regex(prohibited_content_regex,
                                             permitted_content_regex=r'[^\]]', capture_group_name='alt_text')
        bracketed_alt_text_regex = fr'\[ [\s]* {alt_text_regex} [\s]* \]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        label_regex = build_content_regex(prohibited_content_regex,
                                          permitted_content_regex=r'[^\]]', capture_group_name='label')
        bracketed_label_regex = fr'(?: \[ [\s]* {label_regex} [\s]* \] )?'

        return ''.join([
            exclamation_mark_regex,
            bracketed_alt_text_regex,
            attribute_specifications_regex,
            bracketed_label_regex,
        ])

    def build_substitute_function(self, attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            alt = match.group('alt_text')
            alt_protected = PlaceholderMaster.protect(alt)
            alt_attribute_specification = f'alt={alt_protected}'

            label = match.group('label')
            if label is None or label == '':
                label = alt

            try:
                referenced_attribute_specifications, src, title = self._reference_master.load_definition(label)
            except UnrecognisedLabelException:
                return match.group()

            src_protected = PlaceholderMaster.protect(none_to_empty_string(src))
            src_attribute_specification = f'src={src_protected}'

            if title is not None:
                title_protected = PlaceholderMaster.protect(title)
                title_attribute_specification = f'title={title_protected}'
            else:
                title_attribute_specification = ''

            alt_src_title_referenced_attribute_specifications = ' '.join([
                alt_attribute_specification,
                src_attribute_specification,
                title_attribute_specification,
                none_to_empty_string(referenced_attribute_specifications)
            ])

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = ' '.join([
                    alt_src_title_referenced_attribute_specifications,
                    attribute_specifications,
                    none_to_empty_string(matched_attribute_specifications),
                ])
            else:
                combined_attribute_specifications = alt_src_title_referenced_attribute_specifications

            attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)

            substitute = f'<img{attributes_sequence}>'

            return substitute

        return substitute_function


class ExplicitLinkReplacement(
    ReplacementWithAllowedFlags,
    ReplacementWithAttributeSpecifications,
    ReplacementWithContentReplacements,
    ReplacementWithConcludingReplacements,
    Replacement,
):
    """
    A replacement rule for explicit links.

    CMD replacement rule syntax:
    ````
    ExplicitLinkReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - allowed_flags: (def) NONE | «letter»=«FLAG_NAME» [...]
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - content_replacements: (def) NONE | #«id» [...]
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'allowed_flags',
            'attribute_specifications',
            'content_replacements',
            'concluding_replacements',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._has_flags = len(self._flag_name_from_letter) > 0
        self._regex_pattern_compiled = re.compile(
            pattern=ExplicitLinkReplacement.build_regex_pattern(
                self._flag_name_from_letter,
                self._has_flags,
                self._attribute_specifications,
            ),
            flags=re.ASCII | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(
            self._flag_name_from_letter,
            self._has_flags,
            self._attribute_specifications,
        )

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(flag_name_from_letter: dict[str, str], has_flags: bool,
                            attribute_specifications: Optional[str]) -> str:
        flags_regex = build_flags_regex(flag_name_from_letter, has_flags)
        opening_angle_bracket_regex = '[<]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        uri_regex = r'(?P<uri> [a-zA-Z.+-]+ [:] [^\s>]*? )'
        closing_angle_bracket_regex = '[>]'

        return ''.join([
            flags_regex,
            opening_angle_bracket_regex,
            attribute_specifications_regex,
            uri_regex,
            closing_angle_bracket_regex,
        ])

    def build_substitute_function(self, flag_name_from_letter: dict[str, str], has_flags: bool,
                                  attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            enabled_flag_names = ReplacementWithAllowedFlags.get_enabled_flag_names(match,
                                                                                    flag_name_from_letter, has_flags)

            href = match.group('uri')
            href_protected = PlaceholderMaster.protect(href)
            href_attribute_specification = f'href={href_protected}'

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = ' '.join([
                    href_attribute_specification,
                    none_to_empty_string(matched_attribute_specifications),
                ])
            else:
                combined_attribute_specifications = href_attribute_specification

            attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)

            content = href
            for replacement in self._content_replacements:
                content = replacement.apply(content, enabled_flag_names)

            substitute = f'<a{attributes_sequence}>{content}</a>'
            for replacement in self._concluding_replacements:
                substitute = replacement.apply(substitute, enabled_flag_names)

            return substitute

        return substitute_function


class SpecifiedLinkReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    Replacement,
):
    """
    A replacement rule for specified links.

    CMD replacement rule syntax:
    ````
    SpecifiedLinkReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
            'prohibited_content',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=SpecifiedLinkReplacement.build_regex_pattern(
                self._attribute_specifications,
                self._prohibited_content_regex,
            ),
            flags=re.ASCII | re.VERBOSE,
        )
        self._substitute_function = SpecifiedLinkReplacement.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str], prohibited_content_regex: Optional[str]) -> str:
        link_text_regex = build_content_regex(prohibited_content_regex,
                                              permitted_content_regex=r'[^\]]', capture_group_name='link_text')
        bracketed_link_text_regex = fr'\[ [\s]* {link_text_regex} [\s]* \]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        opening_parenthesis_regex = r'\('
        uri_regex = build_uri_regex(be_greedy=False)
        whitespace_then_uri_regex = fr'(?: [\s]* {uri_regex} )?'
        title_regex = build_title_regex()
        whitespace_then_title_regex = fr'(?: [\s]* {title_regex} )?'
        whitespace_regex = r'[\s]*'
        closing_parenthesis_regex = r'\)'

        return ''.join([
            bracketed_link_text_regex,
            attribute_specifications_regex,
            opening_parenthesis_regex,
            whitespace_then_uri_regex,
            whitespace_then_title_regex,
            whitespace_regex,
            closing_parenthesis_regex,
        ])

    @staticmethod
    def build_substitute_function(attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            content = match.group('link_text')

            angle_bracketed_uri = match.group('angle_bracketed_uri')
            if angle_bracketed_uri is not None:
                href = angle_bracketed_uri
            else:
                href = match.group('bare_uri')

            if href is not None:
                href_protected = PlaceholderMaster.protect(href)
                href_attribute_specification = f'href={href_protected}'
            else:
                href_attribute_specification = ''

            double_quoted_title = match.group('double_quoted_title')
            if double_quoted_title is not None:
                title = double_quoted_title
            else:
                title = match.group('single_quoted_title')

            if title is not None:
                title_protected = PlaceholderMaster.protect(title)
                title_attribute_specification = f'title={title_protected}'
            else:
                title_attribute_specification = ''

            href_title_attribute_specifications = ' '.join([
                href_attribute_specification,
                title_attribute_specification,
            ])

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = ' '.join([
                    href_title_attribute_specifications,
                    attribute_specifications,
                    none_to_empty_string(matched_attribute_specifications),
                ])
            else:
                combined_attribute_specifications = href_title_attribute_specifications

            attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)

            substitute = f'<a{attributes_sequence}>{content}</a>'

            return substitute

        return substitute_function


class ReferencedLinkReplacement(
    ReplacementWithAttributeSpecifications,
    ReplacementWithProhibitedContent,
    Replacement,
):
    """
    A replacement rule for referenced links.

    CMD replacement rule syntax:
    ````
    ReferencedLinkReplacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _reference_master: 'ReferenceMaster'
    _regex_pattern_compiled: Optional[re.Pattern]
    _substitute_function: Optional[Callable[[re.Match], str]]

    def __init__(self, id_: str, reference_master, verbose_mode_enabled):
        super().__init__(id_, verbose_mode_enabled)
        self._reference_master = reference_master
        self._regex_pattern_compiled = None
        self._substitute_function = None

    @property
    def attribute_names(self) -> tuple[str, ...]:
        return (
            'queue_position',
            'attribute_specifications',
            'prohibited_content',
        )

    def _validate_mandatory_attributes(self):
        pass

    def _set_apply_method_variables(self):
        self._regex_pattern_compiled = re.compile(
            pattern=ReferencedLinkReplacement.build_regex_pattern(
                self._attribute_specifications,
                self._prohibited_content_regex,
            ),
            flags=re.ASCII | re.VERBOSE,
        )
        self._substitute_function = self.build_substitute_function(self._attribute_specifications)

    def _apply(self, string: str) -> str:
        return re.sub(
            pattern=self._regex_pattern_compiled,
            repl=self._substitute_function,
            string=string,
        )

    @staticmethod
    def build_regex_pattern(attribute_specifications: Optional[str], prohibited_content_regex: Optional[str]) -> str:
        link_text_regex = build_content_regex(prohibited_content_regex,
                                              permitted_content_regex=r'[^\]]', capture_group_name='link_text')
        bracketed_link_text_regex = fr'\[ [\s]* {link_text_regex} [\s]* \]'
        attribute_specifications_regex = build_attribute_specifications_regex(attribute_specifications,
                                                                              require_newline=False)
        label_regex = build_content_regex(prohibited_content_regex,
                                          permitted_content_regex=r'[^\]]', capture_group_name='label')
        bracketed_label_regex = fr'(?: \[ [\s]* {label_regex} [\s]* \] )?'

        return ''.join([
            bracketed_link_text_regex,
            attribute_specifications_regex,
            bracketed_label_regex,
        ])

    def build_substitute_function(self, attribute_specifications: Optional[str]) -> Callable[[re.Match], str]:
        def substitute_function(match: re.Match) -> str:
            content = match.group('link_text')

            label = match.group('label')
            if label is None or label == '':
                label = content

            try:
                referenced_attribute_specifications, href, title = self._reference_master.load_definition(label)
            except UnrecognisedLabelException:
                return match.group()

            if href is not None:
                href_protected = PlaceholderMaster.protect(href)
                href_attribute_specification = f'href={href_protected}'
            else:
                href_attribute_specification = ''

            if title is not None:
                title_protected = PlaceholderMaster.protect(title)
                title_attribute_specification = f'title={title_protected}'
            else:
                title_attribute_specification = ''

            href_title_referenced_attribute_specifications = ' '.join([
                href_attribute_specification,
                title_attribute_specification,
                none_to_empty_string(referenced_attribute_specifications)
            ])

            if attribute_specifications is not None:
                matched_attribute_specifications = match.group('attribute_specifications')
                combined_attribute_specifications = ' '.join([
                    href_title_referenced_attribute_specifications,
                    attribute_specifications,
                    none_to_empty_string(matched_attribute_specifications),
                ])
            else:
                combined_attribute_specifications = href_title_referenced_attribute_specifications

            attributes_sequence = build_attributes_sequence(combined_attribute_specifications, use_protection=True)

            substitute = f'<a{attributes_sequence}>{content}</a>'

            return substitute

        return substitute_function
