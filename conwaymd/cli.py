"""
# Conway-Markdown: cli.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Command-line interface.
"""

import argparse
import os
import re
import sys

from conwaymd._version import __version__
from conwaymd.constants import COMMAND_LINE_ERROR_EXIT_CODE, GENERIC_ERROR_EXIT_CODE
from conwaymd.core import cmd_to_html

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
VERBOSE_MODE_HELP = '''
    run in verbose mode (prints every replacement applied)
'''


def is_cmd_file(file_name: str) -> bool:
    return file_name.endswith('.cmd')


def extract_cmd_name(cmd_file_name_argument: str) -> str:
    """
    Extract name-without-extension from a CMD file name argument.

    Here, CMD file name argument may be of the form `«cmd_name».cmd`, `«cmd_name».`, or `«cmd_name»`.
    The path is normalised by resolving `./` and `../`.
    """
    cmd_file_name_argument = os.path.normpath(cmd_file_name_argument)
    cmd_name = re.sub(pattern=r'[.](cmd)? \Z', repl='', string=cmd_file_name_argument, flags=re.VERBOSE)

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


def generate_html_file(cmd_file_name_argument: str, verbose_mode_enabled: bool, uses_command_line_argument: bool):
    cmd_name = extract_cmd_name(cmd_file_name_argument)
    cmd_file_name = f'{cmd_name}.cmd'
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

    html = cmd_to_html(cmd, cmd_file_name, verbose_mode_enabled)

    html_file_name = f'{cmd_name}.html'
    try:
        with open(html_file_name, 'w', encoding='utf-8') as html_file:
            html_file.write(html)
        print(f'success: wrote to `{html_file_name}`')
    except IOError:
        print(f'error: cannot write to `{html_file_name}`', file=sys.stderr)
        sys.exit(GENERIC_ERROR_EXIT_CODE)


def main():
    parsed_arguments = parse_command_line_arguments()
    cmd_file_name_arguments = parsed_arguments.cmd_file_name_arguments
    all_mode_enabled = parsed_arguments.all_mode_enabled
    verbose_mode_enabled = parsed_arguments.verbose_mode_enabled

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
            generate_html_file(cmd_file_name, verbose_mode_enabled, uses_command_line_argument=False)

    else:
        for cmd_file_name_argument in cmd_file_name_arguments:
            generate_html_file(cmd_file_name_argument, verbose_mode_enabled, uses_command_line_argument=True)


if __name__ == '__main__':
    main()
