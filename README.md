# Conway-Markdown (CMD), v4

A replacement-driven markup language inspired by Markdown.

- Implemented in [Python 3.{whatever Debian stable is at}][python3].
- Licensed under "MIT No Attribution" (MIT-0), see [LICENSE].

[python3]: https://packages.debian.org/stable/python3
[LICENSE]: LICENSE


## Usage

Since this is just a shitty single-file script,
it will not be turned into a proper Python package.

### Linux terminals, macOS Terminal, Git BASH for Windows

1. Make an alias for `cmd.py`
   in whatever dotfile you configure your aliases in:

   ```bashrc
   alias cmd='path/to/cmd.py'
   ```

2. Invoke the alias to convert a CMD file to HTML:

   ```bash
   $ cmd [file.cmd]
   ```

   - Abbreviate `file.cmd` as `file` or `file.` for increased productivity.
   - Omit `file.cmd` to convert all CMD files under the working directory.

### Windows Command Prompt

1. Add the folder containing `cmd.py` to the `%PATH%` variable

2. Invoke `cmd.py` to convert a CMD file to HTML:

   ```cmd
   > cmd.py [file.cmd]
   ```

   - Abbreviate `file.cmd` as `file` or `file.` for increased productivity.
   - Omit `file.cmd` to convert all CMD files under the working directory.

## Features

TODO
