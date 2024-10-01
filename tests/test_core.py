"""
# Conway-Markdown: test_core.py

Licensed under "MIT No Attribution" (MIT-0), see LICENSE.

Perform unit testing for `core.py`.
"""

import unittest

from conwaymd._version import __version__
from conwaymd.core import extract_rules_and_content, extract_separator_normalised_cmd_name
from conwaymd.core import cmd_to_html


class TestCore(unittest.TestCase):
    def test_extract_rules_and_content(self):
        self.assertEqual(extract_rules_and_content(''), (None, ''))
        self.assertEqual(extract_rules_and_content('abc'), (None, 'abc'))
        self.assertEqual(extract_rules_and_content('%%%abc'), (None, '%%%abc'))
        self.assertEqual(extract_rules_and_content('abc%%%'), (None, 'abc%%%'))
        self.assertEqual(extract_rules_and_content('%%%\nabc'), ('', 'abc'))
        self.assertEqual(extract_rules_and_content('X%%\nY'), (None, 'X%%\nY'))
        self.assertEqual(
            extract_rules_and_content('This be the preamble.\nEven two lines of preamble.\n%%%%%\nYea.\n'),
            ('This be the preamble.\nEven two lines of preamble.\n', 'Yea.\n'),
        )
        self.assertEqual(
            extract_rules_and_content('ABC\n%%%\n123\n%%%%%%%\nXYZ'),
            ('ABC\n', '123\n%%%%%%%\nXYZ'),
        )

    def test_extract_separator_normalised_cmd_name(self):
        self.assertEqual(extract_separator_normalised_cmd_name('path/to/cmd_name.cmd'), 'path/to/cmd_name')
        self.assertEqual(extract_separator_normalised_cmd_name(r'path\to\cmd_name.cmd'), 'path/to/cmd_name')

    def test_cmd_to_html(self):
        self.assertEqual(
            cmd_to_html(cmd='', cmd_file_name='test_core.py', verbose_mode_enabled=False),
            '''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Title</title>
</head>
<body>
</body>
</html>
'''
        )

        self.assertEqual(
            cmd_to_html(
                cmd=r'''# Da Rules

OrdinaryDictionaryReplacement: #.boilerplate-properties-override
- queue_position: BEFORE #boilerplate-properties
* %lang --> en-AU
* %title --> "This be a __test__ "
* %styles -->
    #good {
      font-family: sans-serif;
    }
    #bad {
      font-family: serif;
    }

FixedDelimitersReplacement: #.comment-breaker
- queue_position: BEFORE #comments
- syntax_type: INLINE
- allowed_flags:
    u=KEEP_HTML_UNESCAPED
- opening_delimiter: <|
- attribute_specifications: EMPTY
- content_replacements:
    #escape-html
    #trim-whitespace
    #placeholder-protect
- closing_delimiter: |>

OrdinaryDictionaryReplacement: #.test-apply-mode-sequential
- queue_position: BEFORE #placeholder-unprotect
- apply_mode: SEQUENTIAL
* @1 --> @2
* @2 --> @3
* @3 --> @4
* @4 --> @5

OrdinaryDictionaryReplacement: #.test-apply-mode-simultaneous
- queue_position: BEFORE #placeholder-unprotect
- apply_mode: SIMULTANEOUS
* !1 --> !2
* !2 --> !3
* !3 --> !4
* !4 --> !5

%%%

# `test_cmd_to_html`

Sequential `OrdinaryDictionaryReplacement` result: @1, @2, @3, @4
Simultaneous `OrdinaryDictionaryReplacement` result: !1, !2, !3, !4
``{title=&<>"} Attribute specification escape test. ``
``{title='"'} Attribute specification double-quote escape test. ``
``{title="`?` <`` <`!`> ``>"}
  Attribute specification prevail test.
``

## `#placeholder-markers`

If implemented properly, the following shall confound not:
  `'\uF8FF\uE069\uE420\uE000\uF8FE\uE064\uF8FF'`: 

## `#literals`

BEFORE{ <`` Literal & < > ``> }AFTER
    <```
      No indent,
          yet four more spaces hence?
    ```>
   u<```` Flag `u`: unescaped HTML, <b>&amp; for ampersand!</b> ````>
   i<```
          Flag `i`: whitespace stripped on this line,
      but indent preserved on lines thereafter.
    ```>
   uw<````````
      Flag `w`: whitespace trimmed on all lines,
        even trailing whitespace,  
          and even whitespace before a break element:        <br>
    ````````>

## `#display-code`

  ```
    for (int index = 0; index < count; index++)
    {
      // etc. etc.
    }
  ```
  ````{#display-code-1 .class-2 l=en lang=en-AU .class-3}
    :(
    u<``<strong>LITERALS PREVAIL OVER DISPLAY CODE</strong>``>
        <```<``(unless restrained by an outer literal)``>```>
  ````
  i```
    Retained indentation:
      a lot.
   ```
  Empty display code:
  ``
  ``

## `#comment-breaker` (custom)

<| <## Sundered |> be <| this. ##> |>
u<| <strong>Unescaped!</strong> |>

## `#comments`

`Code prevails not <## over comments ##>.`
`Literals may aid code to prevail <`<# over comments #>`>`
Comments can remove code. <# `Like so.` #>

## `#divisions`

||||{.top-level}
  Parent.
  ||{.elder}
  Child 1.
  ||
  ||{.younger}
  Child 2.
  ||
||||

## `#blockquotes`

""""{.four}
"""{.three}
""{.two}
||
"One is not a blockquote"
||
""
"""
""""

## `#unordered-lists`
===={.four}
-
  ==={.three}
  - Dash.
  + Plus.
  * Asterisk.
  1. Not number.
    =={.two}
    - Yes.
    ==
  ===
- Hello!
====
Empty list:
======
======
Empty items, indented source:
  ==
  -
  -
  -
  ==

## `#ordered-lists`
++++
0. Yes.
00. Yep.
000000000000000000000000000. Yeah.
- Nah.
======
- Try.
  +++
  123456789. Still 1.
  2. Indeed 2.
     ++{start=50}
     50. 50/50?
     ++
  +++
======
++++
                '''
                """
## `#tables`

''''
<caption>Why the hell would you have table inception?</caption>
|^
  //
    ; `starting_match`
    ; `tag_name`
|:
  //
    , `|^`
    , `thead`
  //
    , `|:`
    , `tbody`
  //
    , `|_`
    , `tfoot`
|_
  //
    ,{}
      ''{.nested-with-parts}
        |^
          //
            ; No
            ; Logic
        |:
          //
            ,{r2} A
            , 1
          //
            , 2
          //
            ,{c2}
      ''
    ,{style="background: yellow"}
      ''{.nested-without-parts}
        //
          ; Who
          , Me
        //
          ; What
          , Yes
        //
          ;{style="font-weight: bold"} When
          , Didn't Ask
      ''
''''
Empty:
''
''
Head:
''
|^
''
Body:
''
|:
''
Foot:
''
|_
''
Head-body:
''
|^
|:
''
Head-foot:
''
|^
|_
''
Body-foot:
''
|:
|_
''
Header-after-data (seriously, why would you have this?):
'''
//
  , Data
  ; Header
  ; Header2
//
  , Data
  ; Header
  , Data2
'''
                """
                r'''
## `#headings`

### Level 3
#### Level 4
##### Level 5
###### Level 6

###
### Non-empty
### Insufficient closing hashes #
### Excessive closing hashes #######
###{}
###{} Non-empty
###{.class-1 title="This be fancy"} Fancy
### Trailing whitespace     	
### Trailing whitespace after hashes #  	

### Below be
  continuation
  lines

  ### And this also
    hath a continuation

### But this
hath insufficient indentation

###
  Starter line may be empty

#missing-whitespace
####### Excessive opening hashes

## `#paragraphs`

--------{.eight}
This be a paragraph.
--
NOTE: nested paragraphs are illegal.
--
--------
--{.two}
This be another paragraph.
--
||
----
A paragraph cannot contain a <div>block</div>.
----
||

## `#inline-code`

This be `inline code`.
u``{.classy} Whitespace stripped, and <b>unescaped</b>. ``
Even ```inline with ``backticks within`` ```.

Inline code may not contain anchored block tags.
(1) `This code
  <p>will not work`</p>.
(2)
--
Neither will `this
--
code`.
||
(3) But if the block tag be not anchored,
then it `<p>will work</p>`.
||

## `#cmd-properties`

CMD version is <code>v%cmd-version</code>.
CMD name is <code>%cmd-name</code>.
CMD basename is <code>%cmd-basename</code>.
Clean URL is <code>%clean-url</code>.

## `#backslash-escapes`

\\ \" \# \& \' \( \) \* \< \> \[ \] \_ \{ \| \}
\\\3 \\\\4 \\\\\5 \\\\\\6
[space]\ [space]
[tab]\t[tab]

## `#backslash-continuations`

This be \
    continuation.
This be not \\
    continuation, for the backslash is escaped.

Continuation \
without indent

## `#reference-definitions`

[good]: https://example.com
[good double]: https://example.com "Yes"
[good angle-bracketed single]: <https://example.com> 'Yes'

  [good continued]:
    https://example.com
    "Yes"

[some good]: https://example.com
  [more good]: https://example.com

  [good except title]:
    https://example.com
  "No"

  [bad]:
https://example.com

[missing uri]:
  [indented]: https://example.com

## `#specified-images`

![](decoration/image)
![]{-alt}("omitting alt is bad")
![Alt text.]()
![Alt text.](/src/only)
![Alt text.]("title only")
![
  Spacious alt.
](
  <spacious/src>
  'spacious title'
)
![alt]{alt=A src=S title=T}(src "title")

""
  ![Images/links cannot
""
--
  span](across/blocks)
--

## `#referenced-images`

[label]{.test}: file.svg "title"
[Hooray!]{.test2}: yay.png

![Alt text.][label]
![ Space & case test   ][  LaBEl  ]
![Hooray!]{class="no-label"}
![Class dismissed.]{-class .dismissed}[label]

![Untouched][Nonexistent label]


""
  ![Images/links cannot
""
--
  span across blocks][label]
--
(but note that the trailing `[label]` will be consumed by itself).

## `#explicit-links`

<https://example.com>
b<https://example.com>
s<https://example.com>
bs<https://example.com>

bs<mailto:mail@example.com>

s<{href='https://evil.com'}https://example.com>

## `#specified-links`

[](empty/content)
[Empty href](<>)
[No href]{-href}()
[Text]("title only")
[
  Spacious text.
](
  <spacious/href>
  'spacious title'
)
[Link]{href=H title=T}(href "title")

[![alt](src "title")](href 'title2')

In brackets href: ([text](href))
In brackets title: ([text]("title only"))
In brackets both: ([text](href "title"))

## `#referenced-links`

[label2]{.test}: /file "title"
[Rejoice]{.test2}: yay.html

[Content.][label2]
[ Space & case test   ][  LabEL2  ]
[Rejoice]{class="no-label"}
[Class dismissed.]{-class .dismissed}[label2]

[Untouched][Nonexistent label]

## `#inline-semantics`

11 *em*
22 **strong**
33 ***em(strong)***
44 ****strong(strong)****
55 *****em(strong(strong))*****
123 *em **em(strong)***
213 **strong *strong(em)***
312 ***strong(em)* strong**
321 ***em(strong)** em*
1221 *em **em(strong)** em*
2112 **strong *strong(em)* strong**

___foo___ vs __|_bar___

_i_ __b__
*em* **strong**
''cite''
""q""

'not enough single-quotes for cite'
"not enough double-quotes for q"

"""1+"""
""""2""""
"""""2+"""""
""""""3""""""

----
No __spanning
----
----
across block elements__.
----
Yes __spanning
across lines__.
                ''',
                cmd_file_name='test_core.py',
                verbose_mode_enabled=False,
            ),
            r'''<!DOCTYPE html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>This be a __test__ </title>
<style>
#good {
font-family: sans-serif;
}
#bad {
font-family: serif;
}
</style>
</head>
<body>
<h1><code>test_cmd_to_html</code></h1>
Sequential <code>OrdinaryDictionaryReplacement</code> result: @5, @5, @5, @5
Simultaneous <code>OrdinaryDictionaryReplacement</code> result: !2, !3, !4, !5
<code title="&amp;&lt;&gt;&quot;">Attribute specification escape test.</code>
<code title="&quot;">Attribute specification double-quote escape test.</code>
<pre title="`?` &lt;`!`&gt;"><code>Attribute specification prevail test.
</code></pre>
<h2><code>#placeholder-markers</code></h2>
If implemented properly, the following shall confound not:
<code>'\uF8FF\uE069\uE420\uE000\uF8FE\uE064\uF8FF'</code>: 
<h2><code>#literals</code></h2>
BEFORE{ Literal &amp; &lt; &gt; }AFTER
No indent,
    yet four more spaces hence?
Flag `u`: unescaped HTML, <b>&amp; for ampersand!</b>
Flag `i`: whitespace stripped on this line,
      but indent preserved on lines thereafter.
Flag `w`: whitespace trimmed on all lines,
even trailing whitespace,
and even whitespace before a break element:<br>
<h2><code>#display-code</code></h2>
<pre><code>for (int index = 0; index &lt; count; index++)
{
  // etc. etc.
}
</code></pre>
<pre id="display-code-1" class="class-2 class-3" lang="en-AU"><code>:(
<strong>LITERALS PREVAIL OVER DISPLAY CODE</strong>
    &lt;``(unless restrained by an outer literal)``&gt;
</code></pre>
<pre><code>    Retained indentation:
      a lot.
</code></pre>
Empty display code:
<pre><code></code></pre>
<h2><code>#comment-breaker</code> (custom)</h2>
&lt;## Sundered be this. ##&gt;
<strong>Unescaped!</strong>
<h2><code>#comments</code></h2>
<code>Code prevails not.</code>
<code>Literals may aid code to prevail &lt;# over comments #&gt;</code>
Comments can remove code.
<h2><code>#divisions</code></h2>
<div class="top-level">
Parent.
<div class="elder">
Child 1.
</div>
<div class="younger">
Child 2.
</div>
</div>
<h2><code>#blockquotes</code></h2>
<blockquote class="four">
<blockquote class="three">
<blockquote class="two">
<div>
"One is not a blockquote"
</div>
</blockquote>
</blockquote>
</blockquote>
<h2><code>#unordered-lists</code></h2>
<ul class="four">
<li>
<ul class="three">
<li>
Dash.
</li>
<li>
Plus.
</li>
<li>
Asterisk.
1. Not number.
<ul class="two">
<li>
Yes.
</li>
</ul>
</li>
</ul>
</li>
<li>
Hello!
</li>
</ul>
Empty list:
<ul>
</ul>
Empty items, indented source:
<ul>
<li>
</li>
<li>
</li>
<li>
</li>
</ul>
<h2><code>#ordered-lists</code></h2>
<ol>
<li>
Yes.
</li>
<li>
Yep.
</li>
<li>
Yeah.
- Nah.
<ul>
<li>
Try.
<ol>
<li>
Still 1.
</li>
<li>
Indeed 2.
<ol start="50">
<li>
50/50?
</li>
</ol>
</li>
</ol>
</li>
</ul>
</li>
</ol>
<h2><code>#tables</code></h2>
<table>
<caption>Why the hell would you have table inception?</caption>
<thead>
<tr>
<th><code>starting_match</code></th>
<th><code>tag_name</code></th>
</tr>
</thead>
<tbody>
<tr>
<td><code>|^</code></td>
<td><code>thead</code></td>
</tr>
<tr>
<td><code>|:</code></td>
<td><code>tbody</code></td>
</tr>
<tr>
<td><code>|_</code></td>
<td><code>tfoot</code></td>
</tr>
</tbody>
<tfoot>
<tr>
<td><table class="nested-with-parts">
<thead>
<tr>
<th>No</th>
<th>Logic</th>
</tr>
</thead>
<tbody>
<tr>
<td rowspan="2">A</td>
<td>1</td>
</tr>
<tr>
<td>2</td>
</tr>
<tr>
<td colspan="2"></td>
</tr>
</tbody>
</table></td>
<td style="background: yellow"><table class="nested-without-parts">
<tr>
<th>Who</th>
<td>Me</td>
</tr>
<tr>
<th>What</th>
<td>Yes</td>
</tr>
<tr>
<th style="font-weight: bold">When</th>
<td>Didn't Ask</td>
</tr>
</table></td>
</tr>
</tfoot>
</table>
Empty:
<table>
</table>
Head:
<table>
<thead>
</thead>
</table>
Body:
<table>
<tbody>
</tbody>
</table>
Foot:
<table>
<tfoot>
</tfoot>
</table>
Head-body:
<table>
<thead>
</thead>
<tbody>
</tbody>
</table>
Head-foot:
<table>
<thead>
</thead>
<tfoot>
</tfoot>
</table>
Body-foot:
<table>
<tbody>
</tbody>
<tfoot>
</tfoot>
</table>
Header-after-data (seriously, why would you have this?):
<table>
<tr>
<td>Data</td>
<th>Header</th>
<th>Header2</th>
</tr>
<tr>
<td>Data</td>
<th>Header</th>
<td>Data2</td>
</tr>
</table>
<h2><code>#headings</code></h2>
<h3>Level 3</h3>
<h4>Level 4</h4>
<h5>Level 5</h5>
<h6>Level 6</h6>
<h3></h3>
<h3>Non-empty</h3>
<h3>Insufficient closing hashes</h3>
<h3>Excessive closing hashes</h3>
<h3></h3>
<h3>Non-empty</h3>
<h3 class="class-1" title="This be fancy">Fancy</h3>
<h3>Trailing whitespace</h3>
<h3>Trailing whitespace after hashes</h3>
<h3>Below be
continuation
lines</h3>
<h3>And this also
hath a continuation</h3>
<h3>But this</h3>
hath insufficient indentation
<h3>
Starter line may be empty</h3>
#missing-whitespace
####### Excessive opening hashes
<h2><code>#paragraphs</code></h2>
<p class="eight">
This be a paragraph.
--
NOTE: nested paragraphs are illegal.
--
</p>
<p class="two">
This be another paragraph.
</p>
<div>
----
A paragraph cannot contain a <div>block</div>.
----
</div>
<h2><code>#inline-code</code></h2>
This be <code>inline code</code>.
<code class="classy">Whitespace stripped, and <b>unescaped</b>.</code>
Even <code>inline with ``backticks within``</code>.
Inline code may not contain anchored block tags.
(1) `This code
<p>will not work`</p>.
(2)
<p>
Neither will `this
</p>
code`.
<div>
(3) But if the block tag be not anchored,
then it <code>&lt;p&gt;will work&lt;/p&gt;</code>.
</div>
<h2><code>#cmd-properties</code></h2>
'''
            f'CMD version is <code>v{__version__}</code>.'
            r'''
CMD name is <code>test_core.py</code>.
CMD basename is <code>test_core.py</code>.
Clean URL is <code>test_core.py</code>.
<h2><code>#backslash-escapes</code></h2>
\ " # &amp; ' ( ) * &lt; &gt; [ ] _ { | }
\\3 \\4 \\\5 \\\6
[space] [space]
[tab]	[tab]
<h2><code>#backslash-continuations</code></h2>
This be continuation.
This be not \
continuation, for the backslash is escaped.
Continuation without indent
<h2><code>#reference-definitions</code></h2>
"No"
[bad]:
https://example.com
[missing uri]:
<h2><code>#specified-images</code></h2>
<img alt="" src="decoration/image">
<img src="" title="omitting alt is bad">
<img alt="Alt text." src="">
<img alt="Alt text." src="/src/only">
<img alt="Alt text." src="" title="title only">
<img alt="Spacious alt." src="spacious/src" title="spacious title">
<img alt="A" src="S" title="T">
<blockquote>
![Images/links cannot
</blockquote>
<p>
span](across/blocks)
</p>
<h2><code>#referenced-images</code></h2>
<img alt="Alt text." src="file.svg" title="title" class="test">
<img alt="Space &amp; case test" src="file.svg" title="title" class="test">
<img alt="Hooray!" src="yay.png" class="test2 no-label">
<img alt="Class dismissed." src="file.svg" title="title" class="dismissed">
![Untouched][Nonexistent label]
<blockquote>
![Images/links cannot
</blockquote>
<p>
span across blocks]<a href="file.svg" title="title" class="test">label</a>
</p>
(but note that the trailing <code>[label]</code> will be consumed by itself).
<h2><code>#explicit-links</code></h2>
<a href="https://example.com">https://example.com</a>
&lt;<a href="https://example.com">https://example.com</a>&gt;
<a href="https://example.com">example.com</a>
&lt;<a href="https://example.com">example.com</a>&gt;
&lt;<a href="mailto:mail@example.com">mail@example.com</a>&gt;
<a href="https://evil.com">example.com</a>
<h2><code>#specified-links</code></h2>
<a href="empty/content"></a>
<a href="">Empty href</a>
<a>No href</a>
<a title="title only">Text</a>
<a href="spacious/href" title="spacious title">Spacious text.</a>
<a href="H" title="T">Link</a>
<a href="href" title="title2"><img alt="alt" src="src" title="title"></a>
In brackets href: (<a href="href">text</a>)
In brackets title: (<a title="title only">text</a>)
In brackets both: (<a href="href" title="title">text</a>)
<h2><code>#referenced-links</code></h2>
<a href="/file" title="title" class="test">Content.</a>
<a href="/file" title="title" class="test">Space &amp; case test</a>
<a href="yay.html" class="test2 no-label">Rejoice</a>
<a href="/file" title="title" class="dismissed">Class dismissed.</a>
[Untouched][Nonexistent label]
<h2><code>#inline-semantics</code></h2>
11 <em>em</em>
22 <strong>strong</strong>
33 <em><strong>em(strong)</strong></em>
44 <strong><strong>strong(strong)</strong></strong>
55 <em><strong><strong>em(strong(strong))</strong></strong></em>
123 <em>em <strong>em(strong)</strong></em>
213 <strong>strong <em>strong(em)</em></strong>
312 <strong><em>strong(em)</em> strong</strong>
321 <em><strong>em(strong)</strong> em</em>
1221 <em>em <strong>em(strong)</strong> em</em>
2112 <strong>strong <em>strong(em)</em> strong</strong>
<i><b>foo</b></i> vs <b><i>bar</i></b>
<i>i</i> <b>b</b>
<em>em</em> <strong>strong</strong>
<cite>cite</cite>
<q>q</q>
'not enough single-quotes for cite'
"not enough double-quotes for q"
"<q>1+</q>"
<q><q>2</q></q>
"<q><q>2+</q></q>"
<q><q><q>3</q></q></q>
<p>
No __spanning
</p>
<p>
across block elements__.
</p>
Yes <b>spanning
across lines</b>.
</body>
</html>
'''
            '',
        )

        self.assertEqual(
            cmd_to_html(
                cmd=r'''
RegexDictionaryReplacement: #.delete-everything
- queue_position: AFTER #placeholder-unprotect
* [\s\S]* -->

%%%

The quick brown fox jumps over the lazy dog.
Everything is everything, and everything is dumb.
'''
                ,
                cmd_file_name='test_core.py',
            ),
            '',
        )


if __name__ == '__main__':
    unittest.main()
