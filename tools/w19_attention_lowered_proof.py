#!/usr/bin/env python3
"""Reuse pinned attention proof control flow with explicitly lowered GPU recipes.

Dependency injection into a cloned function, never editing pinned code/globals.
CPU numeric proof only. Controller, COS/SIN production and physical fit pending.
"""
import argparse
import json
from pathlib import Path
import subprocess
from types import FunctionType,SimpleNamespace
import numpy as np
import w19_attention_opcode_proof as P
import w19_gpu_attention_finish as C
import w19_gpu_compare_lowering as L
import w19_gpu_compare_vm as VM
from w19_attention_typed_vm import Machine as DotMachine

ROOT=Path(__file__).resolve().parents[1]


def connected(q,rows,sink,cs,scale):
    def profile(n):
        p=C.profile(n);p['recipes']={k:L.lower(v) for k,v in p['recipes'].items()};return p
    def machine(program,memory,attn_scale,active_lanes=32,dot=False):
        return DotMachine(program,memory,attn_scale,active_lanes,dot=True) if dot else VM.Machine(program,memory,attn_scale,active_lanes)
    env={**P.connected.__globals__,'C':SimpleNamespace(profile=profile,ins=C.ins),'Machine':machine}
    fn=FunctionType(P.connected.__code__,env,'connected_lowered')
    got,machines=fn(q,rows,sink,cs,scale)
    if any(t['op'] in ['FMAX','FMIN'] for m in machines.values() for t in m.trace):raise ValueError('nativeMAX/MIN remained')
    return got,machines


def execute(fixture,out):
    if out.exists():raise ValueError('refuse overwrite')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean source required')
    out.mkdir(parents=True)
    z=np.load(fixture,allow_pickle=False);cases=[];trace={}
    for n in [128,640]:
        args=(z[f'q{n}'],z[f'rows{n}'],z[f'sink{n}'],(z[f'cos{n}'],z[f'sin{n}']),z['scale'])
        got,m=connected(*args);expected=P.reference(*args)
        mismatch={k:int(np.count_nonzero(np.asarray(got[k]).view(np.uint32)!=np.asarray(expected[k]).view(np.uint32))) for k in got}
        cases.append(dict(rows=n,mismatch_bits=mismatch,opcode_boundaries=sum(len(v.trace) for v in m.values()),
                          output_sha256=P.N.sha(got['final'].tobytes())))
        trace[str(n)]={k:[{a:b for a,b in t.items() if a!='value'} for t in v.trace] for k,v in m.items()}
    paths=['tools/w19_attention_lowered_proof.py','tools/w19_gpu_compare_lowering.py','tools/w19_gpu_compare_vm.py',
           'tools/w19_attention_opcode_proof.py','tools/w19_attention_typed_vm.py','tools/w19_norm_opcode_proof.py',
           'tools/w19_gpu_attention_finish.py','tools/w19_gpu_attention_dots.py','tools/hdc_golden.py','tools/hdc_golden_v41.py']
    verdict='PASS' if all(v==0 for c in cases for v in c['mismatch_bits'].values()) else 'FAIL'
    r=dict(schema='opentallas.w19.lowered-compare-attention-proof.v1',verdict=verdict,
           source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           source_pins={p:P.N.sha((ROOT/p).read_bytes()) for p in paths},fixture_sha256=P.N.sha(fixture.read_bytes()),
           fixture_provenance=json.loads(fixture.with_suffix('.json').read_text()),cases=cases,
           backend='CPU typed primitive execution: nineteen2srcINT/FCMP permax/min; no nativeFMAX/MIN',
           dependencies='pinned attention control flow +lowered recipes supplied by immutable function-global clone; original modules/globals unchanged',
           full_token_qualified=False,RTL_qualified=False,physical_qualified=False,adopted=False)
    (out/'proof.json').write_text(json.dumps(r,indent=2)+'\n');(out/'trace.json').write_text(json.dumps(trace,indent=2)+'\n')
    print(json.dumps({'verdict':verdict,'opcode_boundaries':sum(c['opcode_boundaries'] for c in cases)}))
    if verdict!='PASS':raise SystemExit(1)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();execute(a.fixture,a.out)
