"""Results-local pure TT/FF branch-sizing proposal; no placement or timing measurements."""
import json,gzip,sys,math,statistics
from pathlib import Path
import numpy as np
B=Path('/srv/opentallas-scratch2/claude/codex-collft-clock-0336');A=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336')
sys.path.insert(0,str(A/'src'));sys.path.insert(0,str(A/'natural_model/tools'));import die_clock_128 as C
plans=json.load(gzip.open(B/'tree_screen_plans.json.gz','rt'));models=json.load(gzip.open(B/'tree_screen_full_models.json.gz','rt'))
pair=['BUFx6f_ASAP7_75t_R','BUFx16f_ASAP7_75t_R'];vec={}
for c in ('TT','FF'):
 libs=C.lib_cells(c,str(A/'lib'),pair)
 for n,l in libs.items():
  load=l['cap']+1.188*.154233;slew=20.
  for _ in range(30):slew=C._bilin(l['trans'],slew,load)
  vec.setdefault(n,[]).append(C._bilin(l['delay'],slew,load)+1.188*.014812*(1.188*.154233/2+l['cap']))
V=np.array([vec[n]for n in pair]).T;INV=np.linalg.inv(V);N=64;opts=np.array([(i,j)for i in range(N+1)for j in range(N+1-i)],dtype=float)
def joint(values):
 if len(values)==1:return values[0],[(0,0)],0.
 A=np.array(values);anchor=A[np.argmax(A.sum(axis=1))];T=anchor+opts@V.T
 T=np.concatenate([T,A.mean(axis=0)[None,:],T+np.array([4.,4.]),T-np.array([4.,4.])])
 worst=np.zeros(len(T));total=np.zeros(len(T));pick=[];actual_low=np.full((len(T),2),np.inf);actual_high=np.full((len(T),2),-np.inf)
 for a in A:
  B=T-a;continuous=B@INV.T;flo=np.floor(continuous);best=np.full(len(T),np.inf);bestn=np.zeros((len(T),2),dtype=int)
  candidates=[flo+np.array([i,j])for i in (-1,0,1,2)for j in (-1,0,1,2)]
  for k in (0,1):
   n=np.rint((B@V[:,k])/(V[:,k]@V[:,k]));z=np.zeros((len(T),2));z[:,k]=np.clip(n,0,N);candidates.append(z)
  for ns in candidates:
   valid=(ns>=0).all(axis=1)&(ns.sum(axis=1)<=N);err=np.max(np.abs(B-ns@V.T),axis=1);err[~valid]=np.inf
   use=(err<best-1e-8)|((np.abs(err-best)<1e-8)&(ns.sum(axis=1)<bestn.sum(axis=1)))
   best[use]=err[use];bestn[use]=ns[use].astype(int)
  worst=np.maximum(worst,best);total+=bestn.sum(axis=1);pick.append(bestn)
  actual=a+bestn@V.T;actual_low=np.minimum(actual_low,actual);actual_high=np.maximum(actual_high,actual)
 # Stop adding cells once actual TT/FF sibling mean windows are within20ps;
 # this is a design objective, not a replacement sign-off gate.
 sibling_window=np.max(actual_high-actual_low,axis=1)
 cost=np.maximum(sibling_window-20.,0.)*10000+total*.05+((actual_high+actual_low)/2).sum(axis=1)*.0001
 k=int(np.argmin(cost));return T[k],[tuple(x[k])for x in pick],float(sibling_window[k])

allchoices=[];summary={};rootvalue={};rootnode={}
for owner,sl in plans.items():
 t=sl['core_tree'];nodes={n['name']:n for n in t['nodes']};parents={n:nodes[n]['parent']for n in nodes};children={n:[]for n in nodes};leaves={l['node']:l for l in t['leaves']};root=next(n for n,p in parents.items()if p.startswith('port:'));rootnode[owner]=root
 for n,p in parents.items():
  if p in children:children[p].append(n)
 m=models[owner];arrival={c:{r['driver']:r['input_arrival_ps']for r in m['corners'][c]['nets']}for c in ('TT','FF')};lm={c:{r['node']:r['mean_ps']for r in m['corners'][c]['leaf_means']}for c in ('TT','FF')};sub={};weights={};order=[]
 def visit(n):
  for ch in children[n]:visit(ch)
  order.append(n)
 visit(root)
 for n in order:
  if n in leaves:sub[n]=np.array([lm[c][n]-arrival[c][n]for c in ('TT','FF')]);weights[n]=len(leaves[n]['sinks']);continue
  cs=children[n];vals=[sub[ch]+np.array([arrival[c][ch]-arrival[c][n]for c in ('TT','FF')])for ch in cs];target,counts,error=joint(vals)
  actual=[v+V@np.array(k)for v,k in zip(vals,counts)];ws=[weights[ch]for ch in cs];sub[n]=np.average(actual,axis=0,weights=ws);weights[n]=sum(ws)
  for ch,count in zip(cs,counts):
   if sum(count):allchoices.append(dict(owner=owner,parent=n,child=ch,counts=list(map(int,count)),estimated_sibling_window_ps=error))
 rootvalue[owner]=sub[root];summary[owner]=dict(prior_clock_cells=len(nodes),estimated_endpoint_mean_ps=sub[root].tolist());print(owner,summary[owner],flush=True)
# Align the eight REAL RCLK entry trees to one planning endpoint target; no synthetic root is emitted.
ro=[n for n in plans if n.startswith('clk')];target,counts,error=joint([rootvalue[n]for n in ro])
for owner,count in zip(ro,counts):
 if sum(count):allchoices.append(dict(owner=owner,parent='port:ck',child=rootnode[owner],counts=list(map(int,count)),estimated_sibling_window_ps=error))
# FCLK screens already meet conservative same-owner80ps; preserve their base trees.
allchoices=[c for c in allchoices if c['owner'].startswith('clk')]
serial=0
for ch in allchoices:
 sl=plans[ch['owner']];nodes={n['name']:n for n in sl['core_tree']['nodes']};child=nodes[ch['child']];origin=child['xy_um'];parent=ch['parent'];sequence=[pair[0]]*ch['counts'][0]+[pair[1]]*ch['counts'][1]
 for k,master in enumerate(sequence):
  serial+=1;name='mp_collft_shared_branch_'+str(serial);pos=[min(780.,max(6.,origin[0]+1.188*(k%8))),min(988.,max(6.,origin[1]+.54*(k//8)))];sl['core_tree']['nodes'].append(dict(name=name,parent=parent,master=master,xy_um=pos));parent=name
 child['parent']=parent
for sl in plans.values():
 par={n['name']:n['parent']for n in sl['core_tree']['nodes']};depth={'port:ck':0}
 def dep(n):
  if n not in depth:depth[n]=dep(par[n])+1
  return depth[n]
 sl['core_tree']['nodes'].sort(key=lambda n:(dep(n['name']),n['name']))
with gzip.open(B/'tree_balanced_proposal.json.gz','wt')as f:json.dump(plans,f)
(B/'tree_balancing_report.json').write_text(json.dumps(dict(scope='UNPLACED common TT/FF sibling branch sizing, exact re-model/actual pin/packing required; no per-pair trims',stage_vectors_ps=vec,added_clock_cells=serial,root_summaries=summary,estimated_joint_RCLK_target_ps=target.tolist(),estimated_joint_window_ps=error,choices=allchoices),indent=1))
print('ADDED',serial,'JOINT',target.tolist(),'WINDOW',error,flush=True)
