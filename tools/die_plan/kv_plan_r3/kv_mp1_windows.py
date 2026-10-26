#!/usr/bin/env python3
"""Reconcile replicated face-window centres with actual neighbouring endpoints.

Each component solves exact signed affine type-coordinate constraints. Infeasible
components stay unchanged and report FAIL; no topology or cycle is changed.
"""
import argparse,json,sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import schema as S

STATE=[]
def reconcile(raw):
 P=S.Plan(raw);edges=collections.defaultdict(list);refs=[];nodes={};reports=[]
 for pr in raw['ports']:
  ep=[];face=pr['face'];axis=0 if face in 'NS' else 1
  if 'window_um' not in pr:continue
  width=pr['window_um'][1]-pr['window_um'][0];c=sum(pr['window_um'])/2
  for side in ['src','dst']:
   v=pr[side];pn=v['part']
   if pn==S.DIE_PART:continue
   pp=P.parts[pn];tn=pp['type'];df=face if side=='src' or pr['src']['part']==S.DIE_PART else S.OPP[face];tf=P.type_face(pn,df);k=(tn,v['bus']);a=P.to_type(pn,(0,0))[axis];b=P.to_type(pn,(1,0) if axis==0 else (0,1))[axis];sg=round(b-a);assert sg in [-1,1]
   dim=P.types[tn]['outline_um'][axis];nodes.setdefault(k,[]).append((sg*c+a,width,dim));ep.append((k,sg,a))
  refs.append((pr,ep,width))
  if len(ep)==2:
   (u,su,au),(v,sv,av)=ep;sg=sv*su;off=av-sg*au;edges[u].append((v,sg,off));edges[v].append((u,sg,-sg*off))
 done=set()
 for root in nodes:
  if root in done:continue
  rel={root:(1,0)};q=[root];reason=None
  for u in q:
   su,au=rel[u]
   for v,s,a in edges[u]:
    want=(s*su,s*au+a)
    if v in rel:
     if abs(rel[v][0]-want[0])>1e-6 or abs(rel[v][1]-want[1])>1e-4:reason='inconsistent replicated-neighbour affine cycle'
    else:rel[v]=want;q.append(v)
  done.update(rel);lo=-1e30;hi=1e30;targets=[];width=max(w for u in rel for _,w,_ in nodes[u])
  for u,(sg,a) in rel.items():
   for c,_,dim in nodes[u]:
    l,h=4.32+width/2,dim-4.32-width/2;l,h=sorted(((l-a)/sg,(h-a)/sg));lo=max(lo,l);hi=min(hi,h);targets.append((c-a)/sg)
  if lo>hi+1e-4:reason='no common bounded window interval'
  if reason:reports.append(dict(status='FAIL',nodes=[list(u) for u in rel],reason=reason));continue
  centre=min(hi,max(lo,sum(targets)/len(targets)))
  STATE.append((rel,lo-centre,hi-centre))
  for pr,ep,_ in refs:
   if not ep or ep[0][0] not in rel:continue
   u,sg,a=ep[0];sr,ar=rel[u];c=(sr*centre+ar-a)/sg;pr['window_um']=[round(c-width/2,4),round(c+width/2,4)]
  reports.append(dict(status='PASS',nodes=len(rel),width_um=width))
 return reports
def fit_reach(raw):
 import numpy as np
 from scipy.optimize import linprog
 from scipy.sparse import coo_matrix
 from gen_phys import type_pins
 P=S.Plan(raw);lookup={u:(j,sg) for j,(rel,_,_) in enumerate(STATE) for u,(sg,_) in rel.items()};n=len(STATE);rows=[];cols=[];vals=[];rhs=[]
 def add(coeff,b):
  i=len(rhs);rhs.append(b)
  for j,v in coeff.items():
   if v:rows.append(i);cols.append(j);vals.append(v)
 for tn,t in P.types.items():
  pins={}
  for bus,bit,_,x,y,f in type_pins(P,tn):pins.setdefault(bus,{})[bit]=(x,y,f)
  for slot in t.get('ft_slots',[]):
   sn=slot['name'];aa=pins.get(sn+'_i',{});bb=pins.get(sn+'_o',{})
   for bit in aa.keys() & bb.keys():
    a,b=aa[bit],bb[bit];xy=[];coeff=[]
    for bus,p in [(sn+'_i',a),(sn+'_o',b)]:
     x,y,f=p;dx,dy={'E':(-1,0),'W':(1,0),'N':(0,-1),'S':(0,1)}[f];xy.append((x+dx,y+dy));j,sg=lookup[(tn,bus)];coeff.append((j,sg,0 if f in 'NS' else 1))
    for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
     co={};
     for sign,(j,sg,axis) in zip([1,-1],coeff):co[j]=co.get(j,0)+sign*sg*(sx if axis==0 else sy)
     add(co,slot['stations']*405.-1.-sx*(xy[0][0]-xy[1][0])-sy*(xy[0][1]-xy[1][1]))
 for j in range(n):add({j:1,n+j:-1},0);add({j:-1,n+j:-1},0)
 A=coo_matrix((vals,(rows,cols)),shape=(len(rhs),2*n)).tocsr();res=linprog(np.r_[np.zeros(n),np.ones(n)],A_ub=A,b_ub=rhs,bounds=[(lo,hi) for _,lo,hi in STATE]+[(0,None)]*n,method='highs')
 if not res.success:return dict(status='FAIL',reason=res.message)
 for pr in raw['ports']:
  if 'window_um' not in pr:continue
  for side in ['src','dst']:
   v=pr[side];pn=v['part']
   if pn==S.DIE_PART:continue
   tn=P.parts[pn]['type'];j,sg=lookup[(tn,v['bus'])];axis=0 if pr['face'] in 'NS' else 1;a=P.to_type(pn,(0,0))[axis];ss=round(P.to_type(pn,(1,0) if axis==0 else (0,1))[axis]-a);delta=res.x[j]*sg/ss;pr['window_um']=[round(z+delta,4) for z in pr['window_um']];break
 # Slot declarations describe the same canonical type-frame windows.
 for pr in raw['ports']:
  if 'window_um' not in pr:continue
  axis=0 if pr['face'] in 'NS' else 1
  for side in ['src','dst']:
   v=pr[side];pn=v['part']
   if pn==S.DIE_PART:continue
   tn=P.parts[pn]['type'];bus=v['bus']
   for slot in raw['partition_types'][tn].get('ft_slots',[]):
    if bus not in [slot['name']+'_i',slot['name']+'_o']:continue
    coords=[P.to_type(pn,(z,0) if axis==0 else (0,z))[axis] for z in pr['window_um']]
    slot['in_window_um' if bus.endswith('_i') else 'out_window_um']=[round(z,4) for z in sorted(coords)]
 return dict(status='PASS',components=n,moved=int(sum(abs(z)>1e-5 for z in res.x[:n])),max_shift_um=float(max(abs(z) for z in res.x[:n])))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('--out',required=True);p.add_argument('--report',required=True);a=p.parse_args();d=json.load(open(a.plan));r=reconcile(d);r.append(dict(reach=fit_reach(d),status='MODEL'));json.dump(d,open(a.out,'w'),indent=1);json.dump(r,open(a.report,'w'),indent=1);print(collections.Counter(x['status'] for x in r))
