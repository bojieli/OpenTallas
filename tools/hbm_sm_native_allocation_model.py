#!/usr/bin/env python3
"""Immutable installed-span allocation lookup, sized before RTL generation."""
import json

def model(records=256):
    if not 0<records<=256:raise ValueError('bounded native program')
    return dict(status='prebuild_candidate',records=records,MACs_per_cycle=0,
        immutable_ROM_bits=records*(32+24),ROM_ECC=False,
        mutable_response_bits=2*(1+16+32+1),fault_bits=2,
        request_bits=1+16+24,response_bits=1+16+32+1,
        peak_bytes_per_cycle=4,lookup_cycles=1,queue_depth=1,
        mux='up to256×56 immutable table; no SS/FF qualification, registered request-to-response boundary',
        comparison='two50bit response banks, valid compared always; payload only when valid; sticky dual-rail fault',
        replicas=32,flop_area_lower_bound_um2=102*.2916,
        latency='one capture edge plus consumer backpressure; response valid cleared only after consumption',
        scope='actual byte base from Program.put divided by160, integral and bounded; no dynamic allocation or hardware installation grant',
        physical_admitted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
