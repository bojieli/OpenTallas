#!/usr/bin/env python3
"""Current-plan geometric placement census for the production ROWX XM lot; no abstract fit claim."""
import json,sys
from pathlib import Path
src,out=sys.argv[1:];D=json.load(open(src));ps={p['name']:p for p in D['partitions']};rows=[]
def overlap(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
for name in ('svc_5','svc_11'):
 p=ps[name];t=D['partition_types'][p['type']];W,H=t['outline_um'];obs=[]
 for c in t.get('hard_cores',[]):
  x,y=c['origin_um'];ox,oy=c.get('track_offset_um',[0,0]);w,h=c['outline_um']
  if c.get('orient') in ('R90','R270','MXR90','MYR90'):w,h=h,w
  obs.append([x+ox-4.32,y+oy-4.32,x+ox+w+4.32,y+oy+h+4.32,c['inst']])
 tests=[]
 for w,h,label in ((475.2,604.8,'XM_recipe'),(604.8,475.2,'XM_rotated'),(171.288,153.912,'RP_SRAM'),(167.4,104.232,'LC_SRAM')):
  xs=sorted({4.32,W-w-4.32,*[x for b in obs for x in (b[2],b[0]-w)]});ys=sorted({4.32,H-h-4.32,*[y for b in obs for y in (b[3],b[1]-h)]})
  fits=[];best=None
  for x in xs:
   if x<4.32-1e-6 or x+w>W-4.32+1e-6:continue
   for y in ys:
    if y<4.32-1e-6 or y+h>H-4.32+1e-6:continue
    box=[x,y,x+w,y+h];hit=[b[4] for b in obs if overlap(box,b)]
    if not hit:fits.append(box)
    if best is None or len(hit)<best['overlap_cores']:best=dict(box_um=box,overlap_cores=len(hit),cores=hit)
  tests.append(dict(shape=label,outline_um=[w,h],valid_positions=len(fits),first_fit_um=fits[0] if fits else None,least_conflict=best))
 rows.append(dict(part=name,type=p['type'],orient=p.get('orient','R0'),origin_um=p['origin_um'],outline_um=[W,H],halo_um=4.32,hard_core_count=len(obs),hard_core_area_um2=sum(c['outline_um'][0]*c['outline_um'][1] for c in t.get('hard_cores',[])),obstacles=obs,tests=tests))
R=dict(schema='opentallas.s81.rowx_lot_census.v1',plan=src,kind='GEOMETRIC_PLANNING_ONLY',rows=rows,verdict='FAIL_CURRENT_LOT' if any(r['tests'][0]['valid_positions']==0 for r in rows) else 'CANDIDATE',note='Exact rectangle edge-candidate census against all72hardcore bodies+4.32um halo/type; no placement/routing/timing claimed.')
Path(out).write_text(json.dumps(R,indent=1)+'\n');print(json.dumps(dict(verdict=R['verdict'],rows=[dict(part=r['part'],tests=[{k:v for k,v in x.items() if k not in ('least_conflict','first_fit_um')} for x in r['tests']]) for r in rows])))
