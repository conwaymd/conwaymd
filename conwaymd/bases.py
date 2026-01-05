"""
# Conway-Markdown: bases.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Base classes for CMD replacement rules.
"""

import abc
import copy
import re
from typing import Optional

from conwaymd.constants import VERBOSE_MODE_DIVIDER_SYMBOL_COUNT
from conwaymd.exceptions import CommittedMutateException, UncommittedApplyException


class Replacement(abc.ABC):
    """
    Base class for a replacement rule.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    Replacement: #«id»
    - queue_position: (def) NONE | ROOT | BEFORE #«id» | AFTER #«id»
    - positive_flag: (def) NONE | «FLAG_NAME»
    - negative_flag: (def) NONE | «FLAG_NAME»
    ````
    """
    _is_committed: bool
    _id: str
    _queue_position_type: Optional[str]
    _queue_reference_replacement: Optional['Replacement']
    _positive_flag_name: Optional[str]
    _negative_flag_name: Optional[str]
    _verbose_mode_enabled: bool

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        self._is_committed = False
        self._id = id_
        self._queue_position_type = None
        self._queue_reference_replacement = None
        self._positive_flag_name = None
        self._negative_flag_name = None
        self._verbose_mode_enabled = verbose_mode_enabled

    @property
    @abc.abstractmethod
    def attribute_names(self) -> tuple[str, ...]:
        raise NotImplementedError

    @property
    def id_(self) -> str:
        return self._id

    @property
    def queue_position_type(self) -> Optional[str]:
        return self._queue_position_type

    @queue_position_type.setter
    def queue_position_type(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `queue_position_type` after `commit()`')

        self._queue_position_type = value

    @property
    def queue_reference_replacement(self) -> Optional['Replacement']:
        return self._queue_reference_replacement

    @queue_reference_replacement.setter
    def queue_reference_replacement(self, value: 'Replacement'):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `queue_reference_replacement` after `commit()`')

        self._queue_reference_replacement = value

    @property
    def positive_flag_name(self) -> Optional[str]:
        return self._positive_flag_name

    @positive_flag_name.setter
    def positive_flag_name(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `positive_flag_name` after `commit()`')

        self._positive_flag_name = value

    @property
    def negative_flag_name(self) -> Optional[str]:
        return self._negative_flag_name

    @negative_flag_name.setter
    def negative_flag_name(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `negative_flag_name` after `commit()`')

        self._negative_flag_name = value

    def commit(self):
        self._validate_mandatory_attributes()
        self._set_apply_method_variables()
        self._is_committed = True

    def apply(self, string: str, enabled_flag_names: Optional[set[str]] = None) -> str:
        if not self._is_committed:
            raise UncommittedApplyException('error: cannot call `apply(string)` before `commit()`')

        if enabled_flag_names is not None:
            positive_flag_name = self._positive_flag_name
            if positive_flag_name is not None and positive_flag_name not in enabled_flag_names:
                return string

            negative_flag_name = self._negative_flag_name
            if negative_flag_name is not None and negative_flag_name in enabled_flag_names:
                return string

        string_before = string
        string = self._apply(string)
        string_after = string

        if self._verbose_mode_enabled:
            if string_before == string_after:
                no_change_indicator = ' (no change)'
            else:
                no_change_indicator = ''

            try:
                print('<' * VERBOSE_MODE_DIVIDER_SYMBOL_COUNT + f' BEFORE #{self._id}')
                print(string_before)
                print('=' * VERBOSE_MODE_DIVIDER_SYMBOL_COUNT + no_change_indicator)
                print(string_after)
                print('>' * VERBOSE_MODE_DIVIDER_SYMBOL_COUNT + f' AFTER #{self._id}')
                print('\n\n\n\n')
            except UnicodeEncodeError as unicode_encode_error:
                # caused by Private Use Area code points used for placeholders
                error_message = (
                    'bad print due to non-Unicode terminal encoding, likely `cp1252` on Git BASH for Windows. '
                    'Try setting the `PYTHONIOENCODING` environment variable to `utf-8` '
                    '(add `export PYTHONIOENCODING=utf-8` to `.bash_profile` and then source it). '
                    'See <https://stackoverflow.com/a/7865013>.'
                )
                raise FileNotFoundError(error_message) from unicode_encode_error

        return string_after

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
    def _apply(self, string: str) -> str:
        """
        Apply the defined replacement to a string.
        """
        raise NotImplementedError


class ReplacementWithSubstitutions(Replacement, abc.ABC):
    """
    Base class for a replacement rule with substitutions.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithSubstitutions: #«id»
    * "«pattern»" | '«pattern»' | «pattern»
        -->
      CMD_VERSION | CMD_NAME | CMD_BASENAME | CLEAN_URL |
              "«substitute»" | '«substitute»' | «substitute»
    [...]
    ````
    """
    _substitute_from_pattern: dict[str, str]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._substitute_from_pattern = {}

    def add_substitution(self, pattern: str, substitute: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot call `add_substitution(...)` after `commit()`')
        self._substitute_from_pattern[pattern] = substitute


class ReplacementWithSyntaxType(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `syntax_type`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithSyntaxType: #«id»
    - syntax_type: BLOCK | INLINE (mandatory)
    ````
    """
    _syntax_type_is_block: Optional[bool]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._syntax_type_is_block = None

    @property
    def syntax_type_is_block(self) -> Optional[bool]:
        return self._syntax_type_is_block

    @syntax_type_is_block.setter
    def syntax_type_is_block(self, value: bool):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `syntax_type_is_block` after `commit()`')

        self._syntax_type_is_block = value


class ReplacementWithAllowedFlags(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `allowed_flags`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithAllowedFlags: #«id»
    - allowed_flags: (def) NONE | «letter»=«FLAG_NAME» [...]
    ````
    """
    _flag_name_from_letter: dict[str, str]
    _has_flags: bool

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._flag_name_from_letter = {}
        self._has_flags = False

    @property
    def flag_name_from_letter(self) -> dict[str, str]:
        return self._flag_name_from_letter

    @flag_name_from_letter.setter
    def flag_name_from_letter(self, value: dict[str, str]):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `flag_name_from_letter` after `commit()`')

        self._flag_name_from_letter = copy.copy(value)

    @staticmethod
    def get_enabled_flag_names(match: re.Match, flag_name_from_letter: dict[str, str], has_flags: bool) -> set[str]:
        enabled_flag_names: set[str] = set()
        if has_flags:
            flags = match.group('flags')
            for flag_letter, flag_name in flag_name_from_letter.items():
                if flag_letter in flags:
                    enabled_flag_names.add(flag_name)

        return enabled_flag_names


class ReplacementWithAttributeSpecifications(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `attribute_specifications`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithAttributeSpecifications: #«id»
    - attribute_specifications: (def) NONE | EMPTY | «string»
    ````
    """
    _attribute_specifications: Optional[str]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._attribute_specifications = None

    @property
    def attribute_specifications(self) -> Optional[str]:
        return self._attribute_specifications

    @attribute_specifications.setter
    def attribute_specifications(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `attribute_specifications` after `commit()`')

        self._attribute_specifications = value


class ReplacementWithProhibitedContent(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `prohibited_content`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithProhibitedContent: #«id»
    - prohibited_content: (def) NONE | BLOCKS | ANCHORED_BLOCKS
    ````
    """
    _prohibited_content_regex: Optional[str]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._prohibited_content_regex = None

    @property
    def prohibited_content_regex(self) -> Optional[str]:
        return self._prohibited_content_regex

    @prohibited_content_regex.setter
    def prohibited_content_regex(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `prohibited_content_regex` after `commit()`')

        self._prohibited_content_regex = value


class ReplacementWithContentReplacements(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `content_replacements`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithContentReplacements: #«id»
    - content_replacements: (def) NONE | #«id» [...]
    ````
    """
    _content_replacements: list['Replacement']

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._content_replacements = []

    @property
    def content_replacements(self) -> list['Replacement']:
        return self._content_replacements

    @content_replacements.setter
    def content_replacements(self, value: list['Replacement']):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `content_replacements` after `commit()`')

        self._content_replacements = copy.copy(value)


class ReplacementWithTagName(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `tag_name`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithTagName: #«id»
    - tag_name: (def) NONE | «name»
    ````
    """
    _tag_name: Optional[str]

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._tag_name = None

    @property
    def tag_name(self) -> Optional[str]:
        return self._tag_name

    @tag_name.setter
    def tag_name(self, value: str):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `tag_name` after `commit()`')

        self._tag_name = value


class ReplacementWithConcludingReplacements(Replacement, abc.ABC):
    """
    Base class for a replacement rule with `concluding_replacements`.

    Not to be used when authoring CMD documents.
    (Hypothetical) CMD replacement rule syntax:
    ````
    ReplacementWithConcludingReplacements: #«id»
    - concluding_replacements: (def) NONE | #«id» [...]
    ````
    """
    _concluding_replacements: list['Replacement']

    def __init__(self, id_: str, verbose_mode_enabled: bool):
        super().__init__(id_, verbose_mode_enabled)
        self._concluding_replacements = []

    @property
    def concluding_replacements(self) -> list['Replacement']:
        return self._concluding_replacements

    @concluding_replacements.setter
    def concluding_replacements(self, value: list['Replacement']):
        if self._is_committed:
            raise CommittedMutateException('error: cannot set `concluding_replacements` after `commit()`')

        self._concluding_replacements = copy.copy(value)
