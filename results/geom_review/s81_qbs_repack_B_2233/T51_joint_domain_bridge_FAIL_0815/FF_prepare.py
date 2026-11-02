"""One disabled joint-spread design: preserve bit/slot order, reserve companion DATA region; no CAD."""
from pathlib import Path
import json,gzip,collections,bisect,math
R=Path(__file__).parent;P=R/'inputs'
C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];N={c[0]:c for c in C};F=json.load(open(P/'FF_targets.json'));graph=json.load(gzip.open(P/'classification_graph.json.gz','rt'));E={graph['names'][i]for i in graph['eligible']};rows=json.load(open(P/'rows.json'));ys=sorted({r['origin_dbu'][1]for r in rows});rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for r in rows:rs[r['origin_dbu'][1]].append(r)
regs=json.load(open(P/'per_FF_regions.json'));regs=regs['t51'] if isinstance(regs,dict) and 't51'in regs else regs
print('REGIONTYPE',type(regs).__name__,flush=True)
A={x['name']:x for x in regs};M=set(A);assert len(M)==3192
core=json.load(open(P/'native_census.json'))['core_dbu']
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for c in C:
 if c[0]in M or c[0]in E:continue
 occupy(F[c[0]]['bbox_dbu']if c[0]in F else c[2])
for b in json.load(open(P/'other_declared_band_reservations.json'))['rectangles']:occupy(b['bbox_dbu'])
for y in occ:occ[y].sort()
pos={};desired={}
for n,a in A.items():
 c=N[n];x=(c[2][0]+c[2][2])/2;y=(c[2][1]+c[2][3])/2
 desired[n]=[6000+(x-17820)*1.25,y+259200] if a['family']=='ft2_ring' else [x,y+138240]
 pos[n]=list(desired[n])
# Coupled edge restrictions remain actual endpoint constraints, never an old-position lower-bound claim.
targets={n:t for n,t in F.items()if n not in M};failed=[]
for n in sorted(M,key=lambda n:(0 if A[n]['family']=='ft2_stage0'else 1,-len(A[n]['first_capture_pins']),n)):
 a=A[n];c=N[n];w=a['width_dbu'];h=a['height_dbu'];u0,u1,v0,v1=a['UV_bounds_dbu'];cx,cy=desired[n];maxjog=40000
 for nb in a['coupled_mover_neighbors']:
  x,y=pos[nb];u0=max(u0,x+y-404000);u1=min(u1,x+y+404000);v0=max(v0,x-y-404000);v1=min(v1,x-y+404000)
 best=None;phases=set(a['native_supply_phases'])
 for y in ys[bisect.bisect_left(ys,cy-h/2-maxjog):bisect.bisect_right(ys,cy-h/2+maxjog)]:
  yy=y+h/2;dy=abs(yy-cy)
  if dy>maxjog:continue
  for row in rs[y]:
   if row['orient']not in phases:continue
   lo=max(core[0],row['bbox_dbu'][0],u0-yy-w/2,v0+yy-w/2,cx-w/2-(maxjog-dy));hi=min(core[2]-w,row['bbox_dbu'][2]-w,u1-yy-w/2,v1+yy-w/2,cx-w/2+(maxjog-dy))
   if lo>hi:continue
   free=[];last=lo
   for aa,bb in occ[y]:
    if bb<=lo:continue
    if aa>=hi+w:break
    if aa>last:free.append((last,min(aa,hi+w)))
    last=max(last,bb)
   if last<hi+w:free.append((last,hi+w))
   for aa,bb in free:
    step=row['spacing_dbu'];rx=row['origin_dbu'][0];ia=math.ceil((aa-rx)/step);ib=math.floor((bb-w-rx)/step)
    if ib<ia:continue
    k=min(ib,max(ia,round((cx-w/2-rx)/step)));x=rx+k*step;jog=abs(x+w/2-cx)+dy;key=(jog,y,x)
    if best is None or key<best[0]:best=(key,[x,y,x+w,y+h],row)
 if best is None:failed.append(dict(name=n,desired_dbu=desired[n],UV=[u0,u1,v0,v1]));continue
 key,bb,row=best;occupy(bb)
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].sort()
 xy=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000];pos[n]=[v*1000 for v in xy]
 targets[n]=dict(master=c[1],bbox_dbu=bb,xy_um=xy,orient=c[4],family='ft2_stage0'if a['family']=='ft2_stage0'else'ft2_ring_band_FFs',desired_xy_um=[v/1000 for v in desired[n]],jog_um=key[0]/1000,row=row['name'],proposed_status='FIRM',original_bbox_dbu=c[2])
 if len(targets)%500==0:print('FF_ALLOC',len(targets),len(failed),flush=True)
(P/'joint_FF_targets.json').write_text(json.dumps(targets,indent=2));(R/'FF_preparation.json').write_text(json.dumps(dict(scope='DISABLED single joint ring+stage0+exclusiveDATA geometry, no CAD',ring_transport_y_um=259.2,ring_x_scale=1.25,ring_x_reference_um=17.82,ring_x_new_reference_um=6,stage0_transport_y_um=138.24,companion_owned_DATA_area_um2=849.31416,allocated=len(targets),requested_movers=len(M),failed=failed,unchanged_ft6_stage2=sum(n not in M for n in F),maximum_jog_um=max(t.get('jog_um',0)for t in targets.values()),no_new_FF_cycles_clockports_resetnodes=True),indent=2));print('FF_DONE',len(targets),'FAIL',len(failed),flush=True)
if failed:raise SystemExit('FF allocation incomplete: no DATA allocation or capacity claim')
