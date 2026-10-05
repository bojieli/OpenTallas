#!/usr/bin/env python3
"""Opt2 paired-SM measurement from completed opt1 fixtures, no golden generation.

The original weight and x payload files are byte copies. Only the seven actual
W2 command descriptors are paired; all other operations and dependency flags
remain the same. Compare restored original op/row results with the exact archive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from dshbm_sm_xmap_seq import SRC as BASE_SRC, parse_output

ROOT=Path(__file__).resolve().parents[1]
TB='tb_hbm_accel_sm_w2_pair_seq'
OWN='rtl/hbm_accel/sm/wavepack_20261005/'
SRC=[s for s in BASE_SRC if not s.startswith('rtl/test/')]+[
    OWN+'ot_hbm_accel_w2_address_hook.sv',OWN+'ot_hbm_accel_w2_pair_request_join.sv',
    OWN+'ot_hbm_accel_w2_result_join.sv',OWN+'ot_hbm_accel_w2_caller.sv',
    'rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_issue_pq.sv',
    'rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_sm_pq.sv',
    'rtl/test/tb_hbm_accel_sm_w2_pair_seq.sv']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(fixture,baseline_json,work):
    baseline=json.loads(baseline_json.read_text())
    if baseline['status']!='pass' or baseline['mismatching_ops']:
        raise ValueError('require completed exact original PQ result')
    raw=[int(x,16) for x in (fixture/'seq.hex').read_text().split()]
    if len(raw)%10:
        raise ValueError('original ten-field descriptors required')
    ops=[raw[i:i+10] for i in range(0,len(raw),10)]
    starts=[];total=0
    for o in ops:
        starts.append(total);total+=o[4]
    w2=[o['op'] for o in baseline['ops'] if o['tag'].endswith(' w2')]
    if len(w2)!=7 or w2!=list(range(w2[0],w2[0]+7)):
        raise ValueError('literal seven-op W2 run not found')
    pairs={w2[i]:w2[i+1] for i in (0,2,4)}
    desc=[];labels=[];i=0
    while i<len(ops):
        a=ops[i]
        if i in pairs:
            j=pairs[i];b=ops[j]
            for o in (a,b):
                if o[:6]!=[2,8,2,2,32,1] or o[6]!=1 or o[7]!=16:
                    raise ValueError('actual paired W2 shape differs')
            if b[8] or (a[9]-b[9])%128<16 or (b[9]-a[9])%128<16:
                raise ValueError('dependent/unbound overlapping paired x spans')
            fields=a.copy();fields[0]=4;fields[4]=64
            fields += [1,starts[j],b[9],b[7],i,j]
            labels.append([i,j]);i+=2
        else:
            fields=a+[0,0,0,0,i,i]
            labels.append([i]);i+=1
        desc.append(fields)
    expected,oldmeta,_=parse_output(fixture/'out.txt')
    if len(expected)!=sum(o[0] for o in ops):
        raise ValueError('incomplete original exact outputs')
    work.mkdir(parents=True,exist_ok=False)
    (work/'seq.hex').write_text('\n'.join(f'{x:08x}' for o in desc for x in o)+'\n')
    for n in ('lines.hex','x.hex','out.txt'):
        shutil.copy2(fixture/n,work/('reference_out.txt' if n=='out.txt' else n))
    groups=[k for k,g in enumerate(labels) if g[0] in w2]
    receipt=dict(source_fixture=str(fixture),source_result=str(baseline_json),
                 source_sha256={n:sha(fixture/n) for n in ('seq.hex','lines.hex','x.hex','out.txt')},
                 baseline_result_sha256=sha(baseline_json),logical_op_labels=labels,
                 composite_descriptors=desc,w2_groups=groups,original_w2=w2,
                 baseline_w2_cycles=oldmeta[w2[-1]]['t_done']-oldmeta[w2[0]]['t_load0'],
                 original_shape_count=len(ops),source_arithmetic_generated=False)
    (work/'fixture.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def build(work):
    b=work/'build';b.mkdir(parents=True,exist_ok=True)
    exe=b/('V'+TB)
    paths=[ROOT/s for s in SRC]
    source_pin={s:sha(ROOT/s) for s in SRC}
    prod=ROOT/'rtl/hbm_accel/sm/pq_production_20261005/ot_hbm_accel_sm_pq.sv'
    if 'PACK_W2' not in prod.read_text():
        raise ValueError('Euclid owned before-s1 PACK_W2 hook missing; do not launch partial build')
    if exe.exists():
        if json.loads((b/'source_pin.json').read_text())!=source_pin:
            raise ValueError('existing build source differs; preserve it')
        return exe
    cmd=['verilator','--binary','--timing','-O2','-Wno-fatal','--top-module',TB,'--Mdir',str(b),
         '-j','16','-GNC=8','-GXDEPTH=128','-GRMAX=256','-GLEV=4','-GXB=2',*[str(p) for p in paths]]
    (b/'source_pin.json').write_text(json.dumps(source_pin,indent=2)+'\n')
    (b/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
    with (b/'build.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
    (b/'build.exit').write_text(str(rc)+'\n')
    if rc:
        raise SystemExit(rc)
    return exe


def run(exe,case):
    receipt=json.loads((case/'fixture.json').read_text())
    cmd=[str(exe),f'+DIR={case}',f'+NOPS={len(receipt["logical_op_labels"])}']
    with (case/'runtime.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=case,stdout=log,stderr=subprocess.STDOUT).returncode
    (case/'runtime.exit').write_text(str(rc)+'\n')
    got,meta,total=parse_output(case/'out.txt')
    expected,_,_=parse_output(case/'reference_out.txt')
    mask=(1<<32)-1  # SAME actual P1 active-column contract
    bad=[list(k) for k in expected if k not in got or (got[k]&mask)!=(expected[k]&mask)]
    extra=[list(k) for k in got if k not in expected]
    exact=rc==0 and not bad and not extra and len(got)==len(expected) and len(meta)==len(receipt['logical_op_labels'])
    exact=exact and all(m['fault']==0 and m['results']==d[0] and m['consumed']==d[4]
                        for m,d in zip([meta[k] for k in sorted(meta)],receipt['composite_descriptors']))
    groups=receipt['w2_groups']
    cycles=meta[groups[-1]]['t_done']-meta[groups[0]]['t_load0'] if exact else None
    delta=receipt['baseline_w2_cycles']-cycles if exact else None
    result=dict(status='pass' if exact else 'fail',runtime_returncode=rc,mismatches=bad,extra=extra,
                original_output_rows=len(expected),actual_output_rows=len(got),total_cycles=total,
                paired_w2_cycles=cycles,baseline_pq_w2_cycles=receipt['baseline_w2_cycles'],
                incremental_cycles_saved=delta,ops=meta,active_columns=1,
                no_baseline_rerun=True,no_golden_generation=True,
                adopted=False,physical_ss_ff_qualified=False)
    (case/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','paired_w2_cycles','baseline_pq_w2_cycles','incremental_cycles_saved')}))
    return 0 if exact else 1


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('step',choices=('prepare','build','run'))
    p.add_argument('--work',type=Path,required=True)
    p.add_argument('--fixture',type=Path)
    p.add_argument('--baseline-json',type=Path)
    a=p.parse_args();work=a.work.resolve()
    if a.step=='prepare':prepare(a.fixture.resolve(),a.baseline_json.resolve(),work/'case')
    elif a.step=='build':build(work)
    else:raise SystemExit(run(work/'build'/('V'+TB),work/'case'))


if __name__=='__main__':main()
