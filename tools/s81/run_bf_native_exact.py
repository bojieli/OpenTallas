#!/usr/bin/env python3
"""Full native BF pair oracle with an output-bit negative control; no deadlines."""
import argparse, hashlib, importlib.util, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))

def main():
 p=argparse.ArgumentParser(); p.add_argument('--only-negative',action='store_true'); p.add_argument('--prepare-only',action='store_true'); p.add_argument('--prepared',action='store_true'); p.add_argument('--work',type=Path,required=True); p.add_argument('--jobs',type=int,default=8); p.add_argument('--verilator',default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'); a=p.parse_args()
 if a.prepared:
  prepared=json.loads((a.work/'prepared.json').read_text());files=prepared['files'];base=prepared['base'];record=prepared['record']
  for n,d in files.items():
   if (a.work/n).read_text()!=d: raise SystemExit('prepared source mismatch: '+n)
 else:
  if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(): raise SystemExit('clean pinned worktree required')
  a.work.mkdir(parents=True,exist_ok=False)
  import prepare_dsrom_actual_element_rne_wake as prep
  files=prep.package()
  wrapper=(ROOT/'rtl/s81/ot_s81_bf_native.sv').read_text().replace('ot_v41_rom_elem_w10 #(','cand_ot_v41_rom_elem_w10 #(')
  files['ot_s81_bf_native.sv']=wrapper
  pair='cand_ot_v41_pair_w17w10.sv'; files[pair]=files[pair].replace('cand_ot_v41_rom_elem_w10 #(','ot_s81_bf_native #(')
  bench='tb_dsrom_actual_element_rne_wake.sv'; files[bench]=files[bench].replace('cand_dut.u_e.','cand_dut.u_e.u_elem.')
  for name,data in files.items(): (a.work/name).write_text(data)
  plan=json.loads((ROOT/'results/rtl/dsrom_actual_element_rne_wake_prepare_20261002/sourceplan.json').read_text())['compile_plan_proposed_only']['bfcolumn']
  base=plan.copy()
  base.append('ot_s81_bf_native.sv')
  record={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'top':'ot_s81_bf_native','BF16':1,'NB':2,'XF':8,'extra_cycles':0,'die_pin_compatible':False,'runs':[],'sources_sha256':{n:hashlib.sha256(d.encode()).hexdigest() for n,d in files.items()}}
  (a.work/'prepared.json').write_text(json.dumps({'files':files,'base':base,'record':record}))
  if a.prepare_only: return
 base[0]=a.verilator;base[base.index('-j')+1]=str(a.jobs)
 base=[str(a.work/'dsrom_actual_element_numerical_rom.cpp') if x.startswith('/ABS/FRESH/') else x for x in base]
 for name,negative in ([('negative',True)] if a.only_negative else [('positive',False),('negative',True)]):
  obj='obj_'+name;cmd=base.copy();cmd[cmd.index('--Mdir')+1]=obj
  if negative:
   # One live returned value bit, injected at wrapper boundary; must be detected.
   original=files['ot_s81_bf_native.sv'];mut=original.replace('.pval(pval)', '.pval(negative_value)').replace('    ot_v41_rom_elem_w10 #(', '    ot_v41_rom_elem_w10 #(')
   mut=mut.replace('    cand_ot_v41_rom_elem_w10 #(', '    wire [32*NB-1:0] negative_value;\n    assign pval = negative_value ^ {{(32*NB-1){1\'b0}},pv[0]};\n    cand_ot_v41_rom_elem_w10 #(')
   (a.work/'ot_s81_bf_native.sv').write_text(mut)
  with (a.work/(name+'_build.log')).open('w') as f: build=subprocess.run(cmd,cwd=a.work,stdout=f,stderr=subprocess.STDOUT)
  if build.returncode: raise SystemExit('build failed: '+str(a.work/(name+'_build.log')))
  with (a.work/(name+'_run.log')).open('w') as f:run=subprocess.run([str(a.work/obj/'Vtb_bfcolumn')],cwd=a.work,stdout=f,stderr=subprocess.STDOUT)
  log=(a.work/(name+'_run.log')).read_text()
  ok=(run.returncode!=0 and ('DIFF' in log or 'NUMERICAL value' in log)) if negative else (run.returncode==0 and 'PASS independent-numerical BF=1' in log and 'PASS wake-source BF=1' in log)
  record['runs'].append({'name':name,'returncode':run.returncode,'accepted':ok,'markers':[s for s in log.splitlines() if 'PASS' in s or 'DIFF' in s or 'NUMERICAL' in s]})
  (a.work/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
  if not ok: raise SystemExit('exact gate rejected '+name)
 record['verdict']='PASS';(a.work/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record['runs'],indent=2))
if __name__=='__main__':main()
