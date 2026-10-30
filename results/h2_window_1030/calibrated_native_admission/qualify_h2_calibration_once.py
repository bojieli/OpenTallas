"""Exactly one final resized H2 qualification after footprint/source/LOOK concurrence.

Uses the unchanged standard-width UF3 GRT kernel and existing fit. No planner,
coordinate descent, sizing, fitting or physical tool is invoked.
"""
from pathlib import Path
import copy,hashlib,json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);D=R/'tpqt_slew_geometry';O=R/'tpqt_slew_model'
if O.exists():raise SystemExit('final_model output already exists; never repeat/overwrite final qualification')
O.mkdir()
sys.path[:0]=[str(S/'results/core_lat_r8_1026'),str(S/'tools/die_plan')]
import l0r_r8_uf3 as A,core_plan_to_infra as C,core_infra as CI
rec=json.loads((D/'plan_geometry.json').read_text())[0];sl_geometry=json.loads((D/'slice_geometry_native.json').read_text());fit=json.loads((R/'inputs/uf_phys3_v1.json').read_text())
assert json.loads((D/'geometry_checks.json').read_text())['verdict']=='PASS'
assert json.loads((D/'slew_precheck_summary.json').read_text())['verdict']=='PASS'
assert (D/'LOOK.json').exists(), 'Actual converted image must be personally reviewed first'
for n in rec['nodes_xy']:
 if n[3] not in A.U.SIZES:A.U.SIZES.append(n[3])
L=A.U.load_libs(R/'inputs/lib');P=A.PlanFromRecord(rec,str(R/'baseline/geo.txt'))
assert all(n in P.kids or P.nodes[n]['kind'] in ('leaf','macro') for n in P.nodes), 'dangling non-leaf model node'
root=next(n['xy_um'] for n in sl_geometry['core_tree']['nodes'] if n['name']=='mp_ck_root');native=rec['native_input']['xy_um']
length=sum(abs(a-b) for a,b in zip(root,native));root_master=rec['frozen_masters']['root']
arrival={co:A.U.R45*length*(A.U.C45*length/2+L[co][root_master]['cin']) for co in ('TT','FF')}
slew={co:2.2*arrival[co] for co in arrival}
stock=A.V3.predict3
calls=[];traces={}
def actual_input(plan,libs,corner,*args,**kwargs):
 kwargs['s_root']=math.hypot(kwargs.get('s_root',0.),slew[corner])
 calls.append((corner,kwargs.get('edge','rise')))
 answer=stock(plan,libs,corner,*args,**kwargs)
 arr=answer[1];leafdetail=kwargs['detail'];all_slew={}
 assert all(math.isfinite(float(value)) for state in arr.values()for value in state), 'nonfinite saved buffer arrival/input'
 assert all(float(state[1])>=0 for state in arr.values()), 'negative saved buffer input slew'
 for u,node in plan.nodes.items():
  if u in plan.kids:
   net=plan.nets[u];cw,cp,el,rw=A.U.rc_tree(net['pts'],net['edges'],{net['pin'][child]:libs[corner][plan.nodes[child]['cell']]['cin']for child in plan.kids[u]},A.U.R45,A.U.C45)
   vals=[math.sqrt(max(0.,arr[child][1]**2-(kwargs['gslew']*el[net['pin'][child]])**2))for child in plan.kids[u]]
   assert max(vals)-min(vals)<1e-5
   so=vals[0]
  else:so=leafdetail[u]['slew_out']
  assert math.isfinite(float(so)) and so>=0, 'nonfinite/negative buffer output '+u
  all_slew[u]=dict(input_ps=arr[u][1],output_ps=so)
 traces[corner+'_'+kwargs.get('edge','rise')]={'leaves':answer[0],'node_arrival_slew':arr,'leaf_detail':leafdetail,'all_buffer_slew':all_slew}
 return answer
A.V3.predict3=actual_input
print('H2_FINAL_MODEL_START resized masters; TT rise + FF min(rise,fall)',flush=True)
result=A.calibrated_summary(P,L,fit['PMAX'],fit['PMIN'])
assert calls==[('TT','rise'),('FF','rise'),('FF','fall')],calls
for co in ['TT','FF']:
 rows=[q for tag,v in traces.items()if tag.startswith(co+'_')for q in v['all_buffer_slew'].values()]
 result[co]['all_buffer_slew_in_max']=max(q['input_ps']for q in rows)
 result[co]['all_buffer_slew_out_max']=max(q['output_ps']for q in rows)
for co,x in result.items():
 for key in ('mean','leaf_mean_min','leaf_mean_max','sink_min','sink_max'):x[key]=round(x[key]+arrival[co],6)
receipt=dict(scope='H2 native calibration-repair qualification; explicitMETH12.3a band/windowINFO; canonicalroot0+actualstub; physical/upstream waveform unmeasured',corners=result,kernel_calls=calls,fit='unchanged existing uf_phys3_v1',native_input=dict(port='ck[0]',pin_um=native,converted_root_um=root,wire_um=length,arrival_ps=arrival,slew_ps=slew),candidate_sha256=hashlib.sha256((D/'plan_geometry.json').read_bytes()).hexdigest())
(O/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
(O/'timing_traces.json').write_text(json.dumps(traces)+'\n')
# Save the numerical result BEFORE structural compilation; no kernel retry is
# needed if an independent packaging/compiler check exposes another issue.
for key in ('d1_uf3','model_r7_info','model_pre_d1','island_loads'):
 if key in rec:rec['baseline_diagnostic_'+key]=rec.pop(key)
rec['TT'],rec['FF']=result['TT'],result['FF'];rec['model']='uf_phys3 v1 GRT; sized masters, actual native input; no fitting'
(O/'plan_model.json').write_text(json.dumps([rec])+'\n')
sl=C.convert(rec,C.read_sites(R/'baseline/sites.txt'),'dsfd_coll_lane_w_safe8_ntf','ck[0]',ndr=(1,1));sl.pop('clock_ndr',None)
for key in ('event','core_islands','core_islands_note','core_tree_family','h2fix_event','islands','native_clock_pin_contract','native_input_preserved'):sl[key]=copy.deepcopy(sl_geometry[key])
assert sl['module']=='dsfd_coll_lane_w_safe8_ntf'
sl['core_tree']['model_qualification']['band_policy']='info';sl['core_tree']['model_qualification']['window_policy']='info'
sl['core_tree']['model_qualification']['admission_policy']='Explicit H2 opt-in METH12.3a; 20window and250/202.5band are design targets, all-buffer80 remains required; actualG2/signoff decide'
for co in ['TT','FF']:sl['core_tree']['model_qualification']['corners'][co]['slew_max']=max(result[co]['all_buffer_slew_in_max'],result[co]['all_buffer_slew_out_max'])
sl['core_tree']['model_qualification']['native_input_pricing']=receipt['native_input']
assert sl['core_tree']['nodes']==sl_geometry['core_tree']['nodes'] and sl['core_tree']['leaves']==sl_geometry['core_tree']['leaves']
plan=CI.compile_slice(sl);pg=CI.trunk_pg_clearance(sl,plan)
checks=dict(geometry_unchanged=True,sized_masters_frozen=True,native_pg=pg,TT_window20=result['TT']['window']<=20,FF_window20=result['FF']['window']<=20,both_slews80=all(result[c][key]<=80 for c in ('TT','FF') for key in ('leaf_slew_in_max','leaf_out_slew_max')))
checks['window_policy']='info';checks['band_policy']='info'
checks['all_buffers_80']=all(result[c][key]<=80 for c in ['TT','FF']for key in ['all_buffer_slew_in_max','all_buffer_slew_out_max'])
envelopes={}
for co in ['TT','FF']:
 values=[value for tag,run in traces.items()if tag.startswith(co+'_')for leaf in run['leaf_detail'].values()for value in leaf['sinks']]
 assert values and all(math.isfinite(float(value)) for value in values), 'nonfinite saved sink envelope '+co
 offset=arrival[co]
 envelopes[co]=dict(min=min(values)+offset,max=max(values)+offset,span=max(values)-min(values))
checks['related_model_envelope']=envelopes
checks['local_related_model_bound80']=all(q['span']<=80 for q in envelopes.values())
checks['related_basis']='Union of ALL SAVED states (TT-rise; FF-rise/fall), not TTboth-edge coverage; realG2 exhaustive pairSTA stillrequired'
checks['verdict']='MODEL_ADMISSION_PASS'if checks['all_buffers_80']and checks['local_related_model_bound80']and pg['verdict']=='PASS'else'HOLD'
checks['historical_window_failures_preserved']=True
(O/'checks.json').write_text(json.dumps(checks,indent=2)+'\n');(O/'slice_model.json').write_text(json.dumps(sl,indent=1)+'\n')
if checks['verdict']=='MODEL_ADMISSION_PASS':(O/'master_core_infra.tcl').write_text(CI.emit_tcl(sl))
print('H2_SINGLE_MODEL_DONE '+json.dumps(dict(result=result,checks=checks)),flush=True)
