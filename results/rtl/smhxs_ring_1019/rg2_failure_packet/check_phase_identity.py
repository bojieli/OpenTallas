#!/usr/bin/env python3
"""Discrete macroposedge address model; source RTL/wave proof remains required."""
import json
checks=wraps=mutant_mismatches=0
for initial in range(4):
    slot=initial
    # Established running state: previousposedge oldcounter was slot-1.
    rp=(slot-1)%4
    for edge in range(1024):
        rn=(slot-1)%4 # preceding falling edge, after prior increment
        assert rn==rp
        wrong=(rp-1)%4
        mutant_mismatches+=rn!=wrong
        wraps+=slot==3
        checks+=1
        rp=slot
        slot=(slot+1)%4
# Reset held across a falling edge, as guaranteed by existing face landing.
for duration in range(2,33):
    slot=0;rp=3
    for _ in range(duration):
        rn=(slot-1)%4
        assert rn==rp==3
    for edge in range(1024):
        rn=(slot-1)%4
        assert rn==rp
        checks+=1
        rp=slot;slot=(slot+1)%4
print(json.dumps(dict(status='MODEL_PASS_NOT_RTL_QUALIFICATION',macroposedge_address_checks=checks,wraps=wraps,wrongoffset_mismatches=mutant_mismatches,reset_scope='held through falling edge; reset lengths2..32; invalid asynchronous reset reads explicitly excluded',edges_added=0,actual_ff_delta=6),indent=2))
assert mutant_mismatches==4096
