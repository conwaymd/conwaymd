"""
# Conway-Markdown: cli.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Command-line interface.
"""

import argparse
import ast
import hashlib
import os
import re
import sys
from typing import Optional

from conwaymd._version import __version__
from conwaymd.constants import COMMAND_LINE_ERROR_EXIT_CODE, GENERIC_ERROR_EXIT_CODE
from conwaymd.core import cmd_to_html

CACHE_FILE_NAME = '.cmdcache'
VERSION_KEY = 'version'
CMD_DIGEST_KEY = 'cmd_digest'
HTML_DIGEST_KEY = 'html_digest'

DESCRIPTION = '''
    Convert Conway-Markdown (CMD) to HTML.
'''
CMD_FILE_NAME_HELP = '''
    name of CMD file to be converted
    (can be abbreviated as `file` or `file.` for increased productivity)
'''
ALL_MODE_HELP = '''
    convert all CMD files under the working directory
'''
CACHE_MODE_HELP = f'''
    utilise `{CACHE_FILE_NAME}` to skip unchanged files
'''
VERBOSE_MODE_HELP = '''
    run in verbose mode (prints every replacement applied)
'''


def is_cmd_file(file_name: str) -> bool:
    return file_name.endswith('.cmd')


CMD_NAME_PATTERN = re.compile(pattern=r'[.](cmd)? \Z', flags=re.VERBOSE)


def extract_cmd_name(cmd_file_name_argument: str) -> str:
    """
    Extract name-without-extension from a CMD file name argument.

    Here, CMD file name argument may be of the form `«cmd_name».cmd`, `«cmd_name».`, or `«cmd_name»`.
    The path is normalised by resolving `./` and `../`.
    """
    cmd_file_name_argument = os.path.normpath(cmd_file_name_argument)
    cmd_name = CMD_NAME_PATTERN.sub(repl='', string=cmd_file_name_argument)

    return cmd_name


def parse_command_line_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(description=DESCRIPTION)
    argument_parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'{argument_parser.prog} version {__version__}',
    )
    argument_parser.add_argument(
        '-a', '--all',
        dest='all_mode_enabled',
        action='store_true',
        help=ALL_MODE_HELP,
    )
    argument_parser.add_argument(
        '-c', '--cache',
        dest='cache_mode_enabled',
        action='store_true',
        help=CACHE_MODE_HELP,
    )
    argument_parser.add_argument(
        '-x', '--verbose',
        dest='verbose_mode_enabled',
        action='store_true',
        help=VERBOSE_MODE_HELP,
    )
    argument_parser.add_argument(
        'cmd_file_name_arguments',
        default=[],
        help=CMD_FILE_NAME_HELP,
        metavar='file.cmd',
        nargs='*',
    )

    return argument_parser.parse_args()


def read_cache() -> dict[str, dict]:
    try:
        with open(CACHE_FILE_NAME, 'r', encoding='utf-8') as cache_file:
            cache_file_content = cache_file.read()
    except OSError:
        return {}

    try:
        cached_details_from_cmd_name = ast.literal_eval(cache_file_content)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return {}

    if not isinstance(cached_details_from_cmd_name, dict):
        return {}

    return {
        cmd_name: cached_details
        for cmd_name, cached_details in cached_details_from_cmd_name.items()
        if isinstance(cmd_name, str) and isinstance(cached_details, dict)
    }


def write_cache(cached_details_from_cmd_name: dict[str, dict],
                new_caching_tuples: list[tuple[str, Optional[dict[str, str]]]]):
    new_cached_details_from_cmd_name = {
        **cached_details_from_cmd_name,
        **{
            cmd_name: new_cached_details
            for cmd_name, new_cached_details in new_caching_tuples
            if new_cached_details is not None
        }
    }

    cache_content = str(new_cached_details_from_cmd_name)

    try:
        with open(CACHE_FILE_NAME, 'w', encoding='utf-8') as cache_file:
            cache_file.write(cache_content)
    except OSError:
        print(f'error: cannot write to `{CACHE_FILE_NAME}`', file=sys.stderr)
        sys.exit(GENERIC_ERROR_EXIT_CODE)


def read_cmd_file(cmd_file_name_argument: str, cmd_file_name: str, uses_command_line_argument: bool) -> str:
    try:
        with open(cmd_file_name, 'r', encoding='utf-8') as cmd_file:
            cmd = cmd_file.read()
    except FileNotFoundError as file_not_found_error:
        if uses_command_line_argument:
            print(f'error: argument `{cmd_file_name_argument}`: file `{cmd_file_name}` not found', file=sys.stderr)
            sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)
        else:
            error_message = f'file `{cmd_file_name}` not found for `{cmd_file_name}` in cmd_file_name_list'
            raise FileNotFoundError(error_message) from file_not_found_error

    return cmd


def write_html_file(html_file_name: str, html: str):
    try:
        with open(html_file_name, 'w', encoding='utf-8') as html_file:
            html_file.write(html)
    except OSError:
        print(f'error: cannot write to `{html_file_name}`', file=sys.stderr)
        sys.exit(GENERIC_ERROR_EXIT_CODE)
    else:
        print(f'success: wrote to `{html_file_name}`')


def generate_html_file(cmd_file_name_argument: str, cached_details_from_cmd_name: Optional[dict[str, dict]],
                       verbose_mode_enabled: bool, uses_command_line_argument: bool,
                       ) -> tuple[str, Optional[dict[str, str]]]:
    """
    Generate (or leave unchanged) the HTML file corresponding to a CMD file.

    Return the tuple (normalised CMD name-without-extension, optional dictionary of cached details).
    """
    cmd_name = extract_cmd_name(cmd_file_name_argument)
    cmd_file_name = f'{cmd_name}.cmd'
    cmd = read_cmd_file(cmd_file_name_argument, cmd_file_name, uses_command_line_argument)

    html_file_name = f'{cmd_name}.html'

    if cached_details_from_cmd_name is None:
        cmd_digest = None  # no caching logic required
    else:
        cmd_digest = hashlib.sha256(cmd.encode('utf-8')).hexdigest()

        try:
            cached_details = cached_details_from_cmd_name[cmd_name]
            cached_version = cached_details[VERSION_KEY]
            cached_cmd_digest = cached_details[CMD_DIGEST_KEY]
            cached_html_digest = cached_details[HTML_DIGEST_KEY]
        except KeyError:
            pass
        else:
            if __version__ == cached_version:
                if cmd_digest == cached_cmd_digest:
                    try:
                        with open(html_file_name, 'rb') as html_binary_file:
                            html_binary = html_binary_file.read()
                    except OSError:
                        pass
                    else:
                        html_digest = hashlib.sha256(html_binary).hexdigest()
                        if html_digest == cached_html_digest:
                            print(f'success: left `{html_file_name}` unchanged per cache')
                            return cmd_name, cached_details

    html = cmd_to_html(cmd, cmd_file_name, verbose_mode_enabled)

    write_html_file(html_file_name, html)

    if cmd_digest is None:
        return cmd_name, None
    else:
        new_html_digest = hashlib.sha256(html.encode('utf-8')).hexdigest()
        new_cached_details = {
            VERSION_KEY: __version__,
            CMD_DIGEST_KEY: cmd_digest,
            HTML_DIGEST_KEY: new_html_digest,
        }
        return cmd_name, new_cached_details


def main():
    parsed_arguments = parse_command_line_arguments()
    cmd_file_name_arguments = parsed_arguments.cmd_file_name_arguments
    all_mode_enabled = parsed_arguments.all_mode_enabled
    cache_mode_enabled = parsed_arguments.cache_mode_enabled
    verbose_mode_enabled = parsed_arguments.verbose_mode_enabled

    if cache_mode_enabled:
        cached_details_from_cmd_name = read_cache()
    else:
        cached_details_from_cmd_name = None

    new_caching_tuples: list[tuple[str, Optional[dict[str, str]]]] = []

    if all_mode_enabled:
        if len(cmd_file_name_arguments) > 0:
            print('error: option -a (or --all) cannot be used with positional argument', file=sys.stderr)
            sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)

        cmd_file_names = [
            os.path.join(path, file_name)
            for path, _, file_names in os.walk(os.curdir)
            for file_name in file_names
            if is_cmd_file(file_name)
        ]
        for cmd_file_name in sorted(cmd_file_names):
            new_caching_tuple = generate_html_file(cmd_file_name, cached_details_from_cmd_name,
                                                   verbose_mode_enabled, uses_command_line_argument=False)
            new_caching_tuples.append(new_caching_tuple)

    else:
        for cmd_file_name_argument in cmd_file_name_arguments:
            new_caching_tuple = generate_html_file(cmd_file_name_argument, cached_details_from_cmd_name,
                                                   verbose_mode_enabled, uses_command_line_argument=True)
            new_caching_tuples.append(new_caching_tuple)

    if cached_details_from_cmd_name is not None:
        write_cache(cached_details_from_cmd_name, new_caching_tuples)


if __name__ == '__main__':
    main()
