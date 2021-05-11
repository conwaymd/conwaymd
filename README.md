# conway-markdown

Conway's fence-style Markdown (CMD), implemented in Python 3.6+.

Licensed under "MIT No Attribution" (MIT-0), see [LICENSE](LICENSE).

For a detailed description of the syntax,
see the [GitHub pages documentation][cmd-docs] ([repository][cmd-docs-repo]).

## Installation

Since this is just a crappy, single-file regex converter,
there is no plan on turning it into a proper Python package any time soon.
In the meantime:

````bash
$ cd some-directory/
$ git clone https://github.com/conway-markdown/conway-markdown.git
````

* If you are using Linux or Mac,
  make an alias for `some-directory/conway-markdown/cmd.py` and invoke that.
* If you are using Windows,
  add `some-directory` to the `%PATH%` variable and invoke `cmd.py`.

## Usage

Convert a CMD file to HTML:

````bash
$ cmd.py [cmd_name[.[cmd]]]
````

Omit `[cmd_name[.[cmd]]]` to convert all CMD files,
except those listed in `.cmdignore`.

## Features

1. Set the [width][attributes] of [images]
2. Add [`id` and `class`][attributes] to elements
3. Write [arbitrary text] outside of code elements
   without using backslash escapes or HTML (ampersand) entities
4. [Include] content from another file (e.g.&nbsp;a template)
5. Use [`<b>`, `<i>`, and `<cite>` elements][semantics],
   not just `<strong>` and `<em>`
6. Use [`<div>` elements][blocks] without falling back to HTML
7. [Define your own syntax][regex] as you go.

[cmd-docs]: https://conway-markdown.github.io/
[cmd-docs-repo]: https://github.com/conway-markdown/conway-markdown.github.io

[images]: https://conway-markdown.github.io/#images
[attributes]: https://conway-markdown.github.io/#attribute-specifications
[arbitrary text]: https://conway-markdown.github.io/#cmd-literals
[include]: https://conway-markdown.github.io/#inclusions
[semantics]: https://conway-markdown.github.io/#inline-semantics
[blocks]: https://conway-markdown.github.io/#blocks
[regex]: https://conway-markdown.github.io/#regex-replacements
