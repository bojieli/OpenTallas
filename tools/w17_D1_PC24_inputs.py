#!/usr/bin/env python3
"""Recheck an existing exact bounded service calendar; no compilation or launch."""
import hashlib,importlib.util,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OWNER=Path('/home/ubuntu/w17-window-epoch-candidate')
MODEL=OWNER/'tools/w17_window_epoch9_timing_model.py'
PRED=OWNER/'results/uarch/w17_window_epoch9_reproducible_prediction_20261001/run1/prediction.json'
EVENTS=PRED.parent/'credit1_events.jsonl'
EXPECTED_MODEL='061d685634e33b3601a41b11f366091a8dc879feb8f6e69f42791c77b4b208dd'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def summary(events,cut):
    prior=[e for e in events if e['cycle']<=cut]
    req=[e for e in prior if e['kind']=='request'];rsp=[e for e in prior if e['kind']=='reply']
    return {'cut_cycle':cut,'requests':len(req),'replies':len(rsp),'pending':len(req)-len(rsp),'rows_scale_returned':sum(e['sector']==16 for e in rsp),'last_request':req[-1] if req else None,'last_reply':rsp[-1] if rsp else None,'is_original_live_observation':False}
def build():
    if sha(MODEL)!=EXPECTED_MODEL:raise ValueError('existing calendar model changed')
    old=json.loads(PRED.read_text())
    idx=subprocess.check_output(['git','show','4e38326d6f361bc85e660f48c59c355e2bb95274:rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv'],cwd=ROOT)
    if hashlib.sha256(idx).hexdigest()!=old['idx_sha256']:raise ValueError('backend source pin differs')
    spec=importlib.util.spec_from_file_location('original_calendar',MODEL);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    arm,events=m.replay(1,12300,old['params'])
    stored=[json.loads(x) for x in EVENTS.read_text().splitlines()]
    if events!=stored or arm!=old['arms']['1']:raise ValueError('calendar replay differs; preserve mismatch, no fit')
    live=ROOT/'results/uarch/w17_PC24_terminal_admission_20261002/record.json'
    terminal=json.loads(live.read_text());cycle=terminal['terminal']['cycles'];WD=100000
    req={};dur=[]
    for e in events:
        key=(e['row'],e['sector'])
        if e['kind']=='request':req[key]=e['cycle']
        else:dur.append(e['cycle']-req[key])
    cpp='rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'
    raw=subprocess.check_output(['git','show',m.PIN+':'+cpp],cwd=ROOT)
    if b'if (cyc - last_move > WD)' not in raw:raise ValueError('watchdog source changed')
    return {'scope':'D1_EXACT_BOUNDED_FIXTURE_CALENDAR_NOT_ORIGINAL_LIVE_STATE','source_commit':m.PIN,'original_program_sha256':'e3d93b7bd9b74773c109761c41fbe5fcd72503a2513ac420abc5ddfffae9dd4a','pins':{'model_sha256':sha(MODEL),'prediction_sha256':sha(PRED),'events_sha256':sha(EVENTS),'terminal_record_sha256':sha(live),'host_source_sha256':hashlib.sha256(raw).hexdigest()},'replay':'PASS_ALL2176_REQUESTS_AND2176_REPLIES_AND_PER_PC_METRICS_IDENTICAL','calendar':arm,'edge_identities':old['edge_contract'],'parameters':old['params'],'fixture_binding':{'WIN_STACK':2,'original_live_WIN_STACK':0,'REFPB':3,'clock_note':'Bench toggles500ps; internal model CLK_PS1000. Event cycle equivalence only, no physical clock qualification.','reset_start':old['reset_start'],'cold_no_competitors':True,'historical_prime_API_rows':128,'writes':0,'original_postwriter_bank_queue_state_not_reconstructed':True},'request_to_reply_cycles':{'min':min(dur),'max':max(dur)},'refresh_total':sum(x['refreshes'] for x in arm['per_PC']),'activation_total':sum(x['activations'] for x in arm['per_PC']),'watchdog':{'WD':WD,'terminal_cycle':cycle,'last_ANY_rank_PC_change_inferred_from_tickwise_host':cycle-WD-1,'not_descriptor_start':True,'fixture_staged_minus_live_terminal':arm['metrics']['staged']-cycle,'healthy_refill_minus_PC_threshold':arm['metrics']['refill']-WD},'conditional_fixture_at_original_terminal_cycle':summary(events,cycle),'exact_original_admission':'me_ready && kv_ok && !kvd_v && win_idle','original_terminal_proves':['S_ISSUE','decoded_ME_unit1','all_unit_idles31','SU_wait_satisfied','no_issue_pulse','no_reported_fault','done_false'],'original_missing_inputs':['selected_ME_adapter_ready_and_state','kv_ok_and_descriptor_lifecycle_state','kvd_v','core_packed_writer_win_idle_state','actual_source_start/reset_origin','source_prefetch_state/rows','accepted_read_intents_addr_tag_len','routed_and_qualified_reply_owner_tag_beat_poison','accepted_WC_WS_addr_tag_mask','qualified_selected_writer_ACK_pending_intent','per_PC_bank/open/refresh_deadline/queue_state','other_requester_pending_state'],'cause_status':'kv_ok descriptor staging barrier is leading candidate; actual callback/state missing, causal deadlock not established. Timer mismatch proved only against same-reset cold fixture.','next_actions':['Hubble: supply existing original terminal/source provenance and any retained callback evidence; native public benchmark held, no new original run.','Maxwell: independent actual admission edge/control review and source-bound writer calendar inputs; no duplicate compile.','Owner: freeze additive four-bit and qualified read/write/ACK instrumentation and writer calendar, maintain original fails; await resourceproposal3e90 review and fresh GO.','12GiB runner only after model/fixture source hashes and cap review; old4GiBfailed runner never edited/retried.'],'bounded_gate_status':'MODEL3e90_PROPOSED_AWAITING_REVIEW_NO_GO_NO_COMPILATION','physical_visibility':False,'original_causal_deadlock_proof':False,'whole_L0_prediction':None,'PVE2_PVE3_jobs':[]}
if __name__=='__main__':print(json.dumps(build(),indent=2))
