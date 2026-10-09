"""
# Conway-Markdown: core.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Core conversion logic.

CMD files are parsed as
````
«replacement_rules»
«delimiter»
«main_content»
````
where «delimiter» is the first occurrence of 3-or-more percent signs on its own line.
If the file is free of «delimiter», the whole file is parsed as «main_content».

For details on how «replacement_rules» and «main_content» are parsed, see <https://conwaymd.github.io/>.
"""

import re

from conwaymd.authorities import ReplacementAuthority
from conwaymd.constants import STANDARD_RULES
from conwaymd.utilities import none_to_empty_string


RULES_AND_CONTENT_PATTERN = re.compile(
    pattern=r'''
        (?:
            (?P<replacement_rules> [\s\S]*? )
            (?P<delimiter> ^ [%]{3,} )
            \n
        ) ?
        (?P<main_content> [\s\S]* )
    ''',
    flags=re.ASCII | re.MULTILINE | re.VERBOSE,
)


def extract_rules_and_content(cmd: str) -> tuple[str, str]:
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
    match = RULES_AND_CONTENT_PATTERN.fullmatch(string=cmd)
    assert match is not None

    replacement_rules = match.group('replacement_rules')
    main_content = match.group('main_content')

    return replacement_rules, main_content


NORMALISED_CMD_NAME_PATTERN = re.compile(
    pattern=r'[.](cmd) \Z',
    flags=re.VERBOSE,
)


def extract_separator_normalised_cmd_name(cmd_file_name: str) -> str:
    cmd_name = NORMALISED_CMD_NAME_PATTERN.sub(repl='', string=none_to_empty_string(cmd_file_name))
    separator_normalised_cmd_name = cmd_name.replace('\\', '/')

    return separator_normalised_cmd_name


def cmd_to_html(cmd: str, cmd_file_name: str, verbose_mode_enabled: bool = False) -> str:
    """
    Convert CMD to HTML.
    """
    replacement_rules, main_content = extract_rules_and_content(cmd)
    separator_normalised_cmd_name = extract_separator_normalised_cmd_name(cmd_file_name)

    replacement_authority = ReplacementAuthority(cmd_file_name, verbose_mode_enabled)
    replacement_authority.legislate(
        STANDARD_RULES,
        rules_file_name='STANDARD_RULES',
        cmd_name=separator_normalised_cmd_name,
    )
    replacement_authority.legislate(
        replacement_rules,
        rules_file_name=cmd_file_name,
        cmd_name=separator_normalised_cmd_name,
    )
    html = replacement_authority.execute(main_content)

    return html
