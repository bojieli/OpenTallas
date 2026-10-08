#!/usr/bin/env python3
"""Model before II1 refill successor; the original II3 candidate remains pinned."""
import json
from hbm_collective_cdc_model import model as base

def model():
 m=base();m.update(status='II1_REFILL_CANDIDATE_NOT_ADOPTED',normal_timing=dict(read_initiation_interval=1,empty_start_capture_plus_validate_cycles=2,gray_sync_stages=2,credit_return='readpointer only upon acceptedpop; no same-cycle creditreuse'),additional_state_bits=0,
 new_logic='Nextbinary/Gray pointer availability check and captureaddressselect; pop/refill loads nextencodedword into sameprotectedhead bank, CE/UE permissionsremain failclosed',
 service_contract='II1 only for continuously available fault-free words and readyconsumer; correction pauses and empty startup explicitlypriced',
 composed_cost='Retains2empty-startreadcycles, removes2bubbles per sustainedlaterpop versusII3. Native endpoint latency/calendars unmeasured.',
 actual_credit_producer='Separate acknowledged grant/retirement protocol stillrequired; II1 is not substitute for finiteadvertisedcredits',
 physical_risk='64:1encodedreadmux +captureaddress/path checks; actualSS/FFmapping required beforeclaimingII1clockclosure')
 return m
if __name__=='__main__':print(json.dumps(model(),indent=2))
