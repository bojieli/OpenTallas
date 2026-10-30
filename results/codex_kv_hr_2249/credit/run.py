#!/usr/bin/env python3
"""Run the native PHY credit-return capture coupon (submit through ot-run)."""
import argparse,importlib.util,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--threads',type=int,default=4);a=p.parse_args()
root=Path(__file__).resolve().parents[3];helper=root/'physical/die_plan/qwen_kvsys/cores/harden/hr_credit_return_capture.py'
sp=importlib.util.spec_from_file_location('hr_capture',helper);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);src=Path(a.source).read_text();(out/'original.v').write_text(src)
for name,mut in [('capture',False),('capture_mut',True)]:
 s,r=m.transform(src,new_module='qkd_hr_phy_adp_'+name,mutant=mut);(out/(name+'.v')).write_text(s);(out/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
s,n=re.subn(r'\bmodule qkd_hr_phy_adp\s*\(', 'module qkd_hr_phy_adp_enabled(',src,count=1)
assert n==1;s,r=m.enabled_vehicle(s,module='qkd_hr_phy_adp_enabled');(out/'enabled.v').write_text(s)
s=(Path(__file__).resolve().parent/'tb_credit.sv').read_text().replace('qkd_hr_phy_adp_capture #(.CREDIT_RETURN_CAPTURE(1)) dut','qkd_hr_phy_adp_enabled dut');(out/'tb_credit_enabled.sv').write_text(s)
mem=root/'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v'
cmd=['verilator','--binary','--timing','-Wno-fatal','-j',str(a.threads),'--top-module','tb','-Mdir','obj','original.v','capture.v','capture_mut.v','enabled.v','tb_credit_enabled.sv',str(mem)]
with (out/'build.log').open('w') as f:subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'sim.log').open('w') as f:subprocess.run([str(out/'obj/Vtb')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
print((out/'sim.log').read_text())
