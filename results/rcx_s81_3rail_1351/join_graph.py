from pathlib import Path
import json,sys,collections,hashlib
import numpy as np
r=Path(sys.argv[1]); geom=json.loads((r/'geometry.json').read_text());jid={};capmap={}
for line in (r/'db_graph.tsv').read_text().splitlines():
 p=line.split()
 if p[0]=='J':jid[int(p[1])]=(p[2],int(p[3]),int(p[4]))
 elif p[0]=='C' and p[3]=='I':capmap['*1:'+p[2]]=jid[int(p[2])]
capmap['src']=('M8',10000,18640);capmap['sink']=('M8',522560,403360)
s=(r/'actual.spef').read_text();assert '*C_UNIT 1 PF' in s and '*R_UNIT 1 OHM' in s
es=[(q[1],q[2],float(q[3])) for l in s.split('*RES\n')[1].split('*END')[0].splitlines() if (q:=l.split())]
cs=[(q[1],float(q[2])) for l in s.split('*CAP\n')[1].split('*RES')[0].splitlines() if (q:=l.split()) and len(q)==3]
if any(v<=0 for a,b,v in es):raise ValueError(('nonpositive native resistance',[(a,b,v)for a,b,v in es if v<=0]))
ox,oy=geom['source_global_origin_um']; polys=[]
for p in geom['segments']:
 x0,y0,x1,y1=p['rect_um'];polys.append((p['layer'],round((x0-ox)*1000),round((y0-oy)*1000),round((x1-ox)*1000),round((y1-oy)*1000)))
for v in geom['vias']:
 x,y=round((v['x_um']-ox)*1000),round((v['y_um']-oy)*1000);hw=round(v['pad_um']*500)
 for layer in ['M8','M9']:polys.append((layer,x-hw,y-hw,x+hw,y+hw))
def contact(k):
 layer,x,y=k
 return any(l==layer and x0<=x<=x1 and y0<=y<=y1 for l,x0,y0,x1,y1 in polys)
assert all(contact(k) for k in capmap.values()),[k for k in capmap.values() if not contact(k)]
def groups(edges, mapping):
 g=collections.defaultdict(set)
 for key in mapping.values():g[key]
 for a,b,v in edges:g[mapping[a]].add(mapping[b]);g[mapping[b]].add(mapping[a])
 left=set(g);nc=0
 while left:
  todo=[left.pop()];nc+=1
  while todo:
   for k in g[todo.pop()]:
    if k in left:left.remove(k);todo.append(k)
 return len(g),len(edges),nc,len(edges)-len(g)+nc
raw=groups(es,{k:k for k in capmap});joined=groups(es,capmap)
assert joined==(72,96,1,25),('literal topology mismatch',joined)
# The join key always includes the routing layer. With no actual via edge,
# coincident M8/M9 points remain electrically separate (negative control).
negative=groups([],{'m8':('M8',10,20),'m9':('M9',10,20)});assert negative==(2,0,2,0),negative
nodes=sorted(set(capmap.values()));sink=capmap['sink'];kept=[k for k in nodes if k!=sink];ix={k:i for i,k in enumerate(kept)};a=np.zeros((len(kept),len(kept)));rhs=np.zeros(len(kept));rhs[ix[capmap['src']]]=1
for u,v,res in es:
 u,v=capmap[u],capmap[v];g=1/res
 if u!=sink:a[ix[u],ix[u]]+=g
 if v!=sink:a[ix[v],ix[v]]+=g
 if u!=sink and v!=sink:a[ix[u],ix[v]]-=g;a[ix[v],ix[u]]-=g
voltage=np.linalg.solve(a,rhs);reff=float(voltage[ix[capmap['src']]])
total_cap=float(s.split('*D_NET *1 ')[1].split()[0]);sum_cap=sum(v for n,v in cs)
assert abs(sum_cap-total_cap)<1e-4
out={'verdict':'HYBRID_DIAGNOSTIC','raw_native_mesh_verdict':'FAIL_TREE','method':'Exact integer-DBU same-layer same-XY nodes with actual conductive polygon contact joined after native RCX; every native resistor/capacitor and actual via resistance retained. No R/rails shortcut. Not unmodified native RCX mesh PASS.','raw_graph':dict(zip(['nodes','edges','components','cycles'],raw)),'joined_graph':dict(zip(['nodes','edges','components','cycles'],joined)),'source_sink_effective_resistance_ohm':reff,'total_cap_pf_native':total_cap,'summed_ground_cap_pf':sum_cap,'explicit_coupling_capacitors':0,'coupling_model':'OpenRCX PG SPECIALNETS treated as ground; no independent switching aggressor; same-clock internal coupling not separately qualified','minimum_native_resistance_ohm':min(v for u,w,v in es),'negative_control_same_xy_different_layer_without_via':'PASS remains two separate nodes','nodes':[dict(node=n,layer=k[0],x_dbu=k[1],y_dbu=k[2])for n,k in capmap.items()],'resistors':[dict(a=u,b=v,r_ohm=res)for u,v,res in es],'capacitors_pf':[dict(node=n,c_pf=v)for n,v in cs],'source_geometry_sha256':hashlib.sha256((r/'geometry.json').read_bytes()).hexdigest(),'native_spef_sha256':hashlib.sha256((r/'actual.spef').read_bytes()).hexdigest(),'limits':'local component only; full mesh variation/EM/timing and whole-die BLOCKED obligations remain'}
(r/'hybrid_graph.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items()if k not in ['nodes','resistors','capacitors_pf']},indent=1))
