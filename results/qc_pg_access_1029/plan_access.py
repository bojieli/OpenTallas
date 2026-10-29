#!/usr/bin/env python3
"""Construct power-first access from actual contacts; all dimensions are integer DBU.
No abstract obstruction is waived. A bridge rises inside its legal opening to M8,
then reaches an actual same-net M9 grid stripe. This is geometry, not IR closure.
"""
import argparse,json,collections,math,time
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--clock-seed',required=True,help='Actual fixed future clock lower-layer metal rectangles in um');p.add_argument('--limit',type=int,default=0);p.add_argument('--joint-clock-reserved',help='Clock access reservation rectangles [net,layer,x0,y0,x1,y1] in um; M8 shield clearance already included minus normal 40nm PG clearance');a=p.parse_args();src=Path(a.input);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
g=json.load(open(src/'geometry.json'));terms=json.load(open(src/'power_terms.json'))['terms'];ep=json.load(open(src/'endpoints.json'))['endpoints'];pg=json.load(open(src/'pg_rects.json'));tech=json.load(open(src/'probe_census.json'))['tech_vias_dbu'];D=g['dbu'];spacing={f'M{i}':v for i,v in enumerate([0,18,18,18,24,24,32,32,40,40]) if i}
blocked=collections.defaultdict(list)
grid_keys={(ly,*[round(v*D) for v in r]) for n,ly,*r in pg if ly in ['M8','M9']}
owned_grid_obs=0
for owner,ly,*r in g['obstructions']:
 if owner=='BLOCK' and (ly,*r) in grid_keys:owned_grid_obs+=1
 else:blocked[ly].append(r)
print('exact_owned_grid_obstructions',owned_grid_obs,flush=True)
for _,_,ly,*r in g['signal_shapes']:blocked[ly].append(r)
for e in ep.values():blocked[e['layer']].append([round(v*D) for v in e['rect_um']])
for n,ly,*r in json.load(open(a.clock_seed)):blocked[ly].append([round(v*D) for v in r])
if a.joint_clock_reserved:
 for n,ly,*r in json.load(open(a.joint_clock_reserved)):blocked[ly].append([round(v*D) for v in r])
trees={ly:STRtree([box(*r) for r in rr]) for ly,rr in blocked.items()}
supply=collections.defaultdict(list)
for n,ly,*r in g['existing_supplies']:supply[n,ly].append(r)
for n,ly,*r in pg:supply[n,ly].append([round(v*D) for v in r])
for t in terms:
 for ly,*r in t['shapes_dbu']:supply[t['pin'],ly].append(r)
suptrees={k:STRtree([box(*r) for r in rr]) for k,rr in supply.items()}
# Rail grouping only uses exact same-y, overlapping or abutting native metal.
rows=collections.defaultdict(list)
for t in terms:
 assert len(t['shapes_dbu'])==1
 ly,x0,y0,x1,y1=t['shapes_dbu'][0];assert ly=='M1' and t['orient']=='R0'
 rows[t['pin'],y0,y1].append((x0,x1,t['inst']))
groups=[]
for (n,y0,y1),rr in rows.items():
 rr.sort();cur=None
 for x0,x1,inst in rr:
  if cur and x0<=cur[1]:cur[1]=max(cur[1],x1);cur[2].append(inst)
  else:
   if cur:groups.append((n,cur[0],y0,cur[1],y1,cur[2]))
   cur=[x0,x1,[inst]]
 if cur:groups.append((n,cur[0],y0,cur[1],y1,cur[2]))
groups.sort(key=lambda q:(q[2],q[1],q[0]));print('groups',len(groups),flush=True)
stripes={n:sorted([tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=='M9']) for n in ['VDD','VSS']}
# Opposite proposed conductors are indexed in fine bins. No large die-wide bins.
new=collections.defaultdict(lambda:collections.defaultdict(list));B=4000
reasons=collections.Counter(); examples={}

def binrect(r):
 x0,y0,x1,y1=r
 for x in range(x0//B,x1//B+1):
  for y in range(y0//B,y1//B+1):yield x,y

def hit(r,s):return r[0]<s[2] and s[0]<r[2] and r[1]<s[3] and s[1]<r[3]
def clear(n,ly,r):
 sp=spacing[ly];q=[r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp]
 if q[0]<0 or q[1]<0 or q[2]>g['die_dbu'][2] or q[3]>g['die_dbu'][3]:return False
 b=box(*q)
 if ly in trees and any(hit(q,trees[ly].geometries[j].bounds) for j in trees[ly].query(b)):
  reasons['obstacle_'+ly]+=1
  if ly not in examples:examples[ly]=dict(candidate=r,blocking=list(trees[ly].geometries[trees[ly].query(b)[0]].bounds))
  return False
 opp='VSS' if n=='VDD' else 'VDD'
 if (opp,ly) in suptrees and any(hit(q,suptrees[opp,ly].geometries[j].bounds) for j in suptrees[opp,ly].query(b)):return False
 return not any(hit(q,s) for k in binrect(q) for s in new[opp,ly].get(k,[]))

def stack(x,y):
 sh=[('M1',x-9,y-11,x+9,y+11),('M2',x-25,y-9,x+25,y+9),('M3',x-9,y-25,x+9,y+25),('M4',x-48,y-12,x+48,y+12),('M5',x-12,y-48,x+12,y+48),('M6',x-40,y-16,x+40,y+16),('M7',x-16,y-40,x+16,y+40)]
 return sh
shapes=[];vias=[];paths=[];failed=[]
for gi,(n,x0,y0,x1,y1,members) in enumerate(groups):
 if a.limit and gi>=a.limit:break
 # Land outward by 2nm so VIA12's 22nm M1 box does not consume the native 18nm A/Y spacing.
 y=(y0+y1)//2+(2 if n=='VDD' else -2);par=0 if n=='VDD' else 1
 xs=range(math.ceil((x0+50-32-64*par)/128),math.floor((x1-50-32-64*par)/128)+1)
 xs=sorted((32+64*par+128*k for k in xs),key=lambda x:abs(x-(x0+x1)/2))
 ys=sorted((40+80*par+160*k for k in range(math.floor((y-1400-40-80*par)/160),math.ceil((y+1400-40-80*par)/160)+1)),key=lambda yy:abs(yy-y))
 found=None
 for x in xs:
  ss=stack(x,y)
  if not all(clear(n,ly,list(r)) for ly,*r in ss):continue
  # Nearest actual same-net stripe landing; retain its full via89 enclosure.
  dst=sorted(stripes[n],key=lambda r:max(r[0]+20-x,0,x-r[2]+20))
  for yy in ys:
   stem=('M7',x-16,min(y-40,yy-40),x+16,max(y+40,yy+40))
   land=('M8',x-96,yy-20,x+96,yy+20) # 7680 DBU^2 >= actual M8 minimum AREA7520
   if not clear(n,stem[0],list(stem[1:])) or not clear(n,land[0],list(land[1:])):continue
   for sx0,sy0,sx1,sy1 in dst[:3]:
    if not sy0+20<=yy<=sy1-20:continue
    xx=max(sx0+20,min(x,sx1-20))
    bridge=('M8',min(x,xx)-40,yy-20,max(x,xx)+40,yy+20)
    end=('M9',xx-20,yy-20,xx+20,yy+20)
    if clear(n,'M8',list(bridge[1:])) and clear(n,'M9',list(end[1:])):
     found=ss+[stem,land,bridge,end],x,yy,xx;break
   if found:break
  if found:break
 if not found:failed.append(dict(net=n,rail=[x0,y0,x1,y1],members=members))
 else:
  ss,x,yy,xx=found
  for ly,*r in ss:
   shapes.append([n,ly,*r])
   for k in binrect(r):new[n,ly][k].append(r)
  vv=[(f'VIA{i}{i+1}',x,y) for i in range(1,7)]+[('VIA78',x,yy),('VIA89',xx,yy)]
  for vn,vx,vy in vv:
   vias.append([n,vn,vx,vy])
   for ly,ax,ay,bx,by in tech[vn]:
    if not ly.startswith('M'):continue
    r=[vx+ax,vy+ay,vx+bx,vy+by];shapes.append([n,ly,*r])
    for k in binrect(r):new[n,ly][k].append(r)
  paths.append(dict(net=n,members=members,rail=[x0,y0,x1,y1],stack=[x,y],m8=[x,yy,xx,yy]))
 if gi%1000==0:print(gi,'ok',len(paths),'fail',len(failed),flush=True)
json.dump(dict(source=g['source'],paths=paths,vias_dbu=vias,failed=failed,dbu=D),open(out/'access_plan.json','w'),separators=(',',':'))
json.dump([[n,ly,*[v/D for v in r]] for n,ly,*r in shapes],open(out/'reserved_access.json','w'),separators=(',',':'))
s=dict(groups=len(groups),attempted=len(paths)+len(failed),connected_groups=len(paths),connected_contacts=sum(len(q['members']) for q in paths),failed_groups=len(failed),routing_rectangles=len(shapes),vias=len(vias),verdict='GEOMETRY_CANDIDATE' if not failed else 'INCOMPLETE_NO_MATERIALIZATION')
s['owned_grid_obstructions']=owned_grid_obs;s['rejections']=dict(reasons);s['obstacle_examples']=examples
json.dump(s,open(out/'summary.json','w'),indent=2);print(s,flush=True)
