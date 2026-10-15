#!/usr/bin/env python3
"""Freeze an existing case placement, dimensions and bus bindings for pad trials.
Uses case LEF pin centroids for R0; other orientations use pinned generator offsets.
This is a prototype geometry model, not real-view closure evidence.
"""
import argparse,json,re,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_die_seam'));import extract
ap=argparse.ArgumentParser();ap.add_argument('case');ap.add_argument('template');ap.add_argument('out');a=ap.parse_args()
base=str(Path(a.case))+'/';I,B=extract.parse(base+'die.v')
old=json.load(open(a.template));templates={}
oi={i['n']:i for i in old['insts']}
for ep,p in old['endpoint_pos'].items():
 n,port=ep.split('.');i=oi[n];templates.setdefault((i['m'],i.get('orient','R0'),port),[p[0]-i['x'],p[1]-i['y']])
lef=open(base+'elements.lef').read()+open(base+'phy_ew.lef').read();dims={};lef_points={}
for m,body in re.findall(r'MACRO (\w+)(.*?)END \1',lef,re.S):
 z=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body);dims[m]=list(map(float,z.groups()))
 for pin,pb in re.findall(r'PIN (\S+)(.*?)END \1',body,re.S):
  rects=[list(map(float,r)) for r in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',pb)]
  if rects:
   port=pin.split('[')[0];acc=lef_points.setdefault((m,port),[]);acc.extend([(r[0]+r[2])/2,(r[1]+r[3])/2] for r in rects)
insts=[];P={};missing=[]
for n,x,y,o in re.findall(r'findInst (\w+)\] ([\d.]+) ([\d.]+) (\w+)',open(base+'place.tcl').read()):
 m,ports=I[n];x=float(x);y=float(y);w,h=dims[m];insts.append(dict(n=n,m=m,x=x,y=y,w=w,h=h,orient=o))
 for port in ports:
  off=templates.get((m,o,port))
  if o=='R0' and (m,port) in lef_points:
   pts=lef_points[m,port];off=[sum(p[k] for p in pts)/len(pts) for k in (0,1)]
  if off:P[n+'.'+port]=[x+off[0],y+off[1]]
  else:missing.append((n,m,o,port))
assert not [m for m in missing if m[3] in ('a','b','n_a','n_b','t_out','n_y')],missing[:10]
net=collections.defaultdict(list)
for n,(m,ports) in I.items():
 for port,v in ports.items():net[v].append([n,port])
cls={re.sub(r'__r\d+$','',b[0]):b[1] for b in old['buses']};buses=[]
W={n:int(w)+1 for w,n in re.findall(r'wire \[(\d+):0\] (\w+);',open(base+'die.v').read())}
for n,eps in net.items():
 if not n or n not in W:continue
 bid=n[2:];buses.append([bid,cls.get(re.sub(r'__r\d+$','',bid),'tree_block' if bid.startswith('tree_') else 'unknown'),W[n],eps])
old.update(insts=insts,endpoint_pos=P,buses=buses)
json.dump(old,open(a.out,'w'))
print(len(insts),len(P),len(missing),missing[:5])
