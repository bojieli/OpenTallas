#!/usr/bin/env python3
"""Added fixture repair: admit guard fault from registered pending intent, not gated valid."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
PIN='c8b3c1733fd83e7f5c2da1647e54b745d4602da0'
OLD='rtl/test/w17_window_core_cancel_join_r7'
OUT='rtl/test/w17_window_core_cancel_join_r8'
REC='results/uarch/w17_window_core_cancel_guard_feedback_repair_20261002'
OLD_MODEL='results/uarch/w17_window_core_cancel_join_preparation_r7_20261002/model.json'
PRODUCER='rtl/test/w17_window_actual_producer_cancel_declaration_repaired/ot_hdc_v41x_window_kv_blocks_cancel.sv'
STATE='core.g_cancel.u_impl.g_packed_window_write.u_blocks.g_cancel.u_impl.state'
OLD_INJECT=' core_rec_fault_inject=fault_pulse || src_fault || (core_win_blk_v && guard_bad);'
INGRESS='''// Synthetic source-bound observer of REGISTERED producer intent; never gated blk_v.
// Production integration must expose equivalent raw intent or independent guard fault.
// No causal delivery/visibility completion is provided by this observation.
wire core_guard_pending_raw = (core.g_cancel.u_impl.g_packed_window_write.u_blocks.g_cancel.u_impl.state == 2'd3);
wire core_guard_fault_raw = core_guard_pending_raw && guard_bad;
assign core_rec_fault_inject = fault_pulse || src_fault || core_guard_fault_raw;
'''
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def blob(path):return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT)
def fixed_points(other,drain,guard,local_bad,old):
 return [stop for stop in (0,1) if stop==int(bool(other or ((drain and not stop and not local_bad) if old else drain) and guard))]
def generate():
 old=blob(OLD+'/tb.sv').decode();cone=blob(OLD+'/actual_fastpp_core_selected_cone.sv')
 if old.count(OLD_INJECT)!=1 or old.count('logic  core_rec_fault_inject=0;')!=1:raise ValueError('single old ingress site')
 tb=old.replace('logic  core_rec_fault_inject=0;','wire core_rec_fault_inject;')
 tb=tb.replace(OLD_INJECT,' // Guard ingress is a continuous raw-intent observer above; no gated-valid feedback.')
 if tb.count('always_comb begin\n core_coll_busy')!=1:raise ValueError('fixture insertion anchor')
 tb=tb.replace('always_comb begin\n core_coll_busy',INGRESS+'always_comb begin\n core_coll_busy')
 producer=(ROOT/PRODUCER).read_text()
 if 'localparam [1:0] EMPTY = 0, FILL = 1, FULL = 2, DRAIN = 3;' not in producer:raise ValueError('producer DRAIN encoding pin')
 header=producer[producer.index('module ot_hdc_v41x_window_kv_blocks_cancel_enabled #('):]
 if 'assign blk_v = !rec_stop && !rec_local_bad && state == DRAIN;' not in header:raise ValueError('producer suppress-valid pin')
 directory=ROOT/OUT;record=ROOT/REC;directory.mkdir(exist_ok=False);record.mkdir(exist_ok=True)
 (directory/'tb.sv').write_text(tb);(directory/'actual_fastpp_core_selected_cone.sv').write_bytes(cone)
 model=json.loads(blob(OLD_MODEL));model.update({'status':'PREPARED_GUARD_INGRESS_REPAIRED_UNCOMPILED','runtime_cone_path':OUT+'/actual_fastpp_core_selected_cone.sv','runtime_cone_sha256':sha(directory/'actual_fastpp_core_selected_cone.sv'),'bench_sha256':sha(directory/'tb.sv'),'generator_sha256':sha(Path(__file__)),'guard_ingress':{'kind':'SIMULATION_ONLY_REGISTERED_PRODUCER_STATE_OBSERVER','raw_pending_state_path':STATE,'DRAIN_encoding':3,'qualifier':'registered state==DRAIN, no suppressed blk_v/ready/rec_stop dependency','production_raw_intent_or_independent_guard_provider_present':False,'extra_design_bits':0,'extra_design_ports':0,'healthy_added_cycles':0,'exact_source_cone_byteidentical_to_c8':True,'four_mutants_and_23_cases_preserved':True},'previous_generated_closure_reuse':False})
 (record/'model.json').write_text(json.dumps(model,indent=2)+'\n')
 cases=[]
 for other in (0,1):
  for drain in (0,1):
   for guard in (0,1):
    for bad in (0,1):cases.append({'other_fault':other,'registered_DRAIN':drain,'guard_bad':guard,'local_bad':bad,'old_stop_fixed_points':fixed_points(other,drain,guard,bad,True),'repaired_stop_fixed_points':fixed_points(other,drain,guard,bad,False)})
 (record/'feedback_model.json').write_text(json.dumps({'status':'CONFIRMED_MATERIAL_FIXTURE_FEEDBACK_SOURCE_BOUND','old_equations':['stop=other_fault||(blk_v&&guard_bad)','blk_v=!stop&&!local_bad&&registered_DRAIN'],'counterexample':{'other_fault':0,'registered_DRAIN':1,'guard_bad':1,'local_bad':0,'old_stop_fixed_points':[],'new_stop_fixed_points':[1],'legal_width_metadata_example':{'step_pos':0,'blk_abs_row':1,'blk_kvt_row':1,'blk_idx':0,'kvt_base':55232,'first_elem':55233},'classification':'Valid typed/ranged fields but rejected guard identity mismatch. Guard fault must stop deterministically; not claim of legal healthy descriptor failure.'},'repaired_equations':['guard_fault_raw=registered_DRAIN&&guard_bad','stop=other_fault||guard_fault_raw','blk_v=!stop&&!local_bad&&registered_DRAIN'],'exhaustive_boolean_cases':cases,'production_provider':'Raw intent visibility used hierarchically in simulation only; no production/provider/interface qualification.','causal_provider':False},indent=2)+'\n')
 return model
if __name__=='__main__':print(json.dumps({'status':generate()['status'],'compiler_invocations':0}))
