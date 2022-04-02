#!/usr/bin/env python3

"""
# cmd.py

Convert Conway-Markdown (CMD) to HTML.

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.
"""


import argparse


DESCRIPTION = 'Convert Conway-Markdown (CMD) to HTML.'
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
  print(cmd_file_name)


if __name__ == '__main__':
  main()
