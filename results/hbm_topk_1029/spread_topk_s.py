#!/usr/bin/env python3
"""Copy a plan SRC -> fresh OUT and spread TOPK selected_line on S only.
Preserve every other pin, clocks, outline, RTL, station and latency. Report actual
per-bit station reach with orientation; this is not a route approval.
"""
import argparse,copy,hashlib,json,math,shutil
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('src',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
src=a.src.resolve();out=a.out.resolve();assert src.is_dir() and not out.exists(),'SRC must exist and OUT must be fresh';assert src!=out and src not in out.parents,'OUT must be outside SRC'
plan=json.loads((src/'die_plan.json').read_text());mods=[]
for tn,t in plan['partition_types'].items():
 for c in t.get('hard_cores',[]):
  if c.get('module')=='ot_hbm_idx_topk_link_static':mods.append((tn,t,c))
assert mods,'no TOPK core in plan';updates={};report=[]
def transform(c,p):
 x,y=p['x'],p['y'];w,h=c['outline_um'];o=c.get('orient','R0')
 if o=='MY':x=w-x
 elif o=='MX':y=h-y
 elif o=='R180':x,y=w-x,h-y
 elif o!='R0':raise ValueError('unsupported orientation '+o)
 return [c['origin_um'][0]+x,c['origin_um'][1]+y]
def census(c,ps,station):
 # Station records use unordered connectivity labels, not port directions.
 path=station.get('regs_um') or []
 if not path:return {'status':'NO REGISTERED STATION; requires die-owner review'}
 is_from=station.get('launch','').startswith(c['inst']+'.selected_line') or station.get('conn','').split('|')[0].startswith(c['inst']+'.selected_line')
 s=path[0] if is_from else path[-1]
 ds=[sum(abs(v-z) for v,z in zip(transform(c,p),s)) for p in ps]
 return {'station_um':s,'bits':len(ds),'min_um':round(min(ds),3),'max_um':round(max(ds),3),'over_405':sum(d>405+1e-6 for d in ds),'source_note':'actual pin centres + core origin/orientation, nearest end of declared register chain; old from_um/to_um are NOT trusted'}
for tn,t,c in mods:
 pf=c['pins_file'];old=json.loads((src/pf).read_text());new=copy.deepcopy(old);by={p['name']:p for p in old};sel=[p for p in new if p['name'].startswith('selected_line[')];sel.sort(key=lambda p:int(p['name'].split('[')[1][:-1]));assert len(sel)==2368
 W,H=c['outline_um'];assert all(p['layer']=='M5' and p['y']<1 for p in sel),'S/M5 pin precondition failed';pitch=.24;span=pitch*(len(sel)-1);start=round((W-span)/2/.048)*.048
 assert span/W>=.8 and start>4.32 and start+span<W-4.32,'outline cannot hold requested span'
 fixed=[p for p in old if not p['name'].startswith('selected_line[')]
 for i,p in enumerate(sel):
  p['x']=round(start+i*pitch,3)
  for q in fixed:
   if q['layer']==p['layer'] and abs(q['y']-p['y'])<.6:
    assert abs(q['x']-p['x'])>=.096-1e-6,'fixed-pin collision: '+q['name']
 assert all(p==by[p['name']] for p in new if not p['name'].startswith('selected_line[')),'nonselected pin changed'
 if pf in updates:assert updates[pf]==new,'inconsistent shared pin table'
 updates[pf]=new
 stations=[s for s in t.get('internal_stations',[]) if c['inst']+'.selected_line' in s.get('conn','')]
 rows=[]
 for s in stations:rows.append({'conn':s['conn'],'declared_from_um':s.get('from_um'),'declared_to_um':s.get('to_um'),'before':census(c,[by[p['name']] for p in sel],s),'after':census(c,sel,s)})
 report.append({'type':tn,'inst':c['inst'],'pins_file':pf,'outline_um':c['outline_um'],'orient':c.get('orient','R0'),'changed_pins':len(sel),'new_span_um':round(span,3),'face_fraction':round(span/W,6),'pitch_um':pitch,'new_peak_20um_pins':84,'cycles_added':0,'station_reach':rows,'route_verdict':'HOLD: actual endpoint reach must pass; density-only spreading does not fix stale station coordinates'})
shutil.copytree(src,out)
for pf,ps in updates.items():(out/pf).write_text(json.dumps(ps,indent=1)+'\n')
assert (out/'die_plan.json').read_bytes()==(src/'die_plan.json').read_bytes()
result={'schema':'opentallas.topk_s_pin_spread.v1','source_plan_sha256':hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),'changed_files':sorted(updates),'preserved':'all other files incl die_plan, outlines, clocks, station locations and latency','changes':report};(out/'topk_s_spread_report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
