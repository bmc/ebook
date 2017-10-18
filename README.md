# ebook-template

## Overview

This repository is a template for a project that'll build an eBook (in
ePub, PDF and HTML form) from Markdown input files.

tl;dr: You write your book as a series of Markdown files, adhering to some
[file naming conventions](#book-source-file-names), and you run the `./build`
command (see [Building](#building)) to build your book.

There are sample files in this repository, so you can build a (completely
pointless and utterly useless) eBook right away.

## Getting Started

Start by downloading and unpacking the latest
[release](https://github.com/bmc/ebook-template/releases) of this repository.
(By downloading a release, instead of cloning the repository, you can more
easily create your own Git repository from the results.)

Then, install the required software and update the configuration files.

### Required Software

1. Install [pandoc](http://pandoc.org).
2. Install a TexLive distribution, to generate the PDF. 
    * On the Mac, use [MacTex](https://www.tug.org/mactex/mactex-download.html),
      and ensure that `/Library/TeX/texbin` is in your path.
    * On Ubuntu/Debian, install `texlive`, `texlive-latex-recommended` and
      `texlive-latex-extras`.
3. Install a Python distribution, version 3.6 or better.
4. Install the required Python packages: `pip install -r requirements.txt`


### Initial Configuration

1. Create a cover image, as a PNG. Use a dummy image, if you haven't
   settled on a cover yet.
2. Edit `metadata.py`, and fill in the relevant pieces. The build script
   uses the information in this file to create some of the content for your
   book.
3. Edit the `copyright-template.md` file. You can leave `@YEAR@` and
   `@OWNER@` alone; the Rakefile replaces those with `COPYRIGHT_OWNER`
   and `COPYRIGHT_YEAR` (defined in `metadata.py`), respectively.
   See [Markup Notes](#markup-notes) for details on extensions to normal
   Markdown.


## Markup Notes

Write your book in Markdown, as interpreted by Pandoc. The following Pandoc
extensions are enabled. See the
[Pandoc User's Guide](http://pandoc.org/MANUAL.html) for full details.

* `line_blocks`
* `escaped_line_breaks`

### Additional Markup

The tooling has uses a [Pandoc filter](https://github.com/jgm/pandocfilters)
(in `pandoc-filter.py`) to enrich the Markdown slightly:

1. Level 1 headings denote new chapters and force a new page.
2. If you want to force a new page without starting a new chapter, just
   include a paragraph containing only the line `%newpage%`. The 
   _entire paragraph_ is replaced with a new page directive (except in HTML),
   so don't put any extra content in this paragraph. See
   `copyright-template.md` for an example.
3. A paragraph containing just the line `+++` is replaced by a centered line
   containing "• • •". This is a useful separator.
4. A paragraph that starts with `{<}` followed by at least one space is
   left-justified. See `copyright-template.md` for an example.
5. A paragraph that starts with `{>}` followed by at least one space is
   right-justified.
6. A paragraph that starts with `{|}` followed by at least one space is
   centered.

## Book Source File Names

The tooling expects your book's Markdown sources to adhere to the
following conventions:

* All files must have the extension `.md`.

* If you create a file called `dedication.md`, it'll be placed right after the
  copyright page in the generated output. See `dedication.md` for an example.
  If you don't want a dedication, simply delete the provided `dedication.md`.

* If the book has a prologue, put it in file `prologue.md`. It'll appear
  before the first chapter. If you don't want a prologue, simply delete the
  provided `prologue.md`.
  
* Keep each chapter in a separate file. (This is easier for editing, source
  control, etc.) Name the files `chapter-NN.md`. For instance,
  `chapter-01.md`, `chapter-02.md`, etc. The chapter files are sorted
  lexically, so the leading zeros are necessary if you have more than 9
  chapters. If you have more than 100 chapters (_seriously?_), just add
  another leading zero (e.g., `chapter-001.md`). If you _must_ put the entire
  content in one file, the file's name must start with `chapter-` and end in
  `.md`.
  
* If the book has an epilogue, put it in file `epilogue.md`. It'll follow the
  last chapter. If you don't want an epilogue, simply delete the provided
  `epilogue.md`.
  
* If you create a file called `acknowledgments.md`, it'll be placed after the
  epilogue. If you don't want an acknowledgements chapter, simply delete the
  provided `acknowledgments.md`.

## Building

Once you've prepared everything (see below), you can rebuild the book
by running the command:

```
./build
```

By default, it builds the ePub version (`book.epub`), a PDF version
(`book.pdf`), an HTML version (`book.html`) and a Microsoft Word version
(`book.docx`).

Pandoc can't generate books in Kindle format, but the Word version can serve
as a decent starting point for creating a Kindle version, via
[Kindle Create](https://kdp.amazon.com/en_US/help/topic/G202131100).

`./build` is a Python script using the Python [doit](http://pydoit.org/)
build tool. You should not need to edit it; editing `metadata.py` is
sufficient to specify the information about your book.

### Cleaning up generated files

To clean up the built targets:

```
./build clean
```

To clean _everything_ out (exception `doit-db.json`, which won't go away):

```
./build clobber
```
