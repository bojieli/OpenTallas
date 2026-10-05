#!/usr/bin/env python3
"""Measure opt3 using retained numeric fixtures and prior golden-validated rows.

No inference or numerical golden generation. Repack only x bits, preserve the
weight/descriptor stream, and compare every actual active-column output bit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import hbm_accel_activation_layout as X
import dshbm_sm_pq_seq as P

ROOT=Path(__file__).resolve().parents[1]
TB='tb_hbm_accel_sm_pq_xmap_seq'
SRC=[s for s in P.SRC if s not in ('rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv','rtl/hbm_accel/sm/ot_hbm_accel_sm_pq.sv','rtl/test/tb_hbm_accel_sm_pq_seq.sv')]+[
 'rtl/hbm_accel/sm/ot_hbm_accel_smpq_xmap_leaf.sv','rtl/test/tb_hbm_accel_sm_pq_xmap_seq.sv']


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build(work,jobs=16,xmap=1,production_dir=None):
    out=Path(work)/f'build_xmap{xmap}'
    out.mkdir(parents=True,exist_ok=True)
    exe=out/('V'+TB)
    production_dir=Path(production_dir or ROOT/'rtl/hbm_accel/sm/pq_production_20261005').resolve()
    paths=[ROOT/s for s in SRC]+[production_dir/'ot_hbm_accel_issue_pq.sv',production_dir/'ot_hbm_accel_sm_pq.sv']
    assert all(p.is_file() for p in paths), 'Require frozen Euclid production source and leaf XMAP hook'
    command=['verilator','--binary','--timing','-O2','-Wno-fatal','--top-module',TB,'--Mdir',str(out),'-j',str(jobs),
             '-GNC=8','-GXDEPTH=128','-GRMAX=256','-GLEV=4',f'-GXMAP={xmap}',*[str(p) for p in paths]]
    source_pin={str(p):sha(p) for p in paths}
    pin=out/'sources.json'
    if exe.exists():
        assert json.loads(pin.read_text())==source_pin, 'Refuse stale executable from another source'
        return exe
    pin.write_text(json.dumps(source_pin,indent=2)+'\n')
    with (out/'build.log').open('w') as log:
        rc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
    (out/'build.exit').write_text(str(rc)+'\n')
    if rc:raise SystemExit(rc)
    return exe


def parse_output(path):
    rows,meta={},{}
    total=None
    for line in path.read_text().splitlines():
        if line.startswith('# op '):
            parts=line[2:].split()
            meta[int(parts[1])]={parts[i]:int(parts[i+1]) for i in range(2,len(parts)-1,2)}
        elif line.startswith('# total_cycles '):total=int(line.split()[-1])
        elif not line.startswith('#'):
            op,row,value=line.split();rows[int(op),int(row)]=int(value,16)
    return rows,meta,total


def prepare(old,work,active,xmap=1):
    assert (old/'seq.hex').exists() and (old/'out.txt').exists()
    work.mkdir(parents=True,exist_ok=False)
    seq=[int(v,16) for v in (old/'seq.hex').read_text().split()]
    assert len(seq)%10==0, 'Use original ten-field PQ descriptor fixture'
    reference, reference_meta, _ = parse_output(old/'out.txt')
    required_rows = {(op, row) for op in range(len(seq)//10)
                     for row in range(seq[op*10])}
    assert set(reference) == required_rows, 'Refuse incomplete/negative reference fixture'
    assert len(reference_meta) == len(seq)//10
    assert all(m.get('fault') == 0 and m.get('consumed') == m.get('lines')
               for m in reference_meta.values()), 'Reference must have completed without faults'
    words=[int(v,16) for v in (old/'x.hex').read_text().split()]
    packed=[];cursor=0;table=[]
    for op in range(len(seq)//10):
        desc=seq[op*10:op*10+10]
        fmt=X.FORMATS[desc[3]]
        groups=X.beat_groups(fmt,active) if xmap else list(range((active*X.XC+2047)//2048))
        addresses=desc[7] if desc[6] else 0
        for word in words[cursor:cursor+addresses]:
            packed.append(X.pack_fragment(word,fmt,active) if xmap else word)
        cursor+=addresses
        table.append(dict(op=op,fmt=fmt,groups=groups,addresses=addresses,
                          expected_beats=addresses*len(groups),expected_load_cycles=addresses*len(groups)+1 if addresses else 0))
    assert cursor==len(words), 'Every source fragment belongs to an actual load'
    for name in ('seq.hex','lines.hex'):
        shutil.copy2(old/name,work/name)
    shutil.copy2(old/'out.txt',work/'reference_out.txt')
    width=(8*X.XC+2048+3)//4
    (work/'x.hex').write_text(''.join(f'{v:0{width}x}\n' for v in packed))
    receipt=dict(retained_fixture=str(old),active_columns=active,xmap=xmap,ops=table,
                 source_sha256={n:sha(old/n) for n in ('seq.hex','lines.hex','x.hex','out.txt')},
                 compiler_sha256=sha(Path(X.__file__)))
    (work/'layout.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def run_case(exe,work,receipt,serial=False,negative=False):
    cmd=[str(exe),f'+DIR={work}',f'+NOPS={len(receipt["ops"])}',f'+ACTIVE={receipt["active_columns"]}']
    if serial:cmd.append('+SERIAL')
    if negative:cmd.append('+FP4_AS_FP8')
    with (work/'runtime.log').open('w') as log:
        rc=subprocess.run(cmd,cwd=work,stdout=log,stderr=subprocess.STDOUT).returncode
    got,meta,total=parse_output(work/'out.txt')
    expected,_,_=parse_output(work/'reference_out.txt')
    mask=(1<<(32*receipt['active_columns']))-1
    mismatch=[dict(op=o,row=r) for (o,r),v in expected.items() if (o,r) not in got or (got[o,r]&mask)!=(v&mask)]
    extras=sorted(set(got)-set(expected))
    counts=[]
    for row in receipt['ops']:
        m=meta.get(row['op'],{})
        expected_beats=row['expected_beats']
        if negative and row['fmt']=='fp4':
            expected_beats=row['addresses']*len(X.beat_groups('fp8',receipt['active_columns']))
        counts.append(dict(**row,actual_beats=m.get('xload_beats'),actual_load_cycles=m.get('t_ready',0)-m.get('t_load0',0),
                           complete=m.get('results'),consumed=m.get('consumed'),fault=m.get('fault'),timing=m,
                           beats_exact=m.get('xload_beats')==expected_beats))
    protocol_ok=all(m.get('fault')==0 and m.get('consumed')==m.get('lines') for m in meta.values()) and len(meta)==len(counts)
    exact=rc==0 and not mismatch and not extras and protocol_ok
    beat_ok=all(c['beats_exact'] for c in counts)
    verdict=dict(exact=exact,beat_counts_exact=beat_ok,negative=negative,
                 accepted=beat_ok and ((not exact) if negative else exact),mismatching_rows=mismatch,
                 unexpected_rows=extras,returncode=rc,total_cycles=total,serial=serial,ops=counts,
                 clock_scope='1ns simulation clock only; SS833/60 FF25 root/writer context not qualified',
                 adopted=False,command=cmd,source_sha256=json.loads((exe.parent/'sources.json').read_text()))
    (work/'result.json').write_text(json.dumps(verdict,indent=2)+'\n')
    return verdict


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('step',choices=['build','run'])
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--fixture',type=Path)
    ap.add_argument('--production-dir',type=Path,help='Frozen Euclid production top/issue directory; no legacy integration')
    ap.add_argument('--active',type=int,choices=range(1,9),default=6)
    ap.add_argument('--jobs',type=int,default=16)
    ap.add_argument('--xmap',type=int,choices=[0,1],default=1)
    ap.add_argument('--serial',action='store_true')
    ap.add_argument('--negative-fp4',action='store_true')
    args=ap.parse_args()
    exe=build(args.work.resolve(),args.jobs,args.xmap,args.production_dir)
    if args.step=='build':return
    assert args.fixture is not None
    work=args.work.resolve()/('negative' if args.negative_fp4 else 'serial' if args.serial else 'pq')/f'a{args.active}'/args.fixture.name
    receipt=prepare(args.fixture.resolve(),work,args.active,args.xmap)
    verdict=run_case(exe,work,receipt,args.serial,args.negative_fp4)
    print(json.dumps({k:verdict[k] for k in ('exact','beat_counts_exact','negative','accepted','total_cycles')}))
    raise SystemExit(0 if verdict['accepted'] else 1)


if __name__=='__main__':main()
