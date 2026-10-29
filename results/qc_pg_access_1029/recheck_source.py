#!/usr/bin/env python3
"""Check a constructed PG candidate against a successor's actual native geometry.
No re-optimization, no abstract obstruction waiver, and no substitute for DRC/IR.
"""
import argparse,json,collections,numpy as np,shapely
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--geometry',required=True);p.add_argument('--old-geometry',required=True);p.add_argument('--plan',required=True);p.add_argument('--grid',required=True);p.add_argument('--out',required=True);a=p.parse_args();g=json.load(open(a.geometry));old=json.load(open(a.old_geometry));d=json.load(open(a.plan));pg=json.load(open(a.grid));assert sorted(g['cells'],key=lambda c:c['inst'])==sorted(old['cells'],key=lambda c:c['inst']),'Clock-body/master/orientation/bbox source delta requires new contact census';D=g['dbu'];gridkeys={(ly,*[round(v*D) for v in r]) for n,ly,*r in pg if ly in ['M8','M9']};bl=collections.defaultdict(list);owned=0
for owner,ly,*r in g['obstructions']:
 if owner=='BLOCK' and (ly,*r) in gridkeys:owned+=1
 else:bl[ly].append((owner,r))
for inst,pin,ly,*r in g['signal_shapes']:bl[ly].append((inst+'/'+pin,r))
trees={ly:STRtree(shapely.box(*np.asarray([r for owner,r in rr],dtype=np.int64).T)) for ly,rr in bl.items()}
su=collections.defaultdict(list)
for n,ly,*r in g['existing_supplies']:su[n,ly].append(r)
for n,ly,*r in pg:su[n,ly].append([round(v*D) for v in r])
suptrees={k:STRtree(shapely.box(*np.asarray(rr,dtype=np.int64).T)) for k,rr in su.items()};spacing={f'M{i}':v for i,v in enumerate([0,18,18,18,24,24,32,32,40,40]) if i};bad=[]
def hit(r,s):return r[0]<s[2] and s[0]<r[2] and r[1]<s[3] and s[1]<r[3]
for qi,q in enumerate(d['paths']):
 x,y=q['stack'];xx,yy,ex,ey=q['m8'];n=q['net'];opp='VSS' if n=='VDD' else 'VDD'
 ss=[('M1',x-9,y-11,x+9,y+11),('M2',x-25,y-9,x+25,y+9),('M3',x-9,y-25,x+9,y+25),('M4',x-48,y-12,x+48,y+12),('M5',x-12,y-48,x+12,y+48),('M6',x-40,y-16,x+40,y+16),('M7',x-16,min(y-40,yy-40),x+16,max(y+40,yy+40)),('M8',x-96,yy-20,x+96,yy+20),('M8',min(x,ex)-40,yy-20,max(x,ex)+40,yy+20),('M9',ex-20,yy-20,ex+20,yy+20)]
 errs=[]
 for ly,*r in ss:
  sp=spacing[ly];w=[r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp];bb=box(*w)
  if ly in trees:
   for j in trees[ly].query(bb):
    owner,br=bl[ly][j]
    if hit(w,br):errs.append(dict(layer=ly,metal=r,obstacle_owner=owner,obstacle=br));break
  if (opp,ly) in suptrees:
   for j in suptrees[opp,ly].query(bb):
    br=su[opp,ly][j]
    if hit(w,br):errs.append(dict(layer=ly,metal=r,opposite_supply=opp,obstacle=br));break
 if errs:bad.append(dict(group=qi,net=n,members=q['members'],conflicts=errs))
 if qi%10000==0:print(qi,'bad',len(bad),flush=True)
s=dict(source=g['source'],actual_clock_cells=len(g['cells']),actual_signal_rectangles=len(g['signal_shapes']),actual_obstructions=len(g['obstructions']),exact_owned_grid_obstructions=owned,checked_groups=len(d['paths']),contacts=sum(len(q['members']) for q in d['paths']),failing_groups=len(bad),failures=bad,verdict='PASS_ACTUAL_SOURCE_GEOMETRY' if not bad else 'FAIL_SOURCE_GEOMETRY_REPLAN_REQUIRED');json.dump(s,open(a.out,'w'),indent=2);print({k:v for k,v in s.items() if k!='failures'},flush=True)
