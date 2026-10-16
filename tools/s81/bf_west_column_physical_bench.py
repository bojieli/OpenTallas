#!/usr/bin/env python3
"""Actual W-source column in the full BF pair; compiler fixture is main DELTA0."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args()
    case='west_data' if a.mutant else 'positive';work=a.work.resolve()
    cmd=[sys.executable,str(ROOT/'tools/s81/bf_txn_bench.py'),'--variant','recut','--die-pair',
         '--static-prog','0','--column-roots','--column-west-roots','--mapped-rom-candidate',
         '--desc',str(ROOT/'results/rtl/s81_bf_programme_1015/bf_desc.hex'),
         '--prep',str(ROOT/'results/rtl/s81_bf_compact_20261010/bench_prep_1013'),
         '--work',str(work),'--jobs','8','--no-default-mutants','--only',case]
    if a.mutant:cmd+=['--mutant','west_data=BF_COL_W_MUTANT_DATA']
    result=subprocess.run(cmd,cwd=ROOT)
    if result.returncode or not (work/'terminal.json').exists():raise SystemExit('ERROR: W source bench failed')
    record=json.loads((work/'terminal.json').read_text())['cases'].get(case,{})
    if not record.get('ok'):raise SystemExit('ERROR: W source case did not qualify')
    if a.mutant:
        if not record.get('returncode') or 'DIFF TXN' not in (work/case/'run.log').read_text():raise SystemExit('ERROR: wrong W data did not cause actual transaction mismatch')
        print('MUTANT BF W column data FAIL: DIFF TXN',flush=True);raise SystemExit(1)
    print('PASS BF W column actual pair:456 rows,912 values,448 configs',flush=True)


if __name__=='__main__':main()
