#!/usr/bin/env python3
"""R4 structural trial: keep frozen island sites; exact equal-load sink membership.
Five clock stages (root/M/Q/B/leaf), no entry pad, strongest internal trunks.
Coordinates and membership derive only from GEOM-reviewed placement, before CTS.
"""
import argparse,json,math,re
from collections import defaultdict
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('geo');p.add_argument('old_plan');p.add_argument('out');a=p.parse_args()
old=json.loads(Path(a.old_plan).read_text());sinks=[];macros=[]
for line in Path(a.geo).read_text().splitlines():
 f=line.split()
 if not f:continue
 if f[0]=='CORE':box=tuple(map(float,f[1:5]))
 if f[0]=='SINK':sinks.append((float(f[1]),float(f[2]),f[4],f[5]))
 if f[0]=='MACRO':macros.append((f[1],tuple(map(float,f[3:7])),tuple(map(float,f[8:10]))))
assert len({x[2:] for x in sinks})==len(sinks)
entry=old['entry_pin'];sites=[x['centre_um'] for x in old['leaf_islands']]
d=lambda p,q:abs(p[0]-q[0])+abs(p[1]-q[1])
def pairid(sink):
 name=sink[2].replace(chr(92), '')
 m=re.match(r'^g_(?:wr|mw)\[([01])\]\.(?:g_r\.)?u_d/q\[([0-9]+)\]\$_DFF_P_$',name)
 return ('mif',*m.groups()) if m else ('single',sink[2],sink[3])
def chunks(points,n,key):
 # Existing zero-logic MIF register pairs are atomic same-leaf groups.
 units=defaultdict(list)
 for point in points:units[pairid(point)].append(point)
 seq=sorted(units.values(),key=lambda g:key(g[0]))
 out=[];start=0;cum=0
 for i,g in enumerate(seq):
  if len(out)<n-1 and i>start and abs(cum-len(points)*(len(out)+1)/n)<=abs(cum+len(g)-len(points)*(len(out)+1)/n):
   out.append([v for unit in seq[start:i] for v in unit]);start=i
  cum+=len(g)
 out.append([v for unit in seq[start:] for v in unit])
 assert len(out)==n and all(out)
 return out
def spatial(points,n):
 out=[points]
 while len(out)<n:
  new=[]
  for g in out:
   ax=int(max(x[1] for x in g)-min(x[1] for x in g)>max(x[0] for x in g)-min(x[0] for x in g))
   new.extend(chunks(g,2,lambda x:(x[ax],x[1-ax],x[2])))
  out=new
 return out
def free(q):
 return box[0]+1<=q[0]<=box[2]-2 and box[1]+1<=q[1]<=box[3]-1 and not any(r[0]-1<q[0]<r[2]+1 and r[1]-1<q[1]<r[3]+1 for _,r,_ in macros)
def legal(q):
 if free(q):return q
 for step in range(1,600):
  r=step*.5
  for dx,dy in [(r,0),(-r,0),(0,r),(0,-r),(r,r),(-r,r),(r,-r),(-r,-r)]:
   v=(q[0]+dx,q[1]+dy)
   if free(v):return v
 raise ValueError('no legal clock node')
def centre(g):return legal((sum(x[0] for x in g)/len(g),sum(x[1] for x in g)/len(g)))
def local_leaves(group):
 c=centre(group)
 if len(group)<=60 and max(d(c,p) for p in group)<=25:
  return [group]
 if len({pairid(p) for p in group})<2:
  raise ValueError('atomic clock pair cannot meet local radius')
 return [small for g in spatial(group,2) for small in local_leaves(g)]
def quote(s):
 assert '{' not in s and '}' not in s
 return '{'+s+'}'
# Preserve angular equal-load quadrants and map each group to its nearest unique frozen island.
angle=lambda x:math.atan2(x[1]-entry[1],x[0]-entry[0])
A=sorted(angle(x) for x in sinks);cut=max(range(len(A)),key=lambda i:(A[(i+1)%len(A)]-A[i])%(2*math.pi));a0=A[(cut+1)%len(A)]
groups=chunks(sinks,4,lambda x:((angle(x)-a0)%(2*math.pi),x[2]))
order=sorted((d(centre(g),s),gi,si) for gi,g in enumerate(groups) for si,s in enumerate(sites));used=set();mapping={}
for _,gi,si in order:
 if gi not in mapping and si not in used:mapping[gi]=si;used.add(si)
node=[];leaves=[];fixed=[('ot_ms_root','BUFx24_ASAP7_75t_R',entry)]
for gi,g in enumerate(groups):
 qi=mapping[gi];qs=sites[qi]
 # Use a legal route midpoint through the SRAM-edge channel, never a point in a macro.
 routes=[[entry,(qs[0],entry[1]),qs],[entry,(entry[0],qs[1]),qs]]
 def mid(route):
  lens=[d(x,y) for x,y in zip(route,route[1:])];v=sum(lens)/2
  for (x,y),l in zip(zip(route,route[1:]),lens):
   if v<=l:return (x[0]+(y[0]-x[0])*v/l,x[1]+(y[1]-x[1])*v/l)
   v-=l
 best=min((legal(mid(r)) for r in routes),key=lambda m:d(entry,m)+d(m,qs))
 node.extend([(f'M{qi}','root',best,'BUFx24_ASAP7_75t_R'),(f'Q{qi}',f'M{qi}',qs,'BUFx24_ASAP7_75t_R')]);fixed.append((f'ot_ms_Q{qi}_nd','BUFx24_ASAP7_75t_R',qs))
 for bi,b in enumerate(spatial(g,4)):
  bn=f'Q{qi}B{bi}';node.append((bn,f'Q{qi}',centre(b),'BUFx24_ASAP7_75t_R'))
  for li,l in enumerate([small for g in spatial(b,8 if len(sinks)>3840 else 4) for small in local_leaves(g)]):
   leaves.append((f'{bn}L{li}',bn,centre(l),'BUFx24_ASAP7_75t_R',l))
mac=[]
for name,rect,ck in macros:
 site=legal((ck[0]-2 if ck[0]-rect[0]<rect[2]-ck[0] else ck[0]+2,ck[1]));leaf=min(leaves,key=lambda l:d(l[2],site));mac.append((name,leaf[0],site))
lines=['# R4 equal-load exact named sink membership; no post-CTS decisions','set ot_ms_port ck',f'set ot_ms_root {{{entry[0]} {entry[1]}}}','set ot_h_entry_n 0','set ot_h_fixed {']
lines+=[' {%s %s %.3f %.3f}'%(n,c,xy[0],xy[1]) for n,c,xy in fixed];lines+=['}','set ot_ms_tree {']
lines+=[' {%s %s %.3f %.3f %s}'%(n,p,xy[0],xy[1],c) for n,p,xy,c in node];lines+=['}','set ot_ms_leaves {']
for n,p,xy,c,g in leaves:
 regs=' '.join('{'+quote(x[2])+' '+quote(x[3])+'}' for x in g)
 lines.append(' {%s %s {%.3f %.3f} {%s} %s}'%(n,p,xy[0],xy[1],regs,c))
lines+=['}','set ot_ms_macros {']
lines+=[' {%s %s {%.3f %.3f}}'%(quote(n),l,xy[0],xy[1]) for n,l,xy in mac];lines+=['}']
Path(a.out).write_text('\n'.join(lines)+'\n')
report=dict(type=old['type'],entry=entry,sinks=len(sinks),leaves=len(leaves),leaf_load=[min(len(g) for *_,g in leaves),max(len(g) for *_,g in leaves)],clock_stages=5,entry_chain=0,fixed_cells=fixed,nodes=node,leaf_nodes=[(n,p,xy,c,len(g)) for n,p,xy,c,g in leaves],macros=mac,source_geometry=a.geo,leaf_assignments=[dict(name=n,parent=pa,xy_um=xy,cell=c,sinks=[x[2]+'/'+x[3] for x in g]) for n,pa,xy,c,g in leaves])
Path(a.out+'.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:report[k] for k in ['type','sinks','leaves','leaf_load','clock_stages','entry_chain']}))
