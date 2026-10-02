"""Future native child entry. Admission and inventory are bound by its guard.

No cap changes, retries, or compiler execution during import/test. Opaque shell
payloads require source review; this checks explicit argv and inherited limits.
"""
import os
import resource
import sys
from native_build_completion_policy_r2 import validate_native_argv


def prepare_argv(argv, limits=None):
    if not argv or argv[0] != '--' or len(argv) < 2:
        raise ValueError('explicit -- native command required')
    actual = limits if limits is not None else {
        name: resource.getrlimit(which) for name, which in
        [('FSIZE', resource.RLIMIT_FSIZE), ('AS', resource.RLIMIT_AS),
         ('CPU', resource.RLIMIT_CPU)]}
    for name in ['FSIZE', 'AS', 'CPU']:
        if tuple(actual.get(name, ())) != (-1, -1):
            raise ValueError('inherited native ' + name + ' limit must be unlimited')
    validate_native_argv(argv[1:])
    return argv[1:]


if __name__ == '__main__':
    try:
        command = prepare_argv(sys.argv[1:])
    except ValueError as error:
        raise SystemExit(str(error))
    os.execvp(command[0], command)
