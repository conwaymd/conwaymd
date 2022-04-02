#!/usr/bin/env python3

"""
# cmd.py

Convert Conway-Markdown (CMD) to HTML.

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import argparse
import re
import sys


COMMAND_LINE_ERROR_EXIT_CODE = 2


def extract_cmd_name(cmd_file_name_argument):
  """
  Extract name-without-extension from a CMD file name argument.
  
  The argument received from the command line can be either
  `{cmd_name}.cmd`, `{cmd_name}.`, or `{cmd_name}`.
  If no argument is received from the command line,
  we loop through the file names, which are `{cmd_name}.cmd`.
  In all cases we want `{cmd_name}`.
  """
  
  return re.sub(r'\.(cmd)?\Z', '', cmd_file_name_argument)


def generate_html_file(cmd_file_name_argument, uses_command_line_argument):
  
  cmd_name = extract_cmd_name(cmd_file_name_argument)
  cmd_file_name = f'{cmd_name}.cmd'
  try:
    with open(cmd_file_name, 'r', encoding='utf-8') as cmd_file:
      cmd = cmd_file.read()
  except FileNotFoundError as file_not_found_error:
    if uses_command_line_argument:
      error_message = \
              (
                'error: '
                f'argument `{cmd_file_name_argument}`: '
                f'file `{cmd_file_name}` not found'
              )
      print(error_message)
      sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)
    else:
      error_message = \
              (
                f'file `{cmd_file_name}` not found '
                f'for `{cmd_file_name}` in cmd_file_name_list'
              )
      raise FileNotFoundError(error_message) from file_not_found_error
  
  return # TODO: implement this properly


DESCRIPTION = '''
  Convert Conway-Markdown (CMD) to HTML.
'''
CMD_FILE_NAME_HELP = '''
  Name of CMD file to be converted.
  Abbreviate as `file` or `file.` for increased productivity.
  Omit to convert all CMD files under the working directory.
'''


def parse_command_line_arguments():
  
  argument_parser = argparse.ArgumentParser(description=DESCRIPTION)
  argument_parser.add_argument(
    'cmd_file_name_argument',
    default='',
    help=CMD_FILE_NAME_HELP,
    metavar='file.cmd',
    nargs='?',
  )
  
  return argument_parser.parse_args()


def main():
  
  parsed_arguments = parse_command_line_arguments()
  cmd_file_name_argument = parsed_arguments.cmd_file_name_argument
  
  if cmd_file_name_argument != '':
    generate_html_file(cmd_file_name_argument, uses_command_line_argument=True)
    return
  
  cmd_file_name_list = [] # TODO: implement this properly
  for cmd_file_name in cmd_file_name_list:
    generate_html_file(cmd_file_name, uses_command_line_argument=False)


if __name__ == '__main__':
  main()
