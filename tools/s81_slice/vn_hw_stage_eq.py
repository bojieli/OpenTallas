#!/usr/bin/env python3
"""Exact SRAM write-stage mechanism test; run via ot-run, output directory argv[1]."""
from pathlib import Path
import os,subprocess,sys,json
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
src=(root/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv').read_text()
(out/'st.sv').write_text(src[src.index('module ot_s81sl_hw_write_stage ('):])
(out/'tb.sv').write_bytes((Path(__file__).with_name('tb_vn_hw_stage.sv')).read_bytes())
(out/'mem.v').write_bytes((root/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v').read_bytes())
env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH']
summary={}
for mode,define in [('good',[]),('mutant',['-DOT_VNB_MUT_HW_FORWARD'])]:
 cmd=['verilator','--binary','--timing','--top-module','tb','-Wno-fatal','-j','4','--Mdir','obj_'+mode]+define+['st.sv','mem.v','tb.sv']
 with (out/('build_'+mode+'.log')).open('w') as f:subprocess.run(cmd,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in ([1,7,12345] if mode=='good' else [1]):
  p=subprocess.run([str(out/('obj_'+mode)/'Vtb'),'+SEED='+str(seed)],cwd=out,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  (out/(mode+'_'+str(seed)+'.log')).write_text(p.stdout)
  ok=(p.returncode==0 and 'PASS HW_STAGE exact 39998' in p.stdout) if mode=='good' else (p.returncode!=0 and 'DIFF cycle' in p.stdout)
  summary[mode+'_'+str(seed)]={'pass':ok,'returncode':p.returncode}
  if not ok:print(p.stdout);raise SystemExit(1)
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('PASS 119994 every-cycle comparisons; missing-forward mutant caught')
