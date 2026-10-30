"""PLAN ONLY joint TT/FF bottom-up clock branch balancing.
Adds designed shared trunks at forks, never a per-sink target/pad. Uses only
geometry/NLDM model and actual signed macro insertion; no measured clock arrival.
"""
import json,sys,math,copy,statistics,itertools
from pathlib import Path
import numpy as np
p=Path.cwd();sys.path.insert(0,str(p/'src'));sys.path.insert(0,str(p/'natural_model/tools'))
source,model_file,census,kit,out=sys.argv[1:]
# Reuse exact source/master-cap parser without running a second predictor.
sys.argv=['qualify2.py',source,census,kit,'unused','unused'];e={'__file__':str(p/'src/qualify2.py')};text=(p/'src/qualify2.py').read_text().split('model=M.predict_tree')[0].replace("str(Path('tool_snapshot/tools/die_plan').resolve())","str(Path('natural_model/tools').resolve())");exec(text,e)
C=e['C'];sl=e['sl'];t=sl['core_tree'];M=json.load(open(model_file));libs=e['libs']
# Joint-corner steady-state short-stage vectors, including declared1.188um wire.
names=['BUFx8_ASAP7_75t_R','BUFx12f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];vectors={}
for name in names:
 vec=[]
 for c in ('TT','FF'):
  lib=libs[c][name];load=lib['cap']+1.188*.154233;slew=20.
  for _ in range(30):slew=C._bilin(lib['trans'],slew,load)
  vec.append(C._bilin(lib['delay'],slew,load)+1.188*.014812*(1.188*.154233/2+lib['cap']))
 vectors[name]=np.array(vec)
pairs=list(itertools.combinations(names,2));pair=max(pairs,key=lambda q:abs(np.linalg.det(np.array([vectors[x]/np.linalg.norm(vectors[x])for x in q]))));V=np.array([vectors[x]for x in pair]).T;det=np.linalg.det(V)
if abs(det)<1e-8:raise ValueError('No independent joint-corner stage vectors')
INV=np.linalg.inv(V);N=32;opts=np.array([(i,j)for i in range(N+1)for j in range(N+1-i)],dtype=float)
parents={n['name']:n['parent']for n in t['nodes']};parents.update({g['inst']:g['parent']for g in t['gates']});nodes={n['name']:n for n in t['nodes']};gates={g['inst']:g for g in t['gates']};allnodes={**nodes,**gates};children={n:[]for n in allnodes}
for n,par in parents.items():
 if par in children:children[par].append(n)
arrival={c:{r['driver']:r['input_arrival_ps']for r in M['corners'][c]['nets']}for c in ('TT','FF')};leaf_mean={c:{r['node']:r['mean_ps']for r in M['corners'][c]['leaf_means']}for c in ('TT','FF')}
leafs={l['node']:l for l in t['leaves']};sub={};weights={};choices=[]
def joint(values):
 if len(values)==1:return values[0],[(0,0)],0.
 A=np.array(values);anchor=A[np.argmax(A.sum(axis=1))];T=anchor+opts@V.T
 T=np.concatenate([T,A.mean(axis=0)[None,:],T+np.array([4.,4.]),T-np.array([4.,4.])])
 worst=np.zeros(len(T));total=np.zeros(len(T));pick=[]
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
 # Stop adding cells once ordinary clock-tree quantization is within8ps;
 # this is a design objective, not a replacement sign-off gate.
 cost=np.maximum(worst-8.,0.)*10000+total*.05+T.sum(axis=1)*.0001
 k=int(np.argmin(cost));return T[k],[tuple(x[k])for x in pick],float(worst[k])
order=[]
def visit(n):
 for x in children[n]:visit(x)
 order.append(n)
root=next(n for n,par in parents.items()if par.startswith('port:'));visit(root)
for n in order:
 if n in leafs:
  leaf=leafs[n];value=[]
  for c in ('TT','FF'):
   ins=leaf.get('early_tap_ps',{}).get(c,dict(min=0,max=0));value.append(leaf_mean[c][n]+sum(ins.values())/2-arrival[c][n])
  sub[n]=np.array(value);weights[n]=len(leaf['sinks']);continue
 cs=children[n]
 if not cs:raise ValueError('clock node without a sink '+n)
 vals=[sub[ch]+np.array([arrival[c][ch]-arrival[c][n]for c in ('TT','FF')])for ch in cs]
 target,counts,error=joint(vals)
 actual=[v+V@np.array(k)for v,k in zip(vals,counts)];ws=[weights[ch]for ch in cs];sub[n]=np.average(actual,axis=0,weights=ws);weights[n]=sum(ws)
 for ch,count,v in zip(cs,counts,vals):
  if sum(count):choices.append(dict(parent=n,child=ch,counts=list(map(int,count)),prior_subtree_latency_ps=v.tolist(),target_ps=target.tolist(),quantization_ps=error))
# Planned compact trunks at the child entry. Exact row/island legalization and
# its capacity audit remain required before any physical clock build.
import gen_a0_clock_corridor as G
fr=json.load(open(p/'widen/nk_freeze_candidate.json'));G.CLOCK_ISLANDS[:]=[r for c in fr['candidate_clock_corridors']for r in c['clock_islands_um']];G.CLOCK_COLUMNS[:]=[c['clock_reserved_rect_um']for c in fr['candidate_clock_corridors']];geo={};boxes=[]
for h in fr['hard_children']:
 if h['master']not in geo:geo[h['master']]=G.lef_geom(Path(kit)/'macros'/f"{h['master']}.lef")
 w,hh,_=geo[h['master']];x,y=h['at'];boxes.append((x-G.HALO[0],y-G.HALO[1],x+w+G.HALO[0],y+hh+G.HALO[1]))
P=G.CorridorPlanner(boxes,100.);serial=0;added=[]
for change in choices:
 child=change['child'];parent=change['parent'];origin=allnodes[child]['xy_um'];sequence=[pair[0]]*change['counts'][0]+[pair[1]]*change['counts'][1]
 for k,name in enumerate(sequence):
  serial+=1;new=f'mp_joint_branch_{serial}';width={'BUFx8_ASAP7_75t_R':.648,'BUFx12f_ASAP7_75t_R':.972,'BUFx24_ASAP7_75t_R':1.620}[name];P.cell_width=width
  pos=P.legal([origin[0]+1.944*(k%4),origin[1]+.540*(k//4)]);row=dict(name=new,parent=parent,master=name,xy_um=pos);added.append(row);parent=new
 allnodes[child]['parent']=parent
# Reorder named tree, retaining every functional gate and every endpoint.
t['nodes']+=added;parents={n['name']:n['parent']for n in t['nodes']};parents.update({g['inst']:g['parent']for g in t['gates']});depth={'port:ck':0}
def dep(n):
 if n not in depth:depth[n]=dep(parents[n])+1
 return depth[n]
for n in parents:dep(n)
t['nodes'].sort(key=lambda n:(depth[n['name']],n['name']));t.pop('model_qualification',None)
for l in t['leaves']:l.pop('pin_latency_ps',None)
report=dict(scope='PLAN ONLY bottom-up shared branch balancing; not a physical/timing PASS',measured_timing_used=False,stage_masters=pair,stage_vectors_ps={k:v.tolist()for k,v in vectors.items()},branches_changed=len(choices),added_nodes=serial,clock_nodes=len(t['nodes']),root_estimated_endpoint_mean_ps=sub[root].tolist(),worst_local_quantization_ps=max((c['quantization_ps']for c in choices),default=0),choices=choices,pending=['actual jointNLDM re-predict with changed loads/geometry','clock-cell row/island capacity/legalization','render/review then physicalprototype TT/FF'] )
Path(out+'.json').write_text(json.dumps(sl,indent=1)+'\n');Path(out+'_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='choices'}),flush=True)
