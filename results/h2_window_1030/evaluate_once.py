"""Exactly one frozen-master H2 evaluation after source/LOOK concurrence.

Uses the unchanged standard-width UF3 GRT kernel and existing fit. No planner,
coordinate descent, sizing, fitting or physical tool is invoked.
"""
from pathlib import Path
import copy,hashlib,json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);D=R/'candidate_v2';O=R/'model_once'
if O.exists():raise SystemExit('model_once output already exists; never repeat/overwrite the candidate evaluation')
O.mkdir()
sys.path[:0]=[str(S/'results/core_lat_r8_1026'),str(S/'tools/die_plan')]
import l0r_r8_uf3 as A,core_plan_to_infra as C,core_infra as CI
rec=json.loads((D/'plan_geometry.json').read_text())[0];sl_geometry=json.loads((D/'slice_geometry_native.json').read_text());fit=json.loads((R/'inputs/uf_phys3_v1.json').read_text())
assert rec['frozen_masters']==json.loads((R/'baseline/plan_d1.json').read_text())[0]['frozen_masters']
for n in rec['nodes_xy']:
 if n[3] not in A.U.SIZES:A.U.SIZES.append(n[3])
L=A.U.load_libs(R/'inputs/lib');P=A.PlanFromRecord(rec,str(R/'baseline/geo.txt'))
assert all(n in P.kids or P.nodes[n]['kind'] in ('leaf','macro') for n in P.nodes), 'dangling non-leaf model node'
root=next(n['xy_um'] for n in sl_geometry['core_tree']['nodes'] if n['name']=='mp_ck_root');native=rec['native_input']['xy_um']
length=sum(abs(a-b) for a,b in zip(root,native));root_master=rec['frozen_masters']['root']
arrival={co:A.U.R45*length*(A.U.C45*length/2+L[co][root_master]['cin']) for co in ('TT','FF')}
slew={co:2.2*arrival[co] for co in arrival}
stock=A.V3.predict3
calls=[]
def actual_input(plan,libs,corner,*args,**kwargs):
 kwargs['s_root']=math.hypot(kwargs.get('s_root',0.),slew[corner])
 calls.append((corner,kwargs.get('edge','rise')))
 return stock(plan,libs,corner,*args,**kwargs)
A.V3.predict3=actual_input
print('H2_SINGLE_MODEL_START frozen masters; TT rise + FF min(rise,fall)',flush=True)
result=A.calibrated_summary(P,L,fit['PMAX'],fit['PMIN'])
assert calls==[('TT','rise'),('FF','rise'),('FF','fall')],calls
for co,x in result.items():
 for key in ('mean','leaf_mean_min','leaf_mean_max','sink_min','sink_max'):x[key]=round(x[key]+arrival[co],6)
receipt=dict(scope='One frozen-master H2 standard-width UF3 GRT evaluation; physical unmeasured',corners=result,kernel_calls=calls,fit='unchanged existing uf_phys3_v1',native_input=dict(port='ck[0]',pin_um=native,converted_root_um=root,wire_um=length,arrival_ps=arrival,slew_ps=slew),candidate_sha256=hashlib.sha256((D/'plan_geometry.json').read_bytes()).hexdigest())
(O/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
# Save the numerical result BEFORE structural compilation; no kernel retry is
# needed if an independent packaging/compiler check exposes another issue.
for key in ('d1_uf3','model_r7_info','model_pre_d1','island_loads'):
 if key in rec:rec['baseline_diagnostic_'+key]=rec.pop(key)
rec['TT'],rec['FF']=result['TT'],result['FF'];rec['model']='uf_phys3 v1 GRT; frozen masters, actual native input; no fitting/sizing'
(O/'plan_model.json').write_text(json.dumps([rec])+'\n')
sl=C.convert(rec,C.read_sites(R/'baseline/sites.txt'),'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1));sl.pop('clock_ndr',None)
for key in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event','islands','native_clock_pin_contract','native_input_preserved'):sl[key]=copy.deepcopy(sl_geometry[key])
sl['core_tree']['model_qualification']['band_policy']='info';sl['core_tree']['model_qualification']['native_input_pricing']=receipt['native_input']
assert sl['core_tree']['nodes']==sl_geometry['core_tree']['nodes'] and sl['core_tree']['leaves']==sl_geometry['core_tree']['leaves']
plan=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,plan)
checks=dict(geometry_unchanged=True,masters_unchanged=True,native_pg=pg,TT_window20=result['TT']['window']<=20,FF_window20=result['FF']['window']<=20,both_slews80=all(result[c][key]<=80 for c in ('TT','FF') for key in ('leaf_slew_in_max','leaf_out_slew_max')))
checks['verdict']='PASS' if checks['TT_window20'] and checks['FF_window20'] and checks['both_slews80'] and pg['verdict']=='PASS' else 'FAIL'
(O/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');(O/'slice_model.json').write_text(json.dumps(sl,indent=1)+'\n')
if checks['verdict']=='PASS':(O/'master_core_infra.tcl').write_text(CI.emit_tcl(sl))
print('H2_SINGLE_MODEL_DONE '+json.dumps(dict(result=result,checks=checks)),flush=True)
