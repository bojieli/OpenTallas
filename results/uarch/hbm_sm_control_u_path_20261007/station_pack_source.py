#!/usr/bin/env python3
"""Constructive station-box reservation on candidate control paths."""
import argparse, hashlib, json, math
from pathlib import Path

def point(path,s):
 for a,b in zip(path,path[1:]):
  d=abs(a[0]-b[0])+abs(a[1]-b[1])
  if s<=d+1e-7:return [a[k]+(b[k]-a[k])*min(1,s/d) for k in range(2)]
  s-=d
 return list(path[-1])

def overlap(a,b,gap=0):return max(a[0]-gap,b[0])<min(a[2]+gap,b[2])-1e-7 and max(a[1]-gap,b[1])<min(a[3]+gap,b[3])-1e-7

def pack(rows,obstacles):
 boxes=[]; out=[]
 for r in rows:
  if 'failure'in r:continue
  path=r['path_um'];L=r['path_length_um'];P=r['descriptor_bridge_HOPS'];rec={'sm':r['sm'],'P':P,'stations':[],'conflicts':[]}
  for stage in range(P):
   base=(L-72.96)*stage/(P-1)
   for rail in (range(3,-1,-1) if stage==P-1 else range(4)):
    s=base+rail*24.32
    candidates=[s]+[s+sign*k*2.16 for k in range(1,21) for sign in (-1,1)]
    for candidate in candidates:
     if not 0<=candidate<=L:continue
     if stage==0 and candidate>87.84:continue
     if stage==P-1 and candidate<L-87.84:continue
     centre=point(path,candidate);box=[centre[0]-10,centre[1]-10,centre[0]+10,centre[1]+10]
     if any(overlap(box,other,2.16)for _,other in obstacles) or any(overlap(box,z['box_um'],2.16)for z in boxes):continue
     s=candidate;break
    c=point(path,s);b=[c[0]-10,c[1]-10,c[0]+10,c[1]+10]
    item={'sm':r['sm'],'stage':stage,'rail':rail,'bits':57 if rail<2 else 3,'direction':'forward'if rail<2 else'reverse','arc_distance_um':s,'box_um':b}
    bad=[name for name,box in obstacles if overlap(b,box,2.16)]
    bad += [f"{z['sm']}/stage{z['stage']}/rail{z['rail']}" for z in boxes if overlap(b,z['box_um'],2.16)]
    if bad:rec['conflicts'].append({'stage':stage,'rail':rail,'obstacles':bad})
    rec['stations'].append(item);boxes.append(item)
  out.append(rec)
 max_segment=max(b['arc_distance_um']-a['arc_distance_um'] for r in out for rail in range(4) for ss in [sorted([z for z in r['stations'] if z['rail']==rail],key=lambda z:z['stage'])] for a,b in zip(ss,ss[1:]))
 return {'max_same_rail_link_arc_um':max_segment,'max_link_design_um':300,'link_budget_pass':max_segment<=300,'status':'constructive candidate packing only; actual pins/views unqualified','primitive_bits':64,'station_shape_um':[20,20],'minimum_gap_um':2.16,'station_count':len(boxes),'station_area_um2':len(boxes)*400,'rows':out,'conflict_count':sum(len(r['conflicts'])for r in out)}

if __name__=='__main__':
 parser=argparse.ArgumentParser(description="Provisional four primitive stations per control stage; no physical closure claim")
 parser.add_argument('geometry',type=Path);parser.add_argument('paths',type=Path);parser.add_argument('output',type=Path)
 args=parser.parse_args()
 p=json.loads(args.geometry.read_text());r=json.loads(args.paths.read_text())
 obs=[(i['name'],i['box_um'])for i in p['insts']]+[(k+':'+b['sm'],b['box_um'])for k in ('native_owner_bays','native_descriptor_bays','result_pin_bays')for b in p[k]]
 o=pack(r['rows'],obs)
 o['sources']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (args.geometry,args.paths,Path(__file__))}
 o['gates']=['Actual primitive shape and protected dual-copy RTL binding', 'Actual owner/adapter per-bit pins and endpoint reach', 'Shared full-traffic tracks, clock, reset and PDN', 'Routed SS/FF timing and DRC']
 args.output.write_text(json.dumps(o,indent=2)+'\n')
 print(json.dumps({k:o[k] for k in ('station_count','station_area_um2','conflict_count','max_same_rail_link_arc_um','link_budget_pass')}))
