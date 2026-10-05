#!/usr/bin/env python3
"""Fail-closed prelease/publication/consumer boundary requirements from unchanged sources."""
import argparse,copy,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];PIN='d2c28c279c4b8df731f9c4937e790831529a954b'
SOURCES=['rtl/chip/ot_chip_v41x_ckv_die_service.sv','rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv','rtl/chip/ot_chip_v41x_rope_hbm_cache.sv','rtl/chip/ot_chip_v41x_window_kv_prefetch.sv','rtl/chip/ot_chip_v41x_ckv_stream_merge.sv','rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv','rtl/chip/ckvsel/ot_chip_v41x_die.sv','rtl/w17_runtime/hdc/v41x/ot_hdc_v41x_att_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_attn.sv']
REQUIRED=('C_fetch_retired','C_VM_ID_pipeline_empty','encoder_retired','P_old_requests_returns_retired','P_hold_released_if_reuse','W_old_job_retired','W_bank_pipeline_empty','B_old_job_retired','backend_request_empty','backend_response_empty','prior_B_K_write_owners_zero','old_peer_TX_RX_empty','old_collector_writes_zero')
def validate(x):
 errors=[]
 for k in REQUIRED:
  if x.get(k) is not True:errors.append('prelease:'+k)
 peers=x.get('peers',[])
 if len(peers)!=4:errors.append('four_peer_receivers')
 for p in peers:
  if p.get('rank_rows')!=512 or p.get('row_bits')!=2304 or p.get('generation')!=x.get('generation') or p.get('reserved') is not True:errors.append('peer_rank_seats')
  if p.get('finite_hardware_hop_credit') is not True or p.get('actual_calendar_binding') is not True:errors.append('peer_hop_calendar')
 if x.get('exclusive_all32PC_lease') is not True:errors.append('exclusive_lease')
 writes=x.get('writes',[])
 if len(writes)!=9 or sorted(w.get('sector',-1) for w in writes)!=list(range(9)):errors.append('nine_unique_sectors')
 prev=None
 for w in writes:
  c,v,a=w.get('column_ps'),w.get('visible_ps'),w.get('accepted_ps')
  if any(type(z)!=int for z in (c,v,a)) or v<c+7274 or a<v:errors.append('actual_burst_visibility');continue
  if w.get('actual_backing_commit') is not True or w.get('data_match') is not True or w.get('held_until_accept') is not True:errors.append('write_provider_postcondition')
  if prev is not None and c<prev:errors.append('single_outstanding_owner')
  prev=a
 publish=x.get('publish_ps');fetch=x.get('new_fetch_ps')
 if type(publish)!=int or prev is None or publish<prev or type(fetch)!=int or fetch<publish:errors.append('publish_before_fetch')
 for k in ('read_fence','all_expected_beats_accepted','merger_final_emit_accepted','attention_desc_DRAIN_to_IDLE','attention_engine_idle','vector_output_writes_empty','collectives_retired','reverse_CDC_credit_return'):
  if x.get(k) is not True:errors.append('final_consumer:'+k)
 if x.get('credit_released_before_final_consumer') is not False:errors.append('early_credit_release')
 return sorted(set(errors))
def build():
 raw={p:subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT) for p in SOURCES}
 die=raw[SOURCES[0]].decode();clear=die.index('present <= 0; npresent <= 0;');later=die.index("npresent <= npresent + (KW+1)'(nwr);",clear)
 assert later>clear and "if (sel_v && !rd_act)" in die and "assign job_done = m_done;" in die
 assert 'if (cur == id_count && id_done && !e_v && busy == 0 && !o_v)' in raw[SOURCES[1]].decode()
 assert 'if (next_row == total && full[~o] == 1\'b0)' in raw[SOURCES[4]].decode()
 assert 'DRAIN: begin' in raw[SOURCES[5]].decode() and 'else if (engine_idle) begin state <= IDLE; done <= 1\'b1;' in raw[SOURCES[5]].decode()
 x={k:True for k in REQUIRED};x.update(generation=1,peers=[dict(rank_rows=512,row_bits=2304,generation=1,reserved=True,finite_hardware_hop_credit=True,actual_calendar_binding=True) for _ in range(4)],exclusive_all32PC_lease=True,writes=[dict(sector=i,column_ps=i*7274,visible_ps=(i+1)*7274,accepted_ps=(i+1)*7274,actual_backing_commit=True,data_match=True,held_until_accept=True) for i in range(9)],publish_ps=9*7274,new_fetch_ps=9*7274,credit_released_before_final_consumer=False)
 for k in ('read_fence','all_expected_beats_accepted','merger_final_emit_accepted','attention_desc_DRAIN_to_IDLE','attention_engine_idle','vector_output_writes_empty','collectives_retired','reverse_CDC_credit_return'):x[k]=True
 assert validate(x)==[]
 mutants={}
 for k in REQUIRED:
  m=copy.deepcopy(x);m[k]=False;assert validate(m);mutants[k]=validate(m)
 for k in ['attention_desc_DRAIN_to_IDLE','attention_engine_idle','reverse_CDC_credit_return']:
  m=copy.deepcopy(x);m[k]=False;assert validate(m);mutants[k]=validate(m)
 m=copy.deepcopy(x);m['writes'][8]['visible_ps']=m['writes'][8]['column_ps'];mutants['legacy_column_done']=validate(m);assert mutants['legacy_column_done']
 m=copy.deepcopy(x);m['writes']=m['writes'][:8];mutants['only_eight_writes']=validate(m);assert mutants['only_eight_writes']
 m=copy.deepcopy(x);m['peers'][0]['actual_calendar_binding']=False;mutants['host_ready1']=validate(m);assert mutants['host_ready1']
 m=copy.deepcopy(x);m['credit_released_before_final_consumer']=True;mutants['early_credit']=validate(m);assert mutants['early_credit']
 return dict(status='PASS_SOURCE_BOUND_REQUIREMENTS_CURRENT_PATH_BLOCKED',source_pins={p:dict(commit=PIN,path=p,sha256=hashlib.sha256(b).hexdigest()) for p,b in raw.items()},
 actual_retirement=dict(C='fetch done+ready+no fault; all busy/e_v/o_v/queues retired; VM rd_act/rq_v/tail clear; encoder inactive; do not require step/go zero',P='all8 returns captured/no req/rsp and stateIDLE, fault0; pf_rdy held-cache hit not sufficient; release hold before cache reuse',W='stateIDLE+fault0+balanced old requests/returns; complete two writes through strong burst-visible provider; bank pipeline empty; no ready-on-fault substitution',peer='old TX/RX in-flight and collector writes zero before new selection; reserve allK512 generation-qualified seats eachrank plus3copy fanout finite hop credits',final='merger final emit actual attention-stage write acceptance, THEN descDRAIN+engine_idle+no vectorwrites+collective completion; credit reverseCDC afterwards'),
 peer_storage=dict(rows_per_rank=512,row_bits=2304,bytes_per_rank=147456,existing_collector_storage=True,new_payload_buffer_claim=False,remote_copies_per_owned_row=3,current_RX_ready=False,current_generation_port=False,current_hardware_hop_calendar=None),
 actual_source_blockers=[dict(kind='collector_count_clear_overridden',clear_line=die[:clear].count('\n')+1,override_line=die[:later].count('\n')+1,consequence='Later nonblocking assignment overrides npresent clear even nwr0; repeated selection cannot assume fresh count',measured_RTL_counterexample=False),dict(kind='old_selection_guard_incomplete',actual='sel_v&&!rd_act',missing='C fetch/output/peer/encoder/writer/merger/P/W/backend retirement'),dict(kind='legacy_write_semantics',actual='c_wr_done unused; wr_act releases after ninth grant; current mux blocks C writes; backend commits at column',required='writable source-selected mux + single-owner event through actual burst commit + nine accepted visible writes'),dict(kind='unbound_peer_provider',actual='three ag_rx_valid lanes always taken, no ready or generation',required='preallocated generation-qualified seats and finite physical hop+reversecredit provider'),dict(kind='completion_scope',actual='service job_done=m_done',required='actual desc lifecycle done+engine idle/output writes quiet; cut backend must supply actual engine completion')],
 model_checks=dict(synthetic_positive_requirements=True,rejected_mutants=mutants,synthetic_calendar_not_measured_service=True),
 current_source_admission=False,model_admission=False,hardware_admission=False,RTL_changed=False,scope='Source-extracted requirements and fail-closed synthetic boundary oracle; actual endpoint gates separately qualified, no full boundary runtime/latency/physical claim',next_required='Ram joint latency/ports/finitebuffers/route admission for composed prelease+peer+backend+consumer; source-selected executable top event providers, preserve originals')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();r=build();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'mutants':len(r['model_checks']['rejected_mutants']),'admission':False},indent=2))
