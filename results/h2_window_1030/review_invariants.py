"""Read-only geometry/input invariants. No timing kernel or placement rerun."""
from pathlib import Path
import collections,copy,hashlib,json,sys
B=Path(sys.argv[1]);D=B/'candidate_v2'
base=json.loads((B/'baseline/plan_d1.json').read_text())[0];r=json.loads((D/'plan_geometry.json').read_text())[0]
native=json.loads((B/'baseline/native_master_slice.json').read_text());sl=json.loads((D/'slice_geometry.json').read_text())
assert native['core_clock_port']=='ck[0]'
assert [x['xy_um'] for x in native['core_islands']]==r['islands_requested_xy']
for k in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event'):sl[k]=copy.deepcopy(native[k])
sl['islands']=copy.deepcopy(native['islands']);sl['native_clock_pin_contract']=copy.deepcopy(sl['islands'][0]['clock_pin']);sl['islands'][0]['clock_pin']=None
sl['native_input_preserved']=copy.deepcopy(r['native_input'])
existing=json.loads((D/'slice_geometry_native.json').read_text());assert sl==existing
b={x['edge']:x for x in base['wire_paths']};n={x['edge']:x for x in r['wire_paths']}
bnodes={x[0]:x for x in base['nodes_xy']};nnodes={x[0]:x for x in r['nodes_xy']}
checks=dict(node_names=set(bnodes)==set(nnodes),frozen_masters=base['frozen_masters']==r['frozen_masters'],named_sink_membership=base['leaf_sinks']==r['leaf_sinks'],wire_edges=set(b)==set(n),repeaters_per_edge=all(len(b[u]['segs'])==len(n[u]['segs']) for u in b),all_endpoints_fixed=all(b[u]['paths'][-1][-1]==n[u]['paths'][-1][-1] for u in b),six_model_anchors=base['islands_xy']==r['islands_xy'],six_native_anchors=[x['xy_um'] for x in native['core_islands']]==r['islands_requested_xy'],native_clock_port=sl['core_clock_port']==native['core_clock_port'],native_clock_pin=sl['native_clock_pin_contract']==native['islands'][0]['clock_pin'],native_input_xy=sl['native_clock_pin_contract']['xy_um']==r['native_input']['xy_um'])
def depths(nodes):
 par={x[0]:x[1] for x in nodes}
 def d(u):return 1 if par[u] is None else d(par[u])+1
 return {u:d(u) for u in r['leaf_sinks']}
checks['same_each_leaf_depth']=depths(base['nodes_xy'])==depths(r['nodes_xy'])
changed=[dict(node=u,before=bnodes[u][1],after=nnodes[u][1]) for u in bnodes if bnodes[u][1]!=nnodes[u][1]]
legs=[]
for w in r['wire_paths']:
 for length,ps in zip(w['segs'],w['paths']):
  direct=sum(abs(a-z)for a,z in zip(ps[0],ps[-1]));legs.append((length,direct))
checks['all_segments70']=all(length<=70+1e-8 for length,_ in legs)
checks['all_positive_segments1p10']=all(length<=1.1*direct+1e-8 for length,direct in legs)
out=dict(scope='Geometry/source identity only; timing NOT RUN',checks=checks,changed_parents=changed,cells=len(nnodes),sinks=sum(map(len,r['leaf_sinks'].values())),leaf_depths=sorted(set(depths(r['nodes_xy']).values())),source_plan_sha256=hashlib.sha256((B/'baseline/plan_d1.json').read_bytes()).hexdigest(),candidate_plan_sha256=hashlib.sha256((D/'plan_geometry.json').read_bytes()).hexdigest(),native_input=sl['native_clock_pin_contract'],actual_native_root=next(x['xy_um']for x in sl['core_tree']['nodes']if x['name']=='mp_ck_root'))
out['verdict']='PASS' if all(checks.values()) else 'FAIL'
(D/'source_invariants.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
