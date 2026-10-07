#!/usr/bin/env python3
"""Actual full-slot directed writer priority, using one initialized word."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def run(a):
 a.out.mkdir(parents=True,exist_ok=True)
 root=a.root;bank=root/'rtl/hbm_accel/qwen/vm_direct_readback_20261007';bench=root/'rtl/test/qwen_vm_writer_priority_20261007/tb_qwen_vm_writer_priority.sv'
 fixture=root/'results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex'
 common=[root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',root/'rtl/hdc/ot_hdc_cg.sv',root/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',bank/'ot_qwen_vm_bank4_direct_readback.sv',bank/'ot_qwen_checked_vm_bank_direct_readback.sv']
 source=(bank/'ot_qwen_finite_vm_adapter_direct_readback.sv').read_text();old='pack_data[wa[3:0]*32+:32]<=wd;';assert source.count(old)==1
 results={}
 for mode in ('positive','first_writer_mutant'):
  out=a.out/mode;out.mkdir(exist_ok=True);candidate=out/'adapter.sv';candidate.write_text(source if mode=='positive' else source.replace(old,'if(!pack_mask[wa[3:0]])'+old))
  files=common+[candidate,bench];(out/'source_pins.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
  cmd=['iverilog','-g2012','-s','tb_qwen_vm_writer_priority','-o',str(out/'sim'),*[str(p) for p in files]]
  p=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0
  p=subprocess.run(['vvp',str(out/'sim'),'+FIXTURE='+str(fixture)],capture_output=True,text=True);(out/'run.log').write_text(p.stdout+p.stderr)
  ok=p.returncode==0 and 'PASS directed_full_aperture_source_priority' in p.stdout if mode=='positive' else p.returncode!=0 and 'OVERWRITE_SOURCE_PRIORITY_BROKEN' in p.stdout
  assert ok,(mode,p.returncode,p.stdout);results[mode]={'exit_code':p.returncode,'expected_outcome':True}
 (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
