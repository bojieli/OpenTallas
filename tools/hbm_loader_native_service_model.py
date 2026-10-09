#!/usr/bin/env python3
"""Finite endpoint sizing before RTL. No routing or production admission credit."""
import json

def model():
    return dict(scope='native loader sector endpoint; explicit external address translation and real service completion required',
      parameters=dict(default_enable=0,native_address_bits=32,native_address_parameter_min=32,sector_bits=30,pc_bits=5,tag_bits=16,data_bits=256,stack_instances=4),
      request_bits=291,response_bits=1+5+16+4+256,
      state_bits=3,saved_request_bits=1+5+30+16+256,saved_reply_bits=256,
      flops_per_stack=3+1+5+30+16+256+256+1,
      memory_ports=dict(native=1,service=1),outstanding_per_stack=1,
      bytes_per_service_cycle=32,MACs_per_cycle=0,compute_intensity=0,
      boundaries=dict(native_request_bits=338,native_response_bits=274,service_write_request_bits=291,service_read_request_bits=51,service_response_bits=282),
      latency=dict(request_capture_cycles=1,reply_capture_cycles=1,minimum_endpoint_cycles_per_sector=3,service_cycles='measured downstream; no invented bound',token_path_added_cycles=0,token_path_condition='deployment only; runtime load conflict remains explicitly unqualified'),
      area=dict(flop_count_estimate=568,slot_fit='unqualified: service physical owner must admit'),
      routing=dict(tracks='port bits × actual routing layers and occupancy required',channel_capacity=None,qualified=False),
      mux_demux=dict(replicas=4,request_select='existing physical per-stack arbiter',response_select='single saved PC and tag; we identity'),
      invalid='misaligned/unmapped address or partial write strobe faults before acceptance; malformed/unsolicited service completion faults without loader success',
      address_mapping='external owner supplies actual byte-address→stack/PC/sector translator; endpoint never truncates native address',
      write_visibility='service response for write must originate physical k_wr_done after accepted write; request acceptance is never completion',
      production_read_lease=dict(physical_PCs=32,normal_read_beat_capacity=64,normal_write_capacity=8,read_debt_bits=7,write_debt_bits=4,native_lease_bits=2,native_address_bits=30,native_tag_bits=16,normal_request_added_cycles=0,native_request_capture_cycles=1,native_reply_capture_cycles=1,PC_write_collision="native admission waits externally proven pending WB drain plus accepted write debt0; native lease blocks normal K issue on its PC",native_response_bits=256+16+4+1,per_PC_flops=7+4+2+1+30+16+256,physical_status="requires slot placement and actual wire channel admission"),
      read_lease=dict(outstanding_per_PC=1,beat_mask_bits=16,saved_normal_tag_bits=17,native_tag_bits=16,stages=1,normal_path_added_cycles=0,normal_priority="normal valid or existing lease blocks native admission",same_PC_write_arbitration="must compose with physical WB arbiter"),
      adoption=False,physical_admitted=False)
if __name__=='__main__': print(json.dumps(model(),indent=2))
