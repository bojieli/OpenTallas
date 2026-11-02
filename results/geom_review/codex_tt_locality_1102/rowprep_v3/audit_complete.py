"""Audit completed row candidate with frozen16 source slots; no new placement/solve."""
from pathlib import Path
import json,collections,math
P=Path(__file__).parent
# Reuse the exact finite solve's typed graph/source translation and frozen slots.
exec((P/'rowprep_greedy.py').read_text().split('# Place the most constrained')[0])
homes=json.loads((P/'rowprep_complete_homes.json').read_text())
if {h['name'] for h in homes}!={d.cells[i][6] for i in variables}:raise ValueError('Incomplete solved-home coverage')
for h in homes:
 i=names[h['name']];c=d.cells[i];w,hh=c[4]-c[2],c[5]-c[3];x,y=h['xy'];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
# All original FFs except the replaced S1/S2/PD, plus the same frozen16 new states.
boxes={c[6]:c[2:6] for i,c in d.cells.items() if c[0]=='S' and c[1]!='REAL_MACRO_PORT' and i not in oinv}
for h in source:
 name=f"SOURCE:{h['stage']}:{h['region']}"
 if name in boxes:raise ValueError('Duplicate source slot')
 boxes[name]=h['box']
if len(boxes)!=38244:raise ValueError('Not the exact38244FF cohort')
rowfail=[];boundsfail=[];body=[];overlaps=set();bins=collections.defaultdict(list)
def overlap(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
for name,b in boxes.items():
 if b[0]<4.32-1e-6 or b[1]<4.32-1e-6 or b[2]>773.28+1e-6 or b[3]>514.08+1e-6:boundsfail.append(name)
 if abs(b[0]/.054-round(b[0]/.054))>1e-5 or abs(b[1]/.27-round(b[1]/.27))>1e-5:rowfail.append(name)
 for m in macros:
  if overlap(b,m):body.append(dict(name=name,box=b,macro_box=m))
 near=set()
 for x in range(math.floor(b[0]/8.64),math.floor(b[2]/8.64)+1):
  for y in range(math.floor(b[1]/8.64),math.floor(b[3]/8.64)+1):near.update(bins[x,y])
 for other in near:
  if overlap(b,boxes[other]):overlaps.add(tuple(sorted((name,other))))
 for x in range(math.floor(b[0]/8.64),math.floor(b[2]/8.64)+1):
  for y in range(math.floor(b[1]/8.64),math.floor(b[3]/8.64)+1):bins[x,y].append(name)
# Re-evaluate all actual typed captures in each receiving region's source context.
original_origin={i:d.cells[i] for i in oinv};globalraw=d.cells[rawid];reach=[];count=0;worst=0
for r in [-1,0,1,2,3]:
 for i,st in oinv.items():
  c=orig[i];x,y=fixed[st,max(r,0)];w,hh=c[4]-c[2],c[5]-c[3];d.cells[i]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
 if r<0:d.cells[rawid]=globalraw
 else:
  c=orig[rawid];x,y=fixed['raw',r];w,hh=c[4]-c[2],c[5]-c[3];d.cells[rawid]=(c[0],c[1],x-w/2,y-hh/2,x+w/2,y+hh/2,c[6])
 pairs=[];g.r2r_metrics(d,pairs,0)
 for z in pairs:
  ci=names[z['capture']];scope=z['capture'].split('/')[0]
  if ci in oinv:
   if r<0:continue
  elif ci==rawid:pass
  elif scope in regions:
   if regions[scope]!=r:continue
  elif r!=-1:continue
  count+=1;worst=max(worst,z['distance_um'])
  if z['distance_um']>405.00005:reach.append(dict(**z,region=r))
d.cells.update(original_origin);d.cells[rawid]=globalraw
# Preserve the exact existing63-port assignment, not a new nearest-tap variant.
clockfail=[];clockworst=0;loads=collections.Counter()
for a in clock['assignments']:
 name=a['name'];tap=a['parent_tap'];loads[tap]+=1
 if name in names:pt=g.ctr(d.cells[names[name]])
 else:pt=a['xy'] # Frozen new source/macro ITerm coordinates were not moved.
 x,y=pins[tap]['x'],pins[tap]['y'];dist=abs(pt[0]-x)+abs(pt[1]-y);clockworst=max(clockworst,dist)
 if dist>200.00005:clockfail.append(dict(name=name,parent_tap=tap,distance_um=dist))
pinfail=[]
for i,pt in pin_targets.items():
 x,y=g.ctr(d.cells[i]);dist=abs(x-pt[0])+abs(y-pt[1])
 if dist>30.00005:pinfail.append(dict(name=d.cells[i][6],distance_um=dist))
passed=not any((rowfail,boundsfail,body,overlaps,reach,clockfail,pinfail)) and count==45301 and max(loads.values())<=1200
out=dict(status='PASS_COMPLETE_ROW_SOURCE_MODEL_ONLY' if passed else 'HELD',physical_release=False,ff_count=len(boxes),source_slots_frozen=16,added_ff=13,cycles_added=0,all_typed_captures=count,max_reach_um=worst,row_fail=rowfail,bounds_fail=boundsfail,macro_body_fail=body,ff_overlap=sorted(overlaps),reach_fail=reach,clock_reach_fail=clockfail,max_clock_reach_um=clockworst,max_clock_load=max(loads.values()),pin_reach_fail=pinfail,native_name_master_join='HELD: actual fresh mapped source required',placement_applied=False)
(P/'complete_row_audit.json').write_text(json.dumps(out,indent=1)+'\n')
print('COMPLETE_ROW_AUDIT',out['status'],len(boxes),'FF',count,'typed captures',flush=True)
