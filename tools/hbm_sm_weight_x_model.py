#!/usr/bin/env python3
"""Prebuild native installed-sector weight/X consumers."""
import json
def model():
 return dict(status='prebuild_candidate',replicas=32,MACs_per_cycle=0,
 weight=dict(installed_stride_bytes=160,sectors_per_line=5,wire_bits=1088,padding_zero_bits=192,request_bits=42,
             reqcr_ready_latency_edges=2,permission_slots=1,policy='one ready pulse reserves the only request slot; wait2 edges; no further grant until response consumed',
             assembler_flops=37+16+4+1280+1+4+1,request_wrapper_flops=32+10+1+5+1,service_read_bytes=160),
 x=dict(fragment_bits=25216,installed_stride_bytes=3328,groups=13,sectors_per_group=8,sectors_per_fragment=104,last_group_active_bits=640,
        assembler_flops=37+16+4+2048+1+4+1,context_flops=79+1+3+1,wire_bits=2048),
 shared_service_client_flops_each=677,shared_service='existing loader_service_join owned returns/reverse credits/grants; explicit real issuer; no added controller',
 latency='weight: permission2 + wrapper capture1 +5 serial sector request/response/grant roundtrips +output1; X:8 serial sector roundtrips/group,13 groups/fragment; consumer stalls add',
 protection='stored payload parity, onehot state invalidity, bounds, exact returned tags, zero installation padding; join state and mapped protection need qualification',
 slot_fit=None,tracks_capacity=None,physical_admitted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
