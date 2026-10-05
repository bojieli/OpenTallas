import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_MTP_selected_parent_containment as M

def test_refusal_is_not_architectural_impossibility_or_fit():
 m=M.generate()
 assert m['outcome']=='REFUSE_CURRENT_COMPOSED_CONTAINMENT'
 assert not m['architectural_impossibility'] and not m['admission']['physical_G0']
 assert not m['admission']['slot_reserved'] and not m['admission']['engine_RTL_GO']

def test_source_one_core_not_implicit_PAR2_fleet():
 m=M.generate();assert m['source_cores_per_wrapper']==1
 assert m['fleet_replica_count'] is None and m['selected_actual_stage_rank_shard_core_home'] is None
 assert m['no_N_TP_or_PAR2_implicit_core_multiplier']

def test_scalar_delta_cannot_be_hidden_in_leaf_rectangle():
 m=M.generate();s=m['separate_scalar_width'];a=m['accounting']
 assert s['added_FF']==7690 and s['gross50pct_mm2']==.03135116988 and not s['included_in_leaf_slot']
 assert a['leaf_rectangle_plus_scalar_reservation_mm2']==pytest.approx(.05588876988)
 assert a['scalar_exceeds_entire_leaf_rectangle_mm2']>0
 assert a['combined_min_area_height_at128um']>436
 assert a['old_containment_credit']==0 and a['extra_charge_for_existing578_buffers']==0

def test_eight_reset_sinks_rejected_before_wire_not_library_limit():
 r=M.generate()['reset_branch_refusal']
 assert r['old_eight_pin_load_fF']==pytest.approx(6.423272)
 assert r['old_eight_pin_excess_before_wire_fF']==pytest.approx(.663272)
 assert r['largest_pin_only_positive_wire_fanout']==7
 assert r['minimum_count_levels']==[288,36,5,1] and r['additional_BUF_lower_bound']==41
 assert r['pin_only_repaired_wire_budget_fF']>0 and not r['actual_branch_sites_and_samecount_routes_selected']
 assert r['spare_after_minimum_gross_repair_um2_not_track_credit']==pytest.approx(.27648)

@pytest.mark.parametrize('index,bits,width',[(0,636,30.528),(1,52,2.496),(2,52,2.496)])
def test_source_directional_cuts_kept_separate(index,bits,width):
 c=M.generate()['channel_union'];cut=c['separate_cuts'][index]
 assert cut['signals']==bits and cut['M4_wire_pitch_floor_um']==pytest.approx(width)
 assert c['actual_available_tracks'] is None and c['free_track_credit']==0
 assert c['M4_direction']=='HORIZONTAL' and c['shared_cut_if_explicitly_routed_signals']==740

def test_clock_load_union_keeps_scalar_baseline_bridge_separate():
 c=M.generate()['clock_reset_load_union']
 assert c['leaf_protected_FF']==2016 and c['scalar_added_FF']==7690
 assert c['leaf_plus_scalar_CLK_FF_fF']==pytest.approx(5028.611332)
 assert c['bridge2936_FF_separate_not_in2016_or7690']==2936
 assert c['existing_K512_baseline_retained'] and c['578_local_CLK_RESET_buffers_already_charged']==578
 assert c['parent_serial_clock_ingress_and_reset_release_routes'] is None

def test_known_parent_envelope_not_cell_containment():
 s=M.generate()['selected_parent_regions']
 assert s['serial_service_envelope']['name']=='HUB_SU_VECTOR'
 assert s['prospective_field_reader_home_not_intaken_or_containment_credit']==[10974906,14894010,13300794,15995610]
 assert s['rectangle_only_not_placed_fit']

def test_no_MTP_rate_or_zero_edge_repair_claim():
 m=M.generate();assert m['latency']['full_single_user_MTP_delta'] is None
 assert m['latency']['added_min_ns']==pytest.approx(2/.9)
 assert not m['separate_scalar_width']['measured_zero_added_edges']

def test_count_lower_bound_no_free_spare_for_route():
 m=M.generate();assert m['requested_leaf_slot']['spare_is_not_available_tracks']
 assert m['reset_branch_refusal']['additional50pct_mm2_lower_bound']>0
 assert m['admission']['new_jobs']==0 and not m['admission']['global_live_solver_changed']
