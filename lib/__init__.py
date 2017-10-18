'''
Helper functions
'''

import importlib.util
import sys

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
