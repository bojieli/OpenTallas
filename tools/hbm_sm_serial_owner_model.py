#!/usr/bin/env python3
"""Pre-build sizing for native serial owner; selected physical SM shape NC8."""
import json

def model(max_records=256):
    # Ten-word latch; base/current/limit address; record count/index; word index;
    # resident operand descriptor; descriptor address; output capture; state/status.
    storage = dict(record=320, program_address=32+33, record_identity=16*2,
        word_index=4, operand_resident=7+8+16+2+1, weight_base=32,
        x_capture=2048+7+7+1, counters=8+4, state_status=5+5, local_ingress_and_credit=101)
    n=sum(storage.values())
    return dict(status='prebuild_candidate',max_records=max_records,MACs_per_cycle=0,
        command_format='exact existing ten little-indexed uint32 seq.hex words; no new ISA',
        placement='SM-local control owner; incoming streams end in registered local capture',
        program_port=dict(request_bits=33,response_bits=66,payload_bytes_per_response=4,max_outstanding=1,record_bytes=40),
        allocation_port=dict(request_bits=1+16+24,response_bits=1+16+32+1,max_outstanding=1,meaning='actual selected weight-line base, not simulator line-file offset'),
        x_port=dict(fragment_bits=25216,beats_per_address=13,data_bits_per_beat=2048,last_beat_active_bits=640,
            request_bits=1+16+7+8,response_bits=1+16+7+4+2048+1,bytes_per_accepted_edge=256,queue_depth=1),
        SM_local_pins=dict(op_bits=47,x_bits=1+7+7+2048,descriptor_bits=57,return_bits=4),
        storage_lower_bound_bits=storage,total_flop_lower_bound_bits=n,flop_area_lower_bound_um2=n*.2916,
        slot_lower_bound_um2_at_55pct=n*.2916/.55,
        latency='per record 10*(request_wait + response_wait) + validate1 + allocationRTT + descriptor_wait + optional X-requestRTT + extent*13 accepted beats + capture1 + ingress/HOPS0 channel3 + real operation/arrive + actual result-publication acknowledgement; stalls measured separately',
        serialization='no next record before actual arrive and matching result publication; therefore ring WAR and dependencies cannot overlap',
        replica_count=32,fanout='one local owner per selected SM; no 32-way combinational broadcast',
        tracks_capacity=None,slot_fit=None,
        admission='not admitted; immutable pinned source/constraints and model integration required',
        unresolved=['program memory and actual DMA client allocation','weight allocator parent connection','result publication owner connection','mutable-state protection beyond bounds/identity','SS/FF and slot geometry'])
if __name__=='__main__':print(json.dumps(model(),indent=2))
