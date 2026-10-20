#!/usr/bin/env python3
"""Prepare exact fixed production math inputs and the bounded source manifest."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('work',type=Path);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
 path=ROOT/'rtl/hdc/ot_hdc_fp32_mul_lat.sv';s=path.read_text();s=s[s.index('module ot_hdc_fp32_mul_lat '):];s=s[:s.index('endmodule')+len('endmodule')]
 s=s.replace('module ot_hdc_fp32_mul_lat','module qfd_dv_station_mul_lat',1)
 old=["({6'd0, k[5:0]} == {6'd0, shc} - 12'd1)","({6'd0, k[5:0]} < {6'd0, shc} - 12'd1)"]
 new=['(shc == k + 1)','(shc == 0 || shc > k + 1)']
 for x,y in zip(old,new):assert s.count(x)==1;s=s.replace(x,y)
 (a.work/'station_mul_exact.sv').write_text(s)
 mutant=0
 for sh in range(64):
  for k in range(48):
   oldr=k==((sh-1)&4095);olds=k<((sh-1)&4095)
   assert (oldr,olds)==(sh==k+1,sh==0 or sh>k+1)
   mutant+=olds!=(sh>k+1)
 assert mutant==48

 files=['rtl/qwen_dv/qfd_dv_ring_delay.sv','rtl/qwen_dv/qfd_dv_reset_tree.sv','rtl/common/landed_parent/ot_pl_land.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv','tools/qwen_dv/bound_math_netlist.py','tools/qwen_dv/gen_station_math_input.py','tools/qwen_dv/run_station_math_generate.sh']
 data={'shape':{'add_LAT':7,'mul_LAT':6,'DRST':0},'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},'prepared_mul_sha256':hashlib.sha256(s.encode()).hexdigest(),'mask_identity_cases':3072,'shc0_mutant_mismatches':48,'tool_version':'record actual yosys --version in tool_version.txt','scope':'source construction; exact simulation, native load retention and mapped area/timing required'}
 (a.work/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
