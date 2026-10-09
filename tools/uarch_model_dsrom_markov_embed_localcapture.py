#!/usr/bin/env python3
"""Z7 model before RTL: direct macro capture, mux after capture, same valid cycle."""
import json
from uarch_model_dsrom_markov_embed_pp import model as previous

def model():
 m=previous()
 m.update(schema='opentallas.md6.embed-localcapture.v1',enabled_default=False,
  scope='proposed electrical successor; no new route or closure claim')
 m['macro'].update(capture_edges_after_read=2,local_capture_payload_FF_per_pair=512,
  direct_pin_to_capture=True,pre_capture_combinational_cells=0)
 m['latency'].update(added_cycles_vs_PP=0,pipeline_valid_stages=6,
  phase='both macro payloads continuously captured; third phase FF selects after capture; valid unchanged. Early unqualified capture of inactive macro is never consumed.')
 m['hierarchy'].update(pair_capture_payload_FF_added=256,pair_phase_FF_added=1,
  full_lookup_capture_payload_FF_added=253*256,full_lookup_phase_FF_added=253,
  per_pair_payload_mux_after_capture_bits=256,
  phase_fanout=256,registered_group_consumes_post_capture_mux=True,
  full_head_broadcast_fanout=340,full_head_broadcast_timing_qualified=False)
 m['ports'].update(macro_bytes_per_read=32,active_macro_reads_per_cycle=1,
  macro_capture_bytes_per_cycle=64,pair_output_bytes_per_cycle=32,
  request_bits=17,response_token_bits=17,fault_token_bits=17)
 m['boundary_bits_per_cycle'].update(macro_to_local_capture=512,
  per_capture_bank_to_post_mux=256,post_mux_to_registered_group=256,
  request=17,response=256+17+4+1)
 m['hierarchy'].update(controller_transaction_identity_FF_removed=32,
  controller_fault_identity_FF_reduced=15,
  controller_identity='existing17bit token index only; no transaction/lease/auth/epoch identity',
  response_FIFO_stored_bits=8*(256+4))
 m['routing'].update(local_capture_distance_target_um=20,
  per_bank_corridor_um=28,per_bank_payload_tracks=256,
  per_layer_tracks_at55pct=28/.036*.55,
  CTS_leaf_fanout_limit=16,CTS_proposed_cluster_size=12,
  capture_placement='permacro130FFleft+126FFright actualqfaces; fourcolumns perface on actualsite/rowgrid; no pre-capture mux/buffer logic',
  per_macro_left_payload_pins=130,per_macro_right_payload_pins=126,
  left_payload_tracks=130,right_payload_tracks=126,
  measured_macro_gap_um=8.37,hard_macro_gap_placement_blockage_required=True,
  actual_mapped_capture_master_um=[1.08,.27],
  previous_all_left_anchor_plan_qualified=False,
  fit='analytical only; macro pin coordinates, PG access, fplint and TC electrical checks gate measured fit')
 std_budget=1000
 slot_w,slot_h=190,155
 m['area'].update(hardened_pair_slot_um=[slot_w,slot_h],
  hardened_pair_capture_payload_FF=512,hardened_pair_control_FF_conservative=9,
  standard_cell_budget_um2=std_budget,hold_allowance_in_std_budget_um2=250,
  macro_um=[125.28,62.91],macro_count_per_pair=2,
  proposed_macro_origins_um=[[16,10],[16,82.91]],
  macro_origins_joint_site_and_pin_grid_snap_required=True,
  macro_geometry_fit_pending=True,local_capture_left_strip_um=12,
  macro_q_pin_face='actual mapped M4 faces:130left+126right payload pins permacro; q0 starts y2.112 with .096um pitch',
  local_capture_and_channel_width_um=54.72,
  proposed_total_usage_fraction=(15762.7+std_budget)/(slot_w*slot_h),
  replicated_proposed_pair_slots_mm2=253*slot_w*slot_h/1e6,
  replicated_pair_slots_mm2=253*slot_w*slot_h/1e6,
  previous_actual_replicated_pair_slots_mm2=15.18,
  previous_actual_pair_slot_um=[300,200],
  previous_actual_standard_cell_um2=440.331,
  new_actual_slot_pending=True,full_lookup_slot_fit=False,slot_fit=False,
  slot_scope='new190x155 proposal prices macros+std/hold budget; bank-group selection and340-cache broadcast require extra capacity. No actual smaller slot claimed before Claude intake measurement.')
 m['timing'].update(SS_FF_qualified=False,OptionB_TT_FF_DRC_qualified=False,
  original_actual_TT_setup_ps=249.78,original_actual_FF_hold_ps=30.32,
  original_actual_SS_sensitivity_ps=130.42,original_TC_electrical_qualified=False)
 m['composed_head_latency'].update(localcapture_added_cycles=0,
  current_actual_PP_bundle_pending=True)
 m['identity']='pair contains no request transaction identity or lease/auth/epoch guards'
 return m

if __name__=='__main__':print(json.dumps(model(),indent=2))
