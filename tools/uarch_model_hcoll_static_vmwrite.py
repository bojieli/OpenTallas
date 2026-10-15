#!/usr/bin/env python3
"""Analytic resource/port model for the static COLL VM writer; no PPA claim.

The RTL already existed before this helper was requested. This records explicit
implementation assumptions before any synthesis or physical build, not a
retroactive claim that this model preceded the initial RTL implementation.
"""
import json

def model(dff_um2=4.5, gate_um2=0.8):
    """Return conservative declared-register and ten-source mux estimates.

    Cell areas are deliberately uncalibrated planning inputs, not technology
    measurements. Synthesis can prune unused portions of declared pipelines.
    """
    stages, lanes, banks = 2, 5, 8
    pipeline_flops = stages * lanes * (40 + 512 + 16 + 1)
    flops = pipeline_flops + banks * 281 + lanes + 1
    # Each bank OR-combines up to ten masked sector sources. These are gate
    # equivalents rather than synthesized standard-cell instances.
    mux_data_bits = banks * 280
    source_terms = mux_data_bits * (2 * lanes)
    or_terms = mux_data_bits * (2 * lanes - 1)
    return {
        'status': 'UNQUALIFIED_ANALYTIC_ONLY',
        'production_shape': {'rgx_lanes': 4, 'rgx_bits_per_lane': 512, 'tkw_bits': 568},
        'declared_flop_upper_bound': flops,
        'single_clock_root_sink_upper_bound': flops,
        'clock_root_15000_sink_bound_met_analytically': flops <= 15000,
        'mux': {'sources_per_bank': 10, 'banks': banks,
                'payload_bits_per_bank': 280, 'and_gate_equivalents': source_terms,
                'or_gate_equivalents': or_terms,
                'balanced_or_depth_estimate': 4,
                'decode_and_calendar_check_area_excluded': True},
        'pins': {'input_bits_including_clk_reset': 2831, 'output_bits': 2254, 'total': 5085},
        'area_estimate_um2_uncalibrated': flops * dff_um2 + (source_terms + or_terms) * gate_um2,
        'area_assumptions': {'dff_um2': dff_um2, 'two_input_gate_um2': gate_um2,
                             'excludes': 'decode/calendar checks, clock buffers, routing, hold cells'},
        'bandwidth': {'max_sectors_per_cycle': 8, 'sector_data_bits': 256,
                      'data_bits_per_cycle': 2048, 'sustained_512bit_lines_per_cycle': 4,
                      'five_lane_burst_supported': True,
                      'five_lanes_every_cycle_supported': False},
        'latency_edges_from_ingress_capture': {'low_launch': 1, 'high_launch': 2,
                                              'bank_samples_low': 2, 'bank_samples_high': 3},
        'ownership': {'ingress_exact_bitmap_bits': 5, 'bank_exact_bitmap_bits': 8,
                      'bank_owner_bits': 4, 'low_owner_ids': [0,1,2,3,4],
                      'high_owner_ids': [5,6,7,8,9], 'collision_policy': 'sticky fault; no rescheduling'},
        'unverified': ['mapped area', 'assigned physical slot', 'routed timing',
                       'pin reach and routing cut', 'clock insertion/spread',
                       'integrated SRAM commit calendar', 'remote ring composition'],
    }

if __name__ == '__main__':
    print(json.dumps(model(), indent=2, sort_keys=True))
