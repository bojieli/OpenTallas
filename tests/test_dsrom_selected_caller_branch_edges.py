import sys,json,shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_selected_caller_branch_edges as B
@pytest.fixture(scope='module')
def model():return B.build()

def test_actual_clock_reset_owners_and_source_pins(model):
 m,s=model
 for kind,c in m['branch_construction'].items():
  assert c['clock_FF_replicas']==8 and c['reset_FF_replicas']==4
  assert c['actual_source_ICG']['leaf']==0
  assert c['reset_anchor_not_GCLK']
  assert c['added_sampling_edges']==0 and not c['existing_WAKE8_recharged']
  assert len(c['nets'])==12
  assert all(n['source_net']=='leaf_clk[0]' for n in c['nets'] if n['pin']=='CLK')

def test_finite_clock_buffers_wire_domain_and_collision_gate(model):
 m,s=model;assert len(s)==120
 for kind,c in m['branch_construction'].items():
  assert c['balanced_new_branch_BUF_depth']==5
  assert c['clock_BUF']==40 and c['reset_BUF']==20
  assert all(n['maximum_segment_um']<=m['clock_contract']['wire_segment_max_um'] for n in c['nets'])
  assert c['root_driver_total_existing_plus_extra_load_unqualified']
  for a in [x for x in s if x['case']==kind]:
   assert a['body_clear_of_archived_primitives_macro_bodies_and_WAKE_ICG']
   assert not a['PG_pin_via_access_proven']
 assert m['area']['positive_additional_branch_floor_mm2']==pytest.approx(.02466422784)
 assert not m['full_context_build_admitted']

def test_actual_cfg_capture_deadline_not_clockq_transfer(model):
 c=model[0]['accepted_I66']['cfg']
 assert c['local_ports_per_shard']==2048 and c['bits_per_local_edge_per_shard']==98304
 assert c['read_edges']==[34,58] and c['capture_edges']==[35,59]
 assert c['one_edge_CLKQ_plus_mux_wire_capture_setup_ceiling_ps']==pytest.approx(748.3333333333)
 assert c['weight274_CLKQ_not_transferred_to_configuration72']
 assert c['hard_macro_two_edge_multicycle_with_II1_requires_bank_overwrite_hold_proof']
 assert c['two_edge_capture_if_needed_earliest_GO']==61
 assert c['envelope_is_not_hidden_latency_proof']

def test_actual_activation_all80_not_firstlast_only(model):
 a=model[0]['accepted_I66']['activation']
 assert len(a['actual_accepted_edges'])==80
 assert a['actual_accepted_edges'][0]==82 and a['actual_accepted_edges'][-1]==312
 assert a['paired_source_lead_edges'][0]==23
 assert a['lead_includes_existing_BST17_and_native_stalls_not_free_wire_slack']
 assert a['zero_latency_not_assumed']

def test_root_demand_and_finite_serialization_positive(model):
 r=model[0]['accepted_I66']['roots']
 assert r['peak_root_bits_per_shard']==4416 and r['writer_peak_bits_all_ports']==8064
 assert r['fullwidth_port_contract']['last_VM_visible']==420
 assert r['single_shared_port_counterfactual']['last_VM_visible']==990
 assert r['single_shared_port_counterfactual']['maximum_additional_queue_edges']==570
 assert r['single_shared_port_counterfactual']['all576_preserved']
 assert r['VM_sink_physical_home'] is None

def test_hash_mutant_cannot_remove_accepted_traffic(tmp_path,monkeypatch):
 shutil.copytree(B.BASE/'inputs',tmp_path/'inputs')
 p=tmp_path/'inputs/I66.json';p.write_bytes(p.read_bytes()+b' ')
 monkeypatch.setattr(B,'BASE',tmp_path)
 with pytest.raises(ValueError,match='input hash mismatch'):B.build()

def test_no_unpriced_buffer_site_granted():
 with pytest.raises(ValueError,match='no local buffer body site'):B.locate_buffer([100,100],[[0,0,1000,1000]],[0,0,1000,1000])

def test_macrobody_collision_has_no_same_edge_credit():
 b=B.locate_buffer([300,300],[[0,0,500,500]],[0,0,2000,2000])
 assert not B.rect_overlap(b,[0,0,500,500])

def test_same_hold_length_preferred_wire_avoids_source_PG_default_arrays(model):
 for c in model[0]['branch_construction'].values():
  h=c['required_hold_wire_geometry']
  assert h['horizontal_pattern_not_legal_under_full_source_default_array']
  assert h['source_first_horizontal_pattern_max_phase_clearance_DBU']==27
  assert h['source_default_PGvia_required_clearance_DBU']==41
  assert h['lengths_um']==[18.432,5.4]
  assert h['minimum_M5via_column_clearance_DBU']>41
  assert h['source_RC_unchanged'] and h['hold_BUF_count_unchanged']==2
  assert h['additional_cell_debit']==0
  assert not h['physical_wire_qualified']

def test_committed_tiepins_and_full_clock_reset_union_charged_once(model):
 m,_=model
 assert m['selected_enable_commit'].startswith('8d6baed75')
 assert m['area']['committed_enable8d6_revision_delta_mm2']==pytest.approx(.00095551488)
 assert m['area']['enable_revision_delta_charged_once']
 for k,c in m['branch_construction'].items():
  assert c['committed_enable_um2']==40.06584
  assert len(c['SETN1_ties'])==4
  assert c['source_PG_projection_PASS'] and c['source_PG_terminal_projection_count']==6844
  for v in c['clock_reset_full_source_union'].values():
   assert v['new_leaf0_sinks']==v['existing_leaf0_sinks']+8
   assert v['composed_leaf0_pin_cap_fF']==pytest.approx(v['existing_leaf0_pin_cap_fF']+v['extra_clock_pin_cap_fF'])
   assert v['composed_reset_pin_cap_fF']==pytest.approx(v['existing_reset_pin_cap_fF']+v['extra_reset_pin_cap_fF'])
 assert m['branch_construction']['q']['full_existing_reset_positive_BUF_levels']==[131,15,2,1]
 assert m['branch_construction']['bfcolumn']['full_existing_reset_positive_BUF_levels']==[616,69,8,1]
 assert m['area']['positive_full_existing_reset_floor_mm2']>0
 assert m['area']['original_reset_and_new_clone_nodes_not_doublecounted']

def test_literal_BST_RESET_and_source_polarity_screen_are_not_generic_floor(model):
 b=model[0]['same_BST_source_model']
 assert b['literal_RESET1_source_gate'] and b['bitwise_fourstate_induction_cases']==192
 assert b['source_BST']==17 and b['new_copies']==2 and b['additional_register_edges']==0
 assert b['source_QN_must_restore'] and b['all3264_added_bits_require_reset_not_genericHQ']
 assert b['recursive_BUF_input_domains_ps']==[160]*4
 assert b['final_GO_input_domain_ps']==160
 assert b['recursive_source_correct_GO_upper_ps']>b['period_ps']
 assert not b['recursive_LUT_RC_screen_PASS']
 assert b['total_additional_cell_floor_mm2']>0
 assert all(v['BUF_cells']>0 for v in b['replica_CLK_RESET_pin_floor'].values())
 assert b['screen_failure_not_actual_STA_or_architectural_impossibility']

def test_literal_reset_removal_cannot_claim_same_BST():
 inputs,_=B.read_inputs();inputs['delay.sv']=inputs['delay.sv'].replace("if (!rst_n) line <= {(W*D){1'b0}};",'line <= 0;')
 with pytest.raises(ValueError,match='different literal delay'):B.same_BST_model(inputs,{})
