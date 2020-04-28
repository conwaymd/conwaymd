# conway-markdown

Conway's fence-style markdown (CMD), implemented in Python 3.6+ (see [cmd.py]).

See also: [GitHub pages documentation][cmd-docs] ([repository][cmd-docs-repo])

## Usage

Convert a CMD file to HTML:

````
$ cmd.py [cmd_name[.[cmd]]]
````

Omit `[cmd_name[.[cmd]]]` to convert all CMD files,
except those listed in `.cmdignore`.

### Optional arguments

* `-c`, `--clean-urls`
  
  Remove the `.html` extension from the property `%url`.

[cmd-docs]: https://conway-markdown.github.io/
[cmd-docs-repo]: https://github.com/conway-markdown/conway-markdown.github.io
[cmd.py]: cmd.py
