#!/usr/bin/env python3
"""Plan ALL actual provider cells against immutable clock/hard-core geometry.
Proposal-only: soft partition OBS hits become explicit island requests, never
waivers. Actual import must check a freshly regenerated source's real OBS.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def contained(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--constraints',required=True);p.add_argument('--budget',required=True);p.add_argument('--out',required=True);a=p.parse_args();inv=json.load(open(a.inventory));g=json.load(open(a.constraints));budget=json.load(open(a.budget));D=g['dbu'];assert inv['schema']=='ot_start_provider_cells/1';assert budget['schema']=='ot_provider_placement_budget/1';assert budget['inventory_sha256']==sha(a.inventory),'stale all-cell budget';assert budget['all_cell_count']==len(inv['cells'])==inv['counts']['cells'];assert abs(sum(c['area_um2'] for c in inv['cells'])-budget['all_cell_area_um2'])<1e-5
 bystage=collections.defaultdict(list)
 for c in inv['cells']:
  m=g['masters'][c['master']];wh=[round(v*D) for v in c['wh_um']]
  if wh!=m['wh_dbu']:raise ValueError('actual LEF size differs: '+c['master'])
  bystage[c['stage']].append(c)
 sb={s['stage']:s for s in budget['stages']};assert set(sb)==set(bystage),'missing/extra stage budget'
 for st,cc in bystage.items():
  assert len(cc)<=sb[st]['max_cells'] and sum(c['area_um2'] for c in cc)<=sb[st]['max_area_um2']+1e-8,'all-cell stage budget exceeded: '+st
 hard=[r[1:] for r in g['hard_forbidden']]+[r[2:] for r in g['existing_cells']]+[r[2:] for r in g['actual_lower_PG']];ht=STRtree([box(*r) for r in hard]);soft=[r[2:] for r in g['actual_lower_OBS']];stree=STRtree([box(*r) for r in soft]);new=collections.defaultdict(list);B=8000
 grid=budget['row_grid_um'];assert grid['orient']=='R0';ox,oy=[round(v*D) for v in grid['origin']];dx=round(grid['site_pitch']*D);dy=round(grid['row_pitch']*D);assert dx>0 and dy>0
 def buckets(r):
  for x in range(r[0]//B,(r[2]-1)//B+1):
   for y in range(r[1]//B,(r[3]-1)//B+1):yield x,y
 def closest_slot(left,right,target):
  lo=math.ceil((left-ox)/dx);hi=math.floor((right-ox)/dx)
  if lo>hi:return None
  k=max(lo,min(round((target-ox)/dx),hi));return ox+k*dx
 def take(c,s,preferred):
  w,h=g['masters'][c['master']]['wh_dbu'];ff=[round(v*D) for v in s['legacy_ff_rect_um']];node=[round(v*D) for v in s['node_xy_um']];wins=([[round(v*D) for v in r] for r in s['ff_windows_um']] if c['sequential'] and s.get('ff_windows_um') else ([ff] if preferred else [[round(v*D) for v in r] for r in s['windows_um']]));best=[]
  for win in wins:
   # Budget bounds and die bounds apply to the WHOLE cell body.
   x0,y0,x1,y1=max(win[0],g['die_dbu'][0]),max(win[1],g['die_dbu'][1]),min(win[2],g['die_dbu'][2]),min(win[3],g['die_dbu'][3]);qr=box(x0,y0,x1,y1)
   nearby=[hard[int(i)] for i in ht.query(qr) if overlap([x0,y0,x1,y1],hard[int(i)])];seen=set()
   for z in buckets([x0,y0,max(x0+1,x1),max(y0+1,y1)]):
    for r in new[z]:
     t=tuple(r)
     if t not in seen:seen.add(t);nearby.append(r)
   rlo=math.ceil((y0-oy)/dy);rhi=math.floor((y1-h-oy)/dy)
   for k in sorted(range(rlo,rhi+1),key=lambda k:abs(oy+k*dy-ff[1])):
    y=oy+k*dy;intervals=[(x0,x1-w)]
    for r in nearby:
     if not (y<r[3] and r[1]<y+h):continue
     lo,hi=r[0]-w,r[2];out=[]
     for l,u in intervals:
      if hi<=l or u<=lo:out.append((l,u));continue
      if l<=lo:out.append((l,min(u,lo)))
      if hi<=u:out.append((max(l,hi),u))
     intervals=out
     if not intervals:break
    target=ff[0]
    for l,u in intervals:
     if l>u:continue
     x=closest_slot(l,u,target)
     if x is None:continue
     r=[x,y,x+w,y+h]
     if not contained(r,[x0,y0,x1,y1]) or any(overlap(r,z) for z in nearby):continue
     md=max(abs(xx-node[0])+abs(yy-node[1]) for xx in [r[0],r[2]] for yy in [r[1],r[3]])/D
     if s.get('max_anchor_displacement_um') is not None and md>s['max_anchor_displacement_um']+1e-9:continue
     best.append((abs(x-ff[0])+abs(y-ff[1]),r,md))
   if best:break
  return min(best,key=lambda z:(z[0],z[1]))[1:] if best else None
 output_launch={q.get('launch_inst') for q in inv.get('outputs',[])};placed=[];failed=[];soft_hits=0
 for j,(stage,cc) in enumerate(sorted(bystage.items(),key=lambda kv:(not bool(sb[kv[0]].get('ff_windows_um')),list(bystage).index(kv[0])))):
  s=sb[stage];cc.sort(key=lambda c:(c.get('role',c.get('cell_role','origin'))!='origin',not c['sequential'],c['inst'] not in output_launch,not bool(c.get('state_aliases')),c['inst']))
  for c in cc:
   got=take(c,s,True) if c['sequential'] and c.get('role',c.get('cell_role','origin'))=='origin' else None;legacy=got is not None
   if got is None:got=take(c,s,False)
   if got is None:failed.append(dict(inst=c['inst'],stage=stage,master=c['master'],reason='no legal complete-body slot in explicit all-cell budget'));continue
   r,md=got
   for z in buckets(r):new[z].append(r)
   overlaps=sorted({g['actual_lower_OBS'][int(i)][0] for i in stree.query(box(*r)) if overlap(r,soft[int(i)])});soft_hits+=bool(overlaps)
   placed.append(dict(inst=c['inst'],odb_inst='start_provider/'+c['inst'],stage=stage,master=c['master'],bbox_dbu=r,xy_dbu=r[:2],orient='R0',sequential=c['sequential'],legacy_ff_window=legacy,max_anchor_displacement_um=md,soft_OBS_hosts=overlaps))
  if j%250==0:print('stage',j,'placed',len(placed),'failed',len(failed),flush=True)
 result=dict(schema='ot_provider_placement/1',physical_qualified=False,diagnostic_only=True,source_constraints_sha256=sha(a.constraints),inventory_sha256=sha(a.inventory),budget_sha256=sha(a.budget),dbu=D,cells=placed,failed=failed,requires_fresh_soft_abstracts=soft_hits>0,summary=dict(all_cells=len(inv['cells']),placed=len(placed),failed=len(failed),sequential=sum(q['sequential'] for q in placed),comb=sum(not q['sequential'] for q in placed),sequential_in_legacy_FF_window=sum(q['sequential'] and q['legacy_ff_window'] for q in placed),actual_soft_OBS_overlaps=soft_hits,max_anchor_displacement_um=max((q['max_anchor_displacement_um'] for q in placed),default=0),verdict='PROPOSAL_READY_FOR_REVIEW_AND_EXPLICIT_ISLANDS' if not failed else 'PROPOSAL_INCOMPLETE_NO_IMPORT'))
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);json.dump(result,open(out/'placements.json','w'),separators=(',',':'));(out/'summary.json').write_text(json.dumps(result['summary'],indent=2)+'\n');print(json.dumps(result['summary'],indent=2))
if __name__=='__main__':main()
