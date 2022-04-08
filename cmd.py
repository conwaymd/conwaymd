#!/usr/bin/env python3

"""
# cmd.py

Convert Conway-Markdown (CMD) to HTML.

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import argparse
import os
import re
import sys


GENERIC_ERROR_EXIT_CODE = 1
COMMAND_LINE_ERROR_EXIT_CODE = 2


def none_to_empty_string(string):
  
  if string is not None:
    return string
  
  return ''


def get_group(group_name, match_object):
  """
  Retrieve as string a named capture group from a match object.
  
  Ensures the result is not None.
  """
  
  string = match_object.group(group_name)
  
  return none_to_empty_string(string)


def extract_rules_and_content(cmd):
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
  
  match_object = \
          re.fullmatch(
            r'''
              (?:
                (?P<replacement_rules> [\s\S]*? )
                (?P<delimiter> ^ [%]{3,} )
                \n
              ) ?
              (?P<main_content> [\s\S]* )
            ''',
            cmd,
            flags=re.MULTILINE | re.VERBOSE,
          )
  
  replacement_rules = get_group('replacement_rules', match_object)
  main_content = get_group('main_content', match_object)
  
  return (replacement_rules, main_content)


def cmd_to_html(cmd):
  """
  Convert CMD to HTML.
  """
  
  replacement_rules, main_content = extract_rules_and_content(cmd)
  
  html = main_content # TODO: implement conversion properly
  
  return html


def is_cmd_file(file_name):
  return file_name.endswith('.cmd')


def extract_cmd_name(cmd_file_name_argument):
  """
  Extract name-without-extension from a CMD file name argument.
  
  The argument received from the command line can be either
  `«cmd_name».cmd`, `«cmd_name».`, or `«cmd_name»`,
  or even `./«cmd_name».cmd` if the user is being dumb.
  If no argument be received from the command line,
  we loop through the file names, which are `./«cmd_name».cmd`.
  If the operating system be Windows,
  the directory separators will be backslashes
  instead of forward slashes (as in URLs).
  In all cases we want `«cmd_name»` with forward slashes.
  """
  
  cmd_file_name_argument = re.sub(r'\\', '/', cmd_file_name_argument)
  cmd_file_name_argument = re.sub(r'\A[.][/]', '', cmd_file_name_argument)
  cmd_name = re.sub(r'[.](cmd)?\Z', '', cmd_file_name_argument)
  
  return cmd_name


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
  
  html = cmd_to_html(cmd)
  
  html_file_name = f'{cmd_name}.html'
  try:
    with open(html_file_name, 'w', encoding='utf-8') as html_file:
      html_file.write(html)
      print(f'success: wrote to `{html_file_name}`')
  except IOError:
    print(f'error: cannot write to `{html_file_name}`')
    sys.exit(GENERIC_ERROR_EXIT_CODE)


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
  else:
    for path, _, file_names in os.walk('./'):
      for file_name in file_names:
        if is_cmd_file(file_name):
          cmd_file_name = os.path.join(path, file_name)
          generate_html_file(cmd_file_name, uses_command_line_argument=False)


if __name__ == '__main__':
  main()
