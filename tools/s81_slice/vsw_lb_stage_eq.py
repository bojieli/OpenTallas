#!/usr/bin/env python3
# Usage via ot-run: KIT_RTL SIM_SRAM OUT
from pathlib import Path
import subprocess,os
import sys,shutil
root=Path(__file__).resolve().parents[2]
r=Path(sys.argv[3]).resolve();r.mkdir(parents=True,exist_ok=True)
(r/'rtl').mkdir(exist_ok=True)
for f in Path(sys.argv[1]).glob('*.sv'):shutil.copy2(f,r/'rtl'/f.name)
shutil.copy2(sys.argv[2],r/'mem.v')
shutil.copy2(Path(__file__).with_name('tb_vsw_lb_stage.sv'),r/'tb.sv')
for rel in ['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv']:shutil.copy2(root/rel,r/'rtl'/Path(rel).name)
os.chdir(r)
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
files=[str(p) for p in (r/'rtl').glob('*.sv')]
for mode in ['good','mutant']:
 f=files
 if mode=='mutant':
  p=r/'rtl/ot_s81_su_sw.sv';m=r/'mut_sw.sv';m.write_text(p.read_text().replace('assign wd_mem = data_at_macro;', 'assign wd_mem = wd; // deliberate missing stage'))
  f=[str(m) if x==str(p) else x for x in files]
 cmd=['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','-j','4','--Mdir','obj_'+mode,'tb.sv','mem.v']+f
 with open('build_'+mode+'.log','w') as o:subprocess.run(cmd,env=env,stdout=o,stderr=subprocess.STDOUT,check=True)
 for seed in ([1,7,99] if mode=='good' else [1]):
  q=subprocess.run([str(r/('obj_'+mode)/'Vtb'),'+SEED='+str(seed)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  Path(mode+'_'+str(seed)+'.log').write_text(q.stdout)
  if mode=='good':
   if q.returncode or 'PASS VSW_LB' not in q.stdout:print(q.stdout);raise SystemExit(1)
  else:
   if q.returncode==0 or 'DIFF cyc' not in q.stdout:print(q.stdout);raise SystemExit(2)
print('PASS 3 seeds all-cycle public outputs + missing-stage mutant caught')
