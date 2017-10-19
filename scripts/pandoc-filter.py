#!/usr/bin/env python

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
    if not type(elem) == Para:
        return False
    if len(elem.content) == 0:
        return False
    if matches_text(elem.content[0], string):
        return True
    return False

def paragraph_contains_child(elem, string):
    return (type(elem) == Para and
            any(matches_text(x, string) for x in elem.content))

def is_epub(format):
    return format.startswith('epub')

def justify(elem, format, token, xhtml_class, latex_env, docx_style):
    children = [e for e in elem.content if not matches_text(e, token)]
    if (format == 'html') or is_epub(format):
        return Div(Para(*children), attributes={'class': xhtml_class})
    elif format == 'latex':
        new_children = (
            [RawInline(r'\begin{' + latex_env + '}', 'latex')] +
            children +
            [RawInline(r'\end{' + latex_env + '}', 'latex'),
             RawInline(r'\bigskip', 'latex')]
        )
        return Para(*new_children)

    elif format == 'docx':
        return Div(Para(*children), attributes={'custom-style': docx_style})

    else:
        return Para(*children)

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

def newpage(format):
    if format == 'latex':
        return [RawBlock(r'\newpage', format)]
    elif is_epub(format):
        return [RawBlock(r'<div style="page-break-before:always"></div>')]
    elif format == 'docx':
        return [Div(Para(Str('')), attributes={'custom-style': 'NewPage'})]
    else:
        return []

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
    assert type(elem) == Str
    
    for pat, meta_key in SIMPLE_PATTERNS:
        m = matches_pattern(elem, pat)
        if m:
            s = doc.get_metadata(meta_key, '')
            return Str(f"{m.group(1)}{s}{m.group(2)}")

    return elem

def prepare(doc):
    # Validate the metadata
    validate_metadata(doc.get_metadata())

def transform(elem, doc):
    data = DataHolder()
    if type(elem) == Header and elem.level == 1:
        # Force page break, if not ePub.
        if is_epub(doc.format):
            return elem
        else:
            new_elements = newpage(doc.format) + [elem]
            return Div(*new_elements)

    elif paragraph_contains_child(elem, '%newpage%'):
        return Div(*newpage(doc.format))

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

    elif type(elem) == Str:
        return check_for_simple_pattern(elem, doc)

    else:
        return elem

def main(doc=None):
    return run_filter(transform, prepare=prepare, doc=doc)

if __name__ == "__main__":
    main()
