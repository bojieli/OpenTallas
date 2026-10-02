import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_PAR2_source_deadline_join.py'
S=importlib.util.spec_from_file_location('edges',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
@pytest.fixture(scope='module')
def model():return M.build()
def event():return dict(source_issue=True,PP=1,accepted_gclk_edge=100,lane_valid=True,source_event_receipt='synthetic-directed-source-event',identity=[0,0,1,10,0,13,12])
def test_observed_accept_has_source_capture_and_consume_edges():
    r=M.main_callback(event());assert r['raw_capture_gclk_edge']==102 and r['original_lane_consumption_gclk_edge']==103
    assert r['absolute_stream_mapping_required']
@pytest.mark.parametrize('key,value',[('source_issue',False),('lane_valid',False),('accepted_gclk_edge',None),('source_event_receipt',''),('PP',0)])
def test_offered_or_invalid_input_cannot_be_accept(key,value):
    e=event();e[key]=value
    with pytest.raises(ValueError):M.main_callback(e)
def test_qualified_early_exact_and_late_terminal_cost():
    e=M.main_callback(event());assert M.exposed(e,101,102)==0
    assert M.exposed(e,102,103)==1 and M.exposed(e,104,106)==4
    with pytest.raises(ValueError):M.exposed(e,None,103)
def test_prefix_exact_off_by_one_and_held_credit():
    assert M.prefix_lead(320,192,1,1)==128
    assert M.prefix_lead(64,16,1,1)==48
    assert M.prefix_lead(320,192,2,1)==447
    assert M.prefix_lead(320,192,1,2)==129
def test_measurement_is_detector_only_not_clock_or_II_adoption(model):
    a,b=model['measured_detector_costs'];assert a['SS_clean_delay_ps']==525.730774 and b['SS_clean_delay_ps']==555.61792
    assert b['capture_fed_residual_for_FF_CLKQ_wire_setup_skew_ps']==pytest.approx(217.715413333333)
    t=model['detector_timing_window'];assert t['keep_provisional_held_II']==2 and not t['registered_capture_and_hold_closed']
    assert not model['physical_GO'] and not model['no_token_loss_proven']
def test_actual_profile_and_source_debit_no_doublecount(model):
    c=model['exact_offered_prefix_cases'][0];assert c['distinct_words_per_busy_leaf']==320 and c['ideal_II1_latency1_prefix_lead']==128
    assert c['lead_time_is_not_cache_word_capacity']
    assert model['source_seat_accounting']['additional_inline512_already_in5fc']
    assert model['detector_area_ledger']['additional_isolated_checkers_cell_mm2']>0
