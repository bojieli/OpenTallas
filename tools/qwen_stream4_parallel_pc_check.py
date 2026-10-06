#!/usr/bin/env python3
"""One changed-source simultaneous-sector-lane/warm/ACK minimum PC gate.

Run through the compute host's unchanged admission guard. This is not a
whole-system build, a replay of the prior leaf gold, or physical qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
    'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv', 'rtl/lib/ot_reset_sync.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_kreg.sv', 'rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv',
    'rtl/hdc/kv/ot_qwen_s4_checked_state.sv', 'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
    'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv', 'rtl/hdc/kv/ot_qwen_s4_parallel_protected_pc.sv',
    'rtl/test/qwen_rom_runtime/realmem/tb_qwen_s4_parallel_protected_pc.sv']
def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    exe=out/'pc.vvp'
    b=subprocess.run(['iverilog','-g2012','-s','tb_qwen_s4_parallel_protected_pc','-o',str(exe),*SOURCES],cwd=ROOT,capture_output=True,text=True)
    (out/'build.log').write_text(b.stdout+b.stderr)
    t=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True) if not b.returncode else b
    (out/'run.log').write_text(t.stdout+t.stderr)
    rec=dict(build_exit=b.returncode,run_exit=t.returncode,source_SHA256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        verdict='PASS_PARALLEL_PC_SEAM_ONLY' if b.returncode==0 and t.returncode==0 else 'FAIL_PARALLEL_PC_SEAM',
        CLK_ps=833.333,HCLK_ps=1024,full_system=False,physical_qualified=False,adopted=False)
    (out/'terminal.json').write_text(json.dumps(rec,indent=2)+'\n');print(t.stdout+t.stderr,end='');return t.returncode
if __name__=='__main__':raise SystemExit(main())
