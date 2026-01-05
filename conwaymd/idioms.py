"""
# Conway-Markdown: idioms.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Common idioms.
"""

import re
from typing import Iterable, Optional, Union

from conwaymd.placeholders import PlaceholderMaster
from conwaymd.utilities import escape_attribute_value_html


ATTRIBUTE_NAME_FROM_ABBREVIATION = {
    '#': 'id',
    '.': 'class',
    'l': 'lang',
    'r': 'rowspan',
    'c': 'colspan',
    'w': 'width',
    'h': 'height',
    's': 'style',
}
BLOCK_TAG_NAMES = [
    'address',
    'article',
    'aside',
    'blockquote',
    'dd',
    'details',
    'dialog',
    'div',
    'dl',
    'dt',
    'fieldset',
    'figcaption',
    'figure',
    'footer',
    'form',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'header',
    'hgroup',
    'hr',
    'li',
    'main',
    'nav',
    'ol',
    'p',
    'pre',
    'section',
    'table',
    'tbody',
    'td',
    'tfoot',
    'th',
    'thead',
    'ul',
]


def compute_attribute_specification_matches(attribute_specifications: str) -> Iterable[re.Match]:
    return re.finditer(
        pattern=r'''
            [\s]*
            (?:
                (?P<name> [^\s=]+ ) =
                (?:
                    "(?P<double_quoted_value> [\s\S]*? )"
                        |
                    '(?P<single_quoted_value> [\s\S]*? )'
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
                [-] (?P<delete_name> [\S]+ )
                    |
                (?P<boolean_name> [\S]+ )
            ) ?
            [\s]*
        ''',
        string=attribute_specifications,
        flags=re.ASCII | re.VERBOSE,
    )


def extract_attribute_name_and_value(attribute_specification_match: re.Match,
                                     ) -> Union[tuple[str, Optional[str]], tuple[str], None]:
    """
    Extract (at most) name and value.

    Specifically:
    - («name», «value») for a non-boolean attribute
    - («name», None) for a boolean attribute
    - («name»,) for an attribute to be omitted
    - None for an invalid attribute specification
    """
    name = attribute_specification_match.group('name')
    if name is not None:
        try:
            name = ATTRIBUTE_NAME_FROM_ABBREVIATION[name]
        except KeyError:
            pass

        double_quoted_value = attribute_specification_match.group('double_quoted_value')
        if double_quoted_value is not None:
            return name, double_quoted_value

        single_quoted_value = attribute_specification_match.group('single_quoted_value')
        if single_quoted_value is not None:
            return name, single_quoted_value

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

    delete_name = attribute_specification_match.group('delete_name')
    if delete_name is not None:
        return delete_name,

    boolean_name = attribute_specification_match.group('boolean_name')
    if boolean_name is not None:
        return boolean_name, None

    return None


def build_attributes_sequence(attribute_specifications: Optional[str], use_protection: bool = False) -> str:
    """
    Convert CMD attribute specifications to an attribute sequence.

    CMD attribute specifications are of the following forms:
    ````
    «name»="«quoted_value»"
    «name»=«bare_value»
    #«id»
    .«class»
    r«rowspan»
    c«colspan»
    w«width»
    h«height»
    -«delete_name»
    «boolean_name»
    ````
    In the two forms with an explicit equals sign, the following abbreviations are allowed for `name`:
    - # for id
    - . for class
    - l for lang
    - r for rowspan
    - c for colspan
    - w for width
    - h for height
    - s for style

    If an attribute of the same name is specified multiple times, the latest specification shall prevail,
    except when `class` is specified multiple times, in which case the values will be appended.
    For example, `id=x #y .a .b name=value .=c class="d"` shall be converted to the attribute sequence
    ` id="y" class="a b c d" name="value"`.
    """
    attribute_value_from_name: dict[str, str] = {}

    for attribute_specification_match in compute_attribute_specification_matches(attribute_specifications):
        name_and_value = extract_attribute_name_and_value(attribute_specification_match)

        if name_and_value is None:  # invalid attribute specification
            continue

        try:
            name, value = name_and_value
            if name == 'class':
                try:
                    attribute_value_from_name['class'] += f' {value}'
                except KeyError:
                    attribute_value_from_name['class'] = value
            else:
                attribute_value_from_name[name] = value
        except ValueError:  # attribute to be omitted
            name, = name_and_value
            attribute_value_from_name.pop(name, None)

    attribute_sequence = ''

    for name, value in attribute_value_from_name.items():
        if value is None:  # boolean attribute
            attribute_sequence += f' {name}'
        else:
            value = PlaceholderMaster.unprotect(value)
            value = escape_attribute_value_html(value)
            attribute_sequence += f' {name}="{value}"'

    if use_protection:
        attribute_sequence = PlaceholderMaster.protect(attribute_sequence)

    return attribute_sequence


def build_block_tag_regex(require_anchoring: bool) -> str:
    block_tag_name_regex = '|'.join(re.escape(tag_name) for tag_name in BLOCK_TAG_NAMES)
    after_tag_name_regex = fr'[\s{PlaceholderMaster.MARKER}>]'
    block_tag_regex = f'[<] [/]? (?: {block_tag_name_regex} ) {after_tag_name_regex}'

    if require_anchoring:
        block_anchoring_regex = build_block_anchoring_regex(syntax_type_is_block=True)
        return block_anchoring_regex + block_tag_regex
    else:
        return block_tag_regex


def build_block_anchoring_regex(syntax_type_is_block: bool, capture_anchoring_whitespace: bool = False) -> str:
    if syntax_type_is_block:
        if capture_anchoring_whitespace:
            return r'^ (?P<anchoring_whitespace> [^\S\n]* )'
        else:
            return r'^ [^\S\n]*'

    return ''


def build_maybe_hanging_whitespace_regex() -> str:
    return r'[^\S\n]* (?: \n (?P=anchoring_whitespace) [^\S\n]+ )?'


def build_flags_regex(flag_name_from_letter: dict[str, str], has_flags: bool) -> str:
    if not has_flags:
        return ''

    flag_letters = ''.join(
        re.escape(flag_letter)
        for flag_letter in flag_name_from_letter.keys()
    )
    return f'(?P<flags> [{flag_letters}]* )'


def build_extensible_delimiter_opening_regex(extensible_delimiter_character: str,
                                             extensible_delimiter_min_length: int) -> str:
    character_regex = re.escape(extensible_delimiter_character)
    repetition_regex = f'{{{extensible_delimiter_min_length},}}'

    return f'(?P<extensible_delimiter> {character_regex}{repetition_regex} )'


def build_attribute_specifications_regex(attribute_specifications: Optional[str], require_newline: bool,
                                         capture_attribute_specifications: bool = True, allow_omission: bool = True,
                                         ) -> str:
    if attribute_specifications is not None:
        if capture_attribute_specifications:
            braced_sequence_regex = r'\{ (?P<attribute_specifications> [^}]*? ) \}'
        else:
            braced_sequence_regex = r'\{ [^}]*? \}'

        if allow_omission:
            braced_sequence_regex = f'(?: {braced_sequence_regex} )?'
    else:
        braced_sequence_regex = ''

    if require_newline:
        block_newline_regex = r'\n'
    else:
        block_newline_regex = ''

    return braced_sequence_regex + block_newline_regex


def build_captured_character_class_regex(characters: set[str], capture_group_name: str) -> Optional[str]:
    if len(characters) == 0:
        return None

    characters_escaped = ''.join(re.escape(character) for character in sorted(characters))
    character_class_regex = f'[{characters_escaped}]'

    return f'(?P<{capture_group_name}> {character_class_regex} )'


def build_content_regex(prohibited_content_regex: Optional[str] = None, permitted_content_regex: str = r'[\s\S]',
                        permit_empty: bool = True, capture_group_name: str = 'content') -> str:
    if prohibited_content_regex is None:
        permitted_atom_regex = permitted_content_regex
    else:
        permitted_atom_regex = f'(?: (?! {prohibited_content_regex} ) {permitted_content_regex} )'

    if permit_empty:
        repetition = '*'
    else:
        repetition = '+'

    return f'(?P<{capture_group_name}> {permitted_atom_regex}{repetition}? )'


def build_extensible_delimiter_closing_regex() -> str:
    return '(?P=extensible_delimiter)'


def build_uri_regex(be_greedy: bool) -> str:
    if be_greedy:
        greed = ''
    else:
        greed = '?'

    return fr'(?: [<] (?P<angle_bracketed_uri> [^>]*? ) [>] | (?P<bare_uri> [\S]+{greed} ) )'


def build_title_regex() -> str:
    return r'''(?: "(?P<double_quoted_title> [^"]*? )" | '(?P<single_quoted_title> [^']*? )' )'''
