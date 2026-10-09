#!/usr/bin/env python3
"""Pre-RTL sizing for Qwen p4 finite-window mask and native SU dispatcher.
All physical figures are proposal estimates; no clock or rate credit.
"""
import json
import math


def model():
    banks, depth, native = 4, 4096, 690
    metadata = 42
    rom_bits = depth * (banks*native+metadata)
    rom_macros = banks*math.ceil(native/274)+math.ceil(metadata/274)
    dff_um2=.2916
    mask_ff=6*72
    command_bits=banks*(native+73+12+2+1)
    return dict(schema='opentallas.qwen_r25_su_dispatch_model.v1',default_off=True,
        models=['Qwen3-8B HBM'],replicas_per_die=1,quarters=4,
        production_owner_bits=74,legacy_owner_bits=73,
        owner74_fields="position[73:54],token[53:36],generation[35:32],job[31:0]",
        owner74_added_protected_seats=0,
        mathematical_shape=dict(query_positions=[8191,8192,8193,8194],
            valid_lengths=[8192,8193,8194,8195],kv_capacity_rows=8224,rows_per_group=32),
        mask=dict(MACs_per_cycle=0,comparisons_per_cycle=128,compute_intensity=0,
            memory_bytes_per_cycle=0,input_bits_per_cycle=179,output_bits_per_cycle=308,
            ff=mask_ff,ff_area_um2=mask_ff*dff_um2,comparator_bits=128*21,
            estimated_total_area_um2=10000,proposed_slot_um=[200,200],
            fit_at_55pct_utilization=10000<=200*200*.55,
            routing_tracks_needed=487,routing_tracks_capacity=math.floor(.7*(200/.048+200/.064)),
            replica_mux_demux='four query comparison trees; registered output; output fanout one per consumer',
            max_control_fanout=32,added_latency_cycles=1,
            standalone_timing_harness_added_cycles=2,
            pipeline_successor=dict(extra_cycles=1,extra_FF=16*13+4*72,
                transient_mask_protection="16 independent SECDED8 bytes",
                total_FF=mask_ff+16*13+4*72,estimated_area_um2=13000,
                proposed_slot_um=[200,200],token_latency_credit=0,
                context_code_copy_successor=dict(opt_in_default=False,
                    extra_cycles=0,extra_FF=0,extra_boundary_bits=0,
                    context_transfers_per_frame=4,
                    removed_logic="unchanged SECDED64 context decode then encode on transfer; occupancy clear uses linear codeword XOR",
                    fault_policy="all source and destination SECDED decoders still fence UE; CE remains correctable until overwritten",
                    physical_basis="legacy73 pipeline TT critical pctx[1][14] to seat[3][71], WNS -0.211558ns",
                    numerical_or_rate_credit=0)),
            period_ps=1000/1.2),
        dispatcher=dict(MACs_per_cycle=0,compute_intensity=0,rom_bits=rom_bits,
            memory_ports=dict(program_ROM_bytes_per_fetch=(banks*native+metadata)/8),
            rom_4096x274_macros=rom_macros,rom_macro_area_um2=rom_macros*125.712*119.340,
            boundary_bits_per_cycle=dict(commands=command_bits,completions=banks*(73+12+2+2)),
            routing_tracks_needed=command_bits+banks*(73+12+2+2),
            routing_tracks_capacity=math.floor(.7*(600/.048+600/.064)),
            proposed_slot_um=[600,900],placement_utilization=.55,
            estimated_FF=banks*11*72+3*72,
            protected_command_seats=banks*11,protected_state_seats=3,
            immutable_ROM_provider_external=True,
            physical_candidate_ROM_area_included=False,
            replica_mux_demux='four independent ROM banks; one registered command per quarter; barrier joins four checked completions',
            max_replica_control_fanout=4,dispatch_serial_cycles_per_op=4,
            production_query_release_barrier=True,
            release_minimum_extra_cycles_per_query=1,
            release_wait="actual downstream buffer capture/visibility; no guessed overlap",
            serial_clock_GHz=.9,physical_qualification=False),
        schedule=dict(queries=4,sequential_query_replays=4,
            score_rows_per_head=8224,heads_per_query=8,
            per_query_three_array_vm_words=3*8*8224,vm_capacity_words=262144,
            remaining_vm_words=262144-3*8*8224,
            replay_score_bytes_per_layer=4*8*8224*4,
            replay_lower_bound_us_at_3p8TBs=(4*8*8224*4)/3.8e6,
            latency_composition='four exact per-query SU programs plus four score replays; each opcode pays four dispatch serial cycles; quarter arithmetic and VM transport measured separately',
            cycles_measured=False,
            minimum_quarter_service_vehicle=dict(N=256,M=64,
                persistent_VM_words=262144,persistent_VM_bytes=1048576,
                immutable_zero_VM_word=262143,request_bits=337,response_bits=273,
                outstanding_requests=1,read_visibility_after_every_write=True,
                exact_native_arithmetic=True,DPI=False,
                compile_admission_GiB=128,workers=8,
                reservation_basis="actual full N256 quarter frontend89.9GiB rising at10m26s on EPYC3 plus backend workers8; prior analogous54.2GB superseded",
                virtual_edge_cost="measure actual wrapper counters; every native edge waits read and write scans and visibility replies")),
        protection=dict(ROM_ECC=False,mutable_control='SECDED64 command/owner/state seats; checked launch and completion identity; configuration validity and bounds checked',
            ROM_reads_assumed_fault_free=True),
        physical_closed=False,adopted=False,token_rate_credit=0)

if __name__=='__main__':
    print(json.dumps(model(),indent=2))
