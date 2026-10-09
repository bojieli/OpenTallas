#!/usr/bin/env python3
"""Before-build sizing of actual CP32 to native PC12/count13 launch binding."""
import json

def model():
    seats=6
    protected_bits=(seats+4)*72
    return dict(schema='opentallas.qwen.native_launch.v1',adopted=False,
        models=['Qwen3-8B HBM'],replicas=1,MACs_per_cycle=0,
        storage=dict(mapping_entries=seats,mapping_payload_bits=58,
            mapping_fields='valid1,CP_PC32,ROM_PC12,ROM_count13',
            protected_bits=protected_bits,mutable_SECDED=True,ROM_ECC=False),
        ports=dict(mapping_bytes_per_cycle=8,CP_request_bits=74+32+3+2,
            native_launch_bits=74+12+13+20+3+2,completion_owner_bits=74),
        boundaries=dict(CP_to_SU_bits_per_cycle=111,SU_launch_bits_per_cycle=124,
            routing_tracks=235,channel_width_um=36,track_pitch_um=.072,
            channel_capacity_tracks=350),
        replica_cost=dict(comparators=seats,comparator_width=32,mux_inputs=seats,
            fanout='six protected decoded table entries; one registered launch'),
        area=dict(FF_floor_um2=protected_bits*.2916,slot_um=[160,160],
            standardcell_budget_um2=160*160*.55,
            comparator_and_ECC_area='must measure in synthesis before adoption'),
        latency=dict(lookup_register_cycles=1,launch_handshake='actual dispatcher ready',
            token_contribution='one lookup cycle per SU invocation plus actual launch/completion waits',
            launch_clock_GHz=.9,lookup_ns=1/.9),
        contract=dict(CP_PC_not_ROM_PC=True,map_install='explicit checked mapping; no invented CP entry addresses',
            full_owner='{position20,token18,generation4,job32}',
            VM_ready='actual exclusive operand visibility receipt with equal full owner',
            p4='disabled pending actual per-query producer and consumer lease binding',
            completion='only matching actual dispatcher finished retires CP request',
            quarantine='UE, duplicate map, bad bounds, foreign completion or warm abort'),
        gates=['actual positive and negative control RTL gate','SS/FF and context route before adoption'])

if __name__=='__main__':print(json.dumps(model(),indent=2))
