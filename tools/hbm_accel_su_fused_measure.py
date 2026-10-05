#!/usr/bin/env python3
"""Measure a cached actual1M row through the new fused endpoint, remote only.

No prep, golden computation, inference, or asynchronous output time addition.
This measures the component reservation lease; the program/VM parent is a
separate required integration gate and is not qualified by this record alone.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import dsrom_su_norm as S


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kind',choices=('hc','q','kv'),required=True)
    ap.add_argument('--cached-root',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--fp',choices=('dpi','rtl'),default='dpi')
    a=ap.parse_args()
    meta=json.loads((a.cached_root/'cases.json').read_text())
    cases=[r for r in meta['cases'] if r['kind']==a.kind and r['source'].startswith('golden 1M')]
    if not cases: raise ValueError('no actual1M saved rows')
    params=dict(S.VARIANTS[a.kind],RW=9,BW=9)
    src=[S.ROOT/s for s in S.COMMON+S.FP_SRC[a.fp]]+[
        S.RTL,S.ROOT/'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',
        S.ROOT/'rtl/hbm_accel/su/ot_hbm_accel_su_fused_stream.sv',
        S.ROOT/'rtl/test/tb_hbm_accel_su_fused_norm.sv']
    a.work.mkdir(parents=True,exist_ok=True)
    obj=a.work.resolve()/'obj'
    cmd=[S.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH',
         '--top-module','tb_hbm_accel_su_fused_norm','-Mdir',str(obj),'-j','16',
         '--unroll-count','4','-fno-dfg',*[f'-G{k}={v}' for k,v in params.items()],
         *map(str,src),'-CFLAGS','-O1']
    pin=dict(params=params,LM=6,LA=5,BCAST=7,RET=8,clock_target_hz=1200000000,
        clock_actual_half_period_ns=.416667,SS60_FF25_qualified=False,
        source_sha256={str(s.relative_to(S.ROOT)):sha(s) for s in src},
        cases_meta_sha256=sha(a.cached_root/'cases.json'),build_command=cmd,
        compared_source='cached actual1M expected only',fp_backend=a.fp,
        scope='component; whole-command reservation pregranted; not actual VM parent qualification')
    (a.work/'source.json').write_text(json.dumps(pin,indent=2)+'\n')
    with (a.work/'build.log').open('w') as log:
        r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    (a.work/'build.rc').write_text(str(r.returncode)+'\n')
    if r.returncode: return r.returncode
    exe=obj/'Vtb_hbm_accel_su_fused_norm'
    rows=[]
    for row in cases:
        case=a.cached_root/'cases'/row['case']
        out=a.work/row['case'];out.mkdir()
        hashes={p.name:sha(p) for p in sorted(case.glob('*.mem'))}
        r=subprocess.run([str(exe)],cwd=case,capture_output=True,text=True)
        (out/'run.log').write_text(r.stdout+r.stderr)
        (out/'run.rc').write_text(str(r.returncode)+'\n')
        end=[s for s in r.stdout.splitlines() if s.startswith('FUSED_END ')]
        metrics={k:int(v) for k,v in (x.split('=') for x in end[-1].split()[1:])} if end else None
        ok=r.returncode==0 and 'PASS' in r.stdout and metrics is not None
        rows.append(dict(case=row,pass_exact=ok,metrics=metrics,cached_sha256=hashes,
                         events=[s for s in r.stdout.splitlines() if s.startswith('FUSED_EVENT ')]))
        (a.work/'result.json').write_text(json.dumps(dict(pin=pin,binary_sha256=sha(exe),rows=rows,
            terminal=False,adopted=False),indent=2)+'\n')
        if not ok: return 1
    (a.work/'result.json').write_text(json.dumps(dict(pin=pin,binary_sha256=sha(exe),rows=rows,
        terminal=True,pass_exact=True,adopted=False),indent=2)+'\n')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
