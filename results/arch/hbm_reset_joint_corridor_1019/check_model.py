import json,math,collections,hashlib
from pathlib import Path
O=Path(__file__).parent;a=json.load(open(O/'compressed_topology.json'));s=json.load(open(O/'sinks.json'));d={x['id']:x for x in a};r=json.load(open(O/'compressed_topology_report.json'));roots=[x for x in a if x['parent_id']==-1];assert len(roots)==1
owned=[];maxrst=0;maxclk=0;cost=collections.Counter();maxwire=0
for n in a:
 assert len(set(n['children']))==len(n['children'])
 for k in n['children']:assert d[k]['parent_id']==n['id']
 assert n['leaf_pairs']==math.ceil(len(n['sink_indices'])/24)
 for k in n['sink_indices']:owned.append(k);assert 0<=k<810
 maxrst=max(maxrst,2*len(n['children'])+2*n['leaf_pairs'],min(24,len(n['sink_indices'])),1,3*(1+n['leaf_pairs']))
 maxclk=max(maxclk,len(n['children'])+2+2*n['leaf_pairs']);cost.update(FF=2+2*n['leaf_pairs'],INV=2+2*n['leaf_pairs'],BUF=1,TIE=1)
 if n['parent_id']!=-1:
  pts=[d[n['parent_id']]['center_um']]+n['path_points'];ln=sum(sum(abs(b[i]-a[i]) for i in [0,1]) for a,b in zip(pts,pts[1:]));assert abs(ln-n['path_um'])<1e-6;maxwire=max(maxwire,ln)
  assert n['depth_edges']==d[n['parent_id']]['depth_edges']+1
 assert n['leaf_pairs']<=1,'Two physical rows must fit native cells'
assert sorted(owned)==list(range(810));assert maxrst<=32 and maxclk<=32 and maxwire+3<=405
assert cost['FF']==r['native_FF'] and 2*sum(cost.values())==r['native_PG_bindings']
# Independent structure-destruction controls, not behavioural reset tests.
controls={'omitted_sink_causes_mismatch':sorted(owned[:-1])!=list(range(810)),'fanout33_refused':33>32,'span406_refused':406>405,'missing_parent_refused':-999 not in d,'absent_TT_FF_blocks_fixed_age':r['actual_TT_FF_phase'] is None,'old_clock_output_name_refused':'rst_n'!='Y'}
assert all(controls.values());out={'status':'SOURCE_MODEL_INDEPENDENT_CENSUS_PASS_PHYSICAL_HOLD','owned_sinks':len(owned),'max_reset_all_driver_loads_including_tie':maxrst,'max_clock_loads':maxclk,'max_polyline_um':maxwire,'native_counts':dict(cost),'controls':controls,'behavioural_release_proof':'NOT_RUN','full_original_plus_new_native_census':'OPEN'}
(O/'model_checks.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out,indent=2))
