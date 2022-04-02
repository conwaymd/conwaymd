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


def to_normalised_name(cmd_file_name):
  """
  Normalise a CMD file name.
  
  The CMD file name received from the command line parser
  can be of the form `name.cmd`, `name.`, or `name`.
  Here we normalise it to `name`.
  """
  
  normalised_cmd_name = re.sub(r'\.(cmd)?\Z', '', cmd_file_name)
  
  return normalised_cmd_name


def generate_html_file(cmd_file_name, is_direct_command_line_call):
  
  normalised_cmd_name = to_normalised_name(cmd_file_name)
  normalised_cmd_file_name = f'{normalised_cmd_name}.cmd'
  
  try:
    with open(normalised_cmd_name, 'r', encoding='utf-8') as cmd_file:
      cmd = cmd_file.read()
  except FileNotFoundError as file_not_found_error:
    if is_direct_command_line_call:
      error_message = \
              (
                'error: '
                f'argument `{cmd_file_name}`: '
                f'file `{normalised_cmd_file_name}` not found'
              )
      print(error_message)
      sys.exit(COMMAND_LINE_ERROR_EXIT_CODE)
    else:
      error_message = \
              (
                f'file `{normalised_cmd_file_name}` not found '
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
    'cmd_file_name',
    default='',
    help=CMD_FILE_NAME_HELP,
    metavar='file.cmd',
    nargs='?',
  )
  
  return argument_parser.parse_args()


def main():
  
  parsed_arguments = parse_command_line_arguments()
  cmd_file_name = parsed_arguments.cmd_file_name
  
  if cmd_file_name != '':
    generate_html_file(cmd_file_name, is_direct_command_line_call=True)
    return
  
  cmd_file_name_list = [] # TODO: implement this properly
  for cmd_file_name in cmd_file_name_list:
    generate_html_file(cmd_file_name, is_direct_command_line_call=False)


if __name__ == '__main__':
  main()
