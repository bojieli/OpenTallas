"""No timing evaluation: verify resized physical footprints and frozen graph."""
from pathlib import Path
import copy,json,sys
R=Path(sys.argv[1]);S=R/'src';sys.path[:0]=[str(S/'tools/die_plan')]
import core_plan_to_infra as C,core_infra as CI
O=R/'sizing';r=json.loads((O/'plan_sized.json').read_text())[0];b=json.loads((R/'candidate_v2/plan_geometry.json').read_text())[0];ns=json.loads((R/'candidate_v2/slice_geometry_native.json').read_text())
assert [[n[0],n[1],n[2],n[4]]for n in r['nodes_xy']]==[[n[0],n[1],n[2],n[4]]for n in b['nodes_xy']]
for k in ('leaf_sinks','wire_paths','islands_xy','islands_requested_xy','native_input'):assert r[k]==b[k],k
sites=C.read_sites(R/'baseline/sites.txt');sl=C.convert(r,sites,'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1));sl.pop('clock_ndr',None)
for k in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event','islands','native_clock_pin_contract','native_input_preserved'):sl[k]=copy.deepcopy(ns[k])
sl['core_tree']['model_qualification']['band_policy']='info';sl['core_tree']['model_qualification']['status']='NOT QUALIFIED; pre-final geometry check only'
compiled=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,compiled)
checks=dict(fixed_graph=True,masters_rvt_envelope=True,cells=len(sl['cell_placements']),sinks=sum(map(len,r['leaf_sinks'].values())),converter=sl['plan_conversion'],native_pg=pg,site_rule='Canonical SiteMap places full actual master widths on native rows, excludes occupied/fixed cells and M5 centre straps')
checks['verdict']='PASS' if sl['plan_conversion']['displacement_um']['max']<=2 and pg['verdict']=='PASS'else'FAIL'
(O/'slice_sized_geometry.json').write_text(json.dumps(sl,indent=1)+'\n');(O/'geometry_checks.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
