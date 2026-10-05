"""Proposed native-relink container entry. Requires separate reviewed GO/runner."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys

AS_BYTES = 4 << 30
FILE_BYTES = 2 << 30
GXX_SHA = '2360901d864cf10bfd6296e261cb2c14053552a80377761ab07146ec9ec9a2c0'


def enforce_limits():
    for which, limit in ((resource.RLIMIT_AS, AS_BYTES), (resource.RLIMIT_FSIZE, FILE_BYTES)):
        _, hard = resource.getrlimit(which)
        if hard != resource.RLIM_INFINITY and hard < limit:
            raise ValueError('existing hard cap is lower; no cap relaxation')
        resource.setrlimit(which, (limit, limit))
        if resource.getrlimit(which) != (limit, limit):
            raise ValueError('effective resource cap mismatch')
    return dict(RLIMIT_AS=list(resource.getrlimit(resource.RLIMIT_AS)),
                RLIMIT_FSIZE=list(resource.getrlimit(resource.RLIMIT_FSIZE)))


def check_cgroup(values, affinity):
    if values.get('memory.max') != str(AS_BYTES) or values.get('memory.swap.max') != '0':
        raise ValueError('aggregate memory/swap cap')
    cpu = values.get('cpu.max', '').split()
    if len(cpu) != 2 or not all(x.isdecimal() for x in cpu) or int(cpu[1]) <= 0 or int(cpu[0]) != 2 * int(cpu[1]):
        raise ValueError('aggregate twoCPU quota')
    if values.get('pids.max') != '64' or len(affinity) != 2:
        raise ValueError('pids/cpuset cap')


def main(argv):
    if not argv or argv[0] != 'g++' or argv[-2:] != ['-o', '/output/v41_existing_port_trace']:
        raise ValueError('native compiler entry only')
    caps = enforce_limits()  # Before any tool subprocess or compiler exec.
    cg = Path('/sys/fs/cgroup')
    values = {x: (cg / x).read_text().strip() for x in ('memory.max', 'memory.swap.max', 'cpu.max', 'pids.max')}
    check_cgroup(values, os.sched_getaffinity(0))
    compiler = Path(shutil.which('g++')).resolve()
    digest = hashlib.sha256(compiler.read_bytes()).hexdigest()
    if digest != GXX_SHA:
        raise ValueError('exact retained GCC driver prerequisite')
    print('W17_RELINK_CAPS ' + json.dumps(dict(**caps, cgroup=values,
          compiler_path=str(compiler), compiler_sha256=digest)), flush=True)
    subprocess.run([str(compiler), '--version'], check=True)
    os.execv(str(compiler), argv)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
