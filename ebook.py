#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Build script. Uses doit: http://pydoit.org/
# ---------------------------------------------------------------------------
# Copyright © 2017-2019 Brian M. Clapper
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

import sys
import os
from glob import glob
from string import Template
import codecs
import logging
import click
from tempfile import TemporaryDirectory
from dataclasses import dataclass, fields
from pathlib import Path
from pprint import pprint
import yaml
from enum import Enum, auto as enum_auto
from typing import Optional, Sequence as Seq, Self

sys.path.insert(0, os.path.dirname(__file__))
from lib import *

if tuple(sys.version_info) < (3, 10):
    raise Exception(
        f"Python version is {sys.version}, but 3.10 or better is required."
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "0.8.0"

LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

BOOK_SRC_DIR = 'book'
TMP_DIR  = 'tmp'

BUILD_FILE = 'build'
BUILD_LIB  = 'lib/__init__.py'

# Generated files

OUTPUT_BASENAME            = 'book'

EPUB_METADATA              = os.path.join(TMP_DIR, 'epub-metadata.xml')
LATEX_COVER_PAGE           = os.path.join(TMP_DIR, 'latex-title.latex')

OUTPUT_HTML                = f'{OUTPUT_BASENAME}.html'
OUTPUT_PDF                 = f'{OUTPUT_BASENAME}.pdf'
OUTPUT_EPUB                = f'{OUTPUT_BASENAME}.epub'
OUTPUT_DOCX                = f'{OUTPUT_BASENAME}.docx'
OUTPUT_LATEX               = f'{OUTPUT_BASENAME}.latex'
OUTPUT_JSON                = f'{OUTPUT_BASENAME}.json'

COMBINED_METADATA          = os.path.join(TMP_DIR, 'metadata.yaml')
HTML_BODY_INCLUDE          = os.path.join(TMP_DIR, 'body_include.html')

# Input files

# HTML_HEAD_INCLUDE          = os.path.join(FILES_DIR, "head_include.html")
# HTML_BODY_INCLUDE_TEMPLATE = os.path.join(FILES_DIR, 'body_include.html')

# EPUB_METADATA_TEMPLATE     = os.path.join(FILES_DIR, 'epub-metadata.xml')

# LATEX_COVER_PAGE_TEMPLATE  = os.path.join(FILES_DIR, 'cover-page.latex')
# LATEX_METADATA_YAML        = os.path.join(FILES_DIR, 'latex-metadata.yaml')
# REFERENCES_YAML            = os.path.join(BOOK_SRC_DIR, 'references.yaml')
# REFERENCES                 = os.path.join(FILES_DIR, 'references.md')
# METADATA_YAML              = os.path.join(BOOK_SRC_DIR, 'metadata.yaml')

# metadata                   = load_metadata(METADATA_YAML)
# uses_references            = os.path.exists(REFERENCES_YAML)
# use_weasyprint             = metadata.get('use_weasyprint', False)

# COVER_IMAGE                = os.path.join(BOOK_SRC_DIR, 'cover.png')
# COVER_IMAGE_PDF            = os.path.join(BOOK_SRC_DIR, 'cover-pdf.png')
# CHAPTERS                   = sorted(glob(os.path.join(BOOK_SRC_DIR, 'chapter-*.md')))
# COPYRIGHT                  = os.path.join(BOOK_SRC_DIR, 'copyright.md')
# LATEX_HEADER               = os.path.join(FILES_DIR, 'header.latex')
# APPENDICES                 = glob(os.path.join(BOOK_SRC_DIR, 'appendix-*.md'))

# BOOK_FILE_LIST    = (
#     [COMBINED_METADATA, COPYRIGHT] +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'dedication.md')) +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'foreward.md')) +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'preface.md')) +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'prologue.md')) +
#     CHAPTERS +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'epilogue.md')) +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'acknowledgments.md')) +
#     APPENDICES +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'glossary.md')) +
#     maybe_file(os.path.join(BOOK_SRC_DIR, 'author.md')) +
#     ([REFERENCES] if uses_references else [])
# )

#PANDOC_FILTER      = Path('scripts', 'pandoc-filter.py')

#LOCAL_IMAGES       = find_local_images(BOOK_FILE_LIST)

#HTML_CSS           = file_or_default(os.path.join(BOOK_SRC_DIR, 'html.css'),
#                                     os.path.join(FILES_DIR, 'html.css'))
#EPUB_CSS           = file_or_default(os.path.join(BOOK_SRC_DIR, 'epub.css'),
#                                     os.path.join(FILES_DIR, 'epub.css'))
## When generating PDF from HTML via weasyprint.
#HTML_PDF_CSS       = file_or_default(os.path.join(BOOK_SRC_DIR, 'html-pdf.css'),
#                                     os.path.join(FILES_DIR, 'html-pdf.css'))
#LATEX_TEMPLATE     = os.path.join(FILES_DIR, 'latex.template')
#REF_DOCX           = os.path.join(FILES_DIR, 'custom-reference.docx')
#PLANTUML_FILTER    = os.path.join('scripts', 'plantuml-filter.py')
#
## Lists of dependencies, for ease of reference.
#BUILD_FILE_DEPS = [BUILD_FILE, BUILD_LIB]
#METADATA_DEPS = (
#    [METADATA_YAML, LATEX_METADATA_YAML] +
#    ([REFERENCES_YAML] if uses_references else [])
#)
#
#DEPS          = (BOOK_FILE_LIST + BUILD_FILE_DEPS + LOCAL_IMAGES +
#                 [PANDOC_FILTER, COMBINED_METADATA])
#EPUB_DEPS     = DEPS + [EPUB_METADATA, COVER_IMAGE, EPUB_CSS]
#HTML_DEPS     = DEPS + [HTML_CSS, HTML_BODY_INCLUDE]
#LATEX_DEPS    = DEPS + [LATEX_COVER_PAGE, LATEX_TEMPLATE,
#                        LATEX_HEADER, LATEX_METADATA_YAML]
#DOCX_DEPS     = DEPS + [REF_DOCX]
#HTML_PDF_DEPS = DEPS + [HTML_PDF_CSS, HTML_BODY_INCLUDE]

# +RTS and -RTS delimit Haskell runtime options. See
# http://www.haskell.org/ghc/docs/6.12.2/html/users_guide/runtime-control.html
#
# -Ksize sets the stack size. -K10m uses a 10 Mb stack, for instance. The
# default size is 8M.

#HASKELL_OPTS = '+RTS -K20m -RTS'
HASKELL_OPTS = ''

# Minimum Pandoc version, expressed as a (major, minor, patch) tuple
MIN_PANDOC_VERSION = (3, 1, 0)

PANDOC_EXTENSIONS = (
    "line_blocks",
    "escaped_line_breaks",
    "smart",
    "fenced_code_blocks",
    "fenced_code_attributes",
    "backtick_code_blocks",
    "yaml_metadata_block",
)

INPUT_FORMAT = f"markdown+{'+'.join(PANDOC_EXTENSIONS)}"

#COMMON_PANDOC_OPTS = (
#    f"-f {INPUT_FORMAT} {HASKELL_OPTS} -F {PANDOC_FILTER}" +
#    (" --citeproc" if uses_references else "") +
#    (" --standalone")
#)
#NON_LATEX_PANDOC_OPTS = f"{COMMON_PANDOC_OPTS} "
#LATEX_PANDOC_OPTS = (f"{COMMON_PANDOC_OPTS} --template={LATEX_TEMPLATE} " +
#                     f"-t latex -H {LATEX_HEADER} -B {LATEX_COVER_PAGE} " +
#                     "--toc")
#HTML_PANDOC_OPTS = (f'{NON_LATEX_PANDOC_OPTS} -t html -B {HTML_BODY_INCLUDE} ' +
#                    f'--css={HTML_CSS} ' +
#                    f'-H {HTML_HEAD_INCLUDE}')
#EPUB_PANDOC_OPTS = (f'{NON_LATEX_PANDOC_OPTS} -t epub --toc ' +
#                    f'--split-level=1 --css={EPUB_CSS} ' +
#                    f'--epub-metadata={EPUB_METADATA} ' +
#                    f'--epub-cover-image={COVER_IMAGE}')
#DOCX_PANDOC_OPTS = f'{NON_LATEX_PANDOC_OPTS} -t docx --reference-doc={REF_DOCX}'
#
#HTML_PDF_PANDOC_OPTS = (f'{NON_LATEX_PANDOC_OPTS} -t html ' +
#                        f'--css={HTML_PDF_CSS} --pdf-engine=weasyprint ' +
#                        f'-B {HTML_BODY_INCLUDE}')
#
DEFAULT_LATEX_METADATA = """
documentclass: article
"""

# ---------------------------------------------------------------------------
# Data types and classes
# ---------------------------------------------------------------------------

class VersionError(Exception):
    pass


class OutputType(Enum):
    HTML = enum_auto()
    LATEX = enum_auto()
    PDF = enum_auto()
    WORD = enum_auto()
    EPUB = enum_auto()


@dataclass(frozen=True)
class SourcePaths:
    """
    Make-style sources and dependencies, calculated from the supplied book
    directory.
    """
    metadata: Optional[Path]
    latex_metadata: Path
    author: Optional[Path]
    preface: Optional[Path]
    prologue: Optional[Path]
    epilogue: Optional[Path]
    dedication: Optional[Path]
    foreward: Optional[Path]
    afterward: Optional[Path]
    glossary: Optional[Path]
    copyright: Optional[Path]
    appendices: Seq[Path]
    acknowledgements: Optional[Path]
    cover_image: Optional[Path]
    cover_image_for_pdf: Optional[Path]
    references: Optional[Path]
    chapters: Seq[Path]
    html_css: Path
    html_pdf_css: Path
    epub_css: Path
    latex_template: Path

    @property
    def all_metadata(self: Self) -> Seq[Path]:
        return [f for f in (self.metadata, self.latex_metadata, self.references)
                if f is not None]

    @property
    def markdown_files(self: Self) -> Seq[Path]:
        # Get the list of fields from this data class and look for any that
        # are paths ending in ".md". This looks complicated, but it
        # automatically adjusts to new dataclass fields.
        def is_markdown_file(thing: Any) -> bool:
            return isinstance(thing, Path) and thing.name.endswith(".md")

        self_fields = fields(self)
        markdown_files = []
        for f in self_fields:
            field_value = getattr(self, f.name)
            if field_value is None:
                continue

            if is_markdown_file(field_value):
                markdown_files.append(field_value)
                continue

            if isinstance(field_value, list):
                for thing in field_value:
                    if is_markdown_file(thing):
                        markdown_files.append(thing)

        return sorted(markdown_files)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def configure_logging(s_level: str, path: Optional[str] = None) -> logging.Logger:
    """
    Configure the Python logging subsystem. The returned
    logger will log to standard output and, optionally,
    any log file specified.

    Parameters:

    s_level - the string name of the desired logging
              level (e.g., "INFO", "DEBUG")
    path    - optional path to which to log output

    Returns: the logger to use
    """
    import sys
    # See https://docs.python.org/3/howto/logging.html
    log_level = getattr(logging, s_level.upper(), None)

    formatter = logging.Formatter(
        '[%(asctime)s] (%(levelname)s) %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handlers = []
    handlers.append(logging.StreamHandler(stream=sys.stdout))
    if path is not None:
        handlers.append(logging.FileHandler(filename=path, mode='w'))

    logger = logging.getLogger('main')
    # Remove all existing handlers, in case this cell is rerun.
    for h in logger.handlers:
        logger.removeHandler(h)

    # Don't propagate to the root logger.
    logger.propagate = False
    logger.setLevel(log_level)

    # install new handlers
    for h in handlers:
        h.setLevel(log_level)
        h.setFormatter(formatter)
        logger.addHandler(h)

    logger.info(f'Logging configured, at log level {s_level}.')

    return logger

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

DOIT_DB = 'doit-db.json'

DEFAULT_TASKS = ['html', 'pdf', 'docx', 'epub']

DOIT_CONFIG = {
    'default_tasks': DEFAULT_TASKS,
    'backend': 'json',
    'dep_file': DOIT_DB
}

def task_version():
    '''
    Display the version of this tooling.
    '''
    def run(targets):
        msg(f"eBook generation tooling, version {VERSION}")

    return {
        'actions': [run]
    }

def task_all():
    '''
    Convenient way to generate all default book formats.
    '''
    return {
        'actions':  [_no_op],
        'task_dep': DEFAULT_TASKS
    }

def task_clobber():
    '''
    Convenient way to run: ./build clean -a
    '''
    def run(targets):
        sh('./build clean -a')
        rm_f(glob('*.bak'))
        rm_rf('__pycache__')
        rm_rf('lib/__pycache__')
        rm_rf(f'{BOOK_SRC_DIR}__pycache__')
        rm_rf('tmp')

    return {
        'actions': [run]
    }

def task_html(pandoc_path: str) -> Dict[str, Any]:
    '''
    Generate HTML output.
    '''
    def run(targets):
        with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST, divs=True) as files:
            files_str = ' '.join(files)
            sh(f"{pandoc_path} {HTML_PANDOC_OPTS} -o {targets[0]} {files_str} ")

    return {
        'actions': [run],
        'file_dep': HTML_DEPS,
        'targets': [OUTPUT_HTML],
        'clean':   True
    }

def task_html_body_include():
    '''
    Generate the HTML embedded cover image.
    '''
    def run(targets):
        import base64
        with target_dir_for(HTML_BODY_INCLUDE):
            with open(HTML_BODY_INCLUDE, 'w') as out:
                with open(COVER_IMAGE, 'rb') as img:
                    image_bytes = img.read()

                b64_bytes = base64.encodebytes(image_bytes)
                b64_str = ''.join(chr(b) for b in b64_bytes).replace('\n', '')
                with open(HTML_BODY_INCLUDE_TEMPLATE) as template:
                    data = {'base64_image': b64_str}
                    out.write(Template(template.read()).substitute(data))

    return {
        'actions':  [run],
        'file_dep': [COVER_IMAGE, HTML_BODY_INCLUDE_TEMPLATE] + BUILD_FILE_DEPS,
        'targets':  [HTML_BODY_INCLUDE],
        'clean':    True
    }


def task_pdf():
    '''
    Generate PDF output.
    '''
    def run(targets):
        with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST) as files:
            files_str = ' '.join(files)
            target = targets[0]
            sh(f'{PANDOC} {HTML_PDF_PANDOC_OPTS} -o {target} {files_str}')


    if use_weasyprint:
        return {
            'actions':  [run],
            'file_dep': HTML_PDF_DEPS,
            'targets':  [OUTPUT_PDF],
            'clean':    True,
        }
    else:
        return {
            'actions': [(_latex, [OUTPUT_PDF])],
            'file_dep': LATEX_DEPS,
            'targets': [OUTPUT_PDF],
            'clean':   True
        }

def task_latex():
    '''
    Generate LaTeX output (for debugging).
    '''
    return {
        'actions': [(_latex, [OUTPUT_LATEX])],
        'file_dep': LATEX_DEPS,
        'targets': [OUTPUT_LATEX],
        'clean':   True
    }

def task_json():
    '''
    Generate Pandoc AST JSON, pretty-printed (for debugging).
    '''
    def run(targets):
        with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST) as files:
            files_str = ' '.join(files)
            temp = '_ast.json'
            try:
                sh(f'{PANDOC} {NON_LATEX_PANDOC_OPTS} -o _ast.json -t json ' +
                   files_str)
                with open(temp, 'r') as f:
                    import json
                    js = json.load(f)
                    with open(targets[0], 'w') as out:
                        out.write(json.dumps(js, sort_keys=False, indent=2))
            finally:
                rm_f(temp, silent=True)


    return {
        'actions':  [run],
        'file_dep': HTML_DEPS,
        'targets':  [OUTPUT_JSON],
        'clean':    True
    }

def task_docx():
    '''
    Generate MS Word output.
    '''
    def run(targets):
        with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST) as files:
            files_str = ' '.join(files)
            sh(f"{PANDOC} {DOCX_PANDOC_OPTS} -o {targets[0]} {files_str}")

    return {
        'actions': [run],
        'file_dep': DOCX_DEPS,
        'targets': [OUTPUT_DOCX],
        'clean':   True
    }

def task_epub():
    '''
    Generate ePub output.
    '''

    def run(targets):
        markdown = [f for f in BOOK_FILE_LIST if f.endswith(".md")]
        yamls = [f for f in BOOK_FILE_LIST if f.endswith(".yaml")]
        with preprocess_markdown(TMP_DIR, markdown) as files:
            files_str = ' '.join(yamls + files)
            alert('Ignore any Pandoc warnings about "title" or "pagetitle".')
            sh(f'{PANDOC} {EPUB_PANDOC_OPTS} -o {targets[0]} {files_str}')
            fix_epub(epub=targets[0],
                     book_title=metadata['title'],
                     temp_dir=os.path.join(TMP_DIR, 'book-epub'))

    return {
        'actions': [run],
        'file_dep': EPUB_DEPS,
        'targets': [OUTPUT_EPUB],
        'clean':   True
    }

def task_latex_title():
    '''
    Generate LaTeX title file.
    '''
    # Note: The following requires a custom LaTeX template with
    # \usepackage{graphicx} in the preamble.
    def run(targets):
        with target_dir_for(LATEX_COVER_PAGE):
            with open(LATEX_COVER_PAGE_TEMPLATE) as template:
                with open(LATEX_COVER_PAGE, 'w') as out:
                    data = {'cover_image': COVER_IMAGE}
                    out.write(Template(template.read()).substitute(data))

    return {
        'actions':  [run],
        'file_dep': BUILD_FILE_DEPS + [LATEX_COVER_PAGE_TEMPLATE, COVER_IMAGE],
        'targets':  [LATEX_COVER_PAGE],
        'clean':    True
    }

def task_combined_metadata():
    '''
    Generate the consolidated metadata file.
    '''
    def run(targets):
        target = targets[0]
        with target_dir_for(target):
            with open(target, 'w') as out:
                for f in METADATA_DEPS:
                    if not os.path.exists(f):
                        continue

                    out.write('---\n')
                    with codecs.open(f, 'r', encoding='UTF-8') as input:
                        for line in input.readlines():
                            out.write(line)
                    out.write('...\n\n')

                # Special cases. Put these at the bottom. Pandoc will
                # ignore them if they're already specified (i.e., first one
                # wins, according to the Pandoc documentation).

                out.write('---\n')
                language = metadata.get('language', 'en-US')
                out.write('lang: {}\n'.format(language.split('-')[0]))
                out.write('...\n\n')

    return {
        'actions':  [run],
        'file_dep': BUILD_FILE_DEPS + METADATA_DEPS,
        'targets':  [COMBINED_METADATA],
        'clean':    True
    }

def task_epub_metadata():
    '''
    Generate the ePub metadata file.
    '''
    def run(targets):
        import io
        with open(targets[0], 'w') as out:
            with open(EPUB_METADATA_TEMPLATE, 'r') as input:
                template = ''.join(input.readlines())

            identifier = metadata.get('identifier', {}).get('text', '')
            scheme = metadata.get('identifier', {}).get('scheme', '')
            copyright = metadata['copyright']
            data = {
                'identifier':        identifier,
                'identifier_scheme': scheme,
                'copyright_owner':   copyright['owner'],
                'copyright_year':    copyright['year'],
                'publisher':         metadata['publisher'],
                'language':          metadata.get('language', 'en-US'),
                'genre':             metadata.get('genre', '')
            }
            sbuf = io.StringIO(Template(template).substitute(data))
            for line in sbuf.readlines():
                if not identifier and line.strip().startswith('<dc:identifier'):
                    continue
                out.write(line)

    return {
        'actions':  [run],
        'file_dep': ([EPUB_METADATA_TEMPLATE, COMBINED_METADATA] +
                     BUILD_FILE_DEPS),
        'targets':  [EPUB_METADATA],
        'clean':    True
    }

def task_combined():
    '''
    Generated one big combined Markdown file (for debugging).
    '''
    def run(targets):
        target = targets[0]
        msg(f"Generating {target}.")

        with target_dir_for(target):
            with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST) as files:
                with open(target, 'w') as out:
                    for f in files:
                        with open(f, 'r') as input:
                            copyfileobj(input, out)

    return {
        'actions':  [run],
        'file_dep': DEPS,
        'targets':  [os.path.join(TMP_DIR, 'temp.md')],
        'clean':    True
    }

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _pandoc_options(sources: SourcePaths, output_type: OutputType) -> str:
    common = (
        f"-f {INPUT_FORMAT} {HASKELL_OPTS} -F"
    )

def _combine_metadata(tempdir: str,
                      sources: SourcePaths,
                      logger: logging.Logger) -> Path:
    """
    Create the combined metadata YAML file and return its path.
    """

    # Load the primary metadata file, as we need to pull some things from it.
    metadata: Dict[str, str] = {}
    with open(sources.metadata, encoding="utf-8") as f:
        metadata = yaml.safe_load(f)

    combined_metadata_path = Path(tempdir, "metadata.yaml")
    with open(combined_metadata_path, "w", encoding="utf-8") as out:
        for p in sources.all_metadata:
            if p is None:
                continue
            if not p.exists():
                continue

            out.write('---\n')
            with open(p, 'r', encoding='utf-8') as f:
                for line in f.readlines():
                    out.write(line)
            out.write('...\n\n')

        # If no language was specified, add one.
        if metadata.get("language") is None:
            out.write("---\n")
            out.write("lang: en")
            out.write("...\n\n")

    return combined_metadata_path

def _latex(target):
    with preprocess_markdown(TMP_DIR, BOOK_FILE_LIST) as files:
        files_str = ' '.join(files)
        sh(f"pandoc {LATEX_PANDOC_OPTS} -o {target} {files_str}")


def _make_epub() -> None:
    pass


def _make_temp_file(name: str, contents: str, tempdir: Path) -> Path:
    """
    Write the specified contents (presumably a string with multiple lines)
    to a temporary file in the specified temporary directory, and return the
    path to the file.
    """
    path = Path(tempdir, name)
    with open(path, mode="w", encoding="utf-8") as f:
        f.write(contents)

    return path

def _find_local_image_references(markdown_files: Seq[Path],
                                 bookdir: Path,
                                 logger: logging.Logger) -> Seq[Path]:
    from urllib.parse import urlparse
    image_pat = re.compile(r'^\s*!\[.*\]\(([^\)]+)\).*$')

    images = []
    for path in markdown_files:
        with open(path, mode='r', encoding="utf-8") as md:
            logger.debug(f'Looking at "{path}"')
            for i, line in enumerate(md.readlines()):
                lno = i + 1
                if (m := image_pat.match(line)) is None:
                    continue
                image_ref = m.group(1)
                logger.debug(f"Found possible image on line {lno}: {image_ref}")
                p = urlparse(image_ref)
                if (p.scheme is not None) and (p.scheme.strip() != ""):
                    # Not a local image.
                    logger.debug(f"Non-local image. Scheme={p.scheme}")
                    continue

                image = Path(image_ref)
                if str(image.parent) in ("", "."):
                    logger.debug(f'No directory. Assuming "{bookdir}".')
                    image = Path(bookdir, image_ref)

                if not image.exists():
                    logger.warning(
                        f'File "{path}" refers to nonexistent image '
                        f'"{image}".'
                    )
                    continue

                images.append(image)

    return images


def _find_sources(bookdir: Path, files_dir: Path, tempdir: Path) -> SourcePaths:
    from functools import partial

    opt = partial(optional_path, dir=bookdir)
    expand = partial(path_glob, dir=bookdir)

    def local_or_default(filename: str) -> Path:
        return file_or_default(Path(bookdir, filename),
                               Path(files_dir, filename))

    if (latex_metadata := opt("latex-metadata.yaml")) is None:
        latex_metadata = _make_temp_file("latex-metadata.yaml",
                                         DEFAULT_LATEX_METADATA,
                                         tempdir)
    return SourcePaths(
        metadata=opt("metadata.yaml"),
        latex_metadata=latex_metadata,
        author=opt("author.md"),
        preface=opt("preface.md"),
        prologue=opt("prologue.md"),
        epilogue=opt("epilogue.md"),
        dedication=opt("dedication.md"),
        foreward=opt("foreward.md"),
        afterward=opt("afterward.md"),
        glossary=opt("glossary.md"),
        copyright=opt("copyright.md"),
        appendices=expand("appendix-*.md"),
        acknowledgements=opt("acknowledgements.md"),
        cover_image=opt("cover.png"),
        cover_image_for_pdf=opt("cover-pdf.png"),
        chapters=expand("chapter-*.md"),
        references=opt("references.yaml"),
        latex_template=local_or_default("latex.template"),
        html_css=local_or_default("html.css"),
        html_pdf_css=local_or_default("html-pdf.css"),
        epub_css=local_or_default("epub.css")
    )


def _check_pandoc(logger: logging.Logger) -> str:
    """
    Locate pandoc in the path, and check the version. The first found
    pandoc executable is used.
    """
    import subprocess
    pandoc = find_in_path("pandoc")
    if pandoc is None:
        raise FileNotFoundError("Cannot location pandoc executable.")

    with subprocess.Popen((f"{pandoc}", "--version"),
                          stdout=subprocess.PIPE,
                          encoding='ascii') as p:
        stdout, _ = p.communicate()

    version_pat = re.compile(r'^\s*pandoc\s+(\d+\.\d+[\d.]*).*$')
    version = None
    for l in stdout.split('\n'):
        if (m := version_pat.search(l)) is not None:
            version = m.group(1).split('.')
            break

    if (version is None) or (len(version) < 2):
        raise VersionError('Unable to determine pandoc version.')

    version = tuple(int(v) for v in version)
    if version[0:3] < MIN_PANDOC_VERSION:
        version_str = '.'.join(str(i) for i in version)
        min_version_str = '.'.join(str(i) for i in MIN_PANDOC_VERSION)
        raise VersionError(
            f"Pandoc version is {version_str}. Version {min_version_str} or "
             "newer is required."
        )

    logger.info(f"Using pandoc: {pandoc}")
    return pandoc

def _make_build_dir(build_dir: Path, logger: logging.Logger) -> None:
    if build_dir.exists():
        if not build_dir.is_dir():
            raise click.ClickException(
                f'Build directory "{build_dir}" already exists, but it '
                "isn't a directory."
            )
        logger.debug(f'Build directory "{build_dir}" already exists.')
    else:
        logger.debug(f'Creating directory "{build_dir}"')
        build_dir.mkdir()


def _build_book(book_dir: Path,
                build_dir: Path,
                files_dir: Path,
                logger: logging.Logger) -> None:
    logger.debug(f'Building book in {book_dir}')
    pandoc = _check_pandoc(logger)
    _make_build_dir(build_dir, logger)
    with TemporaryDirectory(prefix="ebook") as tempdir_name:
        tempdir = Path(tempdir_name)
        sources = _find_sources(book_dir, files_dir, tempdir)
        pprint(sources)
        combined_metadata = _combine_metadata(
            tempdir=tempdir, sources=sources, logger=logger
        )
        pprint(sources.markdown_files)
        image_references = _find_local_image_references(
            markdown_files=sources.markdown_files,
            bookdir=book_dir,
            logger=logger
        )
        print(image_references)
    logger.debug(f"{files_dir=} ({files_dir.absolute()})")

def _clean_output(book_dir: Path,
                  build_dir: Path,
                  logger: logging.Logger) -> None:
    if build_dir.exists():
        import shutil
        logger.debug(f"+ rm -rf {build_dir}")
        shutil.rmtree(build_dir)


@click.command("build")
@click.option("-f", "--files-dir", default=None, envvar="EBOOK_FILES_DIR",
              required=True,
              type=click.Path(dir_okay=True, file_okay=False, exists=True),
              help="Path to directory containing ebook's default templates and "
                   "other configuration files. If not specified, the value "
                   "of the EBOOK_FILES_DIR environment variable is used.")
@click.option("-l", "--log-level", default="INFO",
              type=click.Choice(LOG_LEVELS, case_sensitive=False),
              help="Specify log level.",
              show_default=True)
@click.option("-L", "--log-path", default=None,
              type=click.Path(dir_okay=False, writable=True),
              help="Path to additional file to which to log messages.")
@click.argument("bookdir", required=True,
                type=click.Path(dir_okay=True, file_okay=False,
                                writable=True, exists=True))
@click.argument("target", required=False,
                type=click.Choice(("clean", "build")),
                default="build")
def run_build(files_dir: Optional[str],
              log_level: str,
              log_path: Optional[str],
              bookdir: str,
              target: str) -> None:
    """
    Build the ebook. BOOKDIR is the directory containing your book's
    sources. The output will be created in a "build" subdirectory.
    TARGET is the build target, one of "build" or "clean". Note that you
    must have properly installed the program (via the ./install.sh script
    in the source repository) first.

    Valid targets:

    clean: Clean up (remove) all built artifacts

    build: Build all versions of the book (PDF, Epub, HTML, etc.)

    Default: build
    """
    logger = configure_logging(log_level.upper(), log_path)
    bookdir = Path(bookdir)
    build_dir = Path(bookdir, "build")
    match target:
        case 'clean':
            _clean_output(book_dir=bookdir,
                          build_dir=build_dir,
                          logger=logger)
        case 'build':
            _build_book(book_dir=bookdir,
                        build_dir=build_dir,
                        files_dir=Path(files_dir),
                        logger=logger)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if sys.version_info < (3, 12):
        print(f"Python 3.12.0 or better is required. You're using "
              f"{sys.version}")
        sys.exit(1)

    run_build()
