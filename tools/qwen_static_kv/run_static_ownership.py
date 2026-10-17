#!/usr/bin/env python3
"""Small real-RTL ownership/guard component bench and deliberately failing mutants.

Declared boundary stimuli only; not a native token/die/drain-completeness proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv',
         'rtl/test/qwen_static_kv/tb_static_ownership.sv']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);runs=[]
    for mutant,guard_mutant,case in [(0,0,-1),(1,0,0),(2,0,2),(3,0,3),(0,1,6),(0,2,6)]:
        exe=(a.out/f'm{mutant}g{guard_mutant}.vvp').resolve()
        cmd=['iverilog','-g2012','-s','tb_static_ownership',f'-Ptb_static_ownership.MUT={mutant}',f'-Ptb_static_ownership.GMUT={guard_mutant}','-o',str(exe)]+[str(ROOT/p) for p in SOURCES]
        p=subprocess.run(cmd,capture_output=True,text=True)
        (a.out/f'm{mutant}g{guard_mutant}.build.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(f'compile failed m{mutant}: {p.stderr}')
        p=subprocess.run(['vvp',str(exe),f'+CASE={case}'],capture_output=True,text=True)
        (a.out/f'm{mutant}g{guard_mutant}.run.log').write_text(p.stdout+p.stderr)
        expected=(p.returncode==0) if mutant==0 and guard_mutant==0 else (p.returncode!=0 and 'FATAL' in p.stdout)
        runs.append(dict(mutant=mutant,guard_mutant=guard_mutant,case=case,exit=p.returncode,expected_result=expected,output=(p.stdout+p.stderr).strip()))
        if not expected:raise RuntimeError(f'unexpected component result: {runs[-1]}')
    receipt=dict(schema='opentallas.qwen_kv_static.ownership_component.v1',status='COMPONENT_PASS_WITH_FAILING_MUTANTS',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},results=runs,
        scope='Actual ownership/calendar/drain-observation RTL under declared ideal source-boundary observations only.',
        fixed_ages=dict(go_pin_capture_to_internal_accept_core_edges=1,native_enter=4,native_leave=14,deadline=20),
        ownership_fault='Invalid handover disables ownership_valid and aborts; no wait, defer or reschedule.',
        native_full_layer=False,physical_qualified=False,
        gaps=['actual loader/sequencer/host admission and queue debt producers',
              'source-pinned implemented local upstream quiet/fault reductions',
              'actual phi-R clocks, synchronized observation and relay/mux ages',
              'full native programme proof of exact enter/leave/deadline/drain with real PC paths'])
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
