#!/usr/bin/env python3
"""Real boot dispatch component proof; no physical phase qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv',
         'rtl/test/qwen_static_kv/tb_static_boot_dispatch.sv']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    runs=[]
    for m,neg in [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,1),(2,0),(3,0)]:
        binary=(a.out/f'm{m}_n{neg}.vvp').resolve()
        p=subprocess.run(['iverilog','-g2012','-s','tb_static_boot_dispatch',f'-Ptb_static_boot_dispatch.MUT={m}',f'-Ptb_static_boot_dispatch.NEG={neg}','-o',str(binary)]+[str(ROOT/f) for f in SOURCES],capture_output=True,text=True)
        (a.out/f'm{m}_n{neg}.build.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        p=subprocess.run(['vvp',str(binary)]+(['+CASE=0'] if m else []),capture_output=True,text=True)
        (a.out/f'm{m}_n{neg}.run.log').write_text(p.stdout+p.stderr)
        ok=(p.returncode==0) if m==0 else (p.returncode!=0 and 'FATAL' in p.stdout)
        runs.append(dict(mutant=m,negative=neg,exit=p.returncode,expected_result=ok,output=(p.stdout+p.stderr).strip()))
        if not ok:raise RuntimeError(str(runs[-1]))
    result=dict(schema='opentallas.qwen_kv_static.boot_dispatch_component.v1',status='COMPONENT_PASS_WITH_FAILING_MUTANTS',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},results=runs,
        actual_component=dict(config_images=9,exact_writes=4992,pc_destinations=128,group_destinations=32,
            guard='actual HOST image order/epoch/fault and terminal sink application; final ISA digest is real HOST output'),
        scope='Actual dispatcher with explicit authorized HOST replay boundary stimuli and independent destination/data scoreboard; no child or memory results supplied or claimed.',
        native_full_layer=False,physical_qualified=False,
        gaps=['actual target-aware HOST source+dispatcher native replay join',
              'actual boot CDC queues and child application acknowledgements',
              'actual child configuration/fault source wiring and physical qualification'])
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
