#!/usr/bin/env python3
import json,sys,collections,pickle
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'/'autopilot'))
import geom_rules as G
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
P=Path(__file__).parent
D=G.Design(sys.argv[1]);bad=[];nameid={c[6]:i for i,c in D.cells.items()};names={i:c[6] for i,c in D.cells.items()}
# Move internal source of each bad leg; a face input cannot move, so move its internal consumer.
move={nameid['u_fcore.u_bdc.jv']} if 'u_fcore.u_bdc.jv' in nameid else {next(i for n,i in nameid.items() if n.startswith('u_bdc.jv$_DFF') and D.cells[i][0]=='S')}
seq=[i for i,c in D.cells.items() if c[0]=='S'];bit={i:1<<n for n,i in enumerate(seq)};comb={i for i,c in D.cells.items() if c[0] in 'BLK'}
ind=collections.Counter();succ=collections.defaultdict(list);bs={};caps=collections.defaultdict(int)
for i in comb:
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]=='i' and not s[2] and s[1] in comb:succ[i].append(s[1]);ind[s[1]]+=1
for i in seq:
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in bit:caps[s[1]]|=bit[i]
   elif s[1] in comb:bs[s[1]]=bs.get(s[1],0)|bit[i]
q=collections.deque(i for i in comb if ind[i]==0)
while q:
 i=q.popleft();b=bs.get(i,0)
 for ni in D.drives.get(i,[]):
  for s in D.nets[ni][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in bit:caps[s[1]]|=b
   elif s[1] in comb:bs[s[1]]=bs.get(s[1],0)|b
 for j in succ[i]:
  ind[j]-=1
  if ind[j]==0:q.append(j)

xy={i:G.ctr(c) for i,c in D.cells.items()}
i=next(iter(move)); pairs=[]
for j,b in caps.items():
 while b:
  lo=b&-b;k=seq[lo.bit_length()-1];b-=lo
  if i in (j,k):pairs.append((k,j))
print('anchor',names[i],xy[i],'incident',len(pairs))
for x,y in [(100,239),(100,237),(102,237),(100,235),(102,235),(104,235)]:
 worst=[]
 for a,b in pairs:
  ax,ay=(x,y) if a==i else xy[a];bx,by=(x,y) if b==i else xy[b]
  worst.append((abs(ax-bx)+abs(ay-by),names[a],names[b]))
 print(x,y,sorted(worst,reverse=True)[:8])
print('blocks',[(c[1],c[2:6],c[6]) for c in D.cells.values() if c[0]=='M'])
json.dump(dict(anchor=names[i],original_xy=xy[i],incident_pairs=[dict(src=names[a],dst=names[b],src_xy=xy[a],dst_xy=xy[b]) for a,b in pairs]),open(P/'incident.json','w'),indent=2)
