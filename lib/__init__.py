'''
Helper functions
'''

import importlib.util
import sys
import os
from shutil import *
import yaml
from contextlib import contextmanager
import re

def import_from_file(path, module_name):
    '''
    Import a file as a module.

    Parameters:
    - path: the path to the Python file
    - module_name: the name to assign the module_from_spec

    Returns: the module object
    '''
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules[module_name] = mod
    return mod

def maybe_file(f):
    if os.path.exists(f):
        return [f]
    else:
        return []

def msg(s):
    sys.stderr.write(f"{s}\n")

def abort(message):
    msg(message)
    raise Exception(message)

def sh(command):
    msg(command)
    if os.system(command) != 0:
        sys.exit(1)

def load_metadata(metadata_file):
    with open(metadata_file) as f:
        s = ''.join([s for s in f if not s.startswith('---')])
        metadata = yaml.load(s)
    return metadata

def has_references(metadata, references_path):
    return ('references' in metadata) and os.path.exists(references_path)

def validate_metadata(dict_like):
    for key in ('title', 'author', 'copyright.owner', 'copyright.year',
                'publisher', 'language'):
        # Drill through composite keys.
        keys = key.split('.') if '.' in key else [key]
        d = dict_like
        v = None
        for k in keys:
            v = d.get(k)
            d = v if v else {}

        if not v:
            abort(f'Missing required "{key}" in metadata.')

@contextmanager
def target_dir_for(file):
    dir = os.path.dirname(file)
    if not (dir == '.' or len(dir) == 0):
        os.makedirs(dir, exist_ok=True)
    yield

@contextmanager
def preprocess_markdown(*files):
    msg(f"Preprocessing: {files}")
    temp = '_temp.md'
    file_without_dashes = re.compile(r'^[^a-z]*([a-z]+).*$')

    try:
        with open(temp, "w") as t:
            for f in files:
                basefile, ext = os.path.splitext(os.path.basename(f))
                m = file_without_dashes.match(basefile)
                if m:
                    cls = m.group(1)
                else:
                    cls = basefile

                # Added classes to each section. Can be used in CSS.
                if ext is ".md":
                    t.write(f'<div class="book_section section_{cls}">\n')
                with open(f) as input:
                    for line in input.readlines():
                        t.write(f"{line.rstrip()}\n")
                # Force a newline after each file.
                t.write("\n")
                if ext is ".md":
                    t.write('</div>\n')

        yield temp
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def rm_rf(paths, silent=False):
    '''
    Recursively remove one or more files.

    paths - a list or tuple of paths, or a string of one path
    silent - whether or not to make noise about what's going on
    '''
    def do_rm(path):
        if os.path.isdir(path):
            if not silent:
                msg(f'rm -rf {path}')
            rmtree(path)
        else:
            rm_f(path)
    
    if isinstance(paths, list) or isinstance(paths, tuple):
        for f in paths:
            do_rm(f)
    elif isinstance(paths, str):
        do_rm(paths)
    else:
        from doit import TaskError
        raise TaskError('rm_f() expects a list, a tuple or a string.')


def rm_f(paths, silent=False):
    '''
    Remove one or more files.

    paths - a list or tuple of paths, or a string of one path
    silent - whether or not to make noise about what's going on
    '''
    def do_rm(path):
        if not silent:
            msg(f"rm -f {path}")
        if os.path.exists(path):
            os.unlink(path)

    if isinstance(paths, list) or isinstance(paths, tuple):
        for f in paths:
            do_rm(f)
    elif isinstance(paths, str):
        do_rm(paths)
    else:
        from doit import TaskError
        raise TaskError('rm_f() expects a list, a tuple or a string.')

