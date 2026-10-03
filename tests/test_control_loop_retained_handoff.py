import importlib.util,copy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cl',ROOT/'tools/control_loop_retained_handoff.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def sample():
 return {'label':'TEST','top':'TEST','period_ns':.833,'completed_at':'terminal','openroad_rc':0,
         'phases':{'rep':{'r2r_setup_wns_ps':-100,'r2r_path':{'startpoint':'s$_DFF_P_','endpoint':'t$_DFF_P_'}}}}
def test_failure_rc_does_not_promote_stale_timing_to_terminal_pass():
 d=sample();d['openroad_rc']=1
 r=M.screen(d,{'source':{'matched':True}})
 assert not r['timing_usable'] and r['status']=='TERMINAL_EXECUTION_OR_MEASUREMENT_FAIL'
def test_absent_timing_is_not_zero_slack_or_infinite_fmax():
 d=sample();d['phases']['rep']['r2r_setup_wns_ps']=None
 r=M.screen(d,{'source':{'matched':True}})
 assert r['placed']['r2r'] is None and not r['timing_usable']
def test_failed_or_ambiguous_source_binding_not_admitted():
 r=M.screen(sample(),{'source':{'matched':False}})
 assert not r['retained_source_all_matched'] and not r['placed']['physical_signoff']
def test_small_placed_miss_requires_route_and_no_free_FF_verdict():
 r=M.screen(sample(),{'source':{'matched':True}})
 assert r['route_before_small_miss_conclusion'] and r['placed']['FF_hold'] is None
 assert r['placed']['r2r']['fmax_MHz']==pytest.approx(1e6/933)
def test_routed_positive_loops_do_not_hide_output_failure():
 import json
 d=json.loads((M.EVIDENCE/'retained/routes/qwen_tp_seq_0833/corner_sta.json').read_text())
 r=M.routed(d)
 assert r['SS_register_to_register_slack_ps']>0 and r['SS_all_slack_ps']<0
 assert not r['reported_closes_signoff'] and r['FF_all_hold_slack_ps']>0
def test_actual_CDC_positive_two_two_and_no_clock_inheritance():
 import json
 c=json.loads((M.EVIDENCE/'references/current_crossing_model.json').read_text());r=M.ha6(c)
 assert r['positive_accept_cost_ns']['one_round_trip_sum']==pytest.approx(2/.9+2/1.2)
 assert r['replace_once_per_actual_round_trip_saving_ns']==pytest.approx(2/.9+3/1.2)
 assert not r['stale_minus75ps_repair_requested'] and not r['higher_clock_CDC_reuse_qualified']
 assert r['LAT3']['whole_token_measured_gain'] is None and not r['ladder_published_as_result']
def test_actual_cold_generation_preserves_failures_and_full_hash_closure():
 d=M.generate()
 assert d['actual_terminal_records']==45 and d['execution_or_measurement_failures']>0
 assert d['source_binding_gaps'] and not d['whole_target_SSFF_or_rate_PASS']
 assert d['all_ladder_rates_unvalidated_and_excluded']
 assert all(f['recurring_II_increase_selected'] is False for f in d['cycle_cost_fixes_MODEL_ONLY'].values())

def test_input_origin_endpoint_is_not_claimed_as_register_loop():
 d=sample();d['phases']['rep']['r2r_path']['startpoint']='op_g[2]'
 r=M.screen(d,{'source':{'matched':True}})
 assert not r['placed']['r2r']['register_origin_named']
 d['phases']['rep']['r2r_path']['startpoint']='d_hi[4]$_SDFFCE_PP0P_'
 assert M.screen(d,{'source':{'matched':True}})['placed']['r2r']['register_origin_named']
