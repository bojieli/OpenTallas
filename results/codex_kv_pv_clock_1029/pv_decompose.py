import sys,json,collections,functools
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029');sys.path.insert(0,str(p/'named_source/tools/die_plan'))
import core_family_slice as C
rec=json.load(open(p/'named_plan/kv3_pv_pair/plan.json'))[0]
geo=p/'named_plan/kv3_pv_pair/geo.txt';_,_,sinks,_=C.read_macro_geo(geo)
bykey={f'{s[2]}/{s[3]}':s for s in sinks}
nodes=[(u,pa,tuple(xy),m,k)for u,pa,xy,m,k in rec['nodes_xy']];nmap={n[0]:n for n in nodes}
wires=[dict(level=w['level'],edge=w['edge'],segs=w['segs'],cells=w['paths'])for w in rec['wire_paths']];land={}
for w in wires:
 if w['edge']not in nmap:
  last=w['edge']+'_r'+str(len(w['segs'])-2)if len(w['segs'])>1 else w['edge']+'_br'
  assert last in nmap,(w['edge'],last)
  land[last]=(w['segs'][-1],w['edge'])
P=dict(mz=C._LatticeMaze(rec['core']),nodes=nodes,wires=wires,land=land,leafsinks={u:[bykey[k]for k in ks]for u,ks in rec['leaf_sinks'].items()},sinkcap=rec['sinkcap'])
masters=sorted(set(n[3]for n in nodes));libs={c:C.H.lib_cells(str(p/f'invbuf_{c.lower()}.lib'),masters)for c in ['TT','FF']};r=.5*(1.80365e-2+1.89935e-2)*.8;c=.5*(1.78475e-1+1.64264e-1)*.9;wc={}
orig=C.H.mst_edges
@functools.lru_cache(maxsize=None)
def cached(pts):return orig(pts)
C.H.mst_edges=lambda pts:cached(tuple(tuple(x)for x in pts))
res,st=C.M7.model_x(P,libs,r,c,wc)
for cn in ['TT','FF']:
 for k in ['mean','window','leaf_mean_min','leaf_mean_max']:
  assert abs(res[cn][k]-rec[cn][k])<=.05,(cn,k,res[cn][k],rec[cn][k])
def chain(u):
 a=[u]
 while nmap[u][1]:u=nmap[u][1];a.append(u)
 return a[::-1]
children=collections.defaultdict(list)
for n in nodes:
 if n[1]:children[n[1]].append(n[0])
def count(u):
 if u in P['leafsinks']:
  ss=P['leafsinks'][u];return dict(FF=sum(not s[4].startswith('MACRO:')for s in ss),MACRO=sum(s[4].startswith('MACRO:')for s in ss))
 a=[count(v)for v in children[u]];return {k:sum(d[k]for d in a)for k in ['FF','MACRO']}
out=dict(basis='exact frozen bestplan reconstructed from named nodes/wirepaths/actualgeo/caps; original model fields reproduced within0.05ps serialization tolerance',reproduced=res,corner={})
for cn in ['TT','FF']:
 I=P['_int'][cn];L=libs[cn]
 def leafmean(u):
  lib=L[nmap[u][3]];ct,ch=I['drv'][u];sl=I['slew'][u]
  return I['arr'][u]+.5*(C.H.interp(lib['rise'],sl,ct)+C.H.interp(lib['fall'],sl,ct))+ch[0][1]
 early=min(P['leafsinks'],key=leafmean);late=max(P['leafsinks'],key=leafmean)
 ea,la=chain(early),chain(late);common=[x for x,y in zip(ea,la)if x==y];lca=common[-1]
 paths={}
 for tag,u in [('early',early),('late',late)]:
  ch=chain(u);rows=[]
  for i,v in enumerate(ch):
   ct,kids=I['drv'][v];lib=L[nmap[v][3]];sl=I['slew'][v];d=.5*(C.H.interp(lib['rise'],sl,ct)+C.H.interp(lib['fall'],sl,ct));child=ch[i+1]if i+1<len(ch)else'#sinks';el=next(e for kid,e in kids if kid==child)
   rows.append(dict(node=v,kind=nmap[v][4],master=nmap[v][3],xy=nmap[v][2],child=child,input_arrival=I['arr'][v],input_slew=sl,load_fF=ct,cell_delay=d,wire_delay=el,increment=d+el,subtree=count(v)))
  paths[tag]=dict(leaf=u,mean=leafmean(u),leaf_sink_count=len(P['leafsinks'][u]),leaf_kind='macro'if u in rec['macro_leaves']else'register',stages=rows)
 delta=[dict(stage=i,early_node=a['node'],late_node=b['node'],cell_delta=b['cell_delay']-a['cell_delay'],wire_delta=b['wire_delay']-a['wire_delay'],total_delta=b['increment']-a['increment'])for i,(a,b)in enumerate(zip(paths['early']['stages'],paths['late']['stages']))]
 assert abs(sum(d['total_delta']for d in delta)-(leafmean(late)-leafmean(early)))<1e-6
 out['corner'][cn]=dict(lca=lca,lca_depth=len(common)-1,paths=paths,stage_deltas=delta,window=leafmean(late)-leafmean(early),last_leaf_stage_delta=delta[-1]['total_delta'],upper_tree_delta=sum(d['total_delta']for d in delta[:-1]))
f=p/'pv_path_decomposition.json';f.write_text(json.dumps(out,indent=1)+'\n')
print('PV_FROZEN_PATH_DECOMPOSE',json.dumps({cn:{k:out['corner'][cn][k]for k in ['lca','lca_depth','window','last_leaf_stage_delta','upper_tree_delta']}for cn in ['TT','FF']}))
