"""
Import one or more modules and show their non-stdlib dependencies.

Given one or more args, each of which should be a top-level
or dotted module name that can be imported (based on the
invoking Python and the PYTHONPATH), this script records the
modules that have been loaded before importing all the named
modules (`sys.modules`), and then imports all the modules and
reports any new non-stdlib modules that were imported.

The use case I wanted this for was to know which dependencies
I had to install for a third-party script that I had previously
installed into a tmp virtualenv that was used for other things.
For example, I have a virtualenv that has deps for foo.py that
I manually pip-installed also contains deps for other miscellaneous
scripts or packages, so `pip list` isn't helpful to determine
what dependencies were needed by `foo.py`.
"""

import importlib
import imp
import os
import sys
import traceback

DEBUG = False
BASEDIR = os.path.dirname(traceback.__file__)
SUBDIRS = ('lib-dynload',)  # TODO: others for python3 and distro-specific

# the minimal sys.path tuple to be used to ensure that
# non-stdlib resources aren't importable and can thus
# be detected as non-stdlib resources.
DEFAULT_SYS_PATHS = tuple(filter(os.path.isdir, [BASEDIR] + [
    os.path.join(BASEDIR, subdir)
    for subdir in SUBDIRS
]))
if DEBUG:
    print('Using SYS_PATHS: {}'.format(SYS_PATHS))


def stdlib(modname, sys_path=DEFAULT_SYS_PATHS):
    """
    Answer whether top-level module name is a stdlib module.

    Raises `ValueError` if modname is a dotted name.
    """
    if '.' in modname:
        msg = 'modname "%s" should be a top-level (non-dotted) name'
        raise ValueError(msg % (modname,))

    # record original so we can restore it later
    sys_path_orig = sys.path

    # set it to the temporary minimal list of paths
    # that will prevent non-stdlib modules from being found
    sys.path = list(sys_path)

    # if it's importable now, it's a stdlib module
    try:
        imp.find_module(modname)
    except ImportError:
        return False
    else:
        return True
    finally:
        sys.path = sys_path_orig


def compare(initial, later, ignore=()):
    """
    Answer module names in `later` seq that aren't in `initial` seq.

    The added module names will be returned as a list in sorted
    order except for all those that begin with an underscore
    coming after all those that do not. The `ignore` tuple
    is empty by default but may contain names to be ignored.
    """
    initial = set(initial)
    ignore = set(ignore)
    prefixed = []
    unprefixed = []
    for elem in later:
        if elem in initial or elem in ignore:
            continue
        (prefixed if elem.startswith('_') else unprefixed).append(elem)
    prefixed.sort(key=lambda s: s.lower())
    unprefixed.sort(key=lambda s: s.lower())
    return unprefixed + prefixed


def run(args=None):
    if args is None:
        args = list(sys.argv[1:])

    before = list(sys.modules)  # initial modules before imports
    for modname in args:
        try:
            importlib.import_module(modname)
        except ImportError:
            print('ImportError for "{}": skipping'.format(modname))
        except (KeyError, ValueError):
            print('Cannot import invalid name "{}": skipping'.format(modname))

    # get diff of current mods and the initial ones;
    # TODO: not sure why this '__mp_main__' module is so named,
    # but ignoring it for now
    newmods = compare(before, sys.modules, ignore=('__mp_main__',))

    # if none added, we're done
    if not newmods:
        return

    # otherwise, we check each all top-level (non-dotted)
    # module names in sys.modules and report the ones
    # that are not stdlib modules
    non_stdlib = []

    # keep track of top-level names we've seen to avoid
    # dupes and unnecessary processing of sub-modules
    # for which we've already seen the parent module
    seen = set()

    for modname in newmods:
        # we only need to check top-level names, and
        # imp.find_module doesn't support dotted names either,
        # so just use the first part of a dotted name
        basemodname = modname.partition('.')[0]

        if basemodname not in seen:
            if not stdlib(basemodname):
                non_stdlib.append(basemodname)
            seen.add(basemodname)

    for modname in non_stdlib:
        print(modname)


if __name__ == '__main__' and not os.environ.get('_', '').endswith(
        ('/ipython', '/ipython2', '/ipython3')):
    run()
