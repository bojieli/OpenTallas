import sys
import shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_selected_parent_caller as C

def test_exact_inverse_and_child_source_match():
    m,_=C.build()
    assert m['exact_source_gate']['parameter_only_inverse']
    assert m['exact_source_gate']['originals_byteidentical']
    assert m['exact_source_gate']['pair_and_element_match_measured_source']
    assert not m['exact_source_gate']['elaborated']

def test_all_compiled_site_bindings_not_active_only():
    m,s=C.build()
    assert len(s)==4096
    assert len({x['global_site'] for x in s})==4096
    assert sum(x['BF16'] for x in s)==724
    assert all(x['selected_element_parameters']==dict(FIX_SECOND_ROW_INDEX=1,WAKE_REG=1,GRADUAL_RNE=1) for x in s)
    assert m['source_configuration']['physical_weight_macros']==16384

def test_defaults_and_historical_field_are_not_selected():
    m,_=C.build()
    assert set(m['source_configuration']['default_flags'].values())=={0}
    assert m['source_configuration']['RT_CUT_host_must_select_same_three_template_values']
    assert not m['physical_admission']
    assert m['cost']['additional_cycles_vs_measured_selected_elements']==0
    assert m['cost']['additional_cells_vs_measured_selected_elements']==0

def test_source_manifest_is_replacement_not_duplicate_definition():
    m,_=C.build()
    assert len(m['source_overrides'])==4
    assert len({x['original'] for x in m['source_overrides']})==4
    assert all(x['selected']!=x['original'] for x in m['source_overrides'])

def test_positive_clock_wire_slew_construction():
    m,_=C.build();p=m['finite_parent_construction'];c=p['clock']
    assert 64<c['maximum_segment_um']<65
    assert c['SS_cell_plus_2p2_wire_slew_ps']<320
    assert c['SS_cell_plus_2p2_wire_slew_ps']>c['SS_cell_slew_upper_ps']
    assert c['root_and_eight_ICG_profiles']['q']['BUF_total']==901
    assert c['root_and_eight_ICG_profiles']['bfcolumn']['BUF_total']==2724
    assert c['root_and_eight_ICG_profiles']['q']['compute_anchor_grid']==[8,5]
    assert c['root_and_eight_ICG_profiles']['bfcolumn']['compute_anchor_grid']==[23,5]
    assert not c['STA_wire_admission']

def test_shared_global_fanout_is_not_three_local_buffers():
    m,_=C.build();c=m['finite_parent_construction']['shared_broadcast']
    assert c['unreplicated_GO_setup_upper_ps']>c['period_ps']
    assert c['source_endpoint_group_count']==3
    assert c['source_endpoint_group_sizes']==[683,683,682]
    assert c['selected_GO_setup_upper_ps']<c['period_ps']
    assert c['added_BST_register_bits_per_shard']==3264
    assert c['added_source_edges']==0
    assert c['replication_after_same_previous_BST_edge_must_be_proven']
    assert c['actual_shared_tree_BUFFER_cells_per_shard']==3726496
    assert not c['implementation_admitted']

def test_actual_CFG_big_leaf_requires_explicit_driver():
    p=C.build()[0]['finite_parent_construction']
    assert p['local_CFG_requires_BUF8']==[dict(case='bfcolumn',port='cfg_a',index=0,actual_pin_fF=11.549872)]

def test_no_historical_source_timing_or_cell_credit():
    m,_=C.build()
    assert not m['finite_parent_construction']['full_context_PR_admitted']
    assert not m['physical_admission']
    assert m['cost']['changed_from_historical_default0_cannot_inherit_historical_area_or_timing']

def test_wrong_optin_default_fails_source_gate(tmp_path,monkeypatch):
    paths=['rtl/v41die/ot_v41_field_w17w10.sv','rtl/v41die/ot_v41_fieldtop_w17w10.sv','rtl/v41die/ot_v41_field_w17w10_rne_wake_prepare.sv','rtl/v41die/ot_v41_fieldtop_w17w10_rne_wake_prepare.sv']
    for n in paths:
        p=tmp_path/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(C.ROOT/n,p)
    p=tmp_path/paths[2];p.write_text(p.read_text().replace('WAKE_REG = 0','WAKE_REG = 1'))
    monkeypatch.setattr(C,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='exact parameter-only'):C.build()

def test_lower_cost_pin_mutant_fails_before_pricing(tmp_path,monkeypatch):
    d=tmp_path/'inputs';d.mkdir()
    for n in ['physical_input_hashes.json','clock_pin_profiles.json','actual_boundary_pin_summary.json','GO_gate_cell.json','source_simple_ss.lib.gz']:
        shutil.copyfile(C.BASE/'inputs'/n,d/n)
    p=d/'actual_boundary_pin_summary.json';p.write_bytes(p.read_bytes()+b' ')
    monkeypatch.setattr(C,'BASE',tmp_path)
    with pytest.raises(ValueError,match='physical input changed'):C.finite_parent()

def test_enable_WAKE_and_selector_costs_have_disjoint_ownership():
    j=C.build()[0]['whole_reticle_join'];a={x['id']:x['mm2'] for x in j['additions']}
    assert j['no_double_count']['WAKE8_once']
    assert all(x['added_enable_FF_per_element']==8 and not x['existing_WAKE_recharged'] for x in j['enable'])
    assert a['enable_source_repair']==pytest.approx(2048*39.59928/1e6)
    assert a['selector_source_correct_station']==pytest.approx(.59560842564)
    assert all(x['D_FF_hold_screen_margins_ps'][0]>0 for x in j['enable'])
    assert not j['build_admitted'] and not j['actual_packing_PASS']

def test_existing_bottom_strip_not_second_growth_credit_or_debit():
    j=C.build()[0]['whole_reticle_join']
    assert j['q_selected_outline_um']==[510.84,151.20]
    assert j['q_existing_bottom_strip_um']==[144.72,151.20]
    assert 'q_bottom_PG_outline_extension' not in {x['id'] for x in j['additions']}
    assert j['q_second_extension_counterfactual_mm2']>5
    assert j['screen_mm2']==pytest.approx(j['baseline_station_free_mm2']+sum(x['mm2'] for x in j['additions']))

def test_source_correct_226_cycle_station_and_six_position_scope():
    j=C.build()[0]['whole_reticle_join'];l=j['latency']
    assert l['selector_station_cycles_per_call']==226
    assert l['nine_station_cycles']==2034
    assert l['nine_combined_cycles']==3312
    assert l['conditional_six_verify_positions_ns']==16560
    assert not l['whole_token_no_loss_proven']
    assert j['slew_diagnosis']['cause_resolved']
    assert not j['slew_diagnosis']['actual_repaired_SSFF']

def test_owner_record_mutation_cannot_buy_fit(tmp_path,monkeypatch):
    shutil.copytree(C.BASE/'inputs',tmp_path/'inputs')
    p=tmp_path/'inputs/selector_authoritative.json';p.write_bytes(p.read_bytes()+b' ')
    monkeypatch.setattr(C,'BASE',tmp_path)
    with pytest.raises(ValueError,match='owner input changed'):C.whole_join({})

def test_negative_enable_history_not_erased_by_conditional_repair():
    j=C.build()[0]['whole_reticle_join'];h=j['historical_6ed_enable']
    assert h['core_um2_per_element']==pytest.approx(39.13272)
    assert all(x<0 for x in h['D_FF_hold_screen_margins_ps'])
    assert h['new_repair_delta_core_mm2_per_shard']==pytest.approx(.00095551488)
    assert all(v>0 for x in j['enable'] for v in x['D_FF_hold_screen_margins_ps'])
    assert not j['build_admitted']
