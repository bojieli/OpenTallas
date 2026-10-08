#!/usr/bin/env python3
"""Minimum component gates, actual full-depth SRAM model; no full-SM claim."""
import hashlib,json,pathlib,subprocess,tempfile
from hbm_sm_result_provider_model import model
R=pathlib.Path(__file__).resolve().parents[1]
FILES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','physical/asap7_memory_macros/ot_sram_2rw_512x64_m4_r2c2/ot_sram_2rw_512x64_m4_r2c2.v','rtl/hbm_accel/control_20261007/result_provider/ot_hbm_sm_result_provider.sv','rtl/hbm_accel/control_20261007/result_provider/tb_hbm_sm_result_provider.sv']
def run(args):
 p=subprocess.run(args,cwd=R,capture_output=True,text=True)
 return dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
def main():
 cases=[]
 with tempfile.TemporaryDirectory(prefix='sm-result-') as td:
  exe=str(pathlib.Path(td)/'sim')
  c=run(['iverilog','-g2012','-s','tb_hbm_sm_result_provider','-o',exe,*FILES])
  assert c['returncode']==0,c
  for mode,name in enumerate(['full4096_reverse_order','duplicate_row','out_of_range_row','wrong_readback','wrong_response_tag','metadata_double_error','sram_single_error_corrected','sram_double_error_rejected']):
   result=run(['vvp',exe,f'+MODE={mode}']);cases.append(dict(name=name,**result));assert result['returncode']==0,result
  mutant=pathlib.Path(td)/'mutant.sv'
  src=(R/FILES[2]).read_text();assert src.count('if(rsp_data!=req_data)')==1
  mutant.write_text(src.replace('if(rsp_data!=req_data)',"if(1'b0)"))
  c=run(['iverilog','-g2012','-s','tb_hbm_sm_result_provider','-o',exe,*FILES[:2],str(mutant),FILES[3]])
  assert c['returncode']==0,c
  result=run(['vvp',exe,'+MODE=3']);cases.append(dict(name='readback_checker_bypass_must_fail',**result));assert result['returncode']!=0,result
 receipt=dict(schema='opentallas.native_sm.result_provider.component.v1',verdict='PASS',scope='full4096 native no-ready capture and acknowledged/readback publication component; provider peer is test memory, not die service',physical_admitted=False,source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in FILES+['tools/hbm_sm_result_provider_model.py','tools/hbm_sm_result_provider_gate.py']},model=model(),cases=cases)
 out=R/'results/rtl/hbm_sm_result_provider_20261007/component.json'
 out.write_text(json.dumps(receipt,indent=2)+'\n');print(out)
if __name__=='__main__':main()
