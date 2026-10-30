"""One H2 geometry candidate. No timing kernel, sizing or fitting is invoked."""
from pathlib import Path
import collections,copy,functools,json,math,sys
ROOT=Path(sys.argv[1]);SRC=Path(sys.argv[2]);OUT=ROOT/'candidate_v2';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(SRC/'tools/die_plan'))
import core_family_slice as F,core_plan_to_infra as C,core_infra as CI
base=json.loads((ROOT/'baseline/plan_d1.json').read_text())[0];rec=copy.deepcopy(base)
core,_,sinks,macros=F.read_macro_geo(ROOT/'baseline/geo.txt')
mz=F.H.Maze(core,macros,keepout=base['macro_keepout_um'])
cell=lambda p:tuple(round((v-o)/mz.G) for v,o in zip(p,core[:2]))
old={n[0]:tuple(n) for n in base['nodes_xy']}
nodes={n[0]:[n[0],n[1],cell(n[2]),n[3],n[4]] for n in base['nodes_xy']}
for n in base['nodes_xy']:assert list(mz.xy(nodes[n[0]][2]))==list(n[2])
native=[147.948,236.520];entry=mz.cell(native);old_entry=nodes['root'][2]
delta=tuple(a-b for a,b in zip(entry,old_entry));nodes['root'][2]=entry
moved_root=['root']
for n in nodes.values():
 if n[1]=='root':n[2]=tuple(a+b for a,b in zip(n[2],delta));moved_root.append(n[0])
for name in moved_root:assert mz.site_ok(*nodes[name][2]),('native entry cell not legal',name,mz.xy(nodes[name][2]))
MAX=math.floor(70./mz.G+1e-9);changes=[];failed=[]
for w in rec['wire_paths']:
 edge=w['edge'];k=len(w['segs']);br=edge+'_br';end=cell(w['paths'][-1][-1]);start=nodes[br][2]
 # Only incoming landed nets charge a hub's many branch inputs. Leaf endpoint
 # positions and all leaf/sink memberships stay fixed.
 landed=edge not in base['leaf_sinks']
 if not landed and br not in moved_root:continue
 path=mz.path(start,end);L=len(path)-1
 if not (L>MAX or br in moved_root):continue
 own={edge+'_r%d'%i for i in range(k-1)}
 occupied={tuple(n[2]) for name,n in nodes.items() if name not in own}
 valid={i for i,p in enumerate(path) if mz.site_ok(*p) and p not in occupied}
 def leg(a,b):
  x,y=path[a],path[b];man=abs(x[0]-y[0])+abs(x[1]-y[1])
  return b-a<=MAX and b-a<=1.10*man+1e-9
 @functools.lru_cache(None)
 def choose(i,remaining):
  if remaining==1:return () if leg(i,L) else None
  # Furthest legal repeater first: keep the high-capacitance final landing
  # wire short, without increasing any path length or a segment's 70um limit.
  lo=max(i+1,L-(remaining-1)*MAX);hi=min(L,i+MAX)
  for j in range(hi,lo-1,-1):
   if j not in valid or not leg(i,j):continue
   tail=choose(j,remaining-1)
   if tail is not None:return (j,)+tail
  return None
 picked=choose(0,k)
 if picked is None:
  failed.append(dict(edge=edge,why='no same-stage legal shortest-path partition',length_um=L*mz.G,segments=k));continue
 indices=[0]+list(picked)+[L]
 newsegs=[(b-a)*mz.G for a,b in zip(indices,indices[1:])]
 if br not in moved_root:assert sum(newsegs)<=sum(w['segs'])+.011,(edge,newsegs,w['segs'])
 before=[list(mz.xy(nodes[edge+'_r%d'%i][2])) for i in range(k-1)]
 for i,j in enumerate(picked):nodes[edge+'_r%d'%i][2]=path[j]
 w['paths']=[[list(mz.xy(p)) for p in path[a:b+1]] for a,b in zip(indices,indices[1:])]
 w['segs']=newsegs
 changes.append(dict(edge=edge,level=w['level'],segments_before=base['wire_paths'][rec['wire_paths'].index(w)]['segs'],segments_after=newsegs,old_repeaters_um=before,new_repeaters_um=[list(mz.xy(path[j])) for j in picked]))
rec['nodes_xy']=[[n[0],n[1],list(mz.xy(n[2])),n[3],n[4]] for n in nodes.values()]
rec['name']=base['name']+'_native_landing_geometry'
rec['entry']=list(mz.xy(entry))
rec['model']='NOT RUN for candidate; frozen baseline corner fields retained only as diagnostic control'
rec['native_input']=dict(port='ck[0]',layer='M5',xy_um=native,model_root_um=rec['entry'],source='Types actual current centre4 BTerm and KIT/pins.json; prior planner centre was not native')
rec['candidate_changes']=changes
# Existing nearest geometry contains five repeated-leaf legs >70um. Rehang
# only those edges on reachable SAME-depth drivers with the reviewed true
# landing-hub/local-fan/collision guards. This invokes geometry only, no model.
by_sink={q[2]+'/'+q[3]:q for q in sinks}
P=dict(mz=mz,nodes=[(n[0],n[1],cell(n[2]),n[3],n[4]) for n in rec['nodes_xy']],
       wires=[],land={},leafsinks={u:[by_sink[k] for k in ks] for u,ks in rec['leaf_sinks'].items()},sinkcap=rec['sinkcap'])
for w in rec['wire_paths']:
 P['wires'].append(dict(level=w['level'],edge=w['edge'],segs=list(w['segs']),cells=[[cell(p) for p in ps] for ps in w['paths']]))
 if w['edge'] not in P['leafsinks']:
  last=w['edge']+'_r%d'%(len(w['segs'])-2) if len(w['segs'])>1 else w['edge']+'_br'
  P['land'][last]=(w['segs'][-1],w['edge'])
rec['candidate_leaf_reparents']=F.reparent_obstructed_edges(P,70.)
rec['nodes_xy']=[[n[0],n[1],list(mz.xy(n[2])),n[3],n[4]] for n in P['nodes']]
rec['wire_paths']=[dict(level=w['level'],edge=w['edge'],segs=w['segs'],paths=[[list(mz.xy(p)) for p in ps] for ps in w['cells']]) for w in P['wires']]
assert len(rec['nodes_xy'])==len(base['nodes_xy'])==1811
assert rec['frozen_masters']==base['frozen_masters'] and rec['leaf_sinks']==base['leaf_sinks']
assert rec['islands_xy']==base['islands_xy'] and rec['islands_requested_xy']==base['islands_requested_xy']
par={n[0]:n[1] for n in rec['nodes_xy']}
def depth(u):return 1 if par[u] is None else depth(par[u])+1
assert {depth(u) for u in rec['leaf_sinks']}=={12}
bad=[];long=[]
for w in rec['wire_paths']:
 for length,ps in zip(w['segs'],w['paths']):
  a,b=ps[0],ps[-1];d=sum(abs(x-y) for x,y in zip(a,b))
  if d>1 and length>1.1*d+1e-8:bad.append([w['edge'],length,d])
  if length>70.+1e-8:long.append([w['edge'],length])
(OUT/'plan_geometry.json').write_text(json.dumps([rec])+'\n')
result=dict(scope='GEOMETRY ONLY; candidate timing NOT RUN',native_input=rec['native_input'],cells=1811,sinks=rec['sinks'],stages=[12],fixed_six_anchors=rec['islands_requested_xy'],changed_landed_edges=len(changes),changed_root_nodes=moved_root,failed=failed,detours=bad,over70um=long)
try:
 sl=C.convert(rec,C.read_sites(ROOT/'baseline/sites.txt'),'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1))
 sl.pop('clock_ndr',None);sl['islands'][0]['clock_pin']=None
 sl['native_input_preserved']=rec['native_input']
 sl['core_tree']['model_qualification']['band_policy']='info'
 compiled=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,compiled)
 result.update(converter_displacement_um=sl['plan_conversion']['displacement_um'],pg=pg)
 (OUT/'slice_geometry.json').write_text(json.dumps(sl,indent=1)+'\n')
except Exception as e:result['converter_error']=str(e)
result['verdict']='PASS' if not (failed or bad or long or result.get('converter_error')) and result['converter_displacement_um']['max']<=2 and result['pg']['verdict']=='PASS' else 'FAIL'
(OUT/'geometry.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
