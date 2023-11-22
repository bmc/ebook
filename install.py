#!/usr/bin/env python

import sys
import os
from pathlib import Path
import re
import shutil
from typing import Tuple, Optional

src_dir = Path(__file__).parent
python = Path(sys.executable).absolute()
bin_dir = Path("~/bin").expanduser()
etc_dir = Path("~/etc/ebook").expanduser()
executable = Path(bin_dir, "ebook")
ebook_src = Path(src_dir, "ebook.py")

def find_in_path(command: str) -> Optional[Path]:
    """
    Find a command in the path, if possible.
    """
    path = [
        Path(p) for p in os.getenv('PATH', '').split(os.pathsep) if len(p) > 0
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


def locate_pandoc(min_version: Tuple[int, int, int]) -> Path:
    """
    Locate pandoc in the path, and check the version. The first found
    pandoc executable is used. Note that this is similar to the function
    in ebook, itself.
    """
    import subprocess
    pandoc = find_in_path("pandoc")
    if pandoc is None:
        raise FileNotFoundError("Cannot locate pandoc executable.")

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
        raise ValueError('Unable to determine Pandoc version.')

    version = tuple(int(v) for v in version)
    if version[0:3] < min_version:
        version_str = '.'.join(str(i) for i in version)
        min_version_str = '.'.join(str(i) for i in min_version)
        raise ValueError(
            f"Pandoc version is {version_str}. Version {min_version_str} or "
             "newer is required."
        )

    return pandoc

def uninstall() -> None:
    if executable.exists():
        print(f"rm {executable}")
        os.unlink(executable)

    if etc_dir.exists():
        print(f"rm -r {etc_dir}")
        shutil.rmtree(etc_dir)


def install_executable() -> Optional[Tuple[int, int, int]]:
    """
    Install the executable. As a side effect, return the required version of
    Pandoc, if found.
    """
    # Read ebook.py and replace the shebang with the path to this Python.
    shebang = re.compile(r'^#!/.*$')
    pandoc_ver = re.compile(r'MIN_PANDOC_VERSION\s*=\s*\(([^)]+)\)')

    pandoc_min_version: Optional[Tuple[int, int, int]] = None

    print(f"Installing ebook.py as {executable}")
    with (open(executable, mode="w", encoding="utf-8") as out,
        open(ebook_src, mode="r", encoding="utf-8") as src):
        for line in src.readlines():
            if (m := pandoc_ver.search(line)) is not None:
                pandoc_min_version = tuple(
                    [int(s.strip()) for s in m.group(1).split(",")]
                )

            if shebang.search(line) is not None:
                out.write(f"#!{python}\n")
            else:
                out.write(line)

    os.chmod(executable, 0o755)
    return pandoc_min_version


def install_etc_files() -> None:
    print(f"mkdir -p {etc_dir}")
    etc_dir.mkdir(parents=True, exist_ok=True)
    src_etc = Path(src_dir, "etc")
    print(f"cp -r {src_etc} {etc_dir}")
    shutil.copytree(src_etc, etc_dir, dirs_exist_ok=True)

def install_packages() -> None:
    requirements = Path(src_dir, "requirements.txt")
    cmd = f"{python} -m pip install -r {requirements}"
    print(f"+ {cmd}")
    match os.system(cmd):
        case 0:
            pass
        case rc if rc < 0:
            raise OSError(f"Command aborted by signal {-rc}")
        case rc:
            raise OSError(f"Command failed with exit code {rc}")

def install() -> None:

    print(f"Using Python: {python}")
    pandoc_min_version = install_executable()

    if pandoc_min_version is None:
        raise Exception("Unable to find required Pandoc version in {ebook_src}.")
    else:
        pandoc = locate_pandoc(pandoc_min_version)
        print(f"Will use Pandoc: {pandoc}")

    install_etc_files()
    install_packages()

    print('-' * 70)
    print(f"Installation complete.")
    print(f"\nYou can run ebook from {executable}.")
    print("\nHINT: Consider setting EBOOK_ETC in your shell startup:")
    print(f'\nexport EBOOK_ETC="{etc_dir}"')

if __name__ == "__main__":
    try:
        match sys.argv:
            case [_, "-u"]:
                uninstall()
            case [_]:
                install()
            case _:
                print(f"Usage: {sys.argv[0]} [-u]", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        print(f"\n(ERROR) {e}", file=sys.stderr)
        sys.exit(1)
