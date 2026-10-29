#!/usr/bin/env python3
"""Opt-in paired physical ABI delta for the proven native one-clock wrapper.
Use recipe-key MODULE__oneclk; native source uses guarded specialize_instances.
No body/latency move. Parent die/clock/bind rebuild required before routing.
"""
import json,os,shutil,sys
from pathlib import Path
base,out,receipt=map(Path,sys.argv[1:4]);proof=json.load(open(receipt))
assert proof['result']=='PASS' and len(proof['instances'])==8
assert all(x['equal'] and x['hbm_clk']==x['stream_clk'] and len(x['hbm_clk'])==1 for x in proof['instances'])
out.mkdir(parents=True,exist_ok=False);d=json.load(open(base/'die_plan.json'));ce=json.load(open(base/'clock_entries.json'));rows=[];newfiles={}
for tn,t in d['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if not c['module'].startswith('ot_hbm_svc_vm_kshare_splitstrap__'):continue
  f=c['pins_file'];nf=f[:-5]+'__oneclk.json'
  if f not in newfiles:
   pins=json.load(open(base/f));ps=[p for p in pins if p['name']!='stream_clk'];assert len(ps)==len(pins)-1
   newfiles[f]=(nf,ps)
  c['pins_file']=nf
  e=ce[tn][c['inst']];e['port']='hbm_clk';e['merged_clock_ports']=[];e['tap']=c['inst']+'.hbm_clk';e['source']='One physical hbm_clk feeds both proven identical native source clocks via ot_hbm_svc_vm_kshare_oneclk; original TT/FF targets unchanged'
  rows.append({'type':tn,'instance':c['inst'],'module':c['module'],'recipe_key':c['module']+'__oneclk','removed_alias':'stream_clk','retained_clock':'hbm_clk','added_cycles':0})
assert len(rows)==8,len(rows)
for f in base.rglob('*'):
 r=f.relative_to(base);p=out/r
 if p.exists() or r.name in ['die_plan.json','clock_entries.json']:continue
 if f.is_dir():p.mkdir(parents=True,exist_ok=True)
 elif f.is_file():
  p.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(f,p)
  except OSError:shutil.copy2(f,p)
for _,(nf,x) in newfiles.items():p=out/nf;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=1))
d['die']['label']='Kshare exact one-clock physical ABI | '+d['die']['label']
for f,x in [('die_plan.json',d),('clock_entries.json',ce)]: (out/f).write_text(json.dumps(x,indent=1))
(out/'kshare_oneclk_report.json').write_text(json.dumps({'schema':'opentallas.hbm.kshare_oneclk.v1','native_sameclock_proof':str(receipt),'instances':rows,'body_moves':0,'added_cycles':0,'source_helper':'tools/hbm_b2/kshare_oneclock.py:specialize_instances','die_rebuild_required':True},indent=1))
print('kshare oneclock8 instances removed8 redundantports cycles0')
