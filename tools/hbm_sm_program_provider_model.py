#!/usr/bin/env python3
"""Model BEFORE building the native word/shared-service binding."""
import json

def model():
    return dict(status='prebuild_candidate',native_record_bits=320,words_per_record=10,
        MACs_per_cycle=0,replicas=32,finite_outstanding=1,cache=False,
        storage=dict(word_address=32,physical_sector_address=37,issuer_tag=16,result_word=32,
                     payload_parity=1,onehot_state=4,sticky_fault=1),
        adapter_flop_bits=123,existing_join_flop_bits=677,total_client_flop_bits=800,
        existing_join_storage=dict(state=2,sticky=1,write=1,rank=7,identity=192,reverse_owned=465,credit_lock_and_select=8,formatter_fault=1),
        flop_area_lower_bound_um2=800*.2916,slot_lower_bound_um2_at_55pct=800*.2916/.55,
        service_read_bytes_per_word=32,native_bytes_per_word=4,service_read_bytes_per_record=320,
        request_boundary_bits=1+1+37+16,response_boundary_bits=1+1+1+16+256,
        native_request_bits=34,native_response_bits=67,
        latency='one input capture + shared request wait + owned response wait + one output capture; subsequent service request also waits existing reverse-credit/grant completion',
        minimum_unstalled_adapter_edges_per_word=4,
        protection='stored address, physical address, tag and output data parity; illegal/zero/multihot FSM fail closed; existing join identity validation; mapped independence and join mutable protection remain qualification obligations',
        source_addressing='actual installed region: physical_base37 + (word_addr32 - virtual_base32); sector aligned region, exclusive virtual limit33',
        allocation='explicit issuer-provided unique owner identity and tag; no invented client/producer/transport/IRS ownership',
        existing_service='ot_hbm_loader_service_join shares existing four-stack provider; no added memory controller',
        slot_fit=None,tracks_capacity=None,physical_admitted=False,
        unresolved=['installed native program region and real issuer ownership binding','existing shared join mutable-state physical protection','SS/FF and registered floorplan route','system model composition'])
if __name__=='__main__': print(json.dumps(model(),indent=2))
