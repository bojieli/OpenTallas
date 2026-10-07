#!/usr/bin/env python3
"""Pre-RTL sizing of protected global-stall collective flight."""
import json

def model(w=545,depth=14,replicas=16):
 n=(w+1+63)//64
 return {'schema':1,'width':w,'depth':depth,'replicas':replicas,'payload_bits':w*depth,
  'words_per_stage':n,'repair_words_per_stage':5,'encoded_state_bits':depth*(n+5)*72,
  'fault_rail_bits':2*depth,'stored_bits_per_path':depth*((n+5)*72+2),
  'stored_bits_all_paths':replicas*depth*((n+5)*72+2),
  'input_output_bits_per_cycle':w,'input_output_bytes_per_cycle':w/8,
  'input_encoder_words':n,'internal_reencode_words':0,'internal_encoded_boundary_bits_per_cycle':n*72,'macs_per_cycle':0,
  'minimum_capture_to_retire_edges':depth,'unstalled_ii':1,
  'latency_ns_at_1p2GHz':depth/1.2,'stall_cycles':'all sink stalls and CE repair pauses add directly',
  'routing_obligations':{'global_normal_reduction_inputs':depth,'advance_load_fanout':depth*n*72,
   'sink_ready_combinational_to_source_ready':True,'output_correcting_decode_words':n},
  'area_um2':None,'routing_tracks':None,'floorplan_fit':None,
  'physical_status':'Unqualified: encoded flops, ECC, global ready fanout and SS/FF require measurement',
  'protection':'valid is encoded with data; each stage has protected repair state and dual fault rails',
  'protocol':'out_valid may be suppressed during repair; data stable under correctable output error; no transfer while any stage non-normal',
  'reset':'coordinated cold reset only; resets discard all flight, never credit-return events',
  'default_enabled':False}
if __name__=='__main__': print(json.dumps(model(),indent=2))
