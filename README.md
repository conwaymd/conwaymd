# Conway-Markdown (conwaymd, CMD)

Conway-Markdown is:

- A replacement-driven markup language inspired by Markdown.
- A demonstration of the folly of throwing regex at a parsing problem.
- The result of someone joking that "the filenames would look like Windows executables from the 90s".
- Implemented in [Python 3.{whatever Debian stable is at}][python3].
- Licensed under "MIT No Attribution" (MIT-0), see [LICENSE].

For detailed documentation, see <<https://conwaymd.github.io/>>.

[python3]: https://packages.debian.org/stable/python3
[LICENSE]: LICENSE


## Installation

Conway-Markdown is [published to PyPI as `conwaymd`][pypi]:

```bash
$ pip3 install conwaymd
```

- If simply using as a command line tool, do `pipx` instead of `pip3`
  to avoid having to set up a virtual environment.
- If using Windows, do `pip` instead of `pip3`.

[pypi]: https://pypi.org/project/conwaymd/


## Usage (command line)

```bash
$ cmd [-h] [-v] [-a] [-x] [file.cmd ...]

Convert Conway-Markdown (CMD) to HTML.

positional arguments:
  file.cmd       name of CMD file to be converted (can be abbreviated as
                 `file` or `file.` for increased productivity)

options:
  -h, --help     show this help message and exit
  -v, --version  show program's version number and exit
  -a, --all      convert all CMD files under the working directory
  -x, --verbose  run in verbose mode (prints every replacement applied)
```

On Windows:
- Use the aliases `cmd-` or `conwaymd` instead of `cmd` to avoid summoning Command Prompt.
- **Beware not to run any `.cmd` files by accident; they might break your computer. God save!**


## Usage (scripting example)

Code:

```python
from conwaymd.core import cmd_to_html

cmd_content = '''
# Test
==
- This is a *near*-minimal test.
- Here be [__dragons__].
==
[__dragons__]: https://example.com/
'''

html_content = cmd_to_html(cmd_content, cmd_file_name='scripting-test.py')

print(html_content)
```

Output:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Title</title>
</head>
<body>
<h1>Test</h1>
<ul>
<li>
This is a <em>near</em>-minimal test.
</li>
<li>
Here be <a href="https://example.com/"><b>dragons</b></a>.
</li>
</ul>
</body>
</html>
```


## Features

- [Specify element attributes] (e.g. `id` and `class`)
- [Write arbitrary text outside code]
- [Use `<b>`, `<i>`, and `<cite>` elements], not just `<strong>` and `<em>`
- [Use `<div>` elements] without falling back to HTML
- [Define your own syntax] as you go

[Specify element attributes]:
  https://conwaymd.github.io/#cmd-attribute-specifications
[Write arbitrary text outside code]:
  https://conwaymd.github.io/#literals
[Use `<b>`, `<i>`, and `<cite>` elements]:
  https://conwaymd.github.io/#inline-semantics
[Use `<div>` elements]:
  https://conwaymd.github.io/#divisions
[Define your own syntax]:
  https://conwaymd.github.io/#replacement-rule-syntax
