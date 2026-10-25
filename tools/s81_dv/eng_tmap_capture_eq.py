#!/usr/bin/env python3
# Run via ot-run: OUTPUT_DIR
from pathlib import Path
import subprocess,os,json
import sys
root=Path(__file__).resolve().parents[2]
r=Path(sys.argv[1]).resolve();r.mkdir(parents=True,exist_ok=True)
(r/'tb.sv').write_bytes(Path(__file__).with_name('tb_eng_tmap_capture.sv').read_bytes())
src=(root/'rtl/dsrom_sys/s81_dv/eng/ot_s81eng_rr_n32.sv').read_text();a=src.index('module ot_s81eng_token_bit #(');b=src.index('\nmodule ot_s81eng_win_n32',a);(r/'src.sv').write_text(src[a:b])
os.chdir(r);env=dict(os.environ);env['PATH']=str(Path.home()/'.local/opentallas-tools/bin')+':'+env['PATH'];summary={}
for mode,defs in [('good',[]),('mutant',['-DOT_S81ENG_MUT_TMAP_TAG'])]:
 with open('build_'+mode+'.log','w') as f:subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','-j','4','--Mdir','obj_'+mode]+defs+['src.sv','tb.sv'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 for seed in ([1,7,12345] if mode=='good' else [1]):
  q=subprocess.run([str(r/('obj_'+mode)/'Vtb'),'+SEED='+str(seed)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);Path(mode+'_'+str(seed)+'.log').write_text(q.stdout)
  ok=(q.returncode==0 and 'PASS TMAP exact ALL 34 outputs' in q.stdout)if mode=='good' else(q.returncode!=0 and 'DIFF cycle' in q.stdout)
  summary[mode+'_'+str(seed)]={'pass':ok,'rc':q.returncode}
  if not ok:print(q.stdout);raise SystemExit(1)
Path('summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('PASS TMAP 299985 cycles ALLoutputs + wrongtagmutant caught')
