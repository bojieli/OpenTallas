#!/usr/bin/env python3
"""Minimum-component RTL SRAM protection gate, never a physical/adoption gate."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default='results/rtl/hbrom_protection/gate_r1');args=ap.parse_args()
 out=ROOT/args.output;out.mkdir(parents=True,exist_ok=False)
 common=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbrom/ot_hbrom_secded_pipeline_pkg.sv']
 tests={
 'codec':common+['tests/rtl/tb_hbrom_secded_pipeline.sv'],
 'xstore':common+['rtl/hbrom/ot_hbrom_xstore_protected.sv','tests/rtl/tb_hbrom_xstore_protected.sv'],
 'xcontrol':common+['rtl/hbrom/ot_hbrom_xstore_protected.sv','tests/rtl/tb_hbrom_xstore_protected.sv','tests/rtl/tb_hbrom_xstore_control.sv'],
 'leaf_control':common+['rtl/hbrom/ot_hbrom_xstore_protected.sv','rtl/hbrom/ot_hbrom_smv_leaf_protected.sv','tests/rtl/tb_hbrom_xstore_protected.sv','tests/rtl/tb_hbrom_leaf_control.sv'],
 'ring':common+['rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv','rtl/hbrom/ot_hbrom_bulk_copy_control_protected.sv','rtl/hbrom/ot_hbrom_bulk_copy_protected.sv','tests/rtl/tb_hbrom_bulk_copy_protected.sv']}
 sources=sorted(set(sum(tests.values(),[])+['rtl/hbrom/ot_hbrom_smv_leaf_protected.sv']))
 pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}
 result={'schema':'hbrom.protection-minimum-gate.v1','scope':'Actual fixed4leafARstore and full1024/512 ring with behavioral SRAM; no arithmetic,full-engine,SSFF or adoption claim; metadata cases are separately named','sources_sha256':pins,'cases':{}}
 (out/'launch.json').write_text(json.dumps(result,indent=2)+'\n')
 for name,files in tests.items():
  binary=Path('/tmp')/('hbrom-protection-'+out.name+'-'+name+'.vvp')
  top={'xcontrol':'control_tb','leaf_control':'leaf_control_tb'}.get(name,'tb')
  commands=[['iverilog','-g2012','-s',top,'-o',str(binary)]+files,['vvp',str(binary)]]
  logs=[];codes=[]
  for i,cmd in enumerate(commands):
   r=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   (out/(name+('.compile.log' if i==0 else '.log'))).write_text(r.stdout)
   logs.append(r.stdout);codes.append(r.returncode)
   if r.returncode:break
  verdict='PASS' if len(codes)==2 and codes==[0,0] and 'PASS' in logs[-1] else 'FAIL'
  result['cases'][name]={'verdict':verdict,'commands':commands,'returncodes':codes}
  print(name,verdict,flush=True)
 result['sources_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
 result['verdict']='PASS' if result['sources_unchanged'] and all(v['verdict']=='PASS' for v in result['cases'].values()) else 'FAIL'
 (out/'verdict.json').write_text(json.dumps(result,indent=2)+'\n')
 if result['verdict']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
