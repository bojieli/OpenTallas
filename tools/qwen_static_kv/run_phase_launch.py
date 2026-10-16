#!/usr/bin/env python3
"""Real fixed-phase transport component proof; no physical phase qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_phase_launch.sv',
         'rtl/test/qwen_static_kv/tb_static_phase_launch.sv']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    runs=[]
    for m in range(4):
        binary=(a.out/f'm{m}.vvp').resolve()
        p=subprocess.run(['iverilog','-g2012','-s','tb_static_phase_launch',f'-Ptb_static_phase_launch.MUT={m}','-o',str(binary)]+[str(ROOT/f) for f in SOURCES],capture_output=True,text=True)
        (a.out/f'm{m}.build.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        p=subprocess.run(['vvp',str(binary)]+(['+CASE=0'] if m else []),capture_output=True,text=True)
        (a.out/f'm{m}.run.log').write_text(p.stdout+p.stderr)
        ok=(p.returncode==0) if m==0 else (p.returncode!=0 and 'FATAL' in p.stdout)
        runs.append(dict(mutant=m,exit=p.returncode,expected_result=ok,output=(p.stdout+p.stderr).strip()))
        if not ok:raise RuntimeError(str(runs[-1]))
    result=dict(schema='opentallas.qwen_kv_static.phase_launch_component.v1',status='COMPONENT_PASS_WITH_FAILING_MUTANTS',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},results=runs,
        actual_component=dict(packets=36,lanes=3,core_period_u=625,hbm_period_u=768,
            component_safe_window_u=[200,600],held_core_edges=8,
            guard='unsafe phase or metadata overwrite faults; event never waits or reschedules'),
        scope='Actual three-lane toggle transport and held metadata under explicitly declared component clocks; independent edge-index scoreboard.',
        native_full_layer=False,physical_qualified=False,
        gaps=['actual reset/PLL phase origin and measured source/pin/relay setup/hold aperture',
              'actual programme/controller/front/landing source composition',
              'native and physical clock-domain crossing qualification'])
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
