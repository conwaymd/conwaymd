# Changelog


## [Unreleased]


## [v4.1.1] URI greed (2022-05-23)

- Fixed specified links URI too greedy
- Added check for an active class declaration
  when processing attribute declarations
- Added check for an active class declaration
  when processing substitution declarations


## [v4.1.0] Apply simultaneously by default (2022-05-21)

- Made attribute `apply_mode` default to `SIMULTANEOUS`


## [v4.0.0] CMDv4 (2022-05-16)

**SEVERELY BREAKING CHANGE!**

Rewritten from scratch.
Much of the syntax is incompatible with legacy CMD (v3.1.0 or earlier).


## [v3.1.0] CMD name without directory (2021-07-20)

- Added derived property `%cmd-name-file`


## [v3.0.0] Relative inclusions (2021-07-19)

- [Breaking] Changed inclusions file path reckoning:
  - File names beginning with `/` are reckoned relative to the terminal
  - File names not beginning with `/` are reckoned relative to the CMD file
- Improved changelog source formatting
- Removed Added/Changed headings from changelog
- Added release summaries to changelog headings


## [v2.4.1] No angle brackets (2021-07-11)

- Disallowed angle brackets in direct-style URLs.
  
  ````cmd
  ====
  - <https://example.com>
  ====
  ````
  now returns
  ````html
  <ul>
  <li><a href="https://example.com">https://example.com</a>
  </li>
  </ul>
  ````
  rather than the broken
  ````html
  <ul>
  <a href="li&gt;&lt;https://example.com">li><https://example.com</a>
  </li>
  </ul>
  ````

- Fixed missing mention of omittable curly brackets
  in docstring for direct-style links.


## [v2.4.0] Direct-style links (2021-06-06)

- Added direct-style links (called 'autolinks' in CommonMark).


## [v2.3.0] Placeholder reuse (2021-05-13)

- Made placeholder storage reuse placeholders for duplicate markup.
  
  ````cmd
  [`text`]
  @[`text`] url @
  ````
  now returns
  ````html
  <a href="url"><code>text</code></a>
  ````
  whereas previously it would not produce a link
  because the two instances of `` `text` `` would be
  temporarily replaced with different placeholder strings.


## [v2.2.2] Standardised name (2021-05-11)

- Fixed license year out of date
- Improved README description
- Standardised name as 'Conway-Markdown' (hyphenated instead of possessive)


## [v2.2.1] Docstring fixes (2021-03-09)

- Fixed missing mentions of omittable curly brackets
  for empty attribute specifications
  among docstrings for inline-style images and links.


## [v2.2.0] Optional attributes (2021-03-09)

- Added optional attribute specification for inline-style images
- Added optional attribute specification for inline-style links

````cmd
![<ALT>]{<attribute specification>}(<src> <title>)
[<CONTENT>]{<attribute specification>}(<href> <title>)
````


## [v2.1.0] Full form attributes (2021-01-31)

- Added full form `<NAME>=<VALUE>` for attribute specifications.
- Added short form `h<HEIGHT>` for height attribute.


## [v2.0.1] List item processing (2021-01-01)

- Fixed list item processing by requiring attribute specification
  or whitespace after the list item delimiter.
  This ensures that something like
  
  ````cmd
  ====
  * text
    *em*
  ====
  ````
  doesn't get parsed as a 2-item list.


## [v2.0.0] Attribute omission (2020-12-07)

- Added special value `\-` for attribute omission.
- For link and image attributes,
  the empty-string escape `\/` now provides an empty attribute
  instead of omitting it.


## [v1.0.0] First stable (2020-09-02)

- Initial release.


[Unreleased]:
  https://github.com/conway-markdown/conway-markdown/compare/v4.1.1...HEAD
[v4.1.1]:
  https://github.com/conway-markdown/conway-markdown/compare/v4.1.0...v4.1.1
[v4.1.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v4.0.0...v4.1.0
[v4.0.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v3.1.0...v4.0.0
[v3.1.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v3.0.0...v3.1.0
[v3.0.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.4.1...v3.0.0
[v2.4.1]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.4.0...v2.4.1
[v2.4.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.3.0...v2.4.0
[v2.3.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.2.2...v2.3.0
[v2.2.2]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.2.1...v2.2.2
[v2.2.1]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.2.0...v2.2.1
[v2.2.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.1.0...v2.2.0
[v2.1.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.0.1...v2.1.0
[v2.0.1]:
  https://github.com/conway-markdown/conway-markdown/compare/v2.0.0...v2.0.1
[v2.0.0]:
  https://github.com/conway-markdown/conway-markdown/compare/v1.0.0...v2.0.0
[v1.0.0]:
  https://github.com/conway-markdown/conway-markdown/releases/tag/v1.0.0
