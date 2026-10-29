#!/usr/bin/env python3
"""Scoped six-macro channel repair, same lane-exp body/pins/cycles."""
import json,os,shutil,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
cm=json.load(open(base/'core_macros.json'));m='ot_hbm_su_static_pgslice_lg__lane_exp0';rows=[]
for k,p in enumerate(cm['cores'][m]['macros']):
 old=p['rect_um'];x=[64.8,172.8,280.8][k%3];y=[53.73,118.8][k//3];p['rect_um']=[x,y,round(x+94.824,4),round(y+41.064,4)];rows.append({'name':p['name'],'old':old,'new':p['rect_um']})
cm['cores'][m]['basis']='CODEX same outline 3x2 SRAM grid;13.176um column and24.006um row channel; root103.68 horizontal street with4.32um halo'
for f in base.rglob('*'):
 r=f.relative_to(base);p=out/r
 if r==Path('core_macros.json'):continue
 if f.is_dir():p.mkdir(parents=True,exist_ok=True)
 elif f.is_file():
  p.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(f,p)
  except OSError:shutil.copy2(f,p)
(out/'core_macros.json').write_text(json.dumps(cm,indent=1))
mp={'macro_placement':[{'k':p['name'].removeprefix('u_fcore.'),'macro':'ot_sram_1r1w_128x256_m1_r2c2','origin_um':p['rect_um'][:2],'orient':'R0'} for p in cm['cores'][m]['macros']]}
(out/'lane_exp_macro_placement.json').write_text(json.dumps(mp,indent=1));(out/'lane_exp_macro_placement.est.json').write_text(json.dumps({'halo_um':4.32,'masters':{'ot_sram_1r1w_128x256_m1_r2c2':{'w':94.824,'h':41.064}}},indent=1))
(out/'lane_exp_macro_report.json').write_text(json.dumps({'module':m,'moves':rows,'outline_changed':False,'added_cycles':0,'parent_adoption_required':True},indent=1))
print('lane-exp6macros column_gap13.176 row_gap24.006 root_clear>=0.246')
