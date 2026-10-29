#!/usr/bin/env python3
"""Check actual .192x.080 M8 landing geometry against clock and power metal.
Emits corrected PG reservations, never changes an earlier verdict.
"""
import argparse,json,collections
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser()
p.add_argument('--plan',required=True);p.add_argument('--power-access');p.add_argument('--additional-power-access',action='append',default=[]);p.add_argument('--pg',required=True);p.add_argument('--out',required=True);p.add_argument('--source-geometry',help='Fresh actual source geometry; M6/M7 signal, obstruction and native supply shapes remain blocking')
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
plan=json.load(open(a.plan));records=plan['records'];clock=[];clock_owner=[];reserved=[]
for ri,r in enumerate(records):
 x,y=r['backbone_xy_um'][0],r['m8_witness_y_um'];n=r['net']
 clock_owner.extend([ri]*(len(r['geometry'])+1));clock.extend(r['geometry']);clock.append([n,'M8',x-.096,y-.04,x+.096,y+.04])
 reserved.extend(r['geometry']);reserved.append([n,'M8',x-.376,y-.32,x+.376,y+.32])
json.dump(reserved,open(out/'joint_clock_reserved.json','w'),separators=(',',':'))
geometry=collections.defaultdict(list);labels=collections.defaultdict(list)
for i,r in enumerate(clock):
 n,l,*xy=r;geometry[l].append(box(*xy));labels[l].append(('clock',n,clock_owner[i]))
for source in [a.pg,a.power_access]+a.additional_power_access:
 if not source:continue
 for n,l,*xy in json.load(open(source)):
  if l not in ['M6','M7','M8']:continue
  geometry[l].append(box(*xy));labels[l].append(('power',n,None))
if a.source_geometry:
 g=json.load(open(a.source_geometry));D=g['dbu']
 for rows in [g['signal_shapes'],g['obstructions'],g['existing_supplies']]:
  for r in rows:
   if rows is g['signal_shapes']:owner,pin,l,*xy=r;owner+='/'+pin
   else:owner,l,*xy=r
   if l not in ['M6','M7']:continue
   geometry[l].append(box(*[v/D for v in xy]));labels[l].append(('source',owner,None))
 del g
trees={l:STRtree(g) for l,g in geometry.items()};fail=[];counts=collections.Counter();bad_records=set()
for i,(n,l,*xy) in enumerate(clock):
 sp=.32 if l=='M8' else .032;b=box(*xy)
 for j in trees[l].query(b.buffer(sp,cap_style=3,join_style=2)):
  owner,other,other_record=labels[l][j]
  if owner=='clock' and n==other:continue
  d=b.distance(geometry[l][j])
  if d+1e-7<sp:
   counts[l+'_'+owner]+=1
   bad_records.add(max(clock_owner[i],other_record) if owner=='clock' else clock_owner[i])
   if len(fail)<100:fail.append(dict(net=n,layer=l,rect=xy,other=other,owner=owner,distance_um=d,required_um=sp))
 if i%100000==0:print('RECHECK',i,len(clock),dict(counts),flush=True)
repair_failures=list(plan['failures'])+[dict(cell=r['cell'],pin=r['pin'],net=r['net'],base_xy_um=r['entry_xy_um']) for i,r in enumerate(records) if i in bad_records]
json.dump(dict(status='FAIL' if repair_failures else 'PASS_GEOMETRY',records=[r for i,r in enumerate(records) if i not in bad_records],failures=repair_failures,removed_records=len(bad_records),physical_route=False),open(out/'repair_plan.json','w'),separators=(',',':'))
summary=dict(removed_records=len(bad_records),verdict='FAIL' if counts or plan['failures'] else 'PASS_GEOMETRY',records=len(records),unplanned=len(plan['failures']),clock_rectangles=len(clock),M8_landing_um=[.192,.080],violations=dict(counts),examples=fail,physical_route=False)
json.dump(summary,open(out/'summary.json','w'),indent=2);print(summary,flush=True)
