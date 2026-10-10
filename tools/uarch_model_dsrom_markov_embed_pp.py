#!/usr/bin/env python3
"""Modeled two-edge released lookup successor; default off, no closure credit."""
import json
from uarch_model_dsrom_markov_embed import model as prior

def model():
 m=prior();m.update(schema='opentallas.md6.embed-pp.v1',scope='real two-edge pair read/capture plus full-shape lookup; not full-head physical qualification',enabled_default=False,ROM_ECC=False)
 m['macro'].update(capture_edges_after_read=2,pairs=253,count=506,mapping='bank=globalword//8192; macro=2*bank+globalword%2; addr=(globalword%8192)//2',same_macro_read_interval_cycles=2,interval_guard='consecutive same-parity read rejected before macro enable; sticky fault suppresses response')
 m['latency'].update(pipeline_valid_stages=6,first_beat_cycles=8,last_beat_cycles=23,ns_last=23/1.2,added_cycles=1,macro_and_capture_cycles=3,max_reserved=8,queue_depth=8)
 m['hierarchy'].update(bank_selector_FF_added=253,pipeline_metadata_FF_added=13,pair_interval_guard_FF_added=759,bank_capture='unconditional payload capture, qualified consumption; removes globalvalid to64768 capture enable muxes')
 m['boundary_bits_per_cycle'].update(per_pair_macro_q_inputs=512,per_pair_capture_output=256)
 m['routing'].update(per_pair_data_tracks=768,local_pair_corridor_um=40,M2_M3_pitch_um=.036,tracks_per_layer_raw=1111,at70pct_tracks_per_layer=777,local_pair_fit='768tracks against777per-layer analytical capacity; macro pinaccess and PG/routed fit pending')
 m['area'].update(hardened_pair_slot_um=[300,200],hardened_pair_macro_um2=15762.7,hardened_pair_capture_payload_FF=256,hardened_pair_control_FF=8,
  replicated_pair_slots_mm2=253*300*200/1e6,replicated_pair_slot_count=253,
  full_lookup_slot_fit=False,slot_fit=False,
  slot_scope='15.18mm2 is pair slots alone; registered bank selection, group corridors and embedding broadcast require additional placement. Legacy macro-only60pct area is not a full lookup floorplan.')
 m['timing']=dict(SS_clkq_ps=744,clock_ps=833.333,setup_uncertainty_ps=60,hold_uncertainty_ps=25,capture_FF_setup_budget_ps=25,pre_mux_two_edge_margin_ps=2*833.333-744-60-25,minimum_required_margin_ps=15,SS_FF_qualified=False)
 m['energy']='Unconditional capture invalid-payload switching unmeasured; no energy credit'
 m['composed_head_latency']=dict(prior_actual_bundle_query_to_done_cycles=8620,PP_expected_query_to_done_cycles=8621,PP_actual_pending=True,A_input_transport_cycles_included=4)
 return m
if __name__=='__main__':print(json.dumps(model(),indent=2))
