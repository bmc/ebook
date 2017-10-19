**Version 0.4.0**

* Fixed table of contents generation with ePub. 
* ePub is now ePub v3, not ePub v2.

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

