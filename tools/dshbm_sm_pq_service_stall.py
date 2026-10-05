#!/usr/bin/env python3
"""Exact production PQ/result-select under finite HBM request backpressure.

Uses completed sequence payloads and expected outputs; generates no numerics.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from dshbm_sm_pq_production_seq import P
from dshbm_sm_xmap_seq import parse_output

ROOT=Path(__file__).resolve().parents[1]
TB='tb_hbm_accel_sm_pq_service_stall'
SRC=[s for s in P.SRC if not s.startswith('rtl/test/')]+['rtl/test/'+TB+'.sv']

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('step',choices=['build','run'])
    a.add_argument('--work',type=Path,required=True)
    a.add_argument('--fixture',type=Path)
    a.add_argument('--active',type=int,default=1,choices=[1,6])
    a.add_argument('--corrupt-return',action='store_true')
    args=a.parse_args();w=args.work.resolve();w.mkdir(parents=True,exist_ok=True)
    exe=w/'build'/('V'+TB)
    if args.step=='build':
        if exe.exists():raise SystemExit('Existing executable: run it; do not rebuild.')
        cmd=['verilator','--binary','--timing','-O2','-Wno-fatal','--top-module',TB,'--Mdir',str(w/'build'),'-j','16','-GNC=8','-GXDEPTH=128','-GRMAX=256','-GLEV=4',f'-GXB={2 if args.active==1 else 10}',*[str(ROOT/s) for s in SRC]]
        with (w/'build.log').open('w') as f:rc=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
        (w/'build.exit').write_text(str(rc)+'\n');return rc
    fixture=args.fixture.resolve()
    raw=[int(x,16) for x in (fixture/'seq.hex').read_text().split()]
    if len(raw)%10:raise ValueError('require existing ten-field sequence')
    ops=[raw[i:i+10] for i in range(0,len(raw),10)]
    expected,_,_=parse_output(fixture/'out.txt')
    if len(expected)!=sum(o[0] for o in ops):raise ValueError('original results incomplete')
    case=w/('corrupt' if args.corrupt_return else 'exact');case.mkdir(exist_ok=False)
    for n in ['seq.hex','lines.hex','x.hex']:shutil.copyfile(fixture/n,case/n)
    cmd=[str(exe),f'+DIR={case}',f'+NOPS={len(ops)}']
    if args.corrupt_return:cmd.append('+CORRUPT_RETURN')
    with (case/'runtime.log').open('w') as f:rc=subprocess.run(cmd,cwd=case,stdout=f,stderr=subprocess.STDOUT).returncode
    (case/'runtime.exit').write_text(str(rc)+'\n')
    got,meta,cycles=parse_output(case/'out.txt')
    mask=(1<<(32*args.active))-1
    bad=[list(k) for k,v in expected.items() if k not in got or (got[k]&mask)!=(v&mask)]
    extra=[list(k) for k in got if k not in expected]
    log=(case/'runtime.log').read_text();progress=re.search(r'SERVICE_STALLS (\d+) ACCEPTED_REQUESTS (\d+) CORRUPTED (\d+)',log)
    metadata_ok=len(meta)==len(ops) and all(meta.get(i,{}).get('fault')==0 and meta[i]['results']==o[0] and meta[i]['consumed']==o[4] for i,o in enumerate(ops))
    exact=rc==0 and not bad and not extra and len(got)==len(expected) and metadata_ok and progress is not None and int(progress[1])>0 and int(progress[2])==sum(o[4] for o in ops)
    result=dict(status='pass' if exact else 'fail',runtime_exit=rc,total_cycles=cycles,expected_rows=len(expected),actual_rows=len(got),mismatches=bad,extra=extra,metadata_ok=metadata_ok,active_columns=args.active,request_stall_edges=int(progress[1]) if progress else None,accepted_requests=int(progress[2]) if progress else None,corrupted_returns=int(progress[3]) if progress else None,ops=meta)
    (case/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['status','total_cycles','expected_rows','actual_rows','request_stall_edges','accepted_requests','corrupted_returns']}));return 0 if exact else 1

if __name__=='__main__':raise SystemExit(main())
