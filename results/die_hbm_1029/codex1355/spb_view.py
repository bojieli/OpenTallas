#!/usr/bin/env python3
"""Prepare SPB-only physical pin views from the winning modeled PHY escape LEF.
Source/ABI/clock/outline unchanged. Caller must compose native four-stage transport,
plan endpoints and actual clock/reset/PG, and obtain geometry review before route.
"""
import json,re,sys,hashlib,shutil,os
from pathlib import Path
src,lef,out=map(Path,sys.argv[1:4]);raw=json.load(open(src/'die_plan.json'));text=lef.read_text().split('MACRO EP_SPB_PROBE')[0];data={}
for m in re.finditer(r'PIN ((?:rx|tx)\[\d+\])(.*?)END \1',text,re.S):
 layer=re.search(r'LAYER (\w+)\s*;',m[2])[1];r=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2]);x0,y0,x1,y1=map(float,r.groups())
 data[m[1]]=dict(name=m[1],layer=layer,x=(x0+x1)/2,y=(y0+y1)/2-34.56,w=x1-x0,h=y1-y0)
assert len(data)==1024 and all(p['layer']=='M7' for p in data.values())
out.mkdir(parents=True,exist_ok=True);(out/'cores').mkdir(exist_ok=True)
for f in src.iterdir():
 if f.name in ['die_plan.json','cores']:continue
 d=out/f.name
 if not d.exists():os.symlink(f.resolve(),d)
for f in (src/'cores').iterdir():
 d=out/'cores'/f.name
 if not d.exists():os.symlink(f.resolve(),d)
changed=[];written={}
for tn,t in raw['partition_types'].items():
 if tn!='q_spb0' and not tn.startswith('q_spb0__'):continue
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_pdie_serdes':continue
  old=h['pins_file'];pins=json.load(open(src/old));names={p['name'] for p in pins}
  assert set(data)<=names and h['outline_um']==[600.048,600.48]
  result=[dict(p,**{k:v for k,v in data[p['name']].items() if k!='name'}) if p['name'] in data else p for p in pins]
  assert {p['name'] for p in result}==names
  assert all(0<=p['x']<=600.048 and 0<=p['y']<=600.48 for p in result)
  new=old[:-5]+'__spbV3_m67.json';(out/new).write_text(json.dumps(result,indent=1));h['pins_file']=new
  changed.append(dict(type=tn,inst=h['inst'],old=old,new=new,data_pins=1024,clock_reset_unchanged=True,source_and_cycle_changes=0))
assert len(changed)==2,len(changed)
raw['die']['label']='SPB V3 modeled escape physical-view PREP | '+raw['die'].get('label','')
(out/'die_plan.json').write_text(json.dumps(raw,indent=1));report=dict(schema='hbm.spb_view.v1',qualification='PREP_ONLY_NO_ADOPTION',source_sha=hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),winning_lef_sha=hashlib.sha256(lef.read_bytes()).hexdigest(),changes=changed,holds=['Independent geometry review','Native four-stage source/FF contract and actual parent clock/reset/PG','Update stored station endpoint geometry then resite','Regenerate affected PHY view before die GRT'])
(out/'spb_view_report.json').write_text(json.dumps(report,indent=1));print(json.dumps(report,indent=1))
