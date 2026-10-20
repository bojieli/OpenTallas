#!/usr/bin/env python3
"""S81-BF6 2026-10-20: the actual five-root BF front built N32 (native census <= 32 loads) + SOQ (S81-RTAG go-aligned
label tables, SWD 160), inside the full BF die pair against the independent oracle (tools/s81/bf_txn_bench.py).

  --case n32soq        positive: must PASS (exact transactions, QP_CHECK / QT_CHECK on)
  --case mroh          mutant: one-hot read pointer copy of slice 0 stalls on pop (OT_BF6_MUT_ROH): must FAIL (DIFF TXN)
  --case mwsel         mutant: write slice 0 loses the BF16 slice-1 write select (OT_BF6_MUT_WSEL): must FAIL (DIFF TXN)
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = 'DSFD_BF_N32=1,DSFD_BF_SOQ=1,DSFD_BF_SOQ_SWD=160'
MUT = {'mroh': 'OT_BF6_MUT_ROH', 'mwsel': 'OT_BF6_MUT_WSEL'}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--case', choices=['n32soq'] + sorted(MUT), required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    cmd = [sys.executable, str(ROOT/'tools/s81/bf_txn_bench.py'),
           '--variant', 'recut', '--die-pair', '--static-prog', '-1',
           '--front-roots', '--mapped-rom-candidate', '--jobs', '8',
           '--desc', str(ROOT/'results/rtl/s81_bf_programme_1015/bf_desc.hex'),
           '--prep', str(ROOT/'results/rtl/s81_bf_compact_20261010/bench_prep_1013'),
           '--work', str(work), '--no-default-mutants', '--only', args.case]
    if args.case == 'n32soq':
        cmd += ['--positive-define', f'n32soq={BASE}']
    else:
        cmd += ['--mutant', f'{args.case}={BASE},{MUT[args.case]}']
    result = subprocess.run(cmd, cwd=ROOT)
    path = work/'terminal.json'
    if not path.exists():
        raise SystemExit('ERROR: N32 front bench did not run')
    record = json.loads(path.read_text())['cases'].get(args.case, {})
    if args.case == 'n32soq':
        if result.returncode or not record.get('ok'):
            raise SystemExit('ERROR: N32 front positive did not qualify')
        print('PASS BF6 front N32+SOQ five roots: exact transactions', flush=True)
        return
    if not record.get('ok'):
        raise SystemExit('ERROR: N32 mutant did not produce a failing case receipt')
    log = (work/args.case/'run.log').read_text()
    if not record.get('returncode') and 'DIFF TXN' not in log:
        raise SystemExit('ERROR: N32 mutant lacked a transaction mismatch')
    print(f'MUTANT BF6 {args.case} FAIL: DIFF TXN', flush=True)
    raise SystemExit(1)


if __name__ == '__main__':
    main()
