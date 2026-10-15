#!/usr/bin/env python3
"""Pre-build compiler-mode VM/INDEX ingress station for four native flits."""
import json

def model():
 return {'input_ports':{'VM':4*545,'INDEX':4*545},'output_bits':4*545,
 'registers':{'input_payload':2*4*545,'input_valid':8,'mode':1,'expected_valid':4,'output_payload':4*545,'output_valid':4,'sticky_fault':1},
 'register_bits':6558,'clock_roots':1,'mux':'four explicit2way545-bit muxes before output FFs; no runtime arbitration',
 'latency':'input sampledC ->registered outputafterC+1; downstream qslots samplesC+2',
 'added_qslots_capture_edges':2,'new_IDX_emit_to_TKM_sample_edges':7,
 'mode_word_lead':'mode/expected bitmap sampled with input atC; output selects captured mode atC+1',
 'bandwidth':'four native545bit flits per edge if static reservations permit; IDX requiredII8',
 'conflicts':'any valid on inactive typed port or selected actual bitmap !=compiler expected bitmap faults; no reschedule',
 'pins':{'input_bits':4375,'output_bits':2185},'area':'unmeasured; no physicalslotqualification'}
if __name__=='__main__':print(json.dumps(model(),indent=2))
