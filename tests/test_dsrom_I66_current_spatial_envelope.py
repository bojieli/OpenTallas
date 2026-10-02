import copy
import importlib.util
import json
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_I66_current_spatial_envelope as M

@pytest.fixture(scope='module')
def model(): return M.build()

def test_cold_artifact(model):
    assert model==json.loads((M.BASE/'model.json').read_text())

def test_current_capture_width_bank_rows(model):
    c=model['state_and_area']['actual_capture_banking_padding_tag_multiplex_control_area']
    assert c['exact_FF_bits']==41212
    assert c['seats']==576 and c['selected_FF_record_carrier_bits']==69
    assert [v['seats'] for v in c['per_shard']]==[320,256]
    assert [v['raw69_bits'] for v in c['per_shard']]==[22080,17664]
    assert c['common_owner_context_bits']==124
    assert c['pow2_memory_alternative_extra_raw_bits']==4416
    assert c['physical_memory_provider_selected'] is False

def test_circuit_cost_not_free(model):
    c=model['state_and_area']['actual_capture_banking_padding_tag_multiplex_control_area']
    assert c['mux_2to1_bit_equivalents']==70587 and c['row_compare_bits']==9216
    assert all(x>0 for x in c['illustrative_cell_components_um2'].values())
    assert c['illustrative_50pct_reservation_mm2']>0.075
    assert c['illustrative_clock_reset_32way_levels']==[[1288,41,2,1],[46,2,1]]
    assert c['clock_reset_32way_not_electrically_admitted']
    assert c['return_credit_mm2']==0

def test_source_bound_widths(model):
    b=model['boundary'];assert b['forward_bits']==330 and b['reverse_bits']==12
    assert b['full_duplex_bits']==684 and b['remote_credit_input_producer'] is None
    assert not b['source_credit_advertisement_output_present']
    n=model['native_ports'];assert n['cfg_local_bits_per_native_edge']==98304
    assert n['source_GO_edge']-n['source_cfg_last_capture_edge']==1
    assert n['PHW10_full_broadcast_bits']==1632 and n['BST']==17

def test_envelope_not_characterized_link(model):
    s=model['spatial'];assert s['segments_per_leg']==333
    assert s['requested_forward_edges']==s['requested_reverse_edges']==1337
    assert s['physical_successful_service_bound'] is None
    assert s['actual_available_tracks_PG_OBS_via_pin_union'] is None
    assert s['bound_not_data_characterization']

def test_exact_current_reuse_transport(model):
    p=model['current_scalar_reuse_prices']['positive1each_direction']
    assert p['six_W1_current_twoflit']['reuse_serial_transport_edges']==6390
    assert p['six_W1_current_twoflit']['per_expert_serial_transport_edges']==16080
    assert p['six_W1_full2048_descriptor_reuse_edges']==6516
    assert p['six_W1_full2048_descriptor_percopy_edges']==16206
    p=model['current_scalar_reuse_prices']['requested1337each_direction']
    assert p['six_W1_current_twoflit']['reuse_serial_transport_edges']==62502
    assert p['twelve_W1_W3_current_twoflit']['reuse_serial_transport_edges']==115050
    assert not p['no_loss_proven']

def test_timeout_failure_preserved(model):
    assert model['timeout']['default']['verdict']=='FAIL_DEFAULT1024'
    assert model['timeout']['actual_selected'] is None

def test_area_once_not_fit(model):
    w=model['composed_whole_area']
    assert w['exact_enable_core_um2']==[40.06584]*2
    assert w['replacement_enable_delta_mm2']==pytest.approx(.00095551488)
    assert w['corrected_predecessor_screen_mm2']==pytest.approx(754.9624927957258)
    assert w['selector_nine_calls_cycles']==3312
    assert w['WAKE_recharge']==w['ROM_ECC_recharge']==0
    assert w['field_sites_per_die']==2048 and w['all_compiled_macros_per_die']==8192
    assert w['existing_return_capture_containment_credit_mm2']==0
    assert w['no_containment_remaining_mm2']>98
    assert w['necessary_deficit_mm2'] is None
    assert not w['packing_overlap_free'] and not model['physical_build_admitted']

def test_negative_capture_overflow():
    d,_=M.inputs();d['capture.json']['stages']['0']['bank_depths'][0]=5
    with pytest.raises(ValueError,match='allocation differs'): M.capture_cost(d)

def test_negative_owner_fallback(monkeypatch):
    d,r=M.inputs();d['owners.json']['phase_choices'][383]['stage']=0
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='owner mismatch'): M.build()

def test_negative_source_currency(monkeypatch,tmp_path):
    d,r=M.inputs();b=tmp_path/'inputs';b.mkdir()
    row=copy.deepcopy(r[0]);row['sha256']='0'*64
    (b/'origins.json').write_text(json.dumps([row]))
    (b/row['copy']).write_text('{}')
    monkeypatch.setattr(M,'BASE',tmp_path)
    with pytest.raises(ValueError,match='Changed pinned'): M.inputs()

def test_port_state_containment_is_explicit(model):
    a=model['state_and_area']
    assert a['per_port_wrapper_pipeline_CDC_bits']==589539
    assert 0<a['per_port_FF_QN_restore_50pct_proxy_mm2']<a['port_strip_mm2']
    assert a['port_state_proxy_contained_in_strip_not_added_again']
    assert a['endpoint_CRC_mux_clock_reset_PG_wire_cost_unbound']

def test_capture_timing_budget_not_clkq_comparison(model):
    c=model['clock_context']
    assert c['native_hold_wire_um']==[18.972,5.697]
    assert c['twoedge_macro_capture_remaining_after_SS_clkq_and60ps_uncertainty_ps']==pytest.approx(767.5732666666666)
    assert not c['actual_capture_setup_mux_wire_budget_closed']
    assert not c['reset_release_recovery_removal_route_closed']
