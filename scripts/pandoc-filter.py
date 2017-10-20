#!/usr/bin/env python

# ---------------------------------------------------------------------------
# Copyright © 2017 Brian M. Clapper
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------------------------------------------------

"""
Pandoc filter to convert transform special sequences on a per-format basis.

See the README.md file for what's supported.

See http://scorreia.com/software/panflute/ and 
https://github.com/jgm/pandoc/wiki/Pandoc-Filters
"""

import sys
from panflute import *
import os
import re
from itertools import dropwhile, takewhile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib import *

LEFT_JUSTIFY = '{<}'
CENTER_JUSTIFY = '{-}'
RIGHT_JUSTIFY = '{>}'

AUTHOR_PAT = re.compile(r'^(.*)%author%(.*)$')
TITLE_PAT = re.compile(r'^(.*)%title%(.*)$')
SUBTITLE_PAT = re.compile(r'^(.*)%subtitle%(.*)$')
COPYRIGHT_OWNER_PAT = re.compile(r'^(.*)%copyright-owner%(.*)$')
COPYRIGHT_YEAR_PAT = re.compile(r'^(.*)%copyright-year%(.*)$')
PUBLISHER_PAT = re.compile(r'^(.*)%publisher%(.*)$')
LANGUAGE_PAT = re.compile(r'^(.*)%language%(.*)$')

# Patterns that are simple strings in the metadata.
SIMPLE_PATTERNS = (
    (TITLE_PAT, 'title'),
    (SUBTITLE_PAT, 'subtitle'),
    (COPYRIGHT_OWNER_PAT, 'copyright.owner'),
    (COPYRIGHT_YEAR_PAT, 'copyright.year'),
    (PUBLISHER_PAT, 'publisher'),
    (LANGUAGE_PAT, 'language')
)

class DataHolder:
    '''
    Allows for assign-and-test. See 
    http://code.activestate.com/recipes/66061-assign-and-test/
    '''
    def __init__(self, value=None):
        self.value = value

    def set(self, value):
        self.value = value
        return value

    def get(self):
        return self.value

if sys.version_info < (3,6):
    print("Must use Python 3.6 or better.")
    sys.exit(1)

def debug(msg):
    sys.stderr.write(msg + "\n")

def matches_text(elem, text):
    return isinstance(elem, Str) and elem.text == text

def matches_pattern(elem, regex):
    return regex.match(elem.text) if isinstance(elem, Str) else None

def paragraph_starts_with_child(elem, string):
    if not isinstance(elem, Para):
        return False

    # Skip any LineBreak elements at the beginning.
    stripped = list(dropwhile(lambda e: isinstance(e, LineBreak), elem.content))

    if len(stripped) == 0:
        return False

    if matches_text(stripped[0], string):
        return True

    return False

def paragraph_contains_child(elem, string):
    return (isinstance(elem, Para) and
            any(matches_text(x, string) for x in elem.content))

def is_epub(format):
    return format.startswith('epub')

def justify(elem, format, token, xhtml_class, latex_env, docx_style):
    def drop(child):
        return isinstance(child, LineBreak) or matches_text(child, token)

    leading_line_skips = list(takewhile(lambda e: isinstance(e, LineBreak),
                                        elem.content))
    children = list(dropwhile(drop, elem.content))

    if (format == 'html') or is_epub(format):
        return Div(Para(*leading_line_skips), Para(*children),
                   attributes={'class': xhtml_class})
    elif format == 'latex':
        # Leading line skips cause a problem in LaTeX, when combined with
        # these environments (at least, the way Pandoc generates the LaTeX).
        # Don't include them.
        new_children = (
            [RawInline(r'\begin{' + latex_env + '}', 'latex')] +
            children +
            [RawInline(r'\end{' + latex_env + '}', 'latex'),
             RawInline(r'\bigskip', 'latex')]
        )
        return Para(*new_children)

    elif format == 'docx':
        return Div(Para(*leading_line_skips), Para(*children),
                   attributes={'custom-style': docx_style})

    else:
        return Div(Para(*leading_line_skips), Para(*children))

def left_justify_paragraph(elem, format):
    # Note: The "left" class is defined in epub.css and html.css
    return justify(elem, format, LEFT_JUSTIFY, 'left', 'flushleft',
                   'JustifyLeft')

def center_paragraph(elem, format):
    # Note: The "center" class is defined in epub.css and html.css
    return justify(elem, format, CENTER_JUSTIFY, 'center', 'center',
                   'Centered')

def right_justify_paragraph(elem, format):
    # Note: The "right" class is defined in epub.css and html.css
    return justify(elem, format, RIGHT_JUSTIFY, 'right', 'flushright',
                   'JustifyRight')

def section_sep(elem, format):
    sep = "• • •"
    if (format == 'html') or is_epub(format):
        return RawBlock(f'<div class="sep">{sep}</div>')
    elif format == 'latex':
        return Para(*[RawInline(r'\bigskip', format),
                      RawInline(r'\begin{center}', format)] +
                     [Str(sep)] +
                     [RawInline(r'\end{center}', format),
                      RawInline(r'\bigskip', format)])
    elif format == 'docx':
        return center_paragraph(Para(Str(sep)), format)
    else:
        return elem

def check_for_simple_pattern(elem, doc):
    assert isinstance(elem, Str)
    
    for pat, meta_key in SIMPLE_PATTERNS:
        m = matches_pattern(elem, pat)
        if m:
            s = doc.get_metadata(meta_key, '')
            return Str(f"{m.group(1)}{s}{m.group(2)}")

    return elem

def newpage(format):
    if format == 'latex':
        return [RawBlock(r'\newpage', format)]
    elif is_epub(format):
        return [RawBlock(r'<p class="pagebreak"></p>')]
    elif format == 'docx':
        return [Div(Para(Str('')), attributes={'custom-style': 'NewPage'})]
    else:
        return []

def prepare(doc):
    # Validate the metadata
    validate_metadata(doc.get_metadata())

def transform(elem, doc):
    data = DataHolder()
    if isinstance(elem, Header) and elem.level == 1:
        new_elem = elem
        if len(elem.content) == 0:
            # Special case LaTeX and Word: Replace with new page.
            if doc.format in ['latex', 'docx']:
                new_elem = Div(*newpage(doc.format))
        else:
            # Force page break, if not ePub.
            if not is_epub(doc.format):
                new_elements = newpage(doc.format) + [elem]
                new_elem = Div(*new_elements)
        return new_elem

    elif paragraph_contains_child(elem, '%newpage%'):
        abort('%newpage% is no longer supported.')

    elif paragraph_starts_with_child(elem, LEFT_JUSTIFY):
        return left_justify_paragraph(elem, doc.format)

    elif paragraph_starts_with_child(elem, CENTER_JUSTIFY):
        return center_paragraph(elem, doc.format)

    elif paragraph_starts_with_child(elem, RIGHT_JUSTIFY):
        return right_justify_paragraph(elem, doc.format)

    elif paragraph_contains_child(elem, '+++'):
        return section_sep(elem, doc.format)

    elif data.set(matches_pattern(elem, AUTHOR_PAT)):
        authors = doc.get_metadata('author', [])
        m = data.get()
        author_str = ""
        for i, a in enumerate(authors):
            sep = ", " if i < (len(authors) - 1) else " and "
            if i > 0:
                author_str = f"{author_str}{sep}{a}"
            else:
                author_str = a

        return Str(f"{m.group(1)}{author_str}{m.group(2)}")

    elif isinstance(elem, Str):
        return check_for_simple_pattern(elem, doc)

    else:
        return elem

def main(doc=None):
    return run_filter(transform, prepare=prepare, doc=doc)

if __name__ == "__main__":
    main()
