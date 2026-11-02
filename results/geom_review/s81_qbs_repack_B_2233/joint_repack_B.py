from pathlib import Path
import json,sys,pickle
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
from exact_cones import endpoints,physical_port_map
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'repack_B_complete.json'));D=G.Design(P/'geom.tsv');ports=physical_port_map(C)
for m in C['macros'].values():
 c=D.cells[m['cid']];D.cells[m['cid']]=(c[0],c[1],*m['bbox_um'],c[6])
fixed={x['cid']for x in C['fixed']};ids=[i for i,c in D.cells.items()if c[0]=='S'];idx={c:i for i,c in enumerate(ids)};n=len(ids);xy=np.array([G.ctr(D.cells[i])for i in ids]);uv=np.column_stack((xy[:,0]+xy[:,1],xy[:,0]-xy[:,1]));cache=P/'exact_allff_adjacency.pickle'
if cache.exists():adj=pickle.load(open(cache,'rb'))
else:
 adj={}
 for cid in ids:
  a,b=endpoints(D,cid,False);c,d=endpoints(D,cid,True);adj[cid]=(a|c,b|d)
 pickle.dump(adj,open(cache,'wb'))
edges=set()
for c,(nb,_)in adj.items():
 for d in nb:
  if c!=d:edges.add(tuple(sorted((idx[c],idx[d]))))
print('graph',n,len(edges),flush=True)
R=402.0
lo=np.tile(np.array([8.91,-630.0]),(n,1));hi=np.tile(np.array([1278.0,630.0]),(n,1))
for cid,i in idx.items():
 if cid in fixed:lo[i]=hi[i]=uv[i]
 for mk in adj[cid][1]:
  for x,y,_ in ports[mk]:
   q=np.array([x+y,x-y]);lo[i]=np.maximum(lo[i],q-R);hi[i]=np.minimum(hi[i],q+R)
ii=[];jj=[];vv=[]
for a,b in edges:ii.extend([a,b]);jj.extend([b,a]);vv.extend([R,R])
def min_envelope(a):
 offset=float(a.min())-1
 graph=coo_matrix((vv+list(a-offset),(ii+[n]*n,jj+list(range(n)))),shape=(n+1,n+1)).tocsr()
 return dijkstra(graph,directed=True,indices=n)[:n]+offset
result=[]
for dim in range(2):
 lower=-min_envelope(-lo[:,dim]);upper=min_envelope(hi[:,dim]);bad=np.where(lower>upper+1e-7)[0]
 print('axis',dim,'infeasible',len(bad),'maxgap',float((lower-upper).max()),flush=True)
 if len(bad):raise SystemExit(2)
 smooth=(-min_envelope(-uv[:,dim])+min_envelope(uv[:,dim]))/2
 result.append(np.maximum(lower,np.minimum(upper,smooth)))
r=np.array(result).T;newxy=np.column_stack(((r[:,0]+r[:,1])/2,(r[:,0]-r[:,1])/2));badoutline=np.where((newxy<4.32).any(axis=1)|(newxy>643.68).any(axis=1))[0]
maxedge=max(np.max(abs(r[a]-r[b]))for a,b in edges);macro=0
for cid,i in idx.items():
 for mk in adj[cid][1]:
  for x,y,_ in ports[mk]:macro=max(macro,abs(newxy[i,0]-x)+abs(newxy[i,1]-y))
summary=dict(scope='continuous joint graph model, not row-legal or physical pass',FF=n,edges=len(edges),reach_limit_um=R,max_FF_edge_um=float(maxedge),max_macro_edge_um=float(macro),outside_outline=len(badoutline),moved_gt1um=int(np.sum(np.max(abs(newxy-xy),axis=1)>1)),max_move_um=float(np.max(np.sum(abs(newxy-xy),axis=1))))
(P/'joint_repack_B_targets.json').write_text(json.dumps(dict(summary=summary,targets=[dict(cid=cid,center_um=list(newxy[i]))for cid,i in idx.items()]),indent=1));print(json.dumps(summary,indent=2))
