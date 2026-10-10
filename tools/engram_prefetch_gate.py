#!/usr/bin/env python3
"""Full8slot protectedprefetch macro/SECDED component gate; admitted remote only."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/dsrom_sys/engram/ot_dsrom_engram_prefetch.sv'
TB=ROOT/'rtl/test/tb_dsrom_engram_prefetch.sv'
ECC=ROOT/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv'
MACRO=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v'
OUT=ROOT/'results/rtl/engram_prefetch_gate_20261009.json'


def main():
    if OUT.exists():raise FileExistsError('immutable prefetch gate exists')
    paths=[RTL,TB,ECC,MACRO,ROOT/'tools/uarch_model.py',Path(__file__)]
    rec=dict(schema='opentallas.engram-prefetch-macro-gate.v1',
             boundary='1536words through18realSRAM behavioral macros, SECDED, bounds, read2cycles at1word/cycle; no SS/FF/physical or consumer slotready credit',
             predecessor_failure='results/rtl/engram_prefetch_7abb78efd_fail.json',
             input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},cases={})
    with tempfile.TemporaryDirectory(prefix='engram-prefetch-') as tmp:
        work=Path(tmp)
        for mask,name in [(0,'clean'),(1,'single_corrected'),(3,'double_rejected')]:
            exe=work/(name+'.vvp')
            command=['iverilog','-g2012','-s','tb_dsrom_engram_prefetch',
                     f'-Ptb_dsrom_engram_prefetch.INJECT={mask}','-o',str(exe),str(RTL),str(TB),str(ECC),str(MACRO)]
            build=subprocess.run(command,capture_output=True,text=True)
            if build.returncode:raise RuntimeError(build.stderr[-3000:])
            run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            ok=run.returncode==0 and f'ENGRAM_PREFETCH PASS words=1536 slots=8 banks=18 inject={mask} bounds=1 read_latency=2 sustained=1' in run.stdout
            rec['cases'][name]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=ok)
    rec['status']='pass' if all(v['expected_observed'] for v in rec['cases'].values()) else 'fail'
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(rec,indent=1)+'\n')
    print(rec['status']);return 0 if rec['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())
