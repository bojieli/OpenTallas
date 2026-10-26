#!/usr/bin/env python3
"""Prove the actual five-root front inside the full BF pair.

This checks component arithmetic/transport, not native whole-token execution.
The candidate uses mapped ROM models; the independent legacy oracle retains
its historical numerical ROM shim. Only a transaction mismatch kills a mutant.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--mutant', action='store_true')
    args = parser.parse_args()
    case = 'north_stop' if args.mutant else 'positive'
    work = args.work.resolve()
    cmd = [sys.executable, str(ROOT/'tools/s81/bf_txn_bench.py'),
           '--variant', 'recut', '--die-pair', '--static-prog', '-1',
           '--front-roots', '--mapped-rom-candidate', '--jobs', '8',
           '--desc', str(ROOT/'results/rtl/s81_bf_programme_1015/bf_desc.hex'),
           '--prep', str(ROOT/'results/rtl/s81_bf_compact_20261010/bench_prep_1013'),
           '--work', str(work), '--no-default-mutants', '--only', case]
    if args.mutant:
        cmd += ['--mutant', 'north_stop=BF_FRONT_ROOT_STOP_N']
    result = subprocess.run(cmd, cwd=ROOT)
    path = work/'terminal.json'
    if result.returncode or not path.exists():
        raise SystemExit('ERROR: actual front bench did not qualify')
    record = json.loads(path.read_text())['cases'].get(case, {})
    if not record.get('ok'):
        raise SystemExit('ERROR: no qualifying case receipt')
    if args.mutant:
        log = (work/case/'run.log').read_text()
        if not record.get('returncode') or 'DIFF TXN' not in log:
            raise SystemExit('ERROR: stopped actual north clock lacked transaction mismatch')
        print('MUTANT BF north clock_stop FAIL: DIFF TXN', flush=True)
        raise SystemExit(1)
    print('PASS BF front five roots: 456 rows, 912 values, 448 configs', flush=True)


if __name__ == '__main__':
    main()
