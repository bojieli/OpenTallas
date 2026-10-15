"""Static native SVC probability-ingress candidate; no adoption/performance credit.

This explicit component model records the additional transport cost of carrying
actual FP32 SU results to a local SVC converter. It does not assume that this
candidate is the final preferred producer topology or that overlaps are free.
"""
from __future__ import annotations
import math


def model(rows=640, *, replicas_per_die=4, frame_rows=250):
    if type(rows) is not int or not 1 <= rows <= 640:
        raise ValueError('production natural rows must be 1..640')
    if type(frame_rows) is not int or frame_rows < 2 or frame_rows > 640 or frame_rows % 2:
        raise ValueError('intermediate frame chunks must have positive even row capacity')
    if type(replicas_per_die) is not int or replicas_per_die < 1:
        raise ValueError('actual positive slab replica count required')
    chunks = [min(frame_rows, rows-k) for k in range(0, rows, frame_rows)]
    native_words = rows + len(chunks)
    legacy_payload = math.ceil(rows/2)
    legacy_words = legacy_payload + math.ceil(legacy_payload/frame_rows)
    native_output_words = sum(math.ceil(k/2)+1 for k in chunks)
    return dict(
        status='candidate only; native full layer and physical route unqualified',
        source='rtl/dsrom_sys/s81_ph/svc/ot_s81_svc_probability_frame.sv',
        arithmetic=dict(MACs_per_cycle=0, FP32_to_BF16_RNE_lanes=16,
                        natural_rows_per_cycle=1, scalar_RNEs_per_cycle=16),
        input=dict(bits_per_cycle=515, payload_bytes_per_active_cycle=64,
                   natural_rows=rows, payload_words=rows, header_words=len(chunks),
                   total_launch_cycles=native_words),
        output=dict(bits_per_cycle=515, peak_payload_bytes_per_cycle=64,
                    normal_pair_average_payload_bytes_per_cycle=32,
                    payload_words=legacy_payload, total_words=native_output_words),
        memory_ports=dict(new_SRAM_read=0,new_SRAM_write=0,new_ROM_read=0),
        local_state=dict(architectural_pin_capture_bits=515,
                         architectural_pin_launch_bits=515,
                         static_low_half_bits=256,
                         measured_synthesized_flops=2363,
                         clock_roots=1),
        mux_cost=dict(probability_pair_2_to_1_bit_mux_upper_bound=512,
                      pass_vs_probability_2_to_1_bit_mux_upper_bound=515,
                      header_changed_bits=16, runtime_arbiters=0, credit_counters=0),
        physical=dict(replicas_per_die=replicas_per_die,
                      slot_um=[129.6,86.4], slot_area_um2=129.6*86.4,
                      per_die_reserved_area_um2=replicas_per_die*129.6*86.4,
                      measured_pre_route_std_area_um2=1291,
                      assigned_pin_pitch_um=0.096, logical_boundary_tracks=1030,
                      per_q_face_tracks=515, actual_assigned_join_max_um=25.464,
                      raw_source_join_capacity_proven=False,
                      clock_TT_max_ps=171.4, clock_TT_spread_ps=20.7,
                      routed_view_qualified=False),
        timing=dict(clock_Hz=1_200_000_000, register_edges=3,
                    launch_to_launch_cycles=3,
                    accepted_edge_C_to_output_valid_edge='C+2 (after edge)',
                    downstream_capture_edge='C+3',
                    earliest_final_output_launch_offset_cycles=native_words-1+3,
                    legacy_P_only_input_launch_cycles=legacy_words,
                    extra_P_only_input_launch_cycles=native_words-legacy_words,
                    conservative_nonoverlapped_P_path_added_cycles=native_words-legacy_words+3,
                    token_added_cycles=None,
                    token_cost_missing=['actual compiler SU e transpose/producer calendar',
                        'actual service frame exposure on token critical path',
                        'other q-frame delay versus existing path',
                        'assigned wire and clock phase stages',
                        'native output commit/service completion']),
        qualification=dict(unit_exact='T640/T133 and mutants in results/rtl/s81_native_svc_1014',
                           full_native_service=False, native_token=False,
                           measured_token_loss=None,
                           note='Prefer source-side real BF16 packing if it removes raw FP32 transport cost; never price host rounding as native hardware.'))
