**Version 0.4.0**

* Fixed table of contents generation with ePub. This task included (a)
  removing behavior in the Pandoc filter that short-circuited Pandoc's table
  of contents logic, and (b) adding some build code to rewrite the table of
  contents files to remove empty entries and entries that just pointed to
  title pages.
* Fixed center-, left- and right-justification logic in the filter to work if
  the paragraph is preceded by forced line breaks.
* Removed support for `%newpage%`. Just use an empty first-level header ("#")
  to force a new page; the empty header will be removed from the table of
  contents. The Pandoc filter will now abort if it sees `%newpage%`.
* ePub is now ePub v3, not ePub v2.
* Added build logic to allow overriding HTML and/or ePub styling by creating
  `book/html.css` and/or `book/epub.css`.
* Ensured that generated ePub passes
  [EpubCheck](https://github.com/IDPF/epubcheck) with no errors.
* Fixed ePub CSS file to be proper CSS.
* Removed stray styling in ePub CSS that was preventing the correct paragraph
  style.
* Corrected generation of ePub metadata so that a lack of a book identifier
  doesn't generate an empty `<dc:identifier>` element. Necessary to pass
  EpubCheck validation.
* Created a new sample cover image, at a higher resolution. Modified LaTeX
  logic to scale it down properly for PDF.
* Cleaned build file up a bit.

**Version 0.3.0**

* Added support for generating a bibiography (references) section, appendices,
  a foreward, a preface, and a glossary. All are optional.
* Reworked how the pandoc filter handles token substitution.
* Moved metadata to a Pandoc-style metadata file.
* Added more substitution tokens.
* Added `version` target to `build`.
* Added an upgrade script, to help with upgrading to new versions.
* Added code to insert inline cover image in HTML version of the book.

**Version 0.2.0**

* Reorganized files so the top directory isn't so cluttered.
* Enhanced HTML CSS file, based on the "GitHub Pandoc CSS" in
  [this gist](https://gist.github.com/Dashed/6714393).
* Changed HTML build process to inline the CSS, to make the HTML truly
  standalone.

**Version 0.1.1**

Miscellaneous cleanup of unused files, plus addition of this change log.

**Version 0.1.0**

Initial release.

