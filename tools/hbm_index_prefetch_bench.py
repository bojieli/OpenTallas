#!/usr/bin/env python3
"""Remote minimum protected descriptor/receipt mechanism; retain every case."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
     'rtl/hbm_accel/service/ot_hbm_index_prefetch.sv','rtl/test/hbm_accel/tb_hbm_index_prefetch.sv']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args()
    args.work.mkdir(parents=True,exist_ok=False)
    record=dict(schema='opentallas.hbm_index_prefetch_gate.v1',
        source_commit=os.environ['PINNED_SOURCE_COMMIT'],
        inputs_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
            for p in SRC+['tools/hbm_index_prefetch_bench.py','tools/hbm_index_prefetch_model.py']},
        scope='finite two-clock mailbox; stub delays admission, actual service join remains separately required',
        cases=[],verdict='INCOMPLETE',adopted=False)
    out=args.work/'record.json'
    def save():out.write_text(json.dumps(record,indent=2)+'\n')
    save()
    for mutation in range(11):
        case=args.work/f'mut{mutation}'
        case.mkdir()
        exe=case/'gate.vvp'
        with (case/'build.log').open('w') as log:
            build=subprocess.run(['/usr/bin/time','-v','-o',str(case/'build.resources'),
                'iverilog','-g2012','-I'+str(ROOT/'rtl/common'),'-s','tb_hbm_index_prefetch',
                f'-Ptb_hbm_index_prefetch.MUT={mutation}','-o',str(exe)]+
                [str(ROOT/p) for p in SRC if p.endswith('.sv')],stdout=log,stderr=subprocess.STDOUT)
        row=dict(mutation=mutation,build_exit=build.returncode)
        if build.returncode==0:
            with (case/'run.log').open('w') as log:
                run=subprocess.run(['/usr/bin/time','-v','-o',str(case/'run.resources'),'vvp',str(exe)],
                    stdout=log,stderr=subprocess.STDOUT)
            raw=(case/'run.log').read_text()
            row.update(run_exit=run.returncode,passed=run.returncode==0 and
                'PASS_HBM_INDEX_PREFETCH' in raw,
                raw_sha256=hashlib.sha256(raw.encode()).hexdigest())
        else:row['passed']=False
        record['cases'].append(row)
        save()
    record['verdict']='PASS' if all(row['passed'] for row in record['cases']) else 'FAIL'
    save()
    print(record['verdict'],flush=True)
    return 0 if record['verdict']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
