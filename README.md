# conway-markdown

Conway's fence-style markdown (CMD), implemented in Python 3.6+.

For a detailed description of the syntax,
see the [GitHub pages documentation][cmd-docs] ([repository][cmd-docs-repo]).

## Installation

Since this is just a crappy, single-file regex converter,
there is no plan on turning it into a proper Python package any time soon.
In the meantime:

````
$ cd some-directory/
$ git clone https://github.com/conway-markdown/conway-markdown.git
````

* If you are using Linux or Mac,
  make an alias for `some-directory/conway-markdown/cmd.py` and invoke that.
* If you are using Windows,
  add `some-directory` to the `%PATH%` variable and invoke `cmd.py`.

## Usage

Convert a CMD file to HTML:

````
$ cmd.py [cmd_name[.[cmd]]]
````

Omit `[cmd_name[.[cmd]]]` to convert all CMD files,
except those listed in `.cmdignore`.

[cmd-docs]: https://conway-markdown.github.io/
[cmd-docs-repo]: https://github.com/conway-markdown/conway-markdown.github.io
