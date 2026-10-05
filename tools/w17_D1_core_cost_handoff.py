"""Pure D1 expected-cycle/cost handoff. Unobserved runtime rate never invented."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REC=ROOT/'results/uarch/w17_D1_core_cost_handoff_20261002'
def finite_cost(*,cycles,init_seconds,seconds_per_cycle,logging_seconds):
    if type(cycles) is not int or cycles<0:raise ValueError('cycle envelope')
    if any(v is None for v in [init_seconds,seconds_per_cycle,logging_seconds]):return None
    for v in [init_seconds,seconds_per_cycle,logging_seconds]:
        if type(v) not in [int,float] or not 0<=v<float('inf'):raise ValueError('cost measurement envelope')
    if seconds_per_cycle==0:raise ValueError('unmeasured/infinite throughput')
    return init_seconds+cycles*seconds_per_cycle+logging_seconds

def build():
    pins=json.loads((REC/'retained_driver_pins.json').read_text())
    for n,r in pins.items():
        if hashlib.sha256((REC/n).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('retained driver metadata drift')
    main=(REC/'Vtb_D1__main.cpp').read_text()
    for text in ['contextp->threads(1);','topp->eval();','if (!topp->eventsPending()) break;','contextp->time(topp->nextTimeSlot());']:
        if text not in main:raise ValueError('original timed driver identity')
    callback=ROOT/'results/uarch/w17_D1_callback_terminal_archive_20261002/independent_review.json'
    actual=json.loads(callback.read_text())
    calpath=ROOT/'results/uarch/w17_D1_PC24_inputs_20261002/record.json';cal=json.loads(calpath.read_text());c=cal['calendar']['metrics']
    targets=[dict(event=n,pre_NBA_cycle=v,minimum_timed_evaluations=2*v,absolute_simulation_seconds=(v+1.5)*1e-9,expected_wall_seconds=None) for n,v in [('first_read_accept',12302),('first_read_reply',12355),('last_read_reply',136667),('staged',136669),('stream_done',136800)]]
    return dict(status='SOURCE_BOUND_COST_REVIEW_NO_NATIVE_OR_CORE_LAUNCH',core_model_commit='eae01d08de306166a402c613379121276f3632fb',dependency_publications=['65dce: self-contained2512 fixture/prerequisite manifest and enrolled source authority','f69cd549c: exact conditional credit1 calendar','8f9bf400: retained compile cost correction','43be7f7d6/main16e07: actual compile PASS/firstruntimeFAIL archive','tools/hdc_isa_v41.py SHA e32522bab7199130df40a0ba3e4452b6f6ad1cd008372b58ab4c3eda344c17c3'],
      receipt_pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [callback,calpath,ROOT/'results/uarch/w17_D1_portable_successor_20261002/prerequisite_manifest.json']},
      actual_leaf_compile=dict(total_seconds=actual['compile_wall_seconds'],phase_report=actual['frontend_report'],binary_sha256=actual['binary_receipt']['sha256'],CXX_flags='-O0; OPT_FAST/OPT_SLOW/OPT_GLOBAL=-O0',runtime_threads=1,compile_affinity=[0,1],compile_workers=2,generated_bytes_report='638.156 decimal MB /960 C++ files; not RSS or runtime cost'),
      actual_runtime=dict(wall_cap=20,wall_to_kill=actual['first_failure_wall_seconds'],retained_stdout_bytes=0,retained_events=0,actual_cycles=None,construction_seconds=None,first_eval_seconds=None,seconds_per_cycle=None,logging_seconds=None,stdout_buffering_loss_not_excluded=True,rate_from_original_full_L0_transferable=False),
      expected_conditional_cycle_targets=targets,expected_elapsed_cycles=dict(descriptor_to_stage=c['staged']-c['start'],descriptor_to_stream_done=c['done']-c['start'],qualified_request_reply_min=34,qualified_request_reply_max=241),
      model_equation='T_wall = measured constructor/initialization + N_source_cycles*measured seconds_per_cycle + measured observation cost, all for exact same model/binary/flags/clock binding',expected_wall_seconds=finite_cost(cycles=136800,init_seconds=None,seconds_per_cycle=None,logging_seconds=None),
      core_phase_expectation=dict(start=12294,NSLOT=1,descriptor_source_accept=12300,phase_source_only=True,requires_actual_pre_NBA_accept=True,if_decode_writer_busy='No calendar admitted; measure original S_DEC and win_idle, no clock/epoch forcing'),
      native_only_observability_option=dict(selected=False,GO=False,purpose='Measure execution feasibility before expensive actual-core compile; no callback/core qualification transfer',engine_rerun=False,frontend_invocations=0,reuse='Existing generated model archive/global objects, replace only generated native main with additive inverse-proved observation copy',retain_driver=['threads1','identical reset/program/clock/body via unchanged compiled model','every eval and exact nextTimeSlot','same +CASE and commandArgs'],markers=['CONTEXT_ENTER/RETURN','CONSTRUCTOR_ENTER/RETURN','first16 EVAL_ENTER/RETURN with hosttime/simtime/evalcount','periodic heartbeat each256 evals','FINAL_ENTER/RETURN'],unbuffered='direct stderr write for host markers; copied host stdout setvbuf(_IONBF) before construction for existing $display; observational only',bound='No runtime cap increase proposed: if separately admitted, diagnostic uses existing20s runtime cap; cannot claim it reaches12302 or any causal target',model_budget_status='Native relink tool/ABI/object hashes and fresh lease require review before GO; no new compiler command admitted here',nominal_logging_estimate_not_a_bound='Minimum273600 clock evals imply about1070 periodic markers at256eval cadence, plus32 initial markers and phase markers; nominal<600KiB. Extra scheduler slots are unmeasured; enforce a separate log cap if admitted.',what_it_cannot_see='Retained leaf has no real core, so no actual four predicates. Clock advancement is cost evidence only.'),
      causal_gate=dict(require='actual original real core + original descriptor/WINDOW owners; fourbits/context preNBA and registered issue postNBA; source-qualified read/WRACK/publication identities',why='Distinguishes adapter readiness, descriptor staging/stale pulse, and producer lifetime blockers which source callbacks alone cannot identify',controlled_program='single full-shape ME/attention +drainedEND, entry0; original PC24 class/wait2, not original token data or retained PC24 owner state',original_cause_limit='Original fourbit/callback trace absent: controlled reproduction can qualify mechanism but cannot establish which original predicate was false.',attention_endpoint_binding='Unresolved V41_ATT_CUT exact engine binding/closure; old leaf12GiB cannot be inherited',service_status='BOUND_MISSING',no_original_full_L0_restart=True),compiler_invocations=0,simulations=0)
if __name__=='__main__':print(json.dumps(build(),indent=2))
