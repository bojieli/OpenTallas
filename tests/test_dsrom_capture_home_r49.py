import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_capture_home_r49 as M
@pytest.fixture(scope='module')
def model():return M.build()

def test_cold(model):assert model==json.loads((M.BASE/'model.json').read_text())
def test_source_width_area(model):
    s=model['per_shard_raw_homes']
    assert [v['seats'] for v in s]==[320,256]
    assert [v['raw_reserved_um2'] for v in s]==pytest.approx([35411.904,28329.5232])
    assert all(v['bbox_DBU'][2]-v['bbox_DBU'][0]==204930 for v in s)
    assert model['raw_bit_pitch_DBU']==2970

def test_overlap_removed_not_borrowed(model):
    assert model['eliminated_prior_overlap_um']==pytest.approx(47.844)
    assert model['common_shift_um']==pytest.approx(52.164)
    assert model['actual_raw_common_gap_um']==4.32
    assert model['corrected_common_bbox_DBU']==[11188476,15567120,11294586,15991290]
    assert model['area']['reduced_common_reserved_mm2']>model['area']['common_required_mm2']
    assert model['area']['reduced_common_reserved_mm2']==pytest.approx(.0450086787)
    assert model['geometry_raw_common_overlap_free']

def test_roles_and_feedback_cells(model):
    roles=model['actual_raw_bit_cell_roles'];assert len(roles)==7
    assert roles[-2]['role']=='feedback_BUF0' and roles[-1]['role']=='feedback_BUF1'
    assert roles[-2]['x_offset_DBU']==2214 and roles[-1]['x_offset_DBU']==2592
    assert model['forward_payload_does_not_traverse_feedback_BUFs']
    assert model['shared_restore_output_forward_fanout_load_change_requires_characterization']
    assert model['source_feedback_prototype_sha256'] is None
    assert not model['source_typed_feedback_hold_closed']

def test_source_pins_not_route_credit(model):
    paths=model['proposed_feedback_only_pin_routes_per_bit']
    assert len(paths)==6 and all(p['L1_projection_um']>0 for p in paths)
    assert all(p['actual_escape_layer_vias_OBS_and_wire_RC'] is None for p in paths)
    assert model['feedback_route_projection_not_routed_or_closed']

def test_raw_pg_width_and_phase(model):
    for p,r in zip(model['raw_M1_PG_overlay'],model['per_shard_raw_homes']):
        assert p['VSS_first_rail_bbox_DBU'][2]==r['bbox_DBU'][2]
        assert p['VDD_first_rail_bbox_DBU'][2]==r['bbox_DBU'][2]
        assert p['record_bit_pitch_DBU']==2970 and p['feedback_BUF_orientation']=='R0'
        assert p['M1_rail_length_um']==pytest.approx(2*r['seats']*204.93)
        assert p['existing_word_select_INV_in_MX_empty_row_unchanged']

def test_capacity_not_padding_or_repartition(model):
    assert len(model['root_banks'])==128 and sum(v['seats'] for v in model['root_banks'])==576
    assert model['compiled_weight_macros_per_die']==8192 and model['compiled_CFG_macros_per_die']==14336
    assert model['reticle_33by26_S58_NP2048_unchanged']
    assert model['no_combinational576way_crossdie_mux'] and model['no_global_field_ready']

def test_clock_reset_not_recharged(model):
    c=model['clock_reset'];assert c['baseline_FFbits_unchanged']==41227
    assert c['baseline_clock_RESETN_SETN_pin_loads_unchanged']
    assert c['feedback_combinational_BUFs_do_not_add_clock_or_reset_pins']
    assert c['added_new_token_selector_FF_CLK_and_reset_loads'] is None
    assert c['all_feedback_BUF_VDD_VSS_feeds_required']

def test_abi_and_domains(model):
    a=model['ABI'];assert (a['context_bits'],a['request_bits'],a['reply_bits'])==(170,187,240)
    assert a['req_reply_corridor_required_bits']==427 and a['token_capacity_C'] is None
    assert model['domains']['target_stream_GHz']==1.2 and model['domains']['target_serial_SU_GHz']==.9
    assert model['domains']['selected_CDC'] is None

def test_area_finite_no_extra_double_charge(model):
    a=model['area'];assert a['feedback_BUF_body_um2']==pytest.approx(8415.25524)
    assert a['full_owner_cells_with_feedback_mm2']==pytest.approx(.09663352812)
    assert a['interior_left_before_new_tokens_VM_forward_hold_routes_mm2']==pytest.approx(.03713272308)
    assert a['island_change_mm2']==0 and a['whole_reticle_screen_unchanged_mm2']==pytest.approx(759.4209905970058)
    assert a['no_extra_feedback_cost_on_top_of_containing_enclosure']
    assert a['actual_necessary_reticle_deficit_mm2'] is None

def test_no_false_admission(model):
    assert not model['physical_build_admitted'] and not model['physical_fit_proven']
    assert model['common_circuit_home_shard'] is None
    assert model['actual_tracks_after_pg_and_pin_union'] is None
    assert model['timing']['accepted_consumer_deadline'] is None
    assert not model['timing']['new_register_cuts_selected'] and model['new_jobs']==[]

def test_wrong_shard_ABI(monkeypatch):
    d,r=M.inputs();d['shard.json']['context_bits']=169
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='ABI'):M.build()

def test_negative_feedback_count(monkeypatch):
    d,r=M.inputs();d['shard.json']['feedback']['total_BUFs']-=2
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='role union'):M.build()
