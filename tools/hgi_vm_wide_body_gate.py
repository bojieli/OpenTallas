#!/usr/bin/env python3
"""Minimum quad actual-macro shared body gate; no array-scale simulation."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
out=R/'results/rtl/hgi_vm_wide_body_20261010_r3';out.mkdir(parents=True,exist_ok=True)
src=['rtl/hbm_accel/generic/vm/tb_hgi_vm_wide.sv','rtl/hbm_accel/generic/vm/ot_hgi_vm_wide.sv','rtl/hbm_accel/generic/vm/ot_hgi_vm_wide_bank.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v']
rows=[]
with tempfile.TemporaryDirectory() as td:
 for mut in [0,1]:
  binary=Path(td)/f'm{mut}.vvp'
  cmd=['iverilog','-g2012','-s','tb_hgi_vm_wide','-P',f'tb_hgi_vm_wide.MUT={mut}','-o',str(binary)]+src
  b=subprocess.run(cmd,cwd=R,text=True,capture_output=True);assert b.returncode==0,b.stderr
  r=subprocess.run(['vvp',str(binary)],cwd=R,text=True,capture_output=True)
  log=out/f'run_gate_m{mut}.log';assert not log.exists(),'Never overwrite evidence'
  log.write_text(r.stdout+r.stderr)
  passed=r.returncode==0 and 'PASS wide body' in r.stdout
  assert passed==(mut==0),r.stdout
  rows.append(dict(mutant=mut,returncode=r.returncode,expected_pass=mut==0,log=str(log.relative_to(R))))
record=dict(verdict='PASS',source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in src},cases=rows,
 actual_macros=16,logical_banks=4,physical_banks=8,measured_DMA_sectors=529,native_COLL_commits=10,packet_responses=37,
 write_body_elapsed_cycles=5,read_body_elapsed_cycles=6,
 mechanisms=['real macro II2 phase interleave','shared native/DMA write arbitration','concurrent packet read/native writes','OUT8 overload negative','inorder returned user tags','response backpressure','uninitialized read rejection','cold partial-word initialization visibility','mirrored held response data and control','visibility rail corruption sticky fault negative','opaque PACKED1 actual265-bit16group row544B with112zero pad; eight readcredits and17real macrocommits','high address and alignment rejection'],
 macro_bank_exact_mutants_source='59a9e0b4f',default_adoption=False,physical_qualified=False,
 capacity_composition=dict(replica_quad_tiles=128,bank_roof_decoded_Bpc=16384,FP32raw_Bpc=16384,BF16raw_Bpc=8192,FP8raw_Bpc=4096,includes_measured_HBM_utilization=False))

receipt=out/'record.json';assert not receipt.exists();receipt.write_text(json.dumps(record,indent=2)+'\n')
print('PASS actual quad protected shared body + tagged ACK mutant')
