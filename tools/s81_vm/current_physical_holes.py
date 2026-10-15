#!/usr/bin/env python3
"""Exact empty-rectangle capacity screen with all existing local leaf vectors fixed.
Reports actual hard leaf rectangles that cannot fit; never turns remaining area into a fit claim.
"""
import argparse,json,pathlib,time

def intersect(a,b):return a[0]<b[0]+b[2]-1e-7 and a[0]+a[2]>b[0]+1e-7 and a[1]<b[1]+b[3]-1e-7 and a[1]+a[3]>b[1]+1e-7

def subtract(free,b):
 out=[]
 for r in free:
  if not intersect(r,b):out.append(r);continue
  x,y,w,h=r;X,Y,W,H=b
  if X>x:out.append([x,y,X-x,h])
  if X+W<x+w:out.append([X+W,y,x+w-X-W,h])
  if Y>y:out.append([x,y,w,Y-y])
  if Y+H<y+h:out.append([x,Y+H,w,y+h-Y-H])
 # Keep maximal empty rectangles only. Shared free-space fragments are intentional.
 out=[r for r in out if min(r[2:])>1e-6];out.sort(key=lambda r:-r[2]*r[3]);keep=[]
 for r in out:
  if not any(r[0]>=q[0]-1e-6 and r[1]>=q[1]-1e-6 and r[0]+r[2]<=q[0]+q[2]+1e-6 and r[1]+r[3]<=q[1]+q[3]+1e-6 for q in keep):keep.append(r)
 return keep

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();r=a.root;inv=json.loads((r/'inventory.json').read_text());packing=json.loads((r/'packing.json').read_text());leaves=inv['leaves'];fixed_ids={x['leaf']for x in packing['source_binding']};base=packing['options'][0];reports=[]
 for gap in [21.6,10.8,0]:
  t=time.monotonic();free=[[0,0,3952.8,4903.2]];pos={str(i):base['positions'][str(i)]for i in fixed_ids}
  for i in fixed_ids:
   x,y=pos[str(i)];w,h=leaves[i]['outline_um'];free=subtract(free,[x-gap/2,y-gap/2,w+gap,h+gap])
  fail=[]
  for i in sorted(set(range(len(leaves)))-fixed_ids,key=lambda i:(-leaves[i]['outline_um'][0]*leaves[i]['outline_um'][1],-max(leaves[i]['outline_um']))):
   w,h=leaves[i]['outline_um'];ww,hh=w+gap,h+gap;candidates=[]
   for f in free:
    x,y,W,H=f
    if W+1e-6>=ww and H+1e-6>=hh:candidates.append((min(W-ww,H-hh),max(W-ww,H-hh),y,x,f))
   if not candidates:fail.append(i);continue
   _,_,y,x,_=min(candidates);pos[str(i)]=[x+gap/2,y+gap/2];free=subtract(free,[x,y,ww,hh])
  collisions=[];ids=list(map(int,pos))
  for k,i in enumerate(ids):
   for j in ids[k+1:]:
    if intersect(pos[str(i)]+leaves[i]['outline_um'],pos[str(j)]+leaves[j]['outline_um']):collisions.append([i,j])
  assert not collisions
  reports.append(dict(name=f'body2x2_holes_gap{gap:g}',outline_um=[3952.8,4903.2],minimum_new_leaf_gap_um=gap,preserved_local_rectangles=len(fixed_ids),placed_hard_leaves=len(pos),unplaced_hard_leaves=[dict(leaf=i,path=leaves[i]['path'],outline_um=leaves[i]['outline_um'])for i in fail],positions=pos,collision_count=len(collisions),runtime_seconds=time.monotonic()-t,status='RECTANGLE_CAPACITY_ONLY_PARENT_HARDWARE_AND_ALL_TRAFFIC_OPEN',free_maximal_rectangle_count=len(free)))
 for option in list(reports):
  if option['minimum_new_leaf_gap_um']!=21.6:continue
  fail=[x['leaf']for x in option['unplaced_hard_leaves']]
  for sideW in [216,324,432,540,648,864]:
   pos=dict(option['positions']);rows=[];height=0
   for i in sorted(fail,key=lambda i:(-leaves[i]['outline_um'][1],-leaves[i]['outline_um'][0])):
    w,h=leaves[i]['outline_um'];eligible=[(rr[1]-w,j)for j,rr in enumerate(rows)if rr[1]>=w and rr[2]>=h]
    if eligible:
     _,j=min(eligible);y,free,rh,x=rows[j];rows[j]=[y,free-w-21.6,rh,x+w+21.6]
    else:y=height;x=0;rows.append([y,sideW-w-21.6,h,w+21.6]);height=y+h+21.6
    pos[str(i)]=[3952.8+21.6+x,y]
   reports.append(dict(name=f'body2x2_holes_gap21.6_spill{sideW:g}',outline_um=[3952.8+21.6+sideW,max(4903.2,height-21.6)],minimum_new_leaf_gap_um=21.6,preserved_local_rectangles=len(fixed_ids),placed_hard_leaves=len(pos),unplaced_hard_leaves=[],positions=pos,collision_count=0,status='ALL640_RECTANGLE_CAPACITY_ONLY_PARENT_HARDWARE_AND_ALL_TRAFFIC_OPEN',spilled_actual_leaf_count=len(fail)))
 (r/'holes.json').write_text(json.dumps(dict(hard_leaf_area_sum_mm2=sum(x['outline_um'][0]*x['outline_um'][1]for x in leaves)/1e6,body_rectangle_area_mm2=3952.8*4903.2/1e6,options=reports),indent=1)+'\n');print(json.dumps([{k:q.get(k)for k in ['name','outline_um','placed_hard_leaves','collision_count','runtime_seconds']}for q in reports],indent=1))
if __name__=='__main__':main()
