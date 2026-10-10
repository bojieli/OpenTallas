#!/usr/bin/env python3
"""Smallest actual converter quad (8 protected banks/16 real SRAMs), with three mutants."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
root=Path(__file__).resolve().parents[3]
sources=['rtl/hbm_accel/generic/peers/ot_hgi_dma_wide_convert_tile.sv','rtl/hbm_accel/generic/peers/tb_hgi_dma_wide_convert_tile.sv','rtl/hbm_accel/generic/vm/ot_hgi_vm_wide_bank.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v']
out=Path(tempfile.mkdtemp(prefix='hgi-convert-tile-gate-'));records=[]
for m in range(4):
    exe=out/f'tile{m}.vvp'
    build=subprocess.run(['iverilog','-g2012','-s','tb_hgi_dma_wide_convert_tile','-P',f'tb_hgi_dma_wide_convert_tile.TEST_MUT={m}','-o',str(exe),*sources],cwd=root,capture_output=True,text=True)
    (out/f'build{m}.log').write_text(build.stdout+build.stderr);assert build.returncode==0,build.stderr
    run=subprocess.run(['vvp',str(exe)],cwd=root,capture_output=True,text=True);(out/f'run{m}.log').write_text(run.stdout+run.stderr)
    expected='CONVERT_PASS'if m==0 else 'CONVERT_DROP'if m==3 else 'CONVERT_EXACT_OR_DUP'
    good=(run.returncode==0 if m==0 else run.returncode!=0) and expected in run.stdout
    records.append(dict(mutant=m,returncode=run.returncode,expected=expected,gate_pass=good));print(json.dumps(records[-1]),flush=True)
record=dict(records=records,source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in sources})
(out/'run_record.json').write_text(json.dumps(record,indent=2)+'\n');print('ARTIFACT_DIR='+str(out),flush=True)
assert all(r['gate_pass']for r in records)
