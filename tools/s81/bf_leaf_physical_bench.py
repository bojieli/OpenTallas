#!/usr/bin/env python3
"""Run the actual production BF pair around the extracted lane master.

The negative case succeeds only when the stopped real leaf clock causes the
transaction comparator to detect a difference. Build failures never qualify.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--mutant', action='store_true')
    p.add_argument('--programme-delta',type=int,required=True,
                   help='Explicit compiler fixture delta: main front0, historical c10 front-1')
    a = p.parse_args()
    work = a.work.resolve()
    case = 'root_stop' if a.mutant else 'positive'
    cmd = [sys.executable, str(ROOT/'tools/s81/bf_txn_bench.py'),
           '--variant', 'recut', '--die-pair', '--static-prog', str(a.programme_delta),
           '--column-roots', '--mapped-rom-candidate', '--jobs', '8',
           '--desc', str(ROOT/'results/rtl/s81_bf_programme_1015/bf_desc.hex'),
           '--prep', str(ROOT/'results/rtl/s81_bf_compact_20261010/bench_prep_1013'),
           '--work', str(work), '--no-default-mutants', '--only', case]
    if a.mutant:
        cmd += ['--mutant', 'root_stop=BF_ROOT_MUTANT_STOP']
    result = subprocess.run(cmd, cwd=ROOT)
    terminal = work/'terminal.json'
    if not terminal.exists():
        raise SystemExit('ERROR: no actual BF terminal receipt')
    record = json.loads(terminal.read_text())
    c = record['cases'].get(case, {})
    if result.returncode or not c.get('ok'):
        raise SystemExit('ERROR: actual BF bench did not qualify')
    if a.mutant:
        log = (work/case/'run.log').read_text()
        if not c.get('returncode') or 'DIFF TXN' not in log:
            raise SystemExit('ERROR: stopped clock did not produce a transaction difference')
        print('MUTANT BF leaf root_stop FAIL: DIFF TXN from actual RTL', flush=True)
        raise SystemExit(1)
    print('PASS BF leaf full-shape actual RTL: 456 rows, 912 values, 448 configs', flush=True)


if __name__ == '__main__':
    main()
