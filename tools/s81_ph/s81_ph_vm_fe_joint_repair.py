#!/usr/bin/env python3
"""Finite coupled MILP placement repair. Candidate only; exact replay gates remain unchanged."""
import argparse,hashlib,json,sys,time,warnings
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import coo_matrix
import s81_ph_vm_fe_h_floorplan as F

def solve(inp,pins,capture,out,radius,margin,nodes):
 j=json.loads(Path(inp).read_text());F.W=j['width'];F.H=j['height'];F.load_actual_master_pins(pins)
 p=F.Plan('A');F.reposition(p,{n:(v['x'],v['y']) for n,v in j['instances'].items()},True);F.assign_capture(p,capture)
 names=list(p.inst);idx={n:i for i,n in enumerate(names)};N=len(names);xy=np.array([v[1:] for v in p.inst.values()]);size=np.array([F.MP[v[0]][:2] for v in p.inst.values()]);step=np.array([2.16,8.64])
 lower=np.maximum(-radius,-xy);upper=np.minimum(radius,np.array([F.W,F.H])-xy-size)
 for i,n in enumerate(names):
  if n.startswith(('clt','fsr')):lower[i]=0;upper[i]=0
 lo=list(np.ceil(lower/step).ravel());hi=list(np.floor(upper/step).ravel());obj=[0.]*(2*N);integ=[1]*(2*N);rr=[];cc=[];vv=[];rl=[];ru=[]
 def var(l,h,c,integer):
  k=len(lo);lo.append(l);hi.append(h);obj.append(c);integ.append(integer);return k
 def row(d,l=-np.inf,u=np.inf):
  k=len(rl);rl.append(l);ru.append(u)
  for c,v in d.items():
   if v:rr.append(k);cc.append(c);vv.append(v)
 # L1 movement variables, physical micrometres; no geometric objective credit.
 for i in range(N):
  for ax in range(2):
   k=2*i+ax;t=var(0,np.inf,1,0);row({k:step[ax],t:-1},u=0);row({k:-step[ax],t:-1},u=0)
 signs=np.array([[1,1],[1,-1],[-1,1],[-1,-1]])
 for cls,a,b,A,B in p.hops:
  dif=np.array([q[:2] for q in A])-np.array([q[:2] for q in B]);proj=np.max(dif@signs.T,axis=0)
  for s,base in zip(signs,proj):
   d={}
   for n,sg in [(a,1),(b,-1)]:
    if n in idx:
     for ax in range(2):
      # Candidate boundary x follows its leaf except assigned capture/status.
      if ax==0 and (a.startswith('FE.') or b.startswith('FE.')) and cls not in ('f_cap','f_cap_status'):continue
      k=2*idx[n]+ax;d[k]=d.get(k,0)+sg*s[ax]*step[ax]
   row(d,u=500-margin-base)
 # Coupled four-way nonoverlap disjunctions, with tight bounded big-M values.
 disjunctions=0;immediate=[]
 for i in range(N):
  for k in range(i+1,N):
   choices=[];already=False
   for a,b,ax in [(i,k,0),(k,i,0),(i,k,1),(k,i,1)]:
    gap=0. if names[i].startswith('clt') and names[k].startswith('clt') else 2.16
    rhs=xy[b,ax]-xy[a,ax]-size[a,ax]-gap
    lowdiff=lo[2*a+ax]*step[ax]-hi[2*b+ax]*step[ax];highdiff=hi[2*a+ax]*step[ax]-lo[2*b+ax]*step[ax]
    if highdiff<=rhs+1e-7:already=True;break
    if lowdiff<=rhs+1e-7:choices.append((a,b,ax,rhs,max(0.,highdiff-rhs)))
   if already:continue
   if not choices:immediate.append([names[i],names[k]]);row({},l=1,u=0);continue
   zs=[];disjunctions+=1
   for a,b,ax,rhs,M in choices:
    z=var(0,1,0,1);zs.append(z);row({2*a+ax:step[ax],2*b+ax:-step[ax],z:M},u=rhs+M)
   row({z:1 for z in zs},l=1)
 mat=coo_matrix((vv,(rr,cc)),shape=(len(rl),len(lo))).tocsr();start=time.time()
 with warnings.catch_warnings(record=True) as ws:
  res=milp(np.array(obj),integrality=np.array(integ),bounds=Bounds(lo,hi),constraints=LinearConstraint(mat,rl,ru),options={'node_limit':nodes,'mip_rel_gap':.05,'threads':1})
 rec=dict(schema='opentallas.vmfe-coupled-finite-repair.v1',input=inp,input_sha256=hashlib.sha256(Path(inp).read_bytes()).hexdigest(),source_sha256=hashlib.sha256(F.SRC.encode()).hexdigest(),radius_um=radius,direct_reach_reserve_um=margin,node_limit=nodes,elapsed_s=time.time()-start,status=int(res.status),message=res.message,variables=len(lo),constraints=len(rl),coupled_nonoverlap_disjunctions=disjunctions,immediate_infeasible_pairs=immediate,node_count=getattr(res,'mip_node_count',None),mip_gap=getattr(res,'mip_gap',None),objective=getattr(res,'fun',None),warnings=[str(w.message) for w in ws],global_impossibility_claim=False,native_qualified=False,limits={'hop_um':500,'cut':.60},existing_anchored_CLT_abutment_preserved=True,other_macro_gap_um=2.16,fixed_instances=[n for n in names if n.startswith(('clt','fsr'))],actual_clock_rc_budget_um=None)
 if res.x is not None:
  delta=np.rint(res.x[:2*N]).reshape(N,2)*step;F.reposition(p,{n:tuple(xy[i]+delta[i]) for i,n in enumerate(names)},True)
  rec['moved_instances']={n:delta[i].tolist() for i,n in enumerate(names) if np.any(abs(delta[i])>1e-6)}
  rec['placement_violations']=p.check_place();rec['hops_over_500']={k:v['len_max'] for k,v in p.check_hops().items() if v['len_max']>500+1e-6}
  candidate=dict(j,instances={n:{'master':m,'x':x,'y':y,'w':F.MP[m][0],'h':F.MP[m][1]} for n,(m,x,y) in p.inst.items()},placement_violations=rec['placement_violations'],hops_over_500=rec['hops_over_500'],coupled_repair=rec,closure_claim=False,slot_adopted=False)
  Path(out+'.placement.json').write_text(json.dumps(candidate,indent=2)+'\n')
 Path(out+'.record.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--placements',required=True);a.add_argument('--master-pins',required=True);a.add_argument('--assigned-capture',required=True);a.add_argument('--out',required=True);a.add_argument('--radius',type=float,default=172.8);a.add_argument('--margin',type=float,default=43.2);a.add_argument('--nodes',type=int,default=2000);q=a.parse_args();solve(q.placements,q.master_pins,q.assigned_capture,q.out,q.radius,q.margin,q.nodes)
