#!/usr/bin/env python3
"""Pre-build real native SRAM quarter bridge control catalogue."""
import json

def model(banks=2,qid=0):
 if not 1<=banks<=12 or qid not in range(4):raise ValueError('host descriptor supported capacity exceeded')
 return {'banks':banks,'native_macro':'ot_sram_1r1w_64x512_m1_r2c2','catalogue_words':64*banks,
  'operations_per_word':10,'operation_bits':49,'active_operation_bits':49 if qid==0 else 30,
  'zero_reserved_word_bits':22,'q2_zero_reserved_bits_per_operation':19,
  'capacity_control_cycles':640*banks,'current_relay1_calendar_cycles':1093,'final_profile_fit_claim':False,
  'host_target':56+qid,'host_frame_bits':256,'host_frames_per_word':2,
  'host_address':'linear catalogue word*2+half','host_next_word_minimum_gap_edges':2,
  'descriptor':'base control-cycle index aligned10, exclusive limit<=capacity, loops1 only',
  'descriptor_validation_cycles':64*banks,'host_descriptor_launch_gap_edges':64*banks+2,
  'native_macro_read_bytes_per_cycle':64,'native_read_request_spacing_edges':10,
  'average_catalogue_bytes_per_control_cycle':6.4,'active_control_bytes_per_cycle':49/8,
  'raw_host_launch_to_first_control_output_edges':5,'raw_host_launch_to_first_bridge_capture_edges':6,
  'prefetch':'issue next word atoperation4; native read+leafQ+controlcapture completes atoperation7; switchafter9',
  'clock_roots':{'controller':1,'native_memory_leaves':banks},'controller_register_upper_bound':4000+64*banks,
  'memory_leaf_registered_output_bits_each':512,'physical_output_control_bits':49,
  'routing':'local49b control registered face; one physical issuer perquarter; no route/slot claim',
  'replicas_per_die':4,'replicas_for96rank_graph':384,'catalogue_macros_for96rank_graph':384*banks,
  'macs_per_cycle':0,'elastic_queue':0,'runtime_ready_credit':False,
  'area':'native macro abstracts plus controller FF/mux area, not mapped yet',
  'qualification':'component candidate, productionFEC/relaycalendar/actualnetwork integration not yet proven'}
if __name__=='__main__':print(json.dumps({'q3':model(),'q2':model(qid=1),'scaled4banks':model(4)},indent=2))
