#!/usr/bin/env python3
"""HBM unfrozen measured macro repair: relocate keybuf root out of SRAM column."""
import copy,hashlib,json,os,shutil,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=False)
mod='ot_hnx_idxn_keybuf_slice';d=json.load(open(base/'die_plan.json'));ce=json.load(open(base/'clock_entries.json'));cm=json.load(open(base/'core_macros.json'));report=[];files={}
macros=[{'name':f'u_fcore.gm[{k}].mem','master':'ot_sram_1r1w_256x256_m2_r2c2','orient':'R0','rect_um':[24.84,round(15.12+k*51.84,4),197.64,round(56.16+k*51.84,4)]} for k in range(5)]
for tn,t in d['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c['module']!=mod:continue
  e=ce[tn][c['inst']];old=copy.deepcopy(e)
  e['xy_um']=[207.384,146.88];e['island_um']=[203.04,142.56,211.68,151.2];e['source']='CODEX keybuf five-SRAM static column: E-channel entry, no latency/cycle change; die rebuild required'
  f=c['pins_file'];nf=f[:-5]+'__codex_entry.json';files[f]=nf;c['pins_file']=nf
  report.append({'type':tn,'instance':c['inst'],'old_entry':old,'new_entry':copy.deepcopy(e)})
for f,nf in files.items():
 pins=json.load(open(base/f))
 for p in pins:
  if p['name']=='clk':p.update(layer='M5',x=207.384,y=146.88,w=.048,h=.48)
 target=out/nf;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(pins,indent=1))
cm['cores'][mod]={'status':'KNOWN','outline_um':[241.92,293.76],'basis':'production keybuf source gm[0..4].mem; LEF172.8x41.04; explicit stacked five SRAMs','macros':macros,'recipe_macros':['ot_sram_1r1w_256x256_m2_r2c2']}
for f in base.rglob('*'):
 r=f.relative_to(base);p=out/r
 if p.exists() or r.name in ['die_plan.json','clock_entries.json','core_macros.json']:continue
 if f.is_dir():p.mkdir(parents=True,exist_ok=True)
 elif f.is_file():
  p.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(f,p)
  except OSError:shutil.copy2(f,p)
d['die']['label']='Keybuf macro-column clock-entry repair | '+d['die']['label']
for name,x in [('die_plan.json',d),('clock_entries.json',ce),('core_macros.json',cm)]: (out/name).write_text(json.dumps(x,indent=1))
mp={'macro_placement':[{'k':m['name'].removeprefix('u_fcore.'),'macro':m['master'],'origin_um':m['rect_um'][:2],'orient':'R0'} for m in macros]}
(out/'keybuf_macro_placement.json').write_text(json.dumps(mp,indent=1))
(out/'keybuf_macro_placement.est.json').write_text(json.dumps({'halo_um':4.32,'masters':{'ot_sram_1r1w_256x256_m2_r2c2':{'w':172.8,'h':41.04}}},indent=1))
(out/'keybuf_entry_report.json').write_text(json.dumps({'schema':'opentallas.hbm.keybuf_entry.v1','base_sha256':hashlib.sha256((base/'die_plan.json').read_bytes()).hexdigest(),'instances':report,'body_moves':0,'added_cycles':0,'die_rebuild_required':True,'old_verdict':'FAIL root overlaps SRAM column','new_verdict':'PREP requires fresh kit geometry and die clock/rebuild'},indent=1))
print('keybuf entry instances',len(report),'body_moves0 added_cycles0 die_rebuild_required')
