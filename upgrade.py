#!/usr/bin/env python

import sys
from shutil import *
import os

def msg(message):
    print(f'{message}')

def copy_files(path):
    for dir in ('files', 'lib', 'scripts'):
        msg(f'Upgrading "{dir}" directory.')

        if not os.path.isdir(dir):
            msg(f'Creating local "{dir}" directory.')
            os.mkdir(dir)
        else:
            msg(f'Cleaning local "{dir}" directory.')
            for f in os.listdir(dir):
                if f.startswith('.'):
                    continue
                p = os.path.join(dir, f)
                if os.path.isdir(p):
                    rmtree(p)
                else:
                    os.unlink(p)

        new_dir = os.path.join(path, dir)
        msg(f'Copying files from "{new_dir}" to local "{dir}".')
        for f in os.listdir(new_dir):
            if f.startswith('.') or f.startswith('__pycache'):
                continue
            p = os.path.join(new_dir, f)
            if os.path.isdir(p):
                msg(f'--- directory "{p}"')
                copytree(p, os.path.join(dir, f))
            else:
                msg(f'--- file "{p}"')
                copy(p, dir)

    msg('Upgrading build script.')
    copy(os.path.join(path, 'build'), '.')

    msg('Copying upgrade.py (because, why not?).')
    copy(os.path.join(path, 'upgrade.py'), '.')

def upgrade(path):
    msg('Running: ./build clobber')
    if os.system('./build clobber') != 0:
        sys.exit(1)

    copy_files(path)

    msg('Upgraded to:')
    if os.system('./build version') != 0:
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: upgrade.py path-to-new-tools\n')
        sys.exit(1)

    upgrade(sys.argv[1])
