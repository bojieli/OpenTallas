#!/usr/bin/env python3
"""Deterministic legal shelf seed for the recovered P11 planner, not a physical closure."""
import argparse,json,math
from pathlib import Path
import hr_parent as H
p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--width',type=float,required=True);p.add_argument('--channel',type=float,default=129.6);a=p.parse_args()
L=43.2; gap=a.channel;snap=lambda x:round(math.ceil((x-1e-6)/L)*L,3)
assert a.width>0 and abs(a.width/L-round(a.width/L))<1e-6
items=[]
for i,(view,cell) in H.CLOSED.items():
 w,h,_=H.lef_pins(H.gshow(f'{view}/{cell}.lef'));items.append((i,w,h))
sh='u_ingest_qm__u_qm';en='u_ingest_qm__u_eng'
sw,ss=H.STANDIN[sh][1:3];ew,eh=H.STANDIN[en][1:3]
items += [(i,v[1],v[2]) for i,v in H.STANDIN.items() if i not in (sh,en)]
items.insert(0,('INGEST_PAIR',sw+gap+ew,max(ss,eh)))
x=y=gap;rh=0;place={}
for i,w,h in items:
 if x+w>a.width-gap:x=gap;y=snap(y+rh+gap);rh=0
 assert x+w<=a.width-gap,('outline too narrow',i,w)
 if i=='INGEST_PAIR':
  place[sh]=[x,y,'R0'];place[en]=[snap(x+sw+gap),snap(y+max(0,(ss-eh)/2)),'R0']
  h=max(ss,place[en][1]-y+eh)
 else:place[i]=[x,y,'R0']
 x=snap(x+w+gap);rh=max(rh,h)
height=max(a.width,snap(y+rh+gap))
a.output.write_text(json.dumps(dict(outline=[a.width,height],place=place,port_face={},status='DIAGNOSTIC legal shelf placement; no closure or relay timing claim'),indent=1)+'\n')
print('P11_SHELF',a.width,height,len(place))
