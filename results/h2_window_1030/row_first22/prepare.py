"""One authorized row-first upper22 re-expression; no timing/model kernel."""
from pathlib import Path
import collections,copy,functools,json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);O=R/'row_first_geometry'
if O.exists():raise SystemExit('row-first output exists')
O.mkdir();sys.path[:0]=[str(S/'tools/die_plan'),str(S/'results/core_lat_r8_1026')]
import core_family_slice as F,core_plan_to_infra as C,core_infra as CI,l0r_r8_uf3 as A
base=json.loads((R/'final_model/plan_model.json').read_text())[0];r=copy.deepcopy(base);ns=json.loads((R/'candidate_v2/slice_geometry_native.json').read_text())
core,_,sinks,macros=F.read_macro_geo(R/'baseline/geo.txt');mz=F.H.Maze(core,macros,keepout=r['macro_keepout_um'])
def cell(p):return tuple(round((x-o)/mz.G)for x,o in zip(p,core[:2]))
def man(a,b):return sum(abs(x-y)for x,y in zip(a,b))*mz.G
old={n[0]:n for n in base['nodes_xy']};oldw=[w for w in base['wire_paths']if w['level']<=2]
upper=set()
for w in oldw:upper.update([w['edge']+'_br']+[w['edge']+'_r%d'%i for i in range(len(w['segs'])-1)])
assert len(upper)==22
nodes={u:[n[0],n[1],cell(n[2]),n[3],n[4]]for u,n in old.items()if u not in upper}
occupied={n[2]for n in nodes.values()};newnames=[];neww=[];edges={};oldbag=collections.Counter(old[u][3]for u in upper)
# Natural middle row has2trunk stages and3lateral stages; outer rows3+2.
rows=[('hr_bottom',70.2,3),('hr_middle',227.34,2),('hr_top',386.1,3)]
MAX=math.floor(70/mz.G+1e-9)
def make_wire(edge,parent,hub,end,k,level,landed):
 options=[];bound=4 if landed else 3;radius=math.ceil(bound/mz.G)
 for dx in range(-radius,radius+1):
  for dy in range(-radius,radius+1):
   b=(hub[0]+dx,hub[1]+dy);direct=man(hub,b)
   if direct>bound or(not landed and direct>=bound)or b in occupied or not mz.site_ok(*b):continue
   stub=mz.md(hub,b)
   if stub<0 or stub>bound or(not landed and stub>=bound)or stub>1.1*direct+1e-9:continue
   length=mz.md(b,end)
   if not k*mz.G<=length<=k*70 or length>1.1*man(b,end)+1e-9:continue
   options.append((length,stub,b))
 for length,stub,b in sorted(options):
  path=mz.path(b,end);last=len(path)-1
  def legal(a,z):return z-a<=MAX and(z-a)*mz.G<=1.1*man(path[a],path[z])+1e-9
  @functools.lru_cache(None)
  def partition(a,remain):
   if remain==1:return ()if legal(a,last)else None
   ideal=a+(last-a)/remain
   for z in sorted(range(a+1,min(last,a+MAX)+1),key=lambda z:(abs(z-ideal),z)):
    if z==last or path[z]in occupied or not mz.site_ok(*path[z])or not legal(a,z):continue
    rest=partition(z,remain-1)
    if rest is not None:return(z,)+rest
   return None
  chosen=partition(0,k)
  if chosen is None:continue
  at=[0]+list(chosen)+[last];names=[edge+'_br']+[edge+'_r%d'%i for i in range(k-1)]
  for i,u in enumerate(names):
   pos=path[at[i]];assert pos not in occupied;occupied.add(pos)
   nodes[u]=[u,parent if i==0 else names[i-1],pos,'BUFx8_ASAP7_75t_R','branch'if i==0 else'rep'];newnames.append(u)
  w=dict(edge=edge,level=level,segs=[(z-a)*mz.G for a,z in zip(at,at[1:])],paths=[[list(mz.xy(q))for q in path[a:z+1]]for a,z in zip(at,at[1:])]);neww.append(w);edges[edge]=dict(last=names[-1],hub=end)
  return
 raise ValueError('no lawful row-first path '+edge)
root=nodes['root'][2]
for edge,y,k in rows:make_wire(edge,'root',root,mz.cell((147.96,y)),k,1,False)
# Keep all six actual anchors and all lower groups. Rebind only their parent.
for edge,row,k in [('Tpp','hr_bottom',2),('Tqp','hr_bottom',2),('Tpq','hr_middle',3),('Tqq','hr_middle',3),('Tpr','hr_top',2),('Tqr','hr_top',2)]:
 end=cell(next(w for w in oldw if w['edge']==edge)['paths'][-1][-1]);make_wire(edge,edges[row]['last'],edges[row]['hub'],end,k,2,True)
 oldlast=edge+'_r1';newlast=edges[edge]['last']
 for u,n in nodes.items():
  if u not in newnames and n[1]==oldlast:n[1]=newlast
assert len(newnames)==22 and len(nodes)==1811
r['wire_paths']=neww+[copy.deepcopy(w)for w in base['wire_paths']if w['level']>2]
# Deterministic load/cap allocation of the EXACT existing22-master multiset.
# Proxy upper-child Cin is the multiset mean, never a timing/delay surrogate.
# Actual assigned child caps and full net capacitances are reported afterwards.
for master in oldbag:
 if master not in A.U.SIZES:A.U.SIZES.append(master)
L=A.U.load_libs(R/'inputs/lib');mean_cin={co:sum(L[co][m]['cin']*n for m,n in oldbag.items())/22 for co in ['TT','FF']}
rank=lambda m:float(m.split('BUFx')[1].split('_')[0].replace('f','.5'))
bag=sorted(list(oldbag.elements()),key=lambda m:(-rank(m),m));uppernew=set(newnames)
# Complete provisional record supplies exact route lengths and native fanout.
def record_nodes():
 done=set();out=[]
 while len(out)<len(nodes):
  ready=sorted(u for u,n in nodes.items()if u not in done and(n[1]is None or n[1]in done))
  if not ready:raise ValueError('row-first parent cycle')
  for u in ready:
   n=nodes[u];out.append([u,n[1],list(mz.xy(n[2])),n[3],n[4]]);done.add(u)
 return out
r['nodes_xy']=record_nodes();P=A.PlanFromRecord(r,str(R/'baseline/geo.txt'));proxy={}
for u in newnames:
 net=P.nets[u];length=sum(q[2]for q in net['edges'])
 proxy[u]=max(A.U.C45*length+sum(mean_cin[c]if kid in uppernew else L[c][P.nodes[kid]['cell']]['cin']for kid in P.kids[u])for c in ['TT','FF'])
assignment=[]
for u,master in zip(sorted(newnames,key=lambda u:(-proxy[u],u)),bag):nodes[u][3]=master;assignment.append(dict(node=u,master=master,cap_proxy_ff=proxy[u]))
r['nodes_xy']=record_nodes();r['frozen_masters']={n[0]:n[3]for n in r['nodes_xy']}
assert collections.Counter(n[3]for n in r['nodes_xy'])==collections.Counter(n[3]for n in base['nodes_xy'])
# Explicit22old->new map pairs equal masters; no actual native sink aliases.
unused={m:sorted(u for u in upper if old[u][3]==m)for m in oldbag};mapping=[]
for u in sorted(newnames):mapping.append(dict(old=unused[nodes[u][3]].pop(0),new=u,master=nodes[u][3]))
par={n[0]:n[1]for n in r['nodes_xy']};op={u:n[1]for u,n in old.items()}
def depth(u,p):return 1 if p[u]is None else depth(p[u],p)+1
assert {u:depth(u,par)for u in r['leaf_sinks']}=={u:depth(u,op)for u in r['leaf_sinks']}
assert r['leaf_sinks']==base['leaf_sinks']and r['sinkcap']==base['sinkcap']and r['native_input']==base['native_input']
# Full actual final pin/wire loads at both corners, no timing interpolation.
P=A.PlanFromRecord(r,str(R/'baseline/geo.txt'));caps={}
for u in ['root']+newnames:
 net=P.nets[u];length=sum(q[2]for q in net['edges']);caps[u]={c:dict(pin_ff=sum(L[c][P.nodes[kid]['cell']]['cin']for kid in P.kids[u]),wire_ff=A.U.C45*length,wire_um=length,children=P.kids[u])for c in ['TT','FF']}
r['name']=base['name']+'_row_first22';r['splits']=[3,2]+list(base['splits'][2:]);r['model']='NOT RUN row-first22; old timing fields diagnostic only';r['row_first22']=dict(old_new_map=mapping,master_assignment=assignment,rule='Existing22-master multiset; descending max(TT,FF) native wire+fanout-cap proxy, upperchildCin multisetmean for one allocation pass; no fitting/timing search',actual_final_upper_caps=caps)
sl=C.convert(r,C.read_sites(R/'baseline/sites.txt'),'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1));sl.pop('clock_ndr',None)
for key in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event','islands','native_clock_pin_contract','native_input_preserved'):sl[key]=copy.deepcopy(ns[key])
sl['core_tree']['model_qualification']['band_policy']='info';sl['core_tree']['model_qualification']['status']='NOT RUN changed row-first22 source'
compiled=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,compiled)
checks=dict(scope='One row-first upper22 geometry PREP, timing NOT RUN',cells=len(nodes),sinks=sum(map(len,r['leaf_sinks'].values())),changed_upper_nodes=22,explicit_identity_map=mapping,master_multiset_preserved=True,every_sink_depth_preserved=True,all_sinks_and_macro_caps_preserved=True,lower_stage7plus_memberships_fixed=True,native_input_and_six_anchors_fixed=True,all_segments70=all(x<=70+1e-9 for w in r['wire_paths']for x in w['segs']),all_detour1p10=all(x<=1.1*sum(abs(a-b)for a,b in zip(ps[0],ps[-1]))+1e-9 for w in r['wire_paths']for x,ps in zip(w['segs'],w['paths'])),converter=sl['plan_conversion'],native_pg=pg)
checks['verdict']='PASS'if checks['all_segments70']and checks['all_detour1p10']and pg['verdict']=='PASS'and sl['plan_conversion']['displacement_um']['max']<=2 else'FAIL'
(O/'plan_geometry.json').write_text(json.dumps([r])+'\n');(O/'slice_geometry_native.json').write_text(json.dumps(sl,indent=1)+'\n');(O/'geometry_checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
