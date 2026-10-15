#!/usr/bin/env python3
"""Drop-in Verilator front end that refuses models with the in-place NBA-loop miscompile.

Runs the real Verilator with the caller's argv unchanged. When it succeeds and generated a C++ model
(any mode except --lint-only / -E / --xml-only / --json-only), tools/verilator_nba_guard.py scans the
model directory (-Mdir/--Mdir, including options from -f files; default obj_dir). A model that applies
non-blocking loop writes in place exits 86 with VERILATOR_NBA_GUARD FAIL: any PASS/FAIL from it is invalid.

Real binary: $OT_VERILATOR_REAL, else bin/verilator.real next to this file's install, else the fleet
5.050 install. tools/fleet/install_verilator_nba_guard.sh installs this as bin/verilator on a host so
every bench, gate and closure job uses it (absolute-path callers included).
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verilator_nba_guard as G  # noqa: E402

NO_MODEL = {'--lint-only', '-lint-only', '-E', '--xml-only', '-xml-only', '--json-only', '-json-only',
            '--version', '-V', '--help', '-help', '--getenv', '-getenv'}
GUARD_EXIT = 86


def real_verilator() -> str:
    env = os.environ.get('OT_VERILATOR_REAL')
    if env:
        return env
    me = Path(sys.argv[0])
    sibling = me.with_name(me.name + '.real')
    if sibling.exists():
        return str(sibling)
    return str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator.real')


def expand(argv, cwd: Path, depth=0):
    """argv with -f/-F option files expanded (Verilator semantics, enough for -Mdir and mode flags)."""
    out = []
    it = iter(argv)
    for a in it:
        if a in ('-f', '-F') and depth < 8:
            f = next(it, None)
            if f is None:
                break
            p = (cwd / f) if not os.path.isabs(f) else Path(f)
            try:
                words = []
                for line in p.read_text(errors='replace').splitlines():
                    line = line.split('//')[0]
                    words += shlex.split(line, comments=True)
                out += expand(words, p.parent if a == '-F' else cwd, depth + 1)
            except OSError:
                pass
        else:
            out.append(a)
    return out


def model_dir(argv, cwd: Path):
    args = expand(argv, cwd)
    if any(a in NO_MODEL for a in args):
        return None
    mdir = 'obj_dir'
    for k, a in enumerate(args):
        if a in ('-Mdir', '--Mdir') and k + 1 < len(args):
            mdir = args[k + 1]
        elif a.startswith(('-Mdir=', '--Mdir=')):
            mdir = a.split('=', 1)[1]
    p = Path(mdir)
    return p if p.is_absolute() else cwd / p


def main(argv) -> int:
    rc = subprocess.call([real_verilator(), *argv])
    if rc != 0:
        return rc
    d = model_dir(argv, Path.cwd())
    if d is None or not d.is_dir():
        return rc
    try:
        result = G.scan(str(d))
    except FileNotFoundError:
        return rc
    if result['findings']:
        print(G.summarize(result), file=sys.stderr)
        print('VERILATOR_NBA_GUARD FAIL: Verilator applied non-blocking loop writes in place (non-unrolled NBA '
              'loop miscompile). Raise --unroll-count above the largest NBA loop trip count or rewrite the loop. '
              'Simulation results from this model are invalid.', file=sys.stderr)
        return GUARD_EXIT
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
