#!/usr/bin/env python3
"""Real all36 stage-root hardware component proof, not native arithmetic evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/static_kv_20261014/qkd_static_kv_layer_programme.sv',
         'rtl/test/qwen_static_kv/tb_static_layer_programme.sv']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    runs=[]
    for m in range(4):
        binary=(a.out/f'm{m}.vvp').resolve()
        p=subprocess.run(['iverilog','-g2012','-s','tb_static_layer_programme',f'-Ptb_static_layer_programme.MUT={m}','-o',str(binary)]+[str(ROOT/f) for f in SOURCES],capture_output=True,text=True)
        (a.out/f'm{m}.build.log').write_text(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(p.stderr)
        p=subprocess.run(['vvp',str(binary)]+(['+CASE=0'] if m else []),capture_output=True,text=True)
        (a.out/f'm{m}.run.log').write_text(p.stdout+p.stderr)
        ok=(p.returncode==0) if m==0 else (p.returncode!=0 and 'FATAL' in p.stdout)
        runs.append(dict(mutant=m,exit=p.returncode,expected_result=ok,output=(p.stdout+p.stderr).strip()))
        if not ok:raise RuntimeError(str(runs[-1]))
    result=dict(schema='opentallas.qwen_kv_static.layer_programme_component.v1',status='COMPONENT_PASS_WITH_FAILING_MUTANTS',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},results=runs,
        actual_component=dict(layers=36,persistent_tokens=2,stage_frames=72,fixed_control_events=504,
            boot_words=327,roots_per_layer=9,root_storage_bits=36*9*32,
            guard='actual authorized programme digest/epoch and authoritative token metadata are captured; no ready or data input schedules an event'),
        scope='Actual all36 root/control/metadata hardware, declared boundary boot and authorized HOST stimuli. No internal arithmetic/memory/link results supplied or claimed.',
        native_full_layer=False,physical_qualified=False,
        gaps=['source-pinned actual compiler roots and installed HOST boot image path',
              'context-parametric controller images and native-attention calendar176 producer',
              'actual fixed-phase core/HBM launch and pin/relay ages',
              'actual arithmetic/link/memory/HOST native composition and physical qualification'])
    (a.out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
