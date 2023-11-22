# ebook

**Note**: For the old `ebook-template` code, see the
[v0.8.0](https://github.com/bmc/ebook/tree/v0.8.0) tag.
*FYI: That code is no longer maintained.*

## Overview

This repository contains an opinionated tooling framework that allows you to
write an eBook (in ePub, PDF, Microsoft Word, and HTML formats) from [Markdown][]
input files.

Basically, you write your book as a series of Markdown files, adhering to some
[file naming conventions](#book-source-file-names), and you run the `ebook`
command (see [Building your book](#building-your-book)) to build your book in
one or more of the supported formats. `ebook` does some magic, and then it uses
[Pandoc][] to generate your book.

In addition to a simplified convention for laying out your book, `ebook`
supports extras, such as:

- [Enhanced Markdown](#enhanced-markdown) capabilities like YAML metadata,
  fenced code blocks, smart quote conversions, enhanced lists, examples,
  and other features.
- [Additional non-standard markup](#additional-non-standard-markup) to allow
  you to center-, left-, or right-justify paragraphs; create a three-bullet
  paragraph separator easily; and other goodies.
- Bibliographic references

There are sample files in this repository, in the `book` subdirectory,
so you can build a (completely pointless and utterly useless) eBook right
away. You can also use those sample files as templates for starting your
own book.

This tooling has been tested with [Pandoc][] versions 3.1.7.

If you're impatient, jump to [Getting Started](#getting-started).

## Warnings

This code is a work in progress. It generally does what it's supposed to do,
though I haven't finished building out a Docker version yet. (What's in the
`docker` folder is old, from the previous version of this code. It doesn't
work; it's only there so I can use it as a reference.)

Warnings aside, I am actively using this tooling to work on an eBook, which
is driving ongoing fixes and enhancements.

## Supported output formats

`ebook` will generate your book in the following formats:

### ePub

`book.epub`

ePub is the format used by Apple's iBooks and various free readers, including
[Calibre][].

### PDF

`book.pdf` is a single PDF document, generated from HTML via [Weasy Print][].

**Limitations:**

- There's no table of contents.

### HTML

`book.html` is a single-page HTML, styled in a pleasant format.

**Limitations:**

- There's no table of contents.
- There's no real notion of a "page" in HTML, so level 1 headings don't
  start on new pages.

### Microsoft Word

`book.docx` is a Microsoft Word version of your book. The
`customer-reference.docx` file in the `etc/files` directory is used
to style the document. This reference document is an augmented version of
the one shipped with Pandoc. You can get the Pandoc reference document by
running:

```shell
$ pandoc -o custom-reference.docx --print-default-data-file reference.docx
```

The one shipped with `ebook` adds support for left-, right- and center-justified
paragraphs, which you can create via the
[additional non-standard markup](#additional-non-standard-markup) added by
`ebook`.

**Limitations:**

- There's no table of contents. But it's straightforward enough to create
  your own in the generated Word document. In newer versions of Microsoft
  Word (e.g., the version you get with Office 365):
    - Insert a page break to create a new, blank page.
    - Select "References" from the menu bar.
    - Select "Table of Contents", and select your desired style.
- Paragraphs don't have their first lines indented. You can manually correct
  this in the document by putting your cursor within a paragraph and selecting
  **Format > Style** to style all similar paragraphs.
- Level 1 headings don't start on a new page. You can fix that throughout the
  entire document by putting your cursor within a level 1 heading and selecting
  **Format > Style**.
- The cover image may need to be scaled manually within Word.

## Unsupported formats

### Kindle (MOBI)

Pandoc can't generate books in Kindle format. However, there are several
options for generating Kindle content:

- Haul the Microsoft Word version into
  [Kindle Create](https://kdp.amazon.com/en_US/help/topic/G202131100)

- Use the free and open source [Calibre][] suite to convert the ePub format to
  Kindle format.

## Getting started

### Using Docker

A Docker image of this tool chain, with all appropriate dependencies,
is in the works. Stay tuned.

### Required software

You'll need to install a few tools on your local machine.

1. Install [pandoc](http://pandoc.org/installing.html).
2. Install a Python distribution, version 3.10 or better.
3. I recommend creating and activating a
   [Python virtual environment](https://virtualenv.pypa.io/en/stable/),
   to keep the installed version of Python 3 more or less pristine.

### Installation

Once you have your Python 3 environment set up (and activated, if you're
using a virtual environment), check out this repository and run the
`install.py` command. It will install an executable version of `ebook`
in `$HOME/bin`, and it will install its support files in `$HOME/etc/ebook`.
It will also attempt to install all necessary packages (except for Pandoc) in
the activated Python environment.

Note that you'll have to tell `ebook` where to find its `etc` directory.
You can either specify it on the command line, like so:

```shell
$ ebook -e $HOME/etc/ebook
```

You can also simply set an environment variable (preferably in your shell's
startup file):

```shell
export EBOOK_ETC=$HOME/etc/ebook
```

You don't have to be _in_ the repo directory to run the `install.py` program.

### Uninstalling

Simply run

```shell
$ python install.py -u
```

**NOTE**: Uninstalling does *not* remove the pip-installed third party Python
packages that were installed.

### Windows Support

**There is none**.

I don't do development or writing on Windows. I don't, and won't, test this
software on Windows. If you insist on trying to use this program on a Windows
system, _you are entirely on your own_. This is a hobby project for me, and I
have no desire to make my life more miserable by supporting it on Windows.

### Initial configuration

#### Create your cover image

In your `book` directory, create a cover image, as a PNG. If you haven't
settled on a cover image yet, you can use the dummy image that's already
there. The cover image is optional, but you really want one, especially if
you're generating an ePub. You can use the `book/cover.png` file as a
placeholder, until you settle on your own image.

#### Fill in the metadata

Use this repo's `book/metadata.yaml` as an example, and fill in the relevant
pieces for your book. Both Pandoc and `ebook` use this metadata.

**Note**: This file contains
[Pandoc YAML Metadata](http://pandoc.org/MANUAL.html#extension-yaml_metadata_block),
with some additional fields used by this build tooling.

The following elements require your consideration:

- `title` (**Required**): The book title.

- `subtitle` (**Optional**): Subtitle, if any.

- `author` (**Required**): A YAML list of authors. If there is only one author,
  use a single-element YAML list. For example:

```yaml
author:
- Joe Horrid
```

```yaml
author:
- Joe Horrid
- Frances Horrid
```

- `copyright` (**Required**): A block with two required fields, `owner` and
  `year`. See the existing sample `metadata.yaml` for an example. These
  values are substituted into the `copyright.md` file, if it is present.

- `publisher` (**Required**): The publisher of the book.

- `language` (**Required**): The language in which the book is written. The
  value can be a 2-letter [ISO 639-1](https://en.wikipedia.org/wiki/ISO_639)
  code, such as "en" or "fr". It can also be a 2-part string consisting
  of the ISO 639-1 language code and the 2-letter
  [ISO 3166](https://docs.oracle.com/cd/E13214_01/wli/docs92/xref/xqisocodes.html)
  country code, such as "en-US", "en-UK", "fr-CA", "fr-FR", etc.

- `genre` (**Required**): The book's genre. See
  <https://wiki.mobileread.com/wiki/Genre> for a list of genres.

#### Supply copyright information

Use the `book/copyright.md` file in this repo as an example, and fill in the
copyright information for your book. As the sample `copyright.md` file
demonstrates, you can use special tokens to substitute values directly out of
the metadata. You're not required to use these tokens, but they can make things
easier, since you won't have to specify the values in multiple places. The
tokens are:

- `%copyright-year%` is replaced with the copyright "year" value from
  the [metadata](#fill-in-the-metadata)
- `%copyright-owner%` is replaced with the copyright "owner" value from
   the [metadata](#fill-in-the-metadata)

In truth, those tokens are supported in _any_ of your Markdown source files,
though they make the most sense in the `copyright.md` file. See
[Substitution Patterns](#substitution-patterns) for more details.

The `{<}` token in the sample copyright file forces left justification, as
described in [Additional markup](#additional-markup).

Note that `copyright.md` is not required, but it is _highly_ recommended.

## Markup notes

### Enhanced Markdown

Your book will use Markdown, as interpreted by Pandoc. The following Pandoc
extensions are enabled. See the
[Pandoc User's Guide][] for full details.

- `line_blocks`: Use vertical bars to create lines that are formatted as is.
  See <http://pandoc.org/MANUAL.html#line-blocks> for details.

- `escaped_line_breaks`: A backslash followed by a newline is also a hard
  line break.
  See <http://pandoc.org/MANUAL.html#extension-escaped_line_breaks> for details.

- `yaml_metadata_block`: Allows metadata in the Markdown. See
  See <http://pandoc.org/MANUAL.html#extension-yaml_metadata_block> for details.

- `smart`: Interprets straight quotes as curly quotes, "---" as em-dashes,
  "--" as en-dashes, and "..." as ellipses. Nonbreaking spaces are inserted
  after certain abbreviations, such as "Mr.". See
  <http://pandoc.org/MANUAL.html#extension-smart> for details.

- `backtick_code_blocks`, `fenced_code_blocks` and `fenced_code_attributes`:
  Allows fenced code blocks, using backticks (GitHub Flavored Markdown-style)
  and tildes (`~~~`). You can also supply attributes (classes, for instance).
  See <http://pandoc.org/MANUAL.html#extension-fenced_code_blocks>,
  <http://pandoc.org/MANUAL.html#extension-fenced_code_attributes> and
  <http://pandoc.org/MANUAL.html#extension-backtick_code_blocks> for details.

- `startnum`, for more control over lists, as outlined in
  <https://pandoc.org/MANUAL.html#extension-startnum>

- `example_lists` for auto-numbered examples that can be referenced
  from elsewhere in your book.

- `grid_tables` for easy-to-read, nicely-rendered Markdown tables.

- `strikeout`, allowing you to strike a string out (i.e., put a line
  through it) by surround it with `~` characters (e.g., `~stricken~`)

Additional Pandoc Markdown extensions can be specified on the `ebook`
command line. Examples of useful extensions you might wish to enable on
the command line include `superscript`, `subscript`, and
`shortcut_reference_links`. They, and other Pandoc extensions, are disabled
by default, to avoid confusion.

### Additional non-standard markup

The build tool uses a [Pandoc filter](https://github.com/jgm/pandocfilters)
(in `scripts/pandoc-filter.py`) to enrich the Markdown slightly:

1. Level 1 headings denote new chapters and force a new page.
2. If you want to force a new page without starting a new chapter, just
   include an empty level-1 header (`#`). See `book/copyright-template.md`
   for an example.
3. A paragraph containing just the line `+++` is replaced by a centered line
   containing "• • •". This is a useful separator.
4. A paragraph that starts with `{<}` followed by at least one space is
   left-justified. See `book/copyright-template.md` for an example.
5. A paragraph that starts with `{>}` followed by at least one space is
   right-justified.
6. A paragraph that starts with `{-}` followed by at least one space is
   centered.

Note, too, that Pandoc automatically converts your quotation marks into
smart quotes, triple dots (`...`) into an ellipsis, and two dashes (`--`)
into an em-dash.

(The filter is written in Python, using the
[Panflute](http://scorreia.com/software/panflute/) package.)

### Substitution Patterns

`ebook` supports various substitution patterns for substitution metadata
into your book from the [metadata](#fill-in-the-metadata).

- `%author%` is replaced with the "author" value(s)
- `%title%` is replaced with the book title
- `%subtitle%` is replaced with the book subtitle
- `%copyright-year%` is replaced with the copyright "year" value
- `%copyright-owner%` is replaced with the copyright "owner" value
- `%publisher%` is replaced with the "publisher" value
- `%language%` is replaced with the language string

## Book source file names

`ebook` expects your book's Markdown sources to be in a single directory
with no subdirectories (the _book directory_). Images may be in the book
directory or in any subdirectories below the book directory.

You specify the book directory on the command line, as described later.

### Images

Use _relative_ paths for images, not absolute paths. Absolute paths will wreak
havoc on your HTML output, among other things, so they are explicitly
unsupported. `ebook` will abort if you use absolute image references. Also,
currently, URL image references are unsupported.

### Opinionated file names

`ebook` is opinionated about what you call your Markdown files. Each book
section (chapters, acknowledgements, etc.) is in its own file, and each file
must adhere to the following conventions:

- All book text files must have the extension `.md`.

- If you create a `copyright.md` file, it'll be placed at the beginning,
  after the title page.

- If you create a file called `dedication.md`, it'll be placed right after the
  copyright page in the generated output. See `dedication.md` for an example.
  If you don't want a dedication, simply delete the provided `dedication.md`.

- If your book has a foreward, just create file `foreward.md`, and it'll
  be inserted right after the dedication.

- If your book has a preface, just create file `preface.md`, and it'll
  be inserted right after the foreward.

- If the book has a prologue, put it in file `prologue.md`. It'll appear
  before the first chapter.

- Keep each chapter in a separate file. (This is easier for editing, source
  control, etc.) Name the files `chapter-NN.md`. For instance,
  `chapter-01.md`, `chapter-02.md`, etc. The chapter files are sorted
  lexically, so the leading zeros are necessary if you have more than 9
  chapters. If you have more than 100 chapters (_seriously?_), just add
  another leading zero (e.g., `chapter-001.md`). If you _must_ put the entire
  content in one file, the file's name must start with `chapter-` and end in
  `.md` (e.g., `chapter-all-of-them.md`, or even `chapter-s.md`).

- If the book has an epilogue, put it in file `epilogue.md`. It'll follow the
  last chapter.

- If you create a file called `acknowledgments.md`, it'll be placed after the
  epilogue.

- If you need one or more appendices, just create files that start with
  `appendix-` and end with `.md`. Note that the files are sorted lexically.

- If you plan to provide a glossary, create `glossary.md`.

- If you want to include an author biography, just create `author.md`.

- If you need a references (bibliography) section, create `references.yaml`,
  as described below. See the provided sample `references.yaml` as an example.

All other files in the book directory are ignored. One exception is images:
Images that are referenced in the Markdown are included in the result, though there is currently a limitation: With HTML, only images with inline references
(e.g., `![](path/to/image)`) will work. Other image references won't.

Thus, you can safely include a `README.md` in your book directory, without
having it show up in your book.

**NOTE**: There's currently no support for generating an index.

Use the sample book in this repo as an example or a template for your own
book.

### Summary of chapter/section ordering

- title page
- copyright (if present)
- dedication (if present)
- foreward (if present)
- preface (if present)
- prologue (if present)
- all chapters
- epilogue (if present)
- acknowledgments (if present)
- appendices (if present)
- glossary (if present)
- author (if present)
- references (if present)

This ordering is *fixed*. It cannot be changed, either via configuration
or the command line. As I noted, `ebook` is opinionated. This is its, and
my, idea of the proper ordering. A future enhancement may permit you to
define your own ordering (say, via a file in your book's source directory);
for now, though, that's not an option.

### Images

Image references to files are relative to your book directory. It's best to
keep all images in the same directory as your book.
It's best to stick with PNG images.

### Bibliographic references

If you're writing a book that needs a bibliography _and_ uses citations in
the text, there's a bit of extra work.

You'll need to create the bibliography YAML file,
`book/references.yaml`, suitably organized for `pandoc` to consume. The sample
`book/references.yaml` contains a single entry.

See also the [citations section][] in the Pandoc User's Guide.

**NOTE**: The presence of a `book/references.yaml` file triggers the `ebook`
to include a **References** chapter at the very end of the document, to which
`pandoc` will add any cited works. Your bibliography (`book/references.yaml`)
can contain as many references as you want; only the ones you actually cite in
your text will show up in the References section. If your text contains no
citations, the References section will be empty. `ebook` does _not_ check
to see whether you actually have any citations in your text.

An example of a citation is:

```
[See @WatsonCrick1953]
```

Again, see the [citations section][] of the [Pandoc User's Guide][] for
full details.

## Styling your book

Note that `$EBOOK_ETC` refers to the installed `ebook` `etc` directory,
as described above.

- ePub styling uses `$EBOOK_ETC/files/epub.css`
- HTML styling uses `$EBOOK_ETC/files/html.css`
- PDF styling uses `$EBOOK_ETC/files/html-pdf.css`

You can change the styling by providing your own version of those files
in the your book's source directory. That is:

- If `book/html.css` exists, it will be used instead of
  `$EBOOK_ETC/files/html.css`.
- If `book/epub.css` exists, it will be used instead of
  `$EBOOK_ETC/files/epub.css`.
- If `book/html-pdf.css` exists, it will be used instead of
  `$EBOOK_ETC/files/epub.css`.

## Building your book

Once you've prepared everything, as described above, you can rebuild the
book by running the command:

```shell
$ ebook /path/to/your/book/directory
```

or

```shell
$ ebook /path/to/your/book/directory all
```

### Building the sample book

If you want to build the sample book, just to see how things look, it's simple
enough. Assuming you've set `EBOOK_ETC` in your environment, as recommended,
run the following command from the top of this repo:

```shell
$ ebook book
```

The built artifacts will end up in `book/build`, by default.

### Other useful targets

Instead of specifying `all`, you can explicitly specify individual book type
targets:

- `ebook docx`: Build just the Microsoft Word version of the book.
- `ebook pdf`: Build just the PDF version of the book.
- `ebook epub`: Build just the ePub version of the book.
- `ebook html`: Build just the HTML version of the book.

You can combine targets:

```shell
$ ebook /path/to/your/book/directory docx pdf
```

### What version of `ebook` am I using?

```shell
$ ebook --version
```
### Cleaning up generated files

To clean up the built targets:

```shell
$ ebook /path/to/your/book/directory clean
```

### Command-line help

Run `ebook` with `--help` to get complete help on the tool.

## Copyright and License

This software is copyright © 2017-2023 Brian M. Clapper and is released under
the [GPL, version 3][], similar to the license the underlying [Pandoc][] software
uses. See the [LICENSE](LICENSE.md) for further details.

[GPL, version 3]: http://www.gnu.org/copyleft/gpl.html
[citations section]: http://pandoc.org/MANUAL.html#extension-citations
[Pandoc]: http://pandoc.org
[Pandoc User's Guide]: http://pandoc.org/MANUAL.html
[Calibre]: https://www.calibre-ebook.com/
[Weasy Print]: http://weasyprint.org
[Markdown]: https://commonmark.org/help/
