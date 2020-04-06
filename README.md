# conway-markdown

Conway's fence-style markdown (CMD), implemented in [Python][cmd.py].

See also: [GitHub pages documentation][cmd-docs]

## Usage

Convert a CMD file to HTML:

````
$ python cmd.py [cmd_name[.[cmd]]]
````

Omit `[cmd_name[.[cmd]]]` to convert all CMD files,
except those listed in `.cmdignore`.

[cmd-docs]: https://conway-markdown.github.io/
[cmd.py]: cmd.py
