import copy,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_capture_home as M
@pytest.fixture(scope='module')
def model():return M.build()

def test_cold_equality(model):
    assert model==json.loads((M.BASE/'model.json').read_text())

def test_exact_home_and_source_grid(model):
    assert model['model_selected_home_DBU']==[10974906,15562800,11298906,15995610]
    b=model['model_selected_home_DBU'];assert b[0]%54==b[2]%54==0 and b[1]%270==b[3]%270==0
    assert model['known_rectangle_collision_count']==0
    assert model['model_geometry_home_reserved'] and not model['physical_fit_proven']

def test_directional_cut_not_width(model):
    a=model['arrival_cut'];assert a['direction']=='HORIZONTAL'
    assert a['lanes']==4416 and a['minimum_gross_edge_um']==pytest.approx(423.936)
    assert a['enclosure_height_um']==432.81
    assert a['halfpool_reserved_track_sites']>=4416
    assert a['actual_available_tracks_after_OBS_PG_clock_pin_via_union'] is None

def test_all_root_banks_match_row_modulo(model):
    banks=model['root_banks'];assert len(banks)==128
    for b in banks:
        rows=[r for r in range(576) if (r%256)//2==b['global_root']]
        assert len(rows)==b['seats']
        assert b['global_root']==64*b['shard']+b['local_root']
        assert b['write_ports']==1 and b['no_ready']
    assert sum(b['seats'] for b in banks)==576

def test_shard_templates_are_distinct_die_homes(model):
    slots=model['per_shard_raw_slots']
    assert [s['seats'] for s in slots]==[320,256]
    assert [s['record_bits'] for s in slots]==[22080,17664]
    assert all(s['placed_on_distinct_shard_die'] for s in slots)

def test_common_union_and_PG_positive(model):
    assert model['common_reserved_mm2']>model['common_logic_required_mm2']>0
    assert model['per_die_outer_PG_ring_reservation_mm2']>0
    assert model['common_circuit_home_shard'] is None
    assert model['common_physical_576way_tree_must_not_span_dies_combinationally']
    assert model['VM_bridge_state_logic_route_excluded']

def test_inventory_and_area_not_dropped(model):
    assert model['retained_field_pairs']==2048 and model['retained_weight_macros']==8192
    assert model['retained_cfg_macros']==14336 and model['no_retained_instance_or_capacity_removed']
    a=model['whole_area'];assert a['no_containment_screen_mm2']==pytest.approx(a['predecessor_screen_mm2']-a['replaced_old_capture_proxy_mm2']+a['new_capture_enclosure_mm2'])
    assert a['remaining_to858_mm2']>98 and a['actual_necessary_deficit_mm2'] is None
    assert not a['WAKE_enable_BF_selector_station_recharged']
    assert a['selector_station_cycles_per_call']==226
    assert model['inherited418_service_debit_containment_credit_mm2']==0

def test_clock_reset_positive_source_tree_not_extra_charge(model):
    c=model['clock_reset'];assert c['source_FO8_trees']['clock']==[5154,645,81,11,2,1]
    assert c['source_FO8_trees']['reset']==[186,24,3,1]
    assert c['clock_reset_buffers_already_in_body_price'] and c['no_prior32way_tree_recharge']
    assert c['source_pin_loads']['FF']['clock_pin_fF']==pytest.approx(21492.939856)
    assert c['source_pin_loads']['FF']['parent_BUF_A_pin_fF']==pytest.approx(.581966)
    assert c['source_pin_loads']['FF']['upstream_available_budget_fF'] is None
    assert c['SETN_TIEHI_cells']==1483

def test_no_missing_cost_zero_or_build(model):
    t=model['timing'];assert t['scalar_tree_NAND_levels']==20
    assert not t['one_edge_scalar_read_admitted']
    for k in ['added_read_edges','root_delivery_added_edges','VM_bridge_visible_latency_edges','actual_wholeprogram_deadline']:assert t[k] is None
    assert not model['physical_build_admitted'] and model['new_jobs']==[]
    assert model['timeout1024_FAIL_preserved'] and not model['timeout4096_selected']

def test_negative_collision(monkeypatch):
    d,r=M.inputs();d['services.json'].append(dict(name='new_reserved_service',bbox_DBU=[10974000,15560000,11300000,16000000]))
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='intersects'):M.build()

def test_negative_wrong_capture(monkeypatch):
    d,r=M.inputs();d['capture.json']['control_bits']['total']=1468
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='successor'):M.build()

def test_negative_omitted_field(monkeypatch):
    d,r=M.inputs();d['field.json'].pop()
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='inventory'):M.build()

def test_negative_direction_transfer(monkeypatch):
    d,r=M.inputs();d['tech.lef']=d['tech.lef'].replace('DIRECTION HORIZONTAL','DIRECTION VERTICAL')
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='directional'):M.build()

def test_literal_raw_PG_and_MX_select_phase(model):
    assert model['local_raw_M1_rail_polarity_proved']
    assert not model['parent_PG_and_via_connection_qualified']
    for p,s in zip(model['raw_M1_PG_overlay'],model['per_shard_raw_slots']):
        assert p['rail_count']==2*s['seats']
        assert p['record_bit_pitch_DBU']==2214
        assert p['word_select_INV_orientation']=='MX'
        assert p['last_VDD_rail_top_DBU']<s['bbox_DBU'][3]
        assert p['M2_upfeed_via_pitch_and_full_OBS_access'] is None

def test_negative_wrong_PG_phase(monkeypatch):
    d,r=M.inputs();m='INVx1_ASAP7_75t_R'
    d['cell_LEF.json'][m]=d['cell_LEF.json'][m].replace('0.261','0.250')
    monkeypatch.setattr(M,'inputs',lambda:(d,r))
    with pytest.raises(ValueError,match='rail phase'):M.build()
