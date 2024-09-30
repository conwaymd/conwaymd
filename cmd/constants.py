"""
# Conway-Markdown: constants.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Constants.
"""

GENERIC_ERROR_EXIT_CODE = 1
COMMAND_LINE_ERROR_EXIT_CODE = 2
VERBOSE_MODE_DIVIDER_SYMBOL_COUNT = 48

CMD_REPLACEMENT_SYNTAX_HELP = '''\
In CMD replacement rule syntax, a line must be one of the following:
(1) whitespace-only;
(2) a comment (beginning with `#`);
(3) a rules inclusion (`< «included_file_name»`);
(4) a class declaration (`«ClassName»: #«id»`);
(5) the start of an attribute declaration (`- «name»: «value»`);
(6) the start of a substitution declaration (`* «pattern» --> «substitute»`);
(7) a continuation (beginning with whitespace).
- Note for (3): if «included_file_name» begins with a slash,
  it is parsed relative to the working directory;
  otherwise it is parsed relative to the current file.
- Note for (6): the number of hyphens in the delimiter `-->`
  may be arbitrarily increased should «pattern» contain
  a run of hyphens followed by a closing angle-bracket.
- Note for (7): continuations are only allowed for attribute declarations
  and for substitution declarations.
'''

STANDARD_RULES = \
r'''# STANDARD_RULES

PlaceholderMarkerReplacement: #placeholder-markers
- queue_position: ROOT

PlaceholderProtectionReplacement: #placeholder-protect

DeIndentationReplacement: #de-indent
- negative_flag: KEEP_INDENTED

OrdinaryDictionaryReplacement: #escape-html
- negative_flag: KEEP_HTML_UNESCAPED
* & --> &amp;
* < --> &lt;
* > --> &gt;

RegexDictionaryReplacement: #trim-whitespace
* \A [\s]* -->
* [\s]* \Z -->

RegexDictionaryReplacement: #reduce-whitespace
- positive_flag: REDUCE_WHITESPACE
* ^ [^\S\n]+ -->
* [^\S\n]+ $ -->
* [\s]+ (?= <br> ) -->
* [\n]+ --> \n

ExtensibleFenceReplacement: #literals
- queue_position: AFTER #placeholder-markers
- syntax_type: INLINE
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
    i=KEEP_INDENTED
    w=REDUCE_WHITESPACE
- prologue_delimiter: <
- extensible_delimiter: `
- content_replacements:
    #escape-html
    #de-indent
    #trim-whitespace
    #reduce-whitespace
    #placeholder-protect
- epilogue_delimiter: >

RegexDictionaryReplacement: #code-tag-wrap
* \A --> <code>
* \Z --> </code>

ExtensibleFenceReplacement: #display-code
- queue_position: AFTER #literals
- syntax_type: BLOCK
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
    i=KEEP_INDENTED
    w=REDUCE_WHITESPACE
- extensible_delimiter: ``
- attribute_specifications: EMPTY
- content_replacements:
    #escape-html
    #de-indent
    #reduce-whitespace
    #code-tag-wrap
    #placeholder-protect
- tag_name: pre

RegexDictionaryReplacement: #comments
- queue_position: AFTER #display-code
* [^\S\n]*
  [<]
    (?P<hashes> [#]+ )
      [\s\S]*?
    (?P=hashes)
  [>]
    -->

RegexDictionaryReplacement: #prepend-newline
* \A --> \n

ExtensibleFenceReplacement: #divisions
- queue_position: AFTER #comments
- syntax_type: BLOCK
- extensible_delimiter: ||
- attribute_specifications: EMPTY
- content_replacements:
    #divisions
    #prepend-newline
- tag_name: div

ExtensibleFenceReplacement: #blockquotes
- queue_position: AFTER #divisions
- syntax_type: BLOCK
- extensible_delimiter: ""
- attribute_specifications: EMPTY
- content_replacements:
    #blockquotes
    #prepend-newline
- tag_name: blockquote

PartitioningReplacement: #unordered-list-items
- starting_pattern: [-+*]
- attribute_specifications: EMPTY
- content_replacements:
    #prepend-newline
- ending_pattern: [-+*]
- tag_name: li

ExtensibleFenceReplacement: #unordered-lists
- queue_position: AFTER #blockquotes
- syntax_type: BLOCK
- extensible_delimiter: ==
- attribute_specifications: EMPTY
- content_replacements:
    #unordered-lists
    #unordered-list-items
    #prepend-newline
- tag_name: ul

PartitioningReplacement: #ordered-list-items
- starting_pattern: [0-9]+ [.]
- attribute_specifications: EMPTY
- content_replacements:
    #prepend-newline
- ending_pattern: [0-9]+ [.]
- tag_name: li

ExtensibleFenceReplacement: #ordered-lists
- queue_position: AFTER #unordered-lists
- syntax_type: BLOCK
- extensible_delimiter: ++
- attribute_specifications: EMPTY
- content_replacements:
    #ordered-lists
    #ordered-list-items
    #prepend-newline
- tag_name: ol

RegexDictionaryReplacement: #mark-table-headers-for-preceding-table-data
* \A --> ;{}
# Replaces `<th«attributes_sequence»>` with `;{}<th«attributes_sequence»>`,
# so that #table-data will know to stop before it.

PartitioningReplacement: #table-headers
- starting_pattern: [;]
- attribute_specifications: EMPTY
- content_replacements:
    #trim-whitespace
- ending_pattern: [;,]
- tag_name: th
- concluding_replacements:
    #mark-table-headers-for-preceding-table-data

PartitioningReplacement: #table-data
- starting_pattern: [,]
- attribute_specifications: EMPTY
- content_replacements:
    #trim-whitespace
- ending_pattern: [;,]
- tag_name: td

RegexDictionaryReplacement: #unmark-table-headers-for-preceding-table-data
* ^ [;] \{ \} <th (?P<bracket_or_placeholder_marker> [>\uF8FF] )
    -->
  <th\g<bracket_or_placeholder_marker>
# Replaces `;{}<th«attributes_sequence»>` with `<th«attributes_sequence»>`
# so that #mark-table-headers-for-preceding-table-data is undone.

PartitioningReplacement: #table-rows
- starting_pattern: [/]{2}
- attribute_specifications: EMPTY
- ending_pattern: [/]{2}
- content_replacements:
    #table-headers
    #table-data
    #unmark-table-headers-for-preceding-table-data
    #prepend-newline
- tag_name: tr

PartitioningReplacement: #table-head
- starting_pattern: [|][\^]
- attribute_specifications: EMPTY
- ending_pattern: [|][:_]
- content_replacements:
    #table-rows
    #prepend-newline
- tag_name: thead

PartitioningReplacement: #table-body
- starting_pattern: [|][:]
- attribute_specifications: EMPTY
- ending_pattern: [|][_]
- content_replacements:
    #table-rows
    #prepend-newline
- tag_name: tbody

PartitioningReplacement: #table-foot
- starting_pattern: [|][_]
- attribute_specifications: EMPTY
- content_replacements:
    #table-rows
    #prepend-newline
- tag_name: tfoot

ExtensibleFenceReplacement: #tables
- queue_position: AFTER #ordered-lists
- syntax_type: BLOCK
- extensible_delimiter: ''
- attribute_specifications: EMPTY
- content_replacements:
    #tables
    #table-head
    #table-body
    #table-foot
    #table-rows
    #prepend-newline
- tag_name: table

HeadingReplacement: #headings
- queue_position: AFTER #tables
- attribute_specifications: EMPTY

ExtensibleFenceReplacement: #paragraphs
- queue_position: AFTER #headings
- syntax_type: BLOCK
- extensible_delimiter: --
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS
- content_replacements:
    #prepend-newline
- tag_name: p

ExtensibleFenceReplacement: #inline-code
- queue_position: AFTER #paragraphs
- syntax_type: INLINE
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
    i=KEEP_INDENTED
    w=REDUCE_WHITESPACE
- extensible_delimiter: `
- attribute_specifications: EMPTY
- prohibited_content: ANCHORED_BLOCKS
- content_replacements:
    #escape-html
    #de-indent
    #trim-whitespace
    #reduce-whitespace
    #placeholder-protect
- tag_name: code

RegexDictionaryReplacement: #boilerplate
- queue_position: AFTER #inline-code
* \A -->
    <!DOCTYPE html>
    <html lang="%lang">
      <head>
        <meta charset="utf-8">
        %head-elements-before-viewport
        <meta name="viewport" content="%viewport-content">
        %head-elements-after-viewport
        <title>%title</title>
        <style>
          %styles
        </style>
      </head>
      <body>\n
* \Z -->
      </body>
    </html>\n

OrdinaryDictionaryReplacement: #boilerplate-properties
- queue_position: AFTER #boilerplate
* %lang --> en
* %head-elements-before-viewport -->
* %viewport-content --> width=device-width, initial-scale=1
* %head-elements-after-viewport -->
* %title --> Title
* %styles -->

OrdinaryDictionaryReplacement: #cmd-properties
- queue_position: AFTER #boilerplate-properties
* %cmd-version --> CMD_VERSION
* %cmd-name --> CMD_NAME
* %cmd-basename --> CMD_BASENAME
* %clean-url --> CLEAN_URL
- concluding_replacements:
    #placeholder-protect

RegexDictionaryReplacement: #boilerplate-protect
- queue_position: AFTER #cmd-properties
* <style>[\s]*?</style>[\s]* -->
* <style>[\s\S]*?</style> --> \g<0>
* <head>[\s\S]*?</head> --> \g<0>
- concluding_replacements:
    #reduce-whitespace
    #placeholder-protect

OrdinaryDictionaryReplacement: #backslash-escapes
- queue_position: AFTER #boilerplate-protect
* \\ --> \
* \" --> "
* \# --> #
* \& --> &amp;
* \' --> '
* \( --> (
* \) --> )
* \* --> *
* \< --> &lt;
* \> --> &gt;
* \[ --> [
* \] --> ]
* \_ --> _
* \{ --> {
* \| --> |
* \} --> }
* "\ " --> " "
* \t --> "	"
- concluding_replacements:
    #placeholder-protect

RegexDictionaryReplacement: #backslash-continuations
- queue_position: AFTER #backslash-escapes
* \\ \n [^\S\n]* -->

ReferenceDefinitionReplacement: #reference-definitions
- queue_position: AFTER #backslash-continuations
- attribute_specifications: EMPTY

SpecifiedImageReplacement: #specified-images
- queue_position: AFTER #reference-definitions
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS

ReferencedImageReplacement: #referenced-images
- queue_position: AFTER #specified-images
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS

RegexDictionaryReplacement: #suppress-scheme
- positive_flag: SUPPRESS_SCHEME
* \A [\S]+ [:] (?: [/]{2} )? -->

RegexDictionaryReplacement: #angle-bracket-wrap
- positive_flag: ANGLE_BRACKET_WRAP
* \A --> &lt;
* \Z --> &gt;
- concluding_replacements:
    #placeholder-protect

ExplicitLinkReplacement: #explicit-links
- queue_position: AFTER #referenced-images
- allowed_flags:
    b=ANGLE_BRACKET_WRAP
    s=SUPPRESS_SCHEME
- attribute_specifications: EMPTY
- content_replacements:
    #suppress-scheme
- concluding_replacements:
    #angle-bracket-wrap

SpecifiedLinkReplacement: #specified-links
- queue_position: AFTER #explicit-links
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS

ReferencedLinkReplacement: #referenced-links
- queue_position: AFTER #specified-links
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS

InlineAssortedDelimitersReplacement: #inline-semantics
- queue_position: AFTER #referenced-links
- delimiter_conversion:
    __=b
    _=i
    **=strong
    *=em
    ''=cite
    ""=q
- attribute_specifications: EMPTY
- prohibited_content: BLOCKS

RegexDictionaryReplacement: #escape-idle-html
- queue_position: AFTER #inline-semantics
* [&]
  (?!
    (?:
      [a-zA-Z]{1,31}
        |
      [#] (?: [0-9]{1,7} | [xX] [0-9a-fA-F]{1,6} )
    )
    [;]
  )
    --> &amp;
* [<] (?= [\s] ) --> &lt;

ReplacementSequence: #whitespace
- queue_position: AFTER #escape-idle-html
- replacements:
    #reduce-whitespace

PlaceholderUnprotectionReplacement: #placeholder-unprotect
- queue_position: AFTER #whitespace
'''
