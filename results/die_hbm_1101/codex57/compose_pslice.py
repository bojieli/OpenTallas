#!/usr/bin/env python3
"""Compose the exact NCX1 PSlice pin/macro/clock event into an unadopted HBM plan. No latency changes."""
import json,sys,gzip,shutil,fnmatch
from pathlib import Path
base,payload,out=map(Path,sys.argv[1:4]);assert not out.exists(),out
skip=['g0*','current*','specific*','minimal*','positive*','perbit_hops.json','core_faces_full.json','review*','repin*','render.log','plan.png','*.png']
shutil.copytree(base,out,ignore=lambda d,names:[n for n in names if any(fnmatch.fnmatch(n,k) for k in skip)])
raw=json.load(open(out/'die_plan.json')); col=json.load(open(payload/'column_plan.json'))
assert col['added_cycles']==0 and len(col['macro_placement'])==100
assert len({x['name'] for x in col['macro_placement']})==100
pins=json.load(gzip.open(payload/'pins_new.json.gz','rt'));cp=next(x for x in pins if x['name']=='clk');cx,cy=cp['x'],cp['y'];assert abs(cx/4.32-round(cx/4.32))<1e-8 and abs(cy/4.32-round(cy/4.32))<1e-8
newpf='cores/ot_hbm_su_programme_pslice_c5__939.6x760.32__ncx1_columns1101.json';json.dump(pins,open(out/newpf,'w'),indent=0)
macros=json.load(open(out/'core_macros.json'));m=macros['cores']['ot_hbm_su_programme_pslice_c5'];m['macros']=col['macro_placement'];m['basis']='CODEX 11-01: exact NCX1 pgcol c5e763929, logical-column affinity, seven macro columns / 35.064um vertical streets; fixed 4.32-grid density clock sites from the same recipe. Zero added cycles.'
entries=json.load(open(out/'clock_entries.json'));ledger=[]
for tn,t in raw['partition_types'].items():
 for hc in t.get('hard_cores',[]):
  if hc['module']!='ot_hbm_su_programme_pslice_c5':continue
  oldpf=hc['pins_file'];hc['pins_file']=newpf;hc['note']=hc.get('note','')+' | CODEX NCX1 column event, clock entry in reserved V street, no cycles'
  w,h=hc['outline_um'];ori=hc.get('orient','R0');x=w-cx if ori in ('MY','R180') else cx;y=h-cy if ori in ('MX','R180') else cy;dx,dy=hc.get('track_offset_um',[0,0]);xy=[round(hc['origin_um'][0]+dx+x,6),round(hc['origin_um'][1]+dy+y,6)]
  names={hc['inst'],hc['inst']+'.clk'};found=[]
  for tap in t['clock'].get('taps',[]):
   if tap['name'] in names:
    old=tap['xy'];tap['xy']=xy;tap['note']=tap.get('note','')+' | CODEX relocated exact NCX1 V-street clock pin';found.append(dict(name=tap['name'],old=old,new=xy))
  assert len(found)==1,(tn,hc['inst'],found)
  for ename,e in entries.get(tn,{}).items():
   if e.get('module')=='ot_hbm_su_programme_pslice_c5':
    e['xy_um']=[cx,cy];e['island_um']=[cx-4.32,cy-4.32,cx+4.32,cy+4.32];e['source']=e.get('source','')+' | CODEX NCX1 column event'
  ledger.append(dict(type=tn,inst=hc['inst'],old_pins=oldpf,new_pins=newpf,clock_tap=found[0],added_cycles=0))
assert len(ledger)==4
# Every clock driver island incl halo is in real macro whitespace; every macro fits the unchanged outline.
W,H=col['outline_um'];rects=[m['rect_um'] for m in col['macro_placement']]
for i,a in enumerate(rects):
 assert 0<=a[0]<a[2]<=W and 0<=a[1]<a[3]<=H
 for b in rects[:i]:assert min(a[2],b[2])<=max(a[0],b[0])+1e-6 or min(a[3],b[3])<=max(a[1],b[1])+1e-6
for x,y in col['clock_tap_sites_um']+[[cx,cy]]:
 a=[x-8.64,y-8.64,x+8.64,y+8.64]
 for b in rects:assert min(a[2],b[2])<=max(a[0],b[0])+1e-6 or min(a[3],b[3])<=max(a[1],b[1])+1e-6,(a,b)
json.dump(raw,open(out/'die_plan.json','w'),indent=0);json.dump(macros,open(out/'core_macros.json','w'),indent=0);json.dump(entries,open(out/'clock_entries.json','w'),indent=0);json.dump(dict(schema='opentallas.hbm.pslice_compose.v1',candidate=True,added_cycles=0,core_instances=ledger,macro_count=100,clock_site_count=len(col['clock_tap_sites_um']),unresolved='Whole candidate remains G1 FAIL on existing per-bit stations until their separate repair is folded in; parent native bus handoffs and G2 actual geometry still gate adoption.'),open(out/'pslice_compose_ledger.json','w'),indent=2)
print('COMPOSED',len(ledger),'instances,100macros,30clocksites,0cycles',out)
