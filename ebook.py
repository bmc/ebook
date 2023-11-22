#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ---------------------------------------------------------------------------
# Copyright © 2017-2023 Brian M. Clapper
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

import logging
import os
import re
import shutil
import sys
from collections.abc import Generator
from contextlib import chdir, contextmanager
from dataclasses import dataclass
from enum import Enum
from enum import auto as enum_auto
from glob import glob
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional, Self
from typing import Sequence as Seq

import click
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
NAME = "ebook"

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

# +RTS and -RTS delimit Haskell runtime options. See
# http://www.haskell.org/ghc/docs/6.12.2/html/users_guide/runtime-control.html
#
# -Ksize sets the stack size. -K10m uses a 10 Mb stack, for instance. The
# default size is 8M.

# HASKELL_OPTS = '+RTS -K20m -RTS'
HASKELL_OPTS = ""

# Minimum Pandoc version, expressed as a (major, minor, patch) tuple
MIN_PANDOC_VERSION = (3, 1, 0)
MIN_PYTHON_VERSION = (3, 10)

INVARIANT_PANDOC_EXTENSIONS = (
    "line_blocks",
    "escaped_line_breaks",
    "smart",
    "fenced_code_blocks",
    "fenced_code_attributes",
    "backtick_code_blocks",
    "yaml_metadata_block",
    "startnum",
    "example_lists",
    "grid_tables",
    "strikeout",
)

# ---------------------------------------------------------------------------
# Data types and classes
# ---------------------------------------------------------------------------


class VersionError(Exception):
    pass


class OutputType(Enum):
    HTML = enum_auto()
    # LATEX = enum_auto()
    PDF = enum_auto()
    WORD = enum_auto()
    EPUB = enum_auto()
    AST = enum_auto()


@dataclass(frozen=True)
class SourcePaths:
    """
    Make-style sources and dependencies, calculated from the supplied book
    directory.
    """

    metadata: Optional[Path]
    author: Optional[Path]
    preface: Optional[Path]
    prologue: Optional[Path]
    epilogue: Optional[Path]
    dedication: Optional[Path]
    foreward: Optional[Path]
    afterward: Optional[Path]
    glossary: Optional[Path]
    copyright: Optional[Path]
    appendices: list[Path]
    acknowledgements: Optional[Path]
    cover_image: Optional[Path]
    references_yaml: Optional[Path]
    chapters: list[Path]
    html_css: Path
    html_pdf_css: Path
    epub_css: Path

    @property
    def all_metadata(self: Self) -> Seq[Path]:
        return [
            f for f in (self.metadata, self.references_yaml) if f is not None
        ]

    @property
    def markdown_files(self: Self) -> Seq[Path]:
        """
        Return the Markdown files for the book, in the appropriate order.
        """
        maybe_with_nones = (
            [
                self.copyright,
                self.dedication,
                self.foreward,
                self.preface,
                self.prologue,
            ]
            + self.chapters
            + [self.epilogue, self.acknowledgements]
            + self.appendices
            + [self.glossary, self.author]
        )
        return [p for p in maybe_with_nones if p is not None]


@dataclass(frozen=True)
class BuildData:
    """
    Contains all consolidated information necessary to build the book.
    See prepare_build() for details.
    """
    source_paths: SourcePaths
    book_dir: Path
    build_dir: Path
    etc_dir: Path
    files_dir: Path
    scripts_dir: Path
    pandoc: Path
    temp_dir: Path
    combined_metadata: Path
    image_references: list[Path]
    html_body_include: Path
    additional_markdown_extensions: list[str]

    @property
    def markdown_files(self: Self) -> Seq[Path]:
        """
        Return the list of Markdown files to be processed.
        """
        return [self.combined_metadata] + list(
            self.source_paths.markdown_files
        )


class BookError(Exception):
    """
    Base class for exceptions thrown by this tool.
    """
    pass


class BookToolError(BookError):
    """
    Thrown to indicate tooling errors, such as inability to find Pandoc.
    """
    pass


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def configure_logging(
    s_level: str, path: Optional[str] = None
) -> logging.Logger:
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
    log_level: Optional[int] = getattr(logging, s_level.upper(), None)
    if log_level is None:
        raise Exception(
            f'Cannot get log level "{s_level.upper()} from ' "logging package."
        )

    formatter = logging.Formatter(
        "[%(asctime)s] (%(levelname)s) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handlers = []
    handlers.append(logging.StreamHandler(stream=sys.stdout))
    if path is not None:
        handlers.append(logging.FileHandler(filename=path, mode="w"))

    logger = logging.getLogger("main")
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

    logger.debug(f"Logging configured, at log level {s_level}.")

    return logger


def file_or_default(path: Path, default: Path) -> Path:
    """
    Return `path` if it exists, or `default` if not.

    Parameters:

    path    - path to file to test
    default - default file to use, if <path> doesn't exist

    Returns:

    Whichever one exists

    Raises a BookError on error
    """
    if path.is_file():
        return path

    if not default.is_file():
        raise BookError(
            f"Default file {default} does not exist or is not a file."
        )

    return default


def optional_path(filename: str, dir: Path) -> Optional[Path]:
    """
    Look for the specified filename in directory <dir>, returning a Path
    object or None. The <dir> argument is second to faciliate partial
    application via functools.partial().
    """
    p = Path(dir, filename)
    return p if p.exists() and p.is_file() else None


def path_glob(pattern: str, dir: Path) -> list[Path]:
    """
    Expand the specified glob pattern in directory <dir>, returning a sequence
    of Path objects (which might be empty). The <dir> argument is second to
    faciliate partial application via functools.partial().
    """
    return list(Path(dir).glob(pattern))


def sh(command: str, logger: logging.Logger) -> None:
    """
    Runs a shell command, exiting if the command fails.

    Parameters:

    command - the command to run
    logger  - the logger
    """
    import subprocess

    logger.debug(command)
    rc = subprocess.call(command, shell=True)
    if rc < 0:
        raise OSError(f"Command aborted by signal {-rc}")


def find_in_path(command: str) -> Optional[Path]:
    """
    Find a command in the path, if possible.
    """
    path = [
        Path(p) for p in os.getenv("PATH", "").split(os.pathsep) if len(p) > 0
    ]
    found = None
    for d in path:
        if not d.exists():
            continue
        p = Path(d, command)
        if p.is_file() and os.access(p, os.X_OK):
            found = p
            break

    return found


@contextmanager
def ensure_dir(
    directory: Path, autoremove: bool = False
) -> Generator[None, None, None]:
    """
    Run a block in the context of a directory that is created if it doesn't
    exist.

    Parameters:

    dir        - the directory
    autoremove - if True, remove the directory when the "with" block finishes.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        yield
    finally:
        if autoremove:
            if directory.exists():
                shutil.rmtree(str(directory))


def combine_metadata(tempdir: Path, sources: SourcePaths) -> Path:
    """
    Create the combined metadata YAML file and return its path.

    Parameters:

    tempdir - the temporary directory, where the combined metadata file will
              be written
    sources - the sources from the book directory

    Returns the combined metadata file
    """

    # Load the primary metadata file, as we need to pull some things from it.
    metadata: Dict[str, str] = {}
    if sources.metadata is not None:
        with open(sources.metadata, encoding="utf-8") as f:
            metadata = yaml.safe_load(f)

    combined_metadata_path = Path(tempdir, "metadata.yaml")
    with open(combined_metadata_path, "w", encoding="utf-8") as out:
        for p in sources.all_metadata:
            if p is None:
                continue
            if not p.exists():
                continue

            out.write("---\n")
            with open(p, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    out.write(line)
            out.write("...\n\n")

        # If no language was specified, add one.
        if metadata.get("language") is None:
            out.write("---\n")
            out.write("lang: en")
            out.write("...\n\n")

    return combined_metadata_path


def make_temp_text_file(name: str, contents: str, tempdir: Path) -> Path:
    """
    Write the specified contents (presumably a string with multiple lines)
    to a temporary file in the specified temporary directory, and return the
    path to the file.

    Parameters

    name     - the desired name of the file
    contents - the text contents to write to the file
    tempdir  - where the file will be created

    Returns the new, temporary file
    """
    path = Path(tempdir, name)
    with open(path, mode="w", encoding="utf-8") as f:
        f.write(contents)

    return path


@contextmanager
def preprocess_markdown(
    build_data: BuildData, divs: bool = False
) -> Generator[list[Path], None, None]:
    """
    Content manager that preprocesses the Markdown files, adding some content
    and producing new, individual files. These files should be used to generate
    the book, rather than the original user-supplied ones.

    Parameters:

    build_data - the build data
    divs       - True to generate a <div> with a file-based "id" attribute and
                 'class="book_section"' around each Markdown file. Only really
                 useful for HTML.

    Yields the paths to the generated files
    """
    file_without_dashes = re.compile(r"^[^a-z]*([a-z]+).*$")

    directory = Path(build_data.temp_dir, "preprocessed")
    from_to = [
        (f, Path(directory, Path(f).name)) for f in build_data.markdown_files
    ]
    generated = [t for _, t in from_to]
    with ensure_dir(directory, autoremove=True):
        for f, temp in from_to:
            with open(temp, mode="w") as t:
                basefile = f.name
                ext = f.suffix
                m = file_without_dashes.match(basefile)
                if m:
                    cls = m.group(1)
                else:
                    cls = basefile

                # Added classes to each section. Can be used in CSS.
                if divs and ext == ".md":
                    t.write(f'<div class="book_section" id="section_{cls}">\n')
                with open(f, mode="r", encoding="utf-8") as input_file:
                    for line in input_file.readlines():
                        print(line.rstrip(), file=t)

                # Force a newline after each file.
                t.write("\n")
                if divs and ext == ".md":
                    print("</div>", file=t)
                t.close()

        if build_data.source_paths.references_yaml is not None:
            # Create a temporary Markdown file (page) for the references, all
            # the way at the end, which is where Pandoc writes them.
            generated.append(
                make_temp_text_file(
                    name="references.md",
                    tempdir=build_data.temp_dir,
                    contents="# References\n",
                )
            )

        yield generated


def find_image_references(
    markdown_files: Seq[Path], bookdir: Path, logger: logging.Logger
) -> list[Path]:
    """
    Parse image references from the book's Markdown files, so they can
    be copied.

    Parameters:

    markdown_files - the files to parse, looking for image references
    bookdir        - the book directory where the images presumably reside
    logger         - the logger

    Raises an exception if an absolute path or URL is found.
    """
    from urllib.parse import urlparse

    image_pat = re.compile(r"\s*!\[.*\]\(([^\)]+)\).*")

    abort = False
    images = []
    for path in markdown_files:
        with open(path, mode="r", encoding="utf-8") as md:
            logger.debug(f'Looking at "{path}"')
            for i, line in enumerate(md.readlines()):
                lno = i + 1
                if (m := image_pat.search(line)) is None:
                    continue
                image_ref = m.group(1)
                logger.debug(
                    f"Found possible image on line {lno}: {image_ref}"
                )
                p = urlparse(image_ref)
                if (p.scheme is not None) and (p.scheme.strip() != ""):
                    # Not a local image.
                    logger.error(
                        f'Image "{image_ref}" is a URL, which is unsupported.'
                    )
                    abort = True
                    continue

                image = Path(image_ref)
                if image.is_absolute():
                    image_full_path = image
                    logger.error(
                        f'Image "{image_ref}" is an absolute path, which is '
                        "unsupported."
                    )
                    abort = True
                    continue

                image_full_path = Path(bookdir, image_ref)
                if not image_full_path.exists():
                    logger.error(
                        f'File "{path}" refers to nonexistent image '
                        f'"{image_full_path}".'
                    )
                    abort = True
                    continue

                images.append(image)

    if abort:
        raise BookError("One or more images are in error.")

    return images


def find_sources(book_dir: Path, etc_dir: Path) -> SourcePaths:
    """
    Locate all book sources

    Parameters:

    book_dir - the source directory for the book being built
    etc_dir  - this tool's installed "etc" directory

    Returns a SourcePaths object describing all the book sources
    """
    from functools import partial

    book_dir = book_dir.absolute()
    opt = partial(optional_path, dir=book_dir)
    expand = partial(path_glob, dir=book_dir)

    def local_or_default(filename: str) -> Path:
        return file_or_default(
            Path(book_dir, filename), Path(etc_dir, filename)
        )

    return SourcePaths(
        metadata=opt("metadata.yaml"),
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
        chapters=sorted(expand("chapter-*.md")),
        references_yaml=opt("references.yaml"),
        html_css=local_or_default("html.css"),
        html_pdf_css=local_or_default("html-pdf.css"),
        epub_css=local_or_default("epub.css"),
    )


def pandoc_options(build_data: BuildData, output_type: OutputType) -> str:
    """
    Determine the appropriate Pandoc options for a given output file type.

    Parameters:

    build_data  - the build data, used for paths
    output_type - the output type

    Returns a string of command line options
    """
    extensions: set[str] = set(INVARIANT_PANDOC_EXTENSIONS)
    if build_data.additional_markdown_extensions is not None:
        extensions = extensions.union(
            set(build_data.additional_markdown_extensions)
        )

    ext_str = "+".join(extensions)
    input_format = f"markdown+{ext_str}"

    pandoc_filter = Path(build_data.scripts_dir, "pandoc-filter.py")
    common = (
        f"-f {input_format} {HASKELL_OPTS} -F {pandoc_filter} "
        "--standalone --citeproc"
    )

    head_include = Path(build_data.files_dir, "head_include.html")
    html_common = (
        f"{common} -t html "
        f"-H {head_include} -B {build_data.html_body_include} "
    )

    match output_type:
        case OutputType.HTML:
            return f"{html_common} --css {build_data.source_paths.html_css} "

        case OutputType.PDF:
            return (
                f"{html_common} --css {build_data.source_paths.html_pdf_css} "
                f"--pdf-engine=weasyprint"
            )

        case OutputType.WORD:
            ref = Path(build_data.files_dir, "custom-reference.docx")
            return f"{common} -t docx --reference-doc={ref}"

        case OutputType.EPUB:
            return (
                f"{common} -t epub --toc --split-level=1 "
                f"--css {build_data.source_paths.epub_css} "
                f"--epub-cover-image {build_data.source_paths.cover_image}"
            )

        case OutputType.AST:
            return f"{common} -t json"


def locate_pandoc(logger: logging.Logger) -> Path:
    """
    Locate pandoc in the path, and check the version. The first found
    pandoc executable is used.

    Returns the path to the pandoc

    Raises:

    FileNotFoundError - cannot find pandoc
    BookToolError     - unsupported pandoc version
    """
    import subprocess

    pandoc = find_in_path("pandoc")
    if pandoc is None:
        raise FileNotFoundError("Cannot locate pandoc executable.")

    with subprocess.Popen(
        (f"{pandoc}", "--version"), stdout=subprocess.PIPE, encoding="ascii"
    ) as p:
        stdout, _ = p.communicate()

    version_pat = re.compile(r"^\s*pandoc\s+(\d+\.\d+[\d.]*).*$")
    version = None
    for l in stdout.split("\n"):
        if (m := version_pat.search(l)) is not None:
            version = m.group(1).split(".")
            break

    if (version is None) or (len(version) < 2):
        raise BookToolError("Unable to determine pandoc version.")

    version = tuple(int(v) for v in version)
    if version[0:3] < MIN_PANDOC_VERSION:
        version_str = ".".join(str(i) for i in version)
        min_version_str = ".".join(str(i) for i in MIN_PANDOC_VERSION)
        raise BookToolError(
            f"Pandoc version is {version_str}. Version {min_version_str} or "
            "newer is required."
        )

    logger.info(f"Using pandoc: {pandoc}")
    return pandoc


def make_build_dir(build_dir: Path, logger: logging.Logger) -> None:
    """
    Create the build directory, if it doesn't exists.

    Parameters:

    build_dir - the path to the build directory
    logger    - the logger
    """
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


def make_html_body_include(build_data: BuildData) -> None:
    """
    Create the body include for HTML output, which is where the cover page
    image (if any) goes. The output is written to build_data.html_body_include.
    If there's no cover image, then the generated file will be empty. The
    template used is in the etc/files directory (body_include.html). It's
    a string.Template-compatible template.
    """
    import base64

    with open(build_data.html_body_include, mode="w", encoding="utf-8") as out:
        if build_data.source_paths.cover_image is None:
            # Nothing to do. The template is just for a cover image. Make sure
            # there's something in the file, though.
            out.write("\n")
        else:
            with open(build_data.source_paths.cover_image, mode="rb") as img:
                image_bytes = img.read()

            b64_bytes = base64.encodebytes(image_bytes)
            b64_str = "".join(chr(b) for b in b64_bytes).replace("\n", "")
            with open(
                Path(build_data.files_dir, "body_include.html"),
                mode="r",
                encoding="utf-8",
            ) as template:
                out.write(
                    Template(template.read()).substitute(
                        {"base64_image": b64_str}
                    )
                )


def fix_epub(
    epub: Path, build_data: BuildData, book_title: str, logger: logging.Logger
) -> None:
    """
    Make some adjustments to the generated tables of contents in the ePub,
    removing empty elements and removing items matching the book title.

    Parameters:

    epub:       The path to the epub file
    book_title: The book title
    build_data: The build data
    logger:     Logger
    """
    from xml.dom import minidom
    from zipfile import ZIP_DEFLATED, ZipFile

    temp_dir = Path(build_data.temp_dir, "epub")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    def zip_add(zf, path, zippath):
        """Swiped from zipfile module."""
        if os.path.isfile(path):
            zf.write(path, zippath, ZIP_DEFLATED)
        elif os.path.isdir(path):
            if zippath:
                zf.write(path, zippath)
            for nm in os.listdir(path):
                zip_add(zf, os.path.join(path, nm), os.path.join(zippath, nm))

    def unpack_epub() -> None:
        # Assumes pwd is *not* unpack directory.
        logger.debug(f".. Unpacking {epub}.")
        with ZipFile(epub) as z:
            z.extractall(temp_dir)

    def repack_epub() -> None:
        # Assumes pwd is *not* unpack directory.
        logger.debug(f".. Packing new {epub}.")
        with ZipFile(epub, "w") as z:
            with chdir(temp_dir):
                for f in os.listdir("."):
                    if f in ["..", "."]:
                        continue
                    zip_add(z, f, f)

    def strip_text_children(element: minidom.Element) -> None:
        for child in element.childNodes:
            if type(child) == minidom.Text:
                element.removeChild(child)

    def get_text_children(element: minidom.Element) -> Optional[str]:
        text = None
        if element:
            s = ""
            for child in element.childNodes:
                if child and (type(child) == minidom.Text):
                    s += child.data.strip()
            text = s if s else None

        return text

    def fix_toc_ncx(toc: Path) -> None:
        # Assumes pwd *is* unpack directory
        logger.debug(f'(fix_epub) Reading table of contents file "{toc}".')
        with open(toc, encoding="utf-8") as f:
            toc_xml = f.read()

        logger.debug("(fix_epub) Adjusting table of contents.")
        with minidom.parseString(toc_xml) as dom:
            nav_map = dom.getElementsByTagName("navMap")
            if not nav_map:
                raise Exception("Malformed table of contents: No <navMap>.")
            nav_map = nav_map[0]
            for p in nav_map.getElementsByTagName("navPoint"):
                text_nodes = p.getElementsByTagName("text")
                text = None
                if text_nodes:
                    text = get_text_children(text_nodes[0])

                if (not text) or (text == book_title):
                    nav_map.removeChild(p)

            # Renumber the nav points.
            for i, p in enumerate(nav_map.getElementsByTagName("navPoint")):
                num = i + 1
                p.setAttribute("id", f"navPoint-{num}")

            # Strip any text nodes from the navmap.
            strip_text_children(nav_map)

            # Write it out.
            with open(toc, mode="w", encoding="utf-8") as f:
                dom.writexml(f)

    def fix_nav_xhtml(toc: Path) -> None:
        # Assumes pwd *is* unpack directory
        logger.debug(f'(fix_epub) Reading table of contents file "{toc}".')
        with open(toc, encoding="utf8") as f:
            toc_xml = f.read()

        logger.debug("(fix_epub) Adjusting table of contents.")
        with minidom.parseString(toc_xml) as dom:
            navs = dom.getElementsByTagName("nav")
            nav = None
            for n in navs:
                if not n.hasAttributes():
                    continue
                a = n.attributes.get("id")
                if not a:
                    continue
                if a.value == "toc":
                    nav = n
                    break
            else:
                raise Exception("Malformed table of contents: No TOC <nav>.")

            ol = nav.getElementsByTagName("ol")
            if (not ol) or (len(ol) == 0):
                raise Exception(
                    "Malformed table of contents: No list in <nav>."
                )
            ol = ol[0]

            for li in ol.getElementsByTagName("li"):
                a = li.getElementsByTagName("a")
                if not a:
                    raise Exception(
                        "Malformed table of contents: No <a> in <li>."
                    )
                a = a[0]
                text = get_text_children(a)
                if (not text) or (text == book_title):
                    ol.removeChild(li)

            # Renumber the list items
            for i, li in enumerate(ol.getElementsByTagName("li")):
                num = i + 1
                li.setAttribute("id", f"toc-li-{num}")

            # Strip any text nodes from the ol.
            strip_text_children(ol)

            # Write it out.
            with open(toc, mode="w", encoding="utf-8") as f:
                dom.writexml(f)

    def fix_chapter_files() -> None:
        logger.debug("(fix_epub) Fixing titles in chapter files...")
        title_pat = re.compile(r"^(.*<title>).*(</title>).*$")

        def fix_chapter_file(path: Path, title: str) -> None:
            with open(path, encoding="utf-8") as f:
                lines = [l.rstrip() for l in f.readlines()]
            with open(path, mode="w", encoding="utf-8") as f:
                for line in lines:
                    m = title_pat.search(line)
                    if m:
                        line = f"{m.group(1)}{title}{m.group(2)}"
                    f.write(f"{line}\n")

        for file in glob("EPUB/text/ch*.xhtml"):
            fix_chapter_file(Path(file), title=book_title)

    # Main logic
    try:
        unpack_epub()
        with ensure_dir(temp_dir):
            with chdir(temp_dir):
                paths_and_funcs = (
                    (Path("EPUB", "toc.ncx"), fix_toc_ncx),
                    (Path("EPUB", "nav.xhtml"), fix_nav_xhtml),
                )
                for toc, func in paths_and_funcs:
                    if not os.path.exists(toc):
                        logger.debug(f"(fix_epub) No {toc} file. Skipping it.")
                        continue
                    func(toc)

                fix_chapter_files()

        repack_epub()
    finally:
        # rmtree(temp_dir)
        pass


def load_metadata(metadata_file: Path) -> Dict[str, Any]:
    """
    Loads a YAML metadata file, returning the loaded dictionary.

    Parameters:

    metadata_file; path to the file to load
    """
    if metadata_file.exists():
        with open(metadata_file, mode="r") as f:
            s = "".join([s for s in f if not s.startswith("---")])
            metadata = yaml.load(s, Loader=yaml.FullLoader)
    else:
        metadata = {}

    return metadata


@contextmanager
def prepare_build(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> Generator[BuildData, None, None]:
    """
    Prepare the build environment, which includes gathering sources, locating
    images, creating a temporary work directory, ensuring that the final
    build directory exists, etc.

    After the context exits, the temporary work directory is removed, so all
    build work must occur within the context.

    Parameters:

    book_dir - the directory containing the book's sources
    etc_dir  - where the support files are located
    logger   - the logger

    Yields a BuildData object with all the information necessary to build
    the book.
    """
    pandoc = locate_pandoc(logger)
    make_build_dir(build_dir, logger)
    with TemporaryDirectory(prefix="ebook") as tempdir_name:
        tempdir = Path(tempdir_name)
        files_dir = Path(etc_dir, "files")
        sources = find_sources(book_dir, files_dir)
        combined_metadata = combine_metadata(tempdir=tempdir, sources=sources)
        image_references = find_image_references(
            markdown_files=sources.markdown_files,
            bookdir=book_dir,
            logger=logger,
        )
        bd = BuildData(
            source_paths=sources,
            book_dir=book_dir.absolute(),
            build_dir=build_dir.absolute(),
            etc_dir=etc_dir,
            files_dir=files_dir,
            scripts_dir=Path(etc_dir, "scripts"),
            pandoc=pandoc,
            temp_dir=tempdir,
            combined_metadata=combined_metadata,
            image_references=image_references,
            html_body_include=Path(tempdir, "body_include.html"),
            additional_markdown_extensions=additional_extensions,
        )
        make_html_body_include(bd)
        yield bd


def copy_images_to_build(
    build_data: BuildData, logger: logging.Logger
) -> None:
    """
    Copies all images from their source locations into the appropriate
    place in the build directory. This is necessary primarily for HTML,
    where images aren't currently inlined.

    Parameters:

    build-data - the build data, from prepare_build()
    logger     - where to log messages
    """
    with chdir(build_data.book_dir):
        for img in build_data.image_references:
            if img.is_absolute():
                # Do nothing.
                continue

            parent = img.parent
            if str(parent) == ".":
                # Copy straight into build directory.
                target = Path(build_data.build_dir, img.name)

            else:
                # Relative copy.
                target_parent = Path(build_data.build_dir, parent)
                logger.debug(f"mkdir -p {target_parent}")
                target_parent.mkdir(parents=True, exist_ok=True)
                target = Path(build_data.build_dir, img)

            img_abs = Path(build_data.book_dir, img)
            logger.debug(f"Copying: {img_abs} -> {target}")
            shutil.copy(img_abs, target)


def build_html_or_pdf(
    build_data: BuildData, output_type: OutputType, logger: logging.Logger
) -> None:
    """
    Since PDF is built from HTML, building them is almost identical, except
    for a couple OutputType-related differences. This function builds either,
    based off the OutputType.

    Parameters:

    book_dir    - the directory containing the book's sources
    output_type - the output type (OutputType.PDF or OutputType.HTML)
    logger      - the logger
    """
    match output_type:
        case OutputType.PDF:
            extension = ".pdf"
            copy_images = False
        case OutputType.HTML:
            extension = ".html"
            copy_images = True
        case _:
            assert False

    with preprocess_markdown(build_data=build_data, divs=True) as files:
        files_str = " ".join(str(p) for p in files)
        output_path = Path(build_data.build_dir, f"book{extension}")
        logger.info(f'Building "{output_path}"')
        opts = pandoc_options(build_data, output_type)
        with chdir(build_data.book_dir):
            sh(
                f"{build_data.pandoc} {opts} -o {output_path} {files_str}",
                logger,
            )

    # HTML will want the images, so copy them into the output directory.
    if copy_images:
        copy_images_to_build(build_data, logger)


def dump_ast(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Dumps the JSON AST to the build directory.

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        with preprocess_markdown(build_data) as files:
            opts = pandoc_options(build_data, OutputType.AST)
            files_str = " ".join(str(p) for p in files)
            output = Path(build_data.build_dir, "ast.json")
            temp_output = Path(build_data.temp_dir, "ast.json")
            sh(
                f"{build_data.pandoc} {opts} -o {temp_output} {files_str}",
                logger,
            )
            with (
                open(temp_output, mode="r", encoding="utf-8") as temp,
                open(output, mode="w", encoding="utf-8") as out,
            ):
                import json

                js = json.load(temp)
                out.write(json.dumps(js, sort_keys=False, indent=2))


def dump_combined(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Dumps the combined single document to the build directory.

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        with preprocess_markdown(build_data) as files:
            output_path = Path(build_data.build_dir, "combined.md")
            logger.debug(f"Writing {output_path}")
            with open(output_path, mode="w", encoding="utf-8") as out:
                for file in files:
                    with open(file, mode="r", encoding="utf-8") as f:
                        out.write(f.read())


def build_docx(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Creates the Microsoft Word version of the book

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        with preprocess_markdown(build_data=build_data) as files:
            output_path = Path(build_data.build_dir, "book.docx")
            logger.info(f'Building "{output_path}"')
            opts = pandoc_options(build_data, OutputType.WORD)

            # Force-include the cover image, if there is one, because
            # Pandoc won't insert it.
            if build_data.source_paths.cover_image is not None:
                cover = make_temp_text_file(
                    "cover.md",
                    f"![]({build_data.source_paths.cover_image})",
                    build_data.temp_dir,
                )
                files = [cover] + files

            files_str = " ".join(str(p) for p in files)
            with chdir(build_data.book_dir):
                sh(
                    f"{build_data.pandoc} {opts} -o {output_path} {files_str}",
                    logger,
                )


def build_epub(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Creates the ePub version of the book

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        with preprocess_markdown(build_data=build_data) as files:
            files_str = " ".join(str(p) for p in files)
            output_path = Path(build_data.build_dir, "book.epub")
            logger.info(f'Building "{output_path}"')
            opts = pandoc_options(build_data, OutputType.EPUB)
            if build_data.source_paths.metadata is not None:
                metadata = load_metadata(build_data.source_paths.metadata)
            else:
                metadata = {}
            with chdir(build_data.book_dir):
                sh(
                    f"{build_data.pandoc} {opts} -o {output_path} {files_str}",
                    logger,
                )
                fix_epub(
                    epub=output_path,
                    build_data=build_data,
                    book_title=metadata.get("title", ""),
                    logger=logger,
                )


def build_html(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Creates the HTML version of the book

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        build_html_or_pdf(build_data, OutputType.HTML, logger)


def build_pdf(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Target: Creates the PDF version of the book

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    with prepare_build(
        book_dir=book_dir,
        build_dir=build_dir,
        etc_dir=etc_dir,
        additional_extensions=additional_extensions,
        logger=logger,
    ) as build_data:
        build_html_or_pdf(build_data, OutputType.PDF, logger)


def build_all(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Build all versions of the book.

    Parameters:

    book_dir              - the directory containing the book's sources
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
    additional_extensions - any additional Pandoc Markdown extensions
    logger                - the logger to use for messages
    """
    for func in (build_pdf, build_html, build_epub, build_docx):
        func(
            book_dir=book_dir,
            build_dir=build_dir,
            etc_dir=etc_dir,
            additional_extensions=additional_extensions,
            logger=logger,
        )


def clean_output(
    book_dir: Path,
    build_dir: Path,
    etc_dir: Path,
    additional_extensions: list[str],
    logger: logging.Logger,
) -> None:
    """
    Clean the build directory. Note: This function takes all the parameters
    the build functions do, despite not using them all, to adhere to a uniform
    function-calling protocol (which makes the main program simpler).

    Parameters:

    book_dir              - the directory containing the book's sources
                            (not used)
    build_dir             - the desired build (output) directory
    etc_dir               - the directory with the default files and scripts
                            (not used)
    additional_extensions - any additional Pandoc Markdown extensions (not
                            used)
    logger                - the logger to use for messages
    """
    if build_dir.exists():
        logger.debug(f'Removing "{build_dir}" and its contents.')
        shutil.rmtree(build_dir)


@click.command("build")
@click.option(
    "-b",
    "--build-dir",
    default=None,
    type=click.Path(dir_okay=True, file_okay=False),
    help="The directory to which to write the built book files. Defaults to "
    "BOOK_DIR/build",
)
@click.option(
    "-e",
    "--etc-dir",
    default=None,
    envvar="EBOOK_ETC",
    required=True,
    type=click.Path(dir_okay=True, file_okay=False, exists=True),
    help="Path to directory containing ebook's default templates, "
    "scripts, and other files. If not specified, the value "
    "of the EBOOK_ETC environment variable is used.",
)
@click.option(
    "-l",
    "--log-level",
    default="INFO",
    type=click.Choice(LOG_LEVELS, case_sensitive=False),
    help="Specify log level.",
    show_default=True,
)
@click.option(
    "-L",
    "--log-path",
    default=None,
    type=click.Path(dir_okay=False, writable=True),
    help="Path to additional file to which to log messages.",
)
@click.option(
    "-x",
    "--extensions",
    default=None,
    help="Comma-separated list of additional Pandoc Mardown "
    "extensions to be enabled",
)
@click.version_option(VERSION, prog_name=NAME)
@click.argument(
    "book_dir",
    required=True,
    type=click.Path(
        dir_okay=True, file_okay=False, writable=True, exists=True
    ),
)
@click.argument("target", required=False, nargs=-1)
def run_build(
    build_dir: Optional[str],
    etc_dir: str,
    log_level: str,
    log_path: Optional[str],
    book_dir: str,
    extensions: Optional[str],
    target: str,
) -> None:
    """
    Build the ebook. BOOKDIR is the directory containing your book's
    sources. The output will be created in a "build" subdirectory.
    TARGET is the build target, as described below. You can specify multiple
    targets. The default TARGET is "all".

    Note that you must have properly installed the program (via the
    ./install.py script in the source repository) first.

    Valid build targets:

    \b
    clean:           Delete the entire build directory
    build, all:      Build all versions of the book (PDF, Epub, HTML, etc.)
    pdf, book.pdf:   Build just the PDF version of the book.
    html, book.html: Build just the HTML version of the book
    epub, book.epub: Build just the ePub version of the book
    docx, word, book.docx:
                     Build just the Microsoft Word version of the book
    ast:             Write the Pandoc AST, as pretty-printed JSON, to ast.json
                     in the build directory. Primarily for debugging.
    combined:        Write the final combined document, as fed to Pandoc, to
                     combined.md in the build directory. Primarily for
                     debugging.

    Default: build
    """
    logger = configure_logging(log_level.upper(), log_path)
    try:
        target_map = {
            "clean": clean_output,
            "all": build_all,
            "build": build_all,
            "pdf": build_pdf,
            "book.pdf": build_pdf,
            "epub": build_epub,
            "book.epub": build_epub,
            "docx": build_docx,
            "book.docx": build_docx,
            "word": build_docx,
            "html": build_html,
            "book.html": build_html,
            "combined": dump_combined,
            "ast": dump_ast,
        }

        targets = target if len(target) > 0 else ["all"]

        # Validate targets first. Don't run anything unless we know all targets are
        # valid.
        target_funcs = []
        for t in targets:
            if (target_func := target_map.get(t)) is None:
                raise click.ClickException(f'"{t}" is an unknown target.')

            target_funcs.append(target_func)

        additional_extensions = []
        if extensions is not None:
            additional_extensions = [s.strip() for s in extensions.split(",")]

        book_dir_path = Path(book_dir).absolute()
        if build_dir is None:
            build_dir_path = Path(book_dir_path, "build")
        else:
            build_dir_path = Path(build_dir)

        for target_func in target_funcs:
            target_func(
                book_dir=book_dir_path,
                build_dir=build_dir_path,
                etc_dir=Path(etc_dir).absolute(),
                additional_extensions=additional_extensions,
                logger=logger,
            )
    except (BookError, FileNotFoundError) as e:
        logger.error(f"{e}")
        raise click.ClickException("--- ABORTED ---")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if sys.version_info < MIN_PYTHON_VERSION:
        s_ver = ".".join(str(n) for n in MIN_PYTHON_VERSION)
        print(
            f"Python {s_ver}.0 or better is required. You're using "
            f"{sys.version}"
        )
        sys.exit(1)

    run_build()
