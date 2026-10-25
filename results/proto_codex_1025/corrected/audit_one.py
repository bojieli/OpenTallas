"""Cheap per-type planned FT audit: reach/core sites plus explicit cell envelopes.
Station0 uses facepin coordinates for reach; its physical cell packing is left
 to face_flops. Footprint checks cover explicit internal stage cell envelopes.
"""
import argparse,json,math
from pathlib import Path
from collections import defaultdict
from scan import scan,S,g2

def footprints(P,tn):
 t=P.types[tn];boxes=S.placed_macro_boxes(t)
 for c in g2.probe_blockages(t):
  if c['inst'] not in boxes:
   x,y=c['origin_um'];w,h=c['outline_um'];boxes[c['inst']]=(x,y,x+w,y+h)
 cores=list(boxes.values())
 cells=[]
 for slot in t.get('ft_slots',[]):
  if not slot.get('bit_sites_um'):continue
  w,h=slot['bit_site_cell_um']
  for stage,points in enumerate(slot['bit_sites_um'],1):
   for bit,(x,y) in enumerate(points):cells.append((slot['name'],stage,bit,(x,y,x+w,y+h)))
 if not cells:return dict(scope='explicit internal stage envelopes only; station0 pin packing not modeled',cells=0,core_intersections=0,overlaps=0,outside_outline=0,examples=[])
 bw=max(r[3][2]-r[3][0] for r in cells);bh=max(r[3][3]-r[3][1] for r in cells);bins=defaultdict(list);core_count=0;ov=0;outside=0;examples=[];W,H=t['outline_um']
 def hit(a,b):return min(a[2],b[2])-max(a[0],b[0])>1e-6 and min(a[3],b[3])-max(a[1],b[1])>1e-6
 for idx,(slot,stage,bit,r) in enumerate(cells):
  if any(hit(r,c) for c in cores):core_count+=1
  if r[0]<-1e-6 or r[1]<-1e-6 or r[2]>W+1e-6 or r[3]>H+1e-6:outside+=1
  keys=[(x,y) for x in range(math.floor(r[0]/bw),math.floor((r[2]-1e-7)/bw)+1) for y in range(math.floor(r[1]/bh),math.floor((r[3]-1e-7)/bh)+1)]
  other=set(j for key in keys for j in bins[key])
  for j in other:
   if hit(r,cells[j][3]):
    ov+=1
    if len(examples)<10:examples.append({'a':[slot,stage,bit],'b':list(cells[j][:3]),'a_rect':r,'b_rect':cells[j][3]})
  for key in keys:bins[key].append(idx)
 return dict(scope='explicit internal stage envelopes only; station0 pin packing not modeled',cells=len(cells),core_intersections=core_count,overlaps=ov,outside_outline=outside,examples=examples)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('--type',required=True);ap.add_argument('--out');a=ap.parse_args();P=S.Plan(S.load(a.plan));r=scan(P,a.type);r['footprints']=footprints(P,a.type);f=r['footprints'];bad=bool(r['failures'] or f['core_intersections'] or f['overlaps'] or f['outside_outline']);r.update(type=a.type,verdict='FAIL' if bad else 'PASS',source_plan=str(Path(a.plan).resolve()))
 if a.out:Path(a.out).write_text(json.dumps(r,indent=1)+'\n')
 print(a.type,r['verdict'],'max_hop_um',r['max_hop_um'],'station_centers_in_core',r['st_in_core'],'cell_core_intersections',f['core_intersections'],'cell_overlaps',f['overlaps'],'outside',f['outside_outline'],flush=True);return int(bad)
if __name__=='__main__':raise SystemExit(main())
