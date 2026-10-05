#!/usr/bin/env python3
"""Source-pinned bank-major two-group gate for the input-registered ME SRAM."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[ROOT/p for p in (
    'rtl/hdc/v41x/ot_hdc_v41x_me_xbank_macro_inreg.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_me_xbank_macro.sv',
    'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    'rtl/test/tb_v41x_me_two_group_wide_inreg.sv',
    'rtl/test/data/v41x_me_xbank_l0_real.hex')]
OUT=ROOT/'results/rtl/v41x_me_xbank_macro_inreg_two_group.json'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    with tempfile.TemporaryDirectory(prefix='v41_me_xbank_inreg_') as td:
        exe=Path(td)/'tb.vvp'
        build=subprocess.run(['iverilog','-g2012','-s','tb_v41x_me_two_group_wide_inreg',
            '-o',str(exe),*map(str,SOURCES[:4])],cwd=ROOT,capture_output=True,text=True,timeout=120)
        if build.returncode:raise RuntimeError(build.stderr[-2000:])
        sim=subprocess.run(['vvp',str(exe),'+DATA='+str(SOURCES[4])],cwd=ROOT,
                           capture_output=True,text=True,timeout=120)
        if sim.returncode or not re.search(r'ME_TWO_GROUP_WIDE_INREG_PASS preload_cycles=128 reads=8192 errors=0',sim.stdout):
            raise RuntimeError(sim.stdout[-2000:]+sim.stderr[-1000:])
    rec=dict(schema='opentallas.rtl.v41x_me_xbank_macro_inreg.v1',status='pass',
        claim_scope='Standalone input-registered 16-macro store, two K4096 activation groups, bank-major rotation2; no adapter, cluster timing or chip-rate claim',
        preload_issue_cycles=128,exact_read_elements=8192,
        extra_request_latency_cycles=1,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [*SOURCES,Path(__file__)]},
        stdout_sha256=hashlib.sha256(sim.stdout.encode()).hexdigest())
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps({k:rec[k] for k in ('status','preload_issue_cycles','exact_read_elements')}))

if __name__=='__main__':main()
