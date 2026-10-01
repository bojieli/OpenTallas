"""Actual 96-endpoint W15 RTL round; no ISA or bandwidth-slot substitution."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
import hdc_golden as G
import w15_collectives as W

ROOT=Path(__file__).resolve().parents[1]
TOP='tb_w15_tp96_exact'
SOURCES=['rtl/test/'+TOP+'.sv','rtl/test/w15_tp96_measure_counter.sv',*W.TB_SRC['tb_w15_v41_hbm_nvls'][1:]]
OPS=[dict(name='w19_oreduce',mode=0,words=512,bytes=32768),dict(name='expert_intermediate',mode=1,words=5,bytes=288),dict(name='index_candidates',mode=1,words=64,bytes=4096)]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def assert_no_live_tp96(proc=Path('/proc'), own_pid=None):
    """A new output path does not authorize duplicating an existing round."""
    own_pid = os.getpid() if own_pid is None else own_pid
    for directory in proc.iterdir():
        if not directory.name.isdigit() or int(directory.name)==own_pid:
            continue
        try:
            args=(directory/'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        names={Path(os.fsdecode(a)).name for a in args if a}
        if names & {'w15_tp96_exact.py','V'+TOP}:
            raise RuntimeError(f'existing TP96 runner/binary live: PID {directory.name}; do not duplicate')

def measurement(text, op_rows):
    markers=re.findall(r'W15MEASURE version=(\d+) bits=(\d+) protocol_bits=(\d+) period_ps=(\d+) overflow_guard=(\d+)',text)
    if not markers:
        return dict(qualified=False,status='pending_unqualified',reason='legacy 16-bit OP timestamps can wrap; no authoritative elapsed counter')
    assert len(markers)==1
    version,bits,protocol,period,guard=map(int,markers[0])
    assert version==1 and 23<=bits<=64 and protocol==16 and period==1112 and guard==1
    rows=[tuple(map(int,x)) for x in re.findall(r'MEAS op=(\d+) die=(\d+) issue=(\d+) first_tx=(\d+) last_tx=(\d+) first_vm=(\d+) last_vm=(\d+) done=(\d+)',text)]
    assert len(rows)==288 and {(x[0],x[1]) for x in rows}=={(o,d) for o in range(3) for d in range(96)}
    by_key={(x[0],x[1]):x for x in rows}
    # Reporting is observational: low bits still match the original wire-clock OP rows.
    for op in op_rows:
        x=by_key[(op[0],op[1])]
        assert 0<=x[2]<=x[3]<=x[4]<=x[5]==x[6]<x[7]<(1<<bits)
        assert x[7]==x[6]+1
        for j in range(6):
            assert (x[2+j]&65535)==(op[4+j]&65535)
    for die in range(96):
        assert all(by_key[(o,die)][7]<=by_key[(o+1,die)][2] for o in range(2))
    cycles={OPS[o]['name']:max(x[7]-x[2] for x in rows if x[0]==o) for o in range(3)}
    return dict(qualified=True,status='measured_round_only',counter_bits=bits,protocol_bits=protocol,
                cycle_period_ps=period,cycles=cycles,elapsed_ps={k:v*period for k,v in cycles.items()},
                elapsed_ns={k:v*period/1000 for k,v in cycles.items()},
                protocol_wrap_observed=any(x[7]//65536>x[2]//65536 for x in rows))

def tree(values):
    values=list(values)
    while len(values)>1:
        values=[G.add(values[i],values[i+1]) for i in range(0,len(values)-1,2)]+([values[-1]] if len(values)%2 else [])
    return values[0]

def fixture(out):
    out.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(96)
    v=(rng.uniform(-4,4,(3,96,512,16))).astype(np.float32)
    # W19 oreduce: 8 groups x 1,024 FP32 rows, 8 adjacent head ranks/group.
    # All other ranks send canonical zero. Each 8-rank subtree is unchanged.
    for word in range(512):
        group=word//64
        v[0,:group*8,word]=0;v[0,(group+1)*8:,word]=0
    # Non-associative witness: package sums [2**24, 1, -2**24, 1].
    v[0,:,0]=0
    for rank,value in [(0,2**24),(2,1),(4,-2**24),(6,1)]:v[0,rank,0,:]=value
    part=G.bits(v);expected=np.zeros((3,512,16),dtype=np.uint32)
    for word in range(512):
        expected[0,word]=G.bits(tree(v[0,:,word]))
        group=word//64
        assert np.array_equal(expected[0,word],G.bits(tree(v[0,group*8:(group+1)*8,word])))
    for name,array in [('part.hex',part),('expected.hex',expected)]:
        with (out/name).open('w') as f:
            for row in array.reshape(-1,16):f.write(''.join(f'{int(x):08x}' for x in row[::-1])+'\n')
    (out/'desc.hex').write_text(''.join(f"{(x['mode']<<31)|(i<<15)|x['words']:08x}\n" for i,x in enumerate(OPS)))
    meta=dict(ranks=96,packages=48,lanes=16,ops=OPS,golden_sha256=sha(ROOT/'tools/hdc_golden.py'),
              tree='adjacent ranks paired, then pairwise package tree; odd tail passes. Matches W19 aligned8-rank subtrees, inactive ranks zero.',
              bf16_boundary='W19 consumer owns FP32-to-BF16 rounding; this gate transports FP32 reductions exactly.',
              actual_bytes=True,expert_padding_bytes=32,images_sha256={f:sha(out/f) for f in ['part.hex','expected.hex','desc.hex']})
    (out/'manifest.json').write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
    return meta

def parse(text,negative=None):
    if negative:
        witness='reduce mismatch' if negative=='order' else 'tag mismatch'
        return dict(passed=witness in text,expected_rejection=negative,witness=witness)
    ops=[tuple(map(int,m)) for m in W.OPL.findall(text)]
    credits=[tuple(map(int,m)) for m in re.findall(r'CREDIT die=(\d+) waiting=(\d+) consumer_stall=(\d+) landing_peak=(\d+) accepted=(\d+)',text)]
    bp=[tuple(map(int,m)) for m in re.findall(r'BACKPRESSURE pkg=(\d+) forward=(\d+) downlink=(\d+)',text)]
    expected_records=512+96*5+96*64
    assert len(ops)==3*96 and {(r[0],r[1]) for r in ops}=={(o,d) for o in range(3) for d in range(96)}
    assert all(r[-2]==r[-1] for r in ops)
    assert len(credits)==96 and {r[0] for r in credits}==set(range(96))
    assert all(r[3]<=128 and r[4]==expected_records for r in credits)
    assert len(bp)==48 and all(r[1]+r[2]>0 for r in bp),'backpressure not exercised on every package'
    assert all(r[1]>0 for r in credits),'finite-credit wait not exercised on every endpoint'
    assert 'W15DONE' in text and 'faults=0' in text and not any(x in text for x in ['%Error','%Fatal','W15TIMEOUT'])
    timing=measurement(text,ops)
    result=dict(passed=True,endpoints=96,op_rows=len(ops),records_each_endpoint=expected_records,
                consumer_stalls=sum(r[2] for r in credits),credit_wait=sum(r[1] for r in credits),
                actual_link_backpressure=sum(r[1]+r[2] for r in bp),max_landing_records=max(r[3] for r in credits),
                latency_measurement=timing)
    if timing['qualified']:result['cycles']=timing['cycles']
    return result

def campaign(out,build):
    assert_no_live_tp96()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('clean pinned worktree required')
    assert not out.exists() and not build.exists(),'use new immutable output/build paths'
    pre=json.loads((ROOT/'results/uarch/w15_tp96_collective_preflight_20261001.json').read_text())
    for p,h in pre['source_sha256'].items():assert sha(ROOT/p)==h,p
    out.mkdir(parents=True);build.mkdir(parents=True)
    fixture(out/'fixture')
    pins={p:sha(ROOT/p) for p in SOURCES+['tools/w15_tp96_exact.py','tools/w15_tp96_preflight.py','tools/hdc_golden.py','tools/uarch_model.py','results/rtl/w15_tp96_w19_prerequisites_input_20261001.json']}
    record=dict(schema='w15_tp96_exact_v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                source_sha256=pins,preflight_sha256=sha(ROOT/'results/uarch/w15_tp96_collective_preflight_20261001.json'),
                claims='Actual 96-endpoint collective rounds only; no full-token rate, hardware adoption or SS/FF claim.',cases={})
    cases=[('normal',0,0,0,None),('stalled',1,0,0,None),('bad_order',0,1,0,'order'),('bad_tag',0,0,1,'tag')]
    for name,stall,order,tag,negative in cases:
        obj=build/"obj"
        cmd=[str(W.VERILATOR),*W.VFLAGS,'-j',os.environ.get('W15_COMPILE_JOBS','8'),'--top-module',TOP,'-Mdir',str(obj),
             *[str(ROOT/p) for p in SOURCES]]
        # One pinned binary; stress/fault injections are recorded plusargs.
        if name=='normal':
            r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(out/'build.log').write_text(r.stdout+r.stderr)
            if r.returncode:record['cases'][name]=dict(passed=False,phase='build',rc=r.returncode);break
        exe=obj/('V'+TOP)
        if name=='normal':
            (out/'binary_sources.json').write_text(json.dumps(dict(pins={p:pins[p] for p in SOURCES},compiled_at_source=record['source_commit'],binary_sha256=sha(exe)),indent=2,sort_keys=True)+'\n')
            (out/'verFiles.dat').write_bytes((obj/('V'+TOP+'__verFiles.dat')).read_bytes())
        r=subprocess.run([str(exe),f'+VEC={out/"fixture"}','+DET=0','+SEED=96',f'+STALL={stall}',f'+BAD_ORDER={order}',f'+BAD_TAG={tag}'],cwd=build,capture_output=True,text=True)
        log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
        try:
            verdict=parse(log,negative)
            assert (r.returncode!=0) if negative else (r.returncode==0)
            if not negative:assert verdict['latency_measurement']['qualified'],'new measurement requires authoritative elapsed counters'
        except (AssertionError,ValueError) as e:verdict=dict(passed=False,error=str(e))
        record['cases'][name]=dict(verdict,rc=r.returncode,binary_sha256=sha(exe),log_sha256=sha(out/(name+'.log')),
                                   parameters=dict(STALL=stall,BAD_ORDER=order,BAD_TAG=tag))
        (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
        print('CASE',name,json.dumps(record['cases'][name]),flush=True)
        if not verdict['passed']:break
    record['passed']=len(record['cases'])==4 and all(x['passed'] for x in record['cases'].values())
    (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    if not record['passed']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--build',type=Path,required=True);a=p.parse_args();campaign(a.out.resolve(),a.build.resolve())
