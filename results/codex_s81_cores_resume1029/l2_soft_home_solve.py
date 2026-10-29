#!/usr/bin/env python3
"""Prospective soft L2 home solve: retain every cell and resolve physical endpoint reach.
No parent source adoption, synthesis, timing or clock claim.
"""
import bisect, collections, csv, gzip, json, math, re, sys
from pathlib import Path
root=Path(sys.argv[1]); data=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
x=json.load(gzip.open(root/'results/codex_s81_cores_1028/l2_soft/soft_l2_homes.json.gz','rt'))
ns={'__name__':'census'};saved=sys.argv;sys.argv=['census',str(root),str(out)]
exec((root/'results/codex_s81_cores_1028/l2_outline_estimate.py').read_text().split('old=cores')[0],ns);sys.argv=saved
cs,ps,point=ns['cores'],ns['pins'],ns['point']; targets=collections.defaultdict(list);legs=[]
for a in x['actual_soft_endpoint_reach']['direct']:
 inst,port=a['partner'].split('.',1);p=next(p for p in ps[inst] if p['name']==port);t=point(cs[inst],p)
 targets[a['ff_id']].append(t);legs.append(dict(a,target=t))
station=next(v for v in ns['type_']['internal_stations'] if v.get('conn')=='bus:unit_i0')['regs_um'][0]
for a in x['actual_soft_endpoint_reach']['station']:
 targets[a['ff_id']].append(station);legs.append(dict(a,target=station))
ff={v['id']:v for v in x['flops']};origin=x['parent_origin_um'];pitch=.054;rowheight=.27
center=lambda b:((b[0]+b[2])/2,(b[1]+b[3])/2)
def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
old={k:list(v['parent_bbox_um']) for k,v in ff.items()};oldmax=max(distance(center(old[v['ff_id']]),v['target'])for v in legs)
assert abs(oldmax-418.413)<.001,oldmax
limit=400.0
moving={k for k,ts in targets.items() if any(distance(center(old[k]),t)>limit for t in ts)}
byname={v['actual_kit_instance']:k for k,v in ff.items()}
rows=[dict(r,y=r['y']+origin[1])for r in x['rows']]
rowys=[round(r['y'],6)for r in rows];occupied=collections.defaultdict(list)
allcells=[]
for c in csv.DictReader(open(data/'placed.csv')):
 if c['kind']=='pin':continue
 k=byname.get(c['name']);b=[float(c['x'])+origin[0],float(c['y'])+origin[1],float(c['x'])+float(c['w'])+origin[0],float(c['y'])+float(c['h'])+origin[1]]
 allcells.append((c['name'],b,k))
 if k in moving:continue
 for ry in rowys:
  if b[1]<ry+rowheight-1e-6 and b[3]>ry+1e-6:occupied[ry].append((b[0],b[2]))
for ry in occupied:occupied[ry].sort()
# Reuse the ORIGINAL L2 slot, now parent soft area; the old narrow hard core isn't retained.
slot=cs['u_l2'];xmin=slot['origin_um'][0]+4.32;xmax=slot['origin_um'][0]+slot['outline_um'][0]-4.32
assert slot['outline_um']==[345.6,43.2],slot['outline_um']
homes={k:b[:]for k,b in old.items()};failed=[];moved=[]
for k in sorted(moving,key=lambda k:(-len(targets[k]),k)):
 b=old[k];w=b[2]-b[0];h=b[3]-b[1];best=None
 for r in rows:
  if r['orient']!=ff[k]['row_orient']:continue
  y=round(r['y'],6);cy=y+h/2;lo=xmin;hi=xmax-w
  for tx,ty in targets[k]:
   dx=limit-abs(cy-ty)
   lo=max(lo,tx-dx-w/2);hi=min(hi,tx+dx-w/2)
  if lo>hi:continue
  intervals=occupied[y];gaps=[];left=xmin
  for a,z in intervals:
   if a>left+1e-7:gaps.append((left,a-w))
   left=max(left,z)
  gaps.append((left,xmax-w))
  for a,z in gaps:
   a=max(a,lo);z=min(z,hi)
   ilo=math.ceil((a-xmin)/pitch-1e-6);ihi=math.floor((z-xmin)/pitch+1e-6)
   if ilo>ihi:continue
   ix=max(ilo,min(ihi,round((b[0]-xmin)/pitch)));xx=round(xmin+ix*pitch,6)
   score=abs(xx-b[0])+abs(y-b[1]);cand=(score,abs(y-b[1]),xx,y)
   if best is None or cand<best:best=cand
 if best is None:failed.append(k);continue
 _,_,xx,y=best;nb=[xx,y,round(xx+w,6),round(y+h,6)];homes[k]=nb
 bisect.insort(occupied[y],(nb[0],nb[2]));moved.append(dict(ff_id=k,instance=ff[k]['actual_kit_instance'],old_bbox=b,new_bbox=nb,manhattan_move_um=round(best[0],6),orient=ff[k]['orient']))
newlegs=[dict(v,new_um=round(distance(center(homes[v['ff_id']]),v['target']),6))for v in legs]
# All pairs in each row, including every unchanged logic/buffer/tap cell.
allnew=[(name,homes[k] if k is not None else b)for name,b,k in allcells]
rowitems=collections.defaultdict(list)
for name,b in allnew:
 for ry in rowys:
  if b[1]<ry+rowheight-1e-6 and b[3]>ry+1e-6:rowitems[ry].append((b[0],b[2],name))
overlaps=[]
for ry,iv in rowitems.items():
 iv.sort();end=-1e9;ename=None
 for a,z,n in iv:
  if a<end-1e-6:overlaps.append((ry,ename,n,end-a))
  if z>end:end=z;ename=n
covered={v.get('l2_port',v.get('port'))for v in legs};unconstrained=[a['port']for a in x['external']if a['port']not in covered]
summary=dict(scope='Prospective soft L2 placement only: no parent binding/source adoption, clock tree or timing qualification',old_max_um=oldmax,limit_um=limit,ff_count=len(ff),moving_ff_count=len(moving),moved=len(moved),failed_ff_ids=failed,new_max_um=max(v['new_um']for v in newlegs),new_over405=sum(v['new_um']>405 for v in newlegs),known_legs=len(legs),overlaps=overlaps,unconstrained_external_ports=unconstrained,max_move_um=max(v['manhattan_move_um']for v in moved),original_r2r_max_um=221.35,r2r_upper_bound_um=221.35+2*max(v['manhattan_move_um']for v in moved),preserved_orientations=True,preserved_all_other_placed_cells=len(allcells)-len(moving),parent_soft_original_slot=slot,added_cycles=0)
json.dump(summary,open(out/'summary.json','w'),indent=1)
json.dump(dict(summary=summary,moves=moved,homes={str(k):v for k,v in homes.items()},legs=newlegs),open(out/'homes.json','w'),indent=1)
print(json.dumps(summary,indent=1))
