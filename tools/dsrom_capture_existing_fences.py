#!/usr/bin/env python3
"""Prove selected publication ordering from existing LINQ ready admissions.
Conditional source partial order, not accepted PHW10 trace or latency bound.
Prior prospective SU guard remains history, unselected for this proven slice.
"""
import argparse,json
from pathlib import Path
import dsrom_capture_consumer_admission as A
from dsrom_capture_publication_credit import identity
BASE=A.ROOT/'results/uarch/dsrom_capture_existing_fences_20261003'
def source_basis(core):
 required=['wire qe_rom = (X_ROM != 0) && qe_mode == 2\'d0;',
 'assign qe_ready = qe_rom ? rom_ready_w : qe_ready_e;',
 '(d_unit == 3\'d3) ? qe_ready :',
 'waited && unit_ready && q_gate && kv_gate && m0_gate',
 'qe_go <= (d_unit == 3\'d3)',
 'wire          pred_ok = (c_pred == 2\'d0)',
 'd_skip <= !pred_ok || zero;',
 '(c_unit == 3\'d1 && (c_me_nout == 0',
 '(c_unit == 3\'d2 && (c_su_nout == 0',
 '(c_unit == 3\'d4 && `F(XU_OP)',
 'if (waited && (&idles) && !coll_busy)',
 'S_COLL_ARM: st <= S_COLL_WAIT;',
 'S_COLL_WAIT: if (!coll_busy)',
 'S_GO: begin pc <= pc + 1\'b1; st <= S_FETCH; end']
 if any(s not in core for s in required):raise ValueError('Native issue/ready/predicate source changed')
 # The native zero condition has no QE(unit3) disjunct.
 zero=core.split('wire          zero =',1)[1].split('always @(posedge clk)',1)[0]
 if "c_unit == 3'd3" in zero:raise ValueError('QE skip condition newly possible')
 return True

def proof(nodes,common_transaction_slot=True,ready_gated_by_publication_and_credits=True,X_ROM_enabled=True):
 layer=sorted((n for n in nodes if n.get('scope')==0 and n.get('kind')=='instruction'),key=lambda n:n['instruction_index'])
 c=A.census(nodes);rows=[]
 for p in c['producers']:
  if not p['capture_W1_W3']:continue
  candidates=[n for n in layer if p['producer_pc']<n['instruction_index']<p['first_consumer_pc'] and n['instruction'].get('unit')==3 and n['instruction'].get('qe_mode')==0 and n['instruction'].get('pred',0)==0]
  fence=candidates[0]['instruction_index'] if candidates else None
  collective=[n['instruction_index'] for n in layer if p['producer_pc']<n['instruction_index']<p['first_consumer_pc'] and n['instruction'].get('unit')==6 and n['instruction'].get('wait')==31]
  rows.append(dict(producer_pc=p['producer_pc'],VM_range=[p['base'],p['end_exclusive']],consumer_pc=p['first_consumer_pc'],consumer_wait=p['wait'],existing_later_LINQ_ready_fence_pc=fence,all_later_LINQ_fences_before_consumer=[n['instruction_index'] for n in candidates],collective_allidle_fences=collective,
   conditional_publication_order_proved=bool(fence is not None and common_transaction_slot and ready_gated_by_publication_and_credits and X_ROM_enabled)))
 return dict(rows=rows,all12_proved=all(r['conditional_publication_order_proved'] for r in rows),not_a_trace_or_clock_service_proof=True)

def check_accepted_order(events,producer_pc,fence_pc,consumer_pc,owned_producer_context):
 # Concrete schema for future enrolled callbacks. No fixture cycles generated.
 # Events must name the shared logical transaction provider; physical owner
 # stage may differ, but per-target bankready cannot replace global slotready.
 kinds=['last_owned_VMvisible','last_owned_credit_capture','bank_rearm','core_LINQ_admit','native_LINQ_accept','core_SU_admit','native_SU_accept','first_VM_read_accept']
 if set(events)!=set(kinds):raise ValueError('Complete accepted callback set required')
 expected_context=identity(owned_producer_context)
 if owned_producer_context['pc']!=producer_pc:raise ValueError('Enrolled producer PC/context')
 if any(identity(events[k].get('owned_producer_context',{}))!=expected_context for k in kinds):raise ValueError('Full169 priorowner user32/generation/version lineage')
 provider=events[kinds[0]]['logical_provider']
 if not provider or any(events[k]['logical_provider']!=provider for k in kinds):raise ValueError('Shared logical ready owner required')
 expected=[producer_pc,producer_pc,producer_pc,fence_pc,fence_pc,consumer_pc,consumer_pc,consumer_pc]
 if any(events[k]['pc']!=pc for k,pc in zip(kinds,expected)):raise ValueError('Accepted PC lineage')
 t=[events[k]['edge'] for k in kinds]
 if any(x is None for x in t):raise ValueError('No missing callback time substituted')
 if not all(b>a for a,b in zip(t,t[1:])):raise ValueError('Visibility/positive-credit/rearm/registered-admission/read order')
 return True

def build():
 d=A.inputs();source_basis(d['core.sv.gz']);nodes=json.loads(d['program.json.gz'])['nodes'];p=proof(nodes)
 if len(p['rows'])!=12 or not p['all12_proved']:raise ValueError('Current LINQ fence coverage incomplete')
 final=[r for r in p['rows'] if r['producer_pc'] in (92,93)]
 return dict(schema='DS_EXISTING_LINQ_PUBLICATION_FENCE_PROOF_1',candidate='DS4096-TP4-S58-PAR2-NP2048',prior_guard_proposal_commit='341e871cb305ae5e3fe520fb1e1f72894aaa3bd4',prior_sources_models_failures_unchanged=True,source_proof=p,final_GU5_chain=final,
  selected_common_ready_contract='One logical ROM-adapter transaction owner across local/remote physical stages: no rom_ready_w/nextLINQ acceptance until prior owned formatted rows VMvisible, sameidentity positive sourcecredit capture and packet debts complete. Rearm registered, never sameedge returned-credit reuse.',
  source_original_ready='qe_rom=(X_ROM!=0 && qe_mode==0); qe_ready selects rom_ready_w; unit_ready gates source core S_ISSUE; registeredqe_go/rom_q_go accepted nextedge; adapterready stS_IDLE&&s_ready',
  pred_and_skip='Every intervening LINQ descriptor has pred0; source zero does not test QEunit3. No legal skip bypass in this frozen healthy sequence. Fault/reset/program-change paths require fresh lineage gate.',
  no_new_SU_guard_required_for_these12_under_selected_contract=True,prospective_SU_guard_selected=False,selected_SU_guard_charge_mm2=0,no_existing_area_credit_taken=True,
  bankphase_release_separate_from_VMversion_lease=True,bank_rearm_does_not_wait_for_SUread=True,VMlease_retained_through_accepted_read_and_Rplus2=True,no_new_payloadseat_assumed=True,
  source_wait_bits={'ME':1,'SU':2,'QE':4,'XU':8,'HE':16},source_nextphase_ready_not_unitidle_alone=True,
  candidate_failure_conditions=['Per-target ready permits new LINQ before old logicalowner publication/credit terminal','Intervening LINQ skipped, mode!=0, X_ROM disabled or source program changed','Captured_credit frees sameedge or does not carry prior full169identity/user32','Competing writer changes protected VM extent after publication and before accepted SUread/tag','PhysicalCDC/ready callback does not implement source sharedslot order'],
  need_actual_callbacks_for_quantified_deadline=True,actual_current_PHW10_program_user_gen_origin=None,accepted_journal_handle=None,first_consumer_upper_edge=None,last_required_read_Rplus2_edge=None,exact_VMlease_peak=None,station_C=None,added_ready_stall_edges=None,token_delta_cycles=None,
  next_runtime_scope='Existing admitted source-owned trace: attach sourcecore LINQ/SUadmit->registeredaccept, priorownerVMvisible/credit/rearm and actual xs_rd_re src0 address + Rplus2 vx/cwx. No fullrun started here.',
  contextual_PR_admitted=False,actualprovider_qualified=False,new_jobs=[])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
