#!/usr/bin/env python3
"""Reproduce known local RTL publication storage coverage gaps and codec controls."""
import argparse,json,hashlib,subprocess
from pathlib import Path

def run(a):
 a.out.mkdir(parents=True,exist_ok=True);root=a.root
 src=root/'results/rtl/qwen_rom_vm_combined_ingress_20261007/src'
 files=[src/n for n in ['ot_gpu_w6_secded_pkg.sv','ot_qwen_vm_bank4_direct_readback.sv','ot_hdc_cg.sv','ot_qwen_checked_vm_bank_direct_readback.sv','ot_qwen_rom_vm_ingress_adapter.sv','ot_sram_1r1w_512x128_m4_r2c2.v']]+[root/'rtl/test/qwen_vm_publication_storage_20261007/tb_qwen_vm_publication_storage.sv']
 (a.out/'source_pins.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
 q=subprocess.run(['iverilog','-g2012','-s','tb_qwen_vm_publication_storage','-o',str(a.out/'sim'),*[str(p) for p in files]],capture_output=True,text=True);(a.out/'compile.log').write_text(q.stdout+q.stderr);assert q.returncode==0
 expected={0:'PASS actual_full_aperture_publication',1:'RELIABILITY_FAILURE_PUBLISHED_REGISTER_REACHES_NATIVE_CONSUMER',2:'RELIABILITY_FAILURE_XVM_HOLD_REACHES_LEASED_PUBLICATION',3:'RELIABILITY_FAILURE_WINDOW_ERROR_REENCODED_AS_VALID_RESPONSE',4:'PASS actual_full_aperture_publication',5:'PASS retained_response_two_bit_error_stops_native_publication'}
 fixture=root/'results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex';result={}
 for n,marker in expected.items():
  q=subprocess.run(['vvp',str(a.out/'sim'),'+FIXTURE='+str(fixture),f'+CASE={n}'],capture_output=True,text=True);(a.out/f'case{n}.log').write_text(q.stdout+q.stderr)
  assert marker in q.stdout and ((q.returncode!=0)==(n in (1,2,3))),(n,q.returncode,q.stdout)
  result[n]={'quality_status':'FAIL_STORAGE_COVERAGE' if n in (1,2,3) else 'PASS_CONTROL','historical_outcome_reproduced':True,'exit_code':q.returncode}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
