#!/usr/bin/env python3
"""Deterministic candidate geometry search; excludes physical reset/clock and cuts.

Keeps fixed child bank geometry and UT relays, fits the21 remaining relays.
A search result alone is never a parent pass. Replay the placement checker.
"""
import sys,json,numpy as np,math,random,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));import s81_ph_hrow_native_placement as m
random.seed(813);p=m.Plan();fixed=[n for n,z in p.inst.items() if not(z['master'].startswith('dsfd_hrow_r') and z['master']!='dsfd_hrow_r2079')];ns=[n for n in p.inst if n not in fixed];allns=list(p.inst);idx={n:i for i,n in enumerate(allns)};ori=['R0','MX','MY','R180','R90','R270'];N=len(allns);xy=np.array([[z['x'],z['y']] for z in p.inst.values()]);oo=np.array([ori.index(z['orient']) for z in p.inst.values()]);sz=np.array([[m.MP[z['master']]['w'],m.MP[z['master']]['h']] for z in p.inst.values()]);edges=[]
for e in p.edges:
 if e['cls']=='reset_direct_rtl':continue
 a,b=idx[e['source']],idx[e['sink']];K=np.zeros((6,6,4))
 for j,o in enumerate(ori):
  p.inst[e['source']]['orient']=o;A=np.array([p.pin(e['source'],q)[:2] for q in e['source_pins']])-xy[a]
  for k,v in enumerate(ori):
   p.inst[e['sink']]['orient']=v;B=np.array([p.pin(e['sink'],q)[:2] for q in e['sink_pins']])-xy[b];d=A-B
   K[j,k]=[(d[:,0]*sx+d[:,1]*sy).max() for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]]
 edges.append((a,b,K))
wh=sz.copy()
def upd(i):wh[i]=sz[i,::-1] if oo[i]>=4 else sz[i]
for i in range(N):upd(i)
def pair(i,j):
 d=np.minimum(xy[i]+wh[i],xy[j]+wh[j])-np.maximum(xy[i],xy[j]);return max(0,min(d))*max(0,min(d))*8 if np.all(d>1e-6) else 0
sign=np.array([[1,1],[1,-1],[-1,1],[-1,-1]])
def edgecost(e):
 a,b,K=e;l=max(sign@(xy[a]-xy[b])+K[oo[a],oo[b]]);return max(0,l-498)**2
emap={i:[e for e in edges if e[0]==i or e[1]==i] for i in range(N)}
def own(i):
 c=sum(pair(i,j) for j in range(N) if i!=j)+sum(edgecost(e) for e in emap[i]);v=np.maximum(0,-xy[i]);u=np.maximum(0,xy[i]+wh[i]-[m.W,m.H]);return c+10*(v@v+u@u)
def score():return sum(pair(i,j) for i in range(N) for j in range(i))+sum(edgecost(e) for e in edges)+sum(10*(np.maximum(0,-xy[i])@np.maximum(0,-xy[i])+np.maximum(0,xy[i]+wh[i]-[m.W,m.H])@np.maximum(0,xy[i]+wh[i]-[m.W,m.H])) for i in range(N))
# Start relays in the unoccupied band; use direction toward hub.
for n in ns:
 i=idx[n];xy[i,1]=max(1252.8,xy[i,1]);oo[i]=2 if '[2]' in n else 0;upd(i)
best=score();saved=(xy.copy(),oo.copy());s=best;t0=time.time()
for it in range(180000):
 i=idx[random.choice(ns)];oldxy=xy[i].copy();oldoo=oo[i];c=own(i);temp=max(.05,3000*(1-(it%45000)/45000)**4);step=random.choice([2.16,8.64,21.6,43.2,86.4])
 if random.random()<.15:oo[i]=random.randrange(6);upd(i)
 else:xy[i]+=np.array([random.randint(-2,2),random.randint(-2,2)])*step
 new=own(i);ds=new-c
 if ds<0 or random.random()<math.exp(-min(ds/temp,700)):s+=ds
 else:xy[i]=oldxy;oo[i]=oldoo;upd(i)
 if s<best-1e-5:
  best=s;saved=(xy.copy(),oo.copy())
  if best<1e-5:break
 if it%10000==0:print(it,round(best,2),flush=True)
 if it%45000==44999:xy,oo=saved[0].copy(),saved[1].copy();s=best;[upd(i) for i in range(N)]
xy,oo=saved
for n,i in idx.items():p.inst[n]['x']=round(xy[i,0],3);p.inst[n]['y']=round(xy[i,1],3);p.inst[n]['orient']=ori[oo[i]]
json.dump(dict(instances=p.inst,score=best,iterations=it),open(m.OUT/'searched_positions.json','w'),indent=1)
print('DONE',best,it,time.time()-t0)
