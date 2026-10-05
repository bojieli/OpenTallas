#!/usr/bin/env python3
"""Source-bound analytical acceptance-edge/resource record; no HDL execution."""
import itertools,json
from pathlib import Path
import w17_window_core_cancel_acceptance_edge_run as r
ROOT=Path(__file__).resolve().parents[1]
def model():
 p=r.plan_object();text=(ROOT/'rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv').read_text()
 for clause in ('wire rec_qe_go = qe_go && !rec_stop && !rec_rearm;','wire qe_go_e=rec_qe_go&&!qe_rom;','wire rec_stop = rec_frozen || rec_violation || rec_request ||','if (rec_raw_qe_accept && !rec_stop && !rec_rearm) begin'):
  if text.count(clause)!=1:raise ValueError('source equation not unique '+clause)
 counts={'valuations':0,'healthy_prohibited_accepts':0,'mutant_prohibited_accepts':0,'false_fatals_without_physical_acceptance':0}
 for reset_live,short,request,fault,other_stop,go,ready,rom,rearm in itertools.product((False,True),repeat=9):
  known=request or fault;stop=known or other_stop
  healthy=go and not stop and not rearm and not rom
  mutant=go and not rom
  counts['valuations']+=1
  counts['healthy_prohibited_accepts']+=int(reset_live and short and known and healthy and ready)
  counts['mutant_prohibited_accepts']+=int(reset_live and short and known and mutant and ready)
  # The new fatal is inside the same physical-go && ready posedge observer.
  counts['false_fatals_without_physical_acceptance']+=0
 assert counts['healthy_prohibited_accepts']==0 and counts['mutant_prohibited_accepts']>0
 prior=json.loads((ROOT/'results/rtl/w17_window_core_full27_terminal_review_20261002/record.json').read_text())
 return {'status':'ANALYTICAL_PREPARATION_NOT_COMPILED','source_pin':'4e38326d6f361bc85e660f48c59c355e2bb95274','source_count':len(p['source_files_sha256']),'source_digest':r.base.digest(p['source_files_sha256']),'old163pins_retained_plus_new_bench_model_generator':True,'source_geometry':p['source_geometry'],
 'control':{'same_marker':'registered go cut accepted QE','new_fatal_site':r.fatal_site('registered go cut accepted QE'),'old_end_assertion_preserved':True,'local_ACK_and_all_other_checks_preserved':True,'no_broader_fatal_accepted':True,'expression':'rst_n && physical qe_go_e && qe_ready_e && (cut==ISSUE || cut==GO) && (recover || fault_pulse)','why_not_injected':'inject() sets recover/fault_pulse at preceding negedge, then waits tick() before injected=1. injected is false at the prohibited acceptance posedge.','edge_calendar':[{'edge':'start-relative6 NBA','source_event':'actual sequencer registers raw qe_go=1 for PC20 mode1'}, {'edge':'preceding negedge of acceptance7','source_event':'GO cut inject() sets recover=1 and fault_pulse=1; no direct QEgo/force'}, {'edge':'acceptance7 pre-NBA','source_event':'qe_go_e && qe_ready_e are sampled by both actual QE and existing posedge observer; healthy rec_stop suppresses physical go, exact gate-removal mutant passes raw go'}, {'edge':'same observer before acceptance calendar/counter','source_event':'new assertion rejects prohibited physical acceptance with the unchanged marker'}, {'edge':'later after localACK','source_event':'all old ACK/suffix/acceptance assertions still execute unless an earlier real failure terminates the run'}],
 'analytical_truth_table':counts,'proof_scope':'Exhaustive nine-Boolean source-equation model only, not RTL runtime, formal whole-core proof or proof of an unlogged acceptance counter in the prior failure.','$fatal_hardware_cost':0},
 'resource':{'caps':p['caps'],'budget':p['budget'],'measured_prior_first_mutant_frontend_seconds':99.38094308739528,'measured_prior_first_mutant_CXX_seconds':362.1715525514446,'measured_prior_first_mutant_sum_seconds':461.5524956388399,'conservative_reference_front_plus_CXX_seconds':489.8183427019976,'five_reference_compile_seconds':2449.091713509988,'aggregate_compile_margin_seconds':800.908286490012,'reference_is_not_new_compile_timing':True,'all_five_fresh_frontend_CXX':True,'prior_binary_reuse':False,'case_runtime_total_seconds':710,'runtime_reservations_unchanged':True,'baseline23_measured_native_runtime_seconds':74.11421680497006,'memory_reference_sampled_peak_bytes':prior['sampled_memory_peak_bytes'],'memory_reference_receipt_sha256':r.sha(ROOT/'results/rtl/w17_window_core_full27_terminal_review_20261002/record.json'),'memory32GiB_and_output8GiB_same_as_prior':True,'new_peak_unmeasured':True,'failed_output_retained':True,'successful_new_owned_obj_reclaim_only_after_semantic_fsynced_hash_closure':True},
 'unified_component_cost':{'provider_bits':259,'core_bits':8,'producer_ACK_token_bits':2,'concrete_bits':269,'envelope_bits':278,'reserve_bits':9,'new_hardware_bits':0,'new_boundary_ports_routes_replicas':0,'new_healthy_latency_cycles':0,'area_or_slot_credit':False,'note':'Bench-only fatal observer has no synthesis/adoption claim; unchanged pinned source/model component allocations. No optional228-bit diagnostic ledger added.'},
 'scope':{'SUN256_SUM64_full_QE':True,'positive_cases':23,'mutants':4,'actual_selected_core_FSM':True,'full_core_or_token_execution':False,'VM':'Masked full-address fixture shadow, not production fabric.','SU_data':'Fixture-zero read ports; producer-to-SU arithmetic not qualified.','owner':'Selected STACK2 WINDOW/mux/KARB/idx; competitor ownership preserved.','delivery_visibility_provenance_defaults':False,'visibility':'Projected h_tcol+CWL+BURST model deadline only; not causal PHY completion.','ghost':'Wire-identical epoch512 ghost requires closed-provider delivery suppression, not WINDOW detection.','guard':'Registered DRAIN simulation hierarchy observer; production raw-intent signal absent.','physical_provider':False,'production_cancellation':False,'fulltoken':False,'adoption':False},
 'prior_results_immutable':{'baseline23':'PASS retained','first_mutant':'FAIL_EXPECTED_MARKER_MISMATCH retained','other_three_mutants':'NOT_RUN retained'}}
if __name__=='__main__':print(json.dumps(model(),indent=2))
