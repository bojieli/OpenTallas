"""Plan-only point-to-point branch isolation for A0 clock trees.
Each long branch has its own local driver, following core_infra_htree's existing
structural form. No RTL or measured arrival is consumed. Macro latency comes
from the original signed-view annotation; total effective stage count stays
uniform after the deterministic terminal compensation.
Usage: p2p_tree.py IN OUT FF_STAGE_PS TT_STAGE_PS REPORT
"""
import json,sys,math,collections,copy
src,out,sff,stt,rep=sys.argv[1:]; sff,stt=float(sff),float(stt)
sl=json.load(open(src)); t=sl['core_tree']; old=copy.deepcopy(t)
nodes={n['name']:n for n in old['nodes']}; gates={g['inst']:g for g in old['gates']}
par={n:q['parent'] for n,q in nodes.items()};par.update({n:q['parent'] for n,q in gates.items()})
xy={n:q['xy_um'] for n,q in nodes.items()};xy.update({n:q['xy_um'] for n,q in gates.items()});xy['port:ck']=[228.948,578.64]
def depths(par):
 d={'port:ck':0}
 def go(n):
  if n not in d:d[n]=go(par[n])+1
  return d[n]
 for n in par:go(n)
 return d
d=depths(par)
oldsp=old['early_tap_stage_ps']
def k_of(l,sp):
 ks={c:int(math.floor((l['early_tap_ps'][c]['min']+l['early_tap_ps'][c]['max'])/2/sp[c]+.5)) for c in ('TT','FF')}
 if len(set(ks.values()))!=1:raise ValueError(('macro stage corner disagreement',ks))
 return ks['FF']
levels={d[l['node']]+(k_of(l,oldsp) if 'early_tap_ps'in l else 0) for l in t['leaves']}
assert len(levels)==1,levels
T=levels.pop()*2
new=[]
for n in old['nodes']:
 p=n['parent'];b='mp_p2p_'+n['name']
 new.append(dict(name=b,parent=p,xy_um=xy[p],master='BUFx12f_ASAP7_75t_R'))
 q=copy.deepcopy(n);q['parent']=b;new.append(q)
for g in t['gates']:
 p=g['parent'];b='mp_p2p_gate_'+g['inst'].replace('/','_')
 new.append(dict(name=b,parent=p,xy_um=xy[p],master='BUFx12f_ASAP7_75t_R'));g['parent']=b
sp={'TT':stt,'FF':sff,'source':'A0 isolated point-to-point branch stage, plan before build; signed macro latency annotations unchanged'}
adjust=[]
for l in t['leaves']:
 if 'early_tap_ps' not in l:continue
 k0=k_of(l,oldsp);k=k_of(l,sp);delta=2*k0-k
 nd={n['name']:n for n in new};node=l['node']
 if delta<0:
  for i in range(-delta):
   p=nd[node]['parent']
   assert p in nd and sum(q['parent']==p for q in new)==1,(node,p)
   nd[node]['parent']=nd[p]['parent'];new.remove(nd[p]);del nd[p]
 elif delta>0:
  for i in range(delta):
   b='mp_p2p_macro_'+node+'_'+str(i)
   pxy=nd[node]['xy_um'];q=dict(name=b,parent=node,xy_um=[pxy[0]+.432*(i+1),pxy[1]],master='BUFx12f_ASAP7_75t_R')
   new.append(q);nd[b]=q;node=b
  l['node']=node
 adjust.append(dict(sinks=l['sinks'],old_k=k0,new_k=k,terminal_stage_adjustment=delta))
t['nodes']=new;t['early_tap_stage_ps']=sp;t['note']='A0 P2P branch isolation: independent local branch driver per long net, equal effective stages, signed macro early taps.'
p={n['name']:n['parent'] for n in new};p.update({g['inst']:g['parent'] for g in t['gates']});dd=depths(p)
lev={dd[l['node']]+(k_of(l,sp) if 'early_tap_ps'in l else 0) for l in t['leaves']};assert lev=={T},lev
xy={n['name']:n['xy_um'] for n in new};xy.update({g['inst']:g['xy_um'] for g in t['gates']});xy['port:ck']=[228.948,578.64]
legs=[abs(xy[n][0]-xy[q][0])+abs(xy[n][1]-xy[q][1]) for n,q in p.items()]
json.dump(sl,open(out,'w'),indent=1)
r=dict(scope='PLAN ONLY NO TIMING/PHYSICAL CLAIM',effective_stages=T,nodes=len(new),macro_adjustments=adjust,max_node_leg_um=max(legs),added_cells=len(new)-len(old['nodes']))
json.dump(r,open(rep,'w'),indent=1);print(json.dumps(r))
