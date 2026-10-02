import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_matched_leaf_clock_reset as M
@pytest.fixture(scope='module')
def model():return M.build()
def test_literal_all_ten_sinks_not_only_clones(model):
    for c in model['cases'].values():
        assert len(c['branches'])==10
        assert len({b['sink']['instance'] for b in c['branches']})==10
        assert len(c['proposed_original_launch_placements'])==2
        assert {b['buffer_levels'] for b in c['branches']}=={6}
def test_geometry_failure_not_erased_by_timing_screen(model):
    for c in model['cases'].values():
        assert c['route_PG_collisions']
        assert c['distinct_clock_net_guard_conflicts']
        assert c['cell_body_collisions']==[]
        assert c['body_inside_source_gap_or_capture_strips']
        assert c['route_D_network_conflicts']
        assert not c['physical_build_admitted']
def test_correlated_source_corner_skew_and_slew(model):
    for c in model['cases'].values():
        for t in c['source_SS_FF_RC_scenarios'].values():
            assert t['worst_relative_skew_ps']<25
            assert t['max_slew_ps']<320
            assert len(t['scenarios'])==14
            assert not t['qualified']
def test_reset_actual_five_pins_no_bank_reset_invention(model):
    for c in model['cases'].values():
        assert len(c['reset']['actual_RESETN_pins'])==5
        assert c['reset']['terminal_release_window_relative_to_previous_sink_rise_ps']==pytest.approx([117.5064,766.5025333333334])
        assert c['reset']['reset_provider_arrival_and_slew'] is None
        assert not c['reset']['reset_release_bound']
def test_corrected_hold_wires_only(model):
    assert all(c['corrected_hold_wire_um']==[5.697,18.972] for c in model['cases'].values())
def test_source_launch_reservation_no_instance_duplication(model):
    for c in model['cases'].values():
        assert c['original_FF_new_instance_count']==0
        assert [p['L1_um'] for p in c['producer_QN_to_hold_input']]==pytest.approx([.108,.432])
        assert c['producer_QN_to_hold_input'][1]['existing_bank_inverter_location_unbound']
def test_whole_union_and_token_unknown_not_zero(model):
    assert model['full_leaf0_existing_sink_union_still_required']
    assert model['full_token_latency'] is None
    assert model['transport_684_wire_union_placement'] is None
    assert model['acknowledgment_timeout1024_FAIL_preserved']
    assert not model['physical_build_admitted']
def test_price_counts_cells_once(model):
    assert model['new_clock_cell_area_um2']==pytest.approx(6.9984)
    assert model['conservative_new_clock_cell_reservation_per_shard_mm2']==pytest.approx(.0286654464)
def test_reach_refuses_short_fixed_matching_length():
    a={'upper_point_DBU':[16,116],'pin_point_DBU':[16,116]}
    b={'upper_point_DBU':[64016,116],'pin_point_DBU':[64016,116]}
    with pytest.raises(ValueError,match='cannot reach'):M.path(a,b)
def test_pin_lookup_refuses_unknown_pin(model):
    e=M.load(M.E); p=model['cases']['q']['proposed_original_launch_placements'][0]
    with pytest.raises(ValueError):M.literal(p,e['physical_master_templates'],'NOT_A_PIN')
def test_rejected_model_reproduces_exactly(model):
    p=M.OUT/'construction_r4/model.json'
    assert p.read_text()==json.dumps(model,indent=2,sort_keys=True)+'\n'

def test_macro_budget_subtracts_clkq_once(model):
    p=model['macro_parent_IO']
    assert p['remaining_before_setup_mux_wire_skew_ps']==pytest.approx(767.5732666666668)
    assert p['remaining_with_full25ps_skew_ps']==pytest.approx(742.5732666666668)
    assert p['actual_capture_setup_mux_wire_delay_ps'] is None
    assert p['capture_edges']==2 and p['lane_edges_after_capture']==1
