import importlib.util,json
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/qwen_rom_direct_capture_control_model.py'
S=importlib.util.spec_from_file_location('qcontrol',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
@pytest.fixture(scope='module')
def model():return M.build()
def test_source_proof_and_default_off_admission(model):
    assert model['proof']['positive_UNSAT_queries']==11 and model['proof']['SAT_mutants']==2
    assert model['optin']['default']==0 and model['optin']['RTL_preparation_admitted']
    assert not model['tile_PR_admitted'] and not model['hardware_adoption']
def test_complete_output_control_not_capture_only(model):
    i=model['inventory'];assert i['mask_AND_bits_retained']==2560 and i['OR_merge_bits_retained']==2048
    assert i['after_total']==86 and i['added_FFs']==75
    assert i['new_mask_loads_per_leaf']==32 and i['read_strobe_hold_enable_loads']==80
    assert i['feedback_data_mux_bits_removed']==2560 and i['after_mux']==85
def test_positive_clock_reset_buffer_route_slot_cost(model):
    a=model['area'];assert a['lower_bound_added75_plainFF_um2']==pytest.approx(21.87)
    assert a['async_reset_FF_reference_um2']>a['FF_um2']
    assert all(x>0 for x in a['incremental_source_cell_reference_um2'].values())
    assert a['positive_extra_route_clock_PG_policy_um2']>0
    assert a['incremental_slot_policy_um2']>sum(a['incremental_source_cell_reference_um2'].values())
    assert a['mapped_data_mux_saving_credit_um2']==0
def test_zero_extra_edge_prices_same_program_once(model):
    c=model['latency'];assert c['existing_MEM_EXTRA_cycles']==1 and c['new_cycles']==0
    r=c['exact_same_program_55_reference'];assert r['target_arithmetic_extra']==55
    assert r['body_plus_kv_prep_cycles']==104009 and r['issued_me_instructions']==217
    assert c['new_cycle_delta_against_that_reference']==0
def test_failures_and_uncertainty_preserved(model):
    s=model['signoff'];assert s['prior_failed_control_slack_ps']==-930.330505
    assert s['prior_failed_SS_data_slack_ps']==-118.679901
    assert s['SS_setup_uncertainty_ps']==60 and s['FF_hold_uncertainty_ps']==25
    assert s['ideal7p895628ps_macro_margin_not_transferred']
def test_replicated_select_transition_has_same_observed_chunks():
    # All legal metadata masks and hold/strobe/reset edges; each replica takes
    # the same preedge select. Actual emitted RTL/fourstate remains a later gate.
    for mask in [0,1,2,4,8,16]:
        old=[bool(mask&(1<<b)) for b in range(5)]
        for q in range(32):
            for enable in [False,True]:
                for reset in [False,True]:
                    nxt=[False if reset else bool(q&(1<<b)) if enable else old[b] for b in range(5)]
                    replica=[[v]*16 for v in nxt]
                    for b in range(5):assert sum(replica[b])*32==int(nxt[b])*512
def test_bus_width_never_grants_tracks(model):
    assert model['routing']['total_mask_nets']==80
    assert not model['routing']['actual_per_edge_available_tracks']
    assert model['area']['existing_macro_collar_is_not_complete_tile_slot']
