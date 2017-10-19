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

def maybe_file(path):
    '''
    Intended to be used when creating a list of files, this function
    determines whether a file exists, returning the file name in a list if
    so, and returning an empty list if not.

    Parameters:

    path: the path to test
    '''
    if os.path.exists(path):
        return [path]
    else:
        return []

def msg(message):
    '''
    Display a message on standard error. Automatically adds a newline.

    Parameters:

    message: the message to display
    '''
    sys.stderr.write(f"{message}\n")

def abort(message):
    '''
    Aborts with a message.

    Parameters:

    message: the message
    '''
    msg(message)
    raise Exception(message)

def sh(command):
    '''
    Runs a shell command, exiting if the command fails.

    Parameters:

    command: the command to run
    '''
    msg(command)
    if os.system(command) != 0:
        sys.exit(1)

def load_metadata(metadata_file):
    '''
    Loads a YAML metadata file, returning the loaded dictionary.

    Parameters:

    metadata_file; path to the file to load
    '''
    with open(metadata_file) as f:
        s = ''.join([s for s in f if not s.startswith('---')])
        metadata = yaml.load(s)
    return metadata

def validate_metadata(dict_like):
    '''
    Validates metadata that's been loaded into a dictionary-like object.
    Throws an exception if a required key is missing.
    '''
    for key in ('title', 'author', 'copyright.owner', 'copyright.year',
                'publisher', 'language', 'genre'):
        # Drill through composite keys.
        keys = key.split('.') if '.' in key else [key]
        d = dict_like
        v = None
        for k in keys:
            v = d.get(k)
            d = v if v else {}

        if not v:
            abort(f'Missing required "{key}" in metadata.')

def _valid_dir(directory):
    return (directory not in ('.', '..')) and (len(directory) > 0)

@contextmanager
def ensure_dir(directory
               , autoremove=False):
    '''
    Run a block in the context of a directory that is created if it doesn't
    exist.

    Parameters:

    dir:   the directory
    remove: if True, remove the directory when the "with" block finishes.
    '''
    try:
        if _valid_dir(directory):
            os.makedirs(directory, exist_ok=True)
        yield
    finally:
        if autoremove:
            if os.path.exists(directory):
                rmtree(directory)

@contextmanager
def target_dir_for(file, autoremove=False):
    '''
    Context manager that ensures that the parent directory of a file exists.

    Parameters:

    file:   the file
    remove: if True, remove the directory when the "with" block finishes.
    '''
    directory = os.path.dirname(file)
    try:
        if _valid_dir(directory):
            os.makedirs(directory, exist_ok=True)
        yield
    finally:
        if autoremove:
            if os.path.exists(directory):
                rmtree(directory)

@contextmanager
def preprocess_markdown(tmp_dir, files, divs=False):
    '''
    Content manager that preprocesses the Markdown files, adding some content
    and producing new, individual files.

    Parameters:

    tmp_dir - the temporary directory for the preprocessed files
    files   - the list of files to process
    divs    - True to generate a <div> with a file-based "id" attribute and
              'class="book_section"' around each Markdown file. Only really 
              useful for HTML.

    Yields the paths to the generated files
    '''
    file_without_dashes = re.compile(r'^[^a-z]*([a-z]+).*$')

    directory = os.path.join(tmp_dir, 'preprocessed')
    from_to = [(f, os.path.join(directory, os.path.basename(f))) for f in files]
    generated = [t for f, t in from_to]
    with ensure_dir(directory, autoremove=False):
        for f, temp in from_to:
            with open(temp, "w") as t:
                basefile, ext = os.path.splitext(os.path.basename(f))
                m = file_without_dashes.match(basefile)
                if m:
                    cls = m.group(1)
                else:
                    cls = basefile

                # Added classes to each section. Can be used in CSS.
                if divs and ext == ".md":
                    t.write(f'<div class="book_section" id="section_{cls}">\n')
                with open(f) as input:
                    for line in input.readlines():
                        t.write(f"{line.rstrip()}\n")
                # Force a newline after each file.
                t.write("\n")
                if divs and ext == ".md":
                    t.write('</div>\n')
                t.close()
        yield generated

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

