"""Analytical sizing of the real static VM edge services; no physical/rate claim."""
from __future__ import annotations


def model(entries: int = 8, cap_pipeline: int = 0, read_pipeline: int = 0) -> dict:
    if entries < 2 or entries & (entries - 1):
        raise ValueError('capture entries must be a power of two >= 2')
    if cap_pipeline not in (0, 1) or read_pipeline not in (0, 1):
        raise ValueError('only measured one-stage structural candidates are supported')
    lane_state = entries * (1 + 10 + 16 + 512)
    return {
        'schema': 'opentallas.s81-static-vm-face-model.v1',
        'macs_per_cycle': 0,
        'capture': {
            'roots': 128, 'lanes': 16, 'entries_per_lane': entries,
            'row_bits': 512, 'elements_per_serial_cycle_max': 256,
            'rows_per_serial_cycle_max': 16,
            'lane_output_age_from_physical_pin_sample_serial_edges': 1 + cap_pipeline,
            'x34_bank_write_age_from_physical_pin_sample_serial_edges': 2 + cap_pipeline,
            'added_fixed_serial_edges': cap_pipeline,
            'initiation_interval_serial_edges': 1,
            'extra_capture_state_bits_per_lane_estimate': 9 * cap_pipeline,
            'first_stream_visibility': 'P=zero-based physical PIN SAMPLE; q=P+2+cap_pipeline;4*(q//3)+2+(q%3); bench tk is one-based and adds1',
            'rows_per_stream_cycle_epoch_average_max': 12,
            'assembly_state_bits_per_lane': lane_state,
            'assembly_state_bits_total': 16 * lane_state,
            'pin_register_bits_per_lane': 832 + 4 + 1,
            'serial_state_bits_per_lane': lane_state + 832 + 4 + 1 + 543 + 5 + (entries.bit_length()) + 1,
            'cdc_data_bits_per_lane': 3 * 543,
            'mux_cost': '16 elements merge into direct-indexed entries; one statically due row per lane edge',
            'clock_plan': '16 separately hardened lanes; no flat >15000-sink capture root',
            'boundary_bits_per_serial_cycle': 13376,
            'write_boundary_bits_per_stream_cycle': 16 * 543,
        },
        'wfc': {
            'writes_per_serial_cycle': 1, 'reads_per_serial_cycle_max': 2,
            'write_bytes_per_serial_cycle': 64, 'read_bytes_per_serial_cycle_max': 128,
            'boundary_request_bits': 560, 'boundary_response_bits': 1029,
            'latency_serial_cycles': 15 + 3 * read_pipeline,
            'added_stream_response_pad_edges': 3 * read_pipeline,
            'added_response_pad_bits': 3 * 1026 * read_pipeline,
            'phase_accounting': 'one core edge plus three actual response-pad edges preserves 4stream/3serial epoch and all x43 legal slots',
            'read_lane_rule': 'paired rows must have different low-two-bit lanes',
        },
        'outbound': {
            'query_or_gather_rows_per_serial_cycle_max': 1,
            'collective_rows_read_per_stream_cycle_max': 1,
            'collective_rows_write_per_stream_cycle_max': 4,
            'collective_read_pin_latency_stream_cycles': 12 + read_pipeline,
            'query_gather_blocked_issue_phase': (2 - read_pipeline) % 4,
            'query_gather_x43_sample_offset_edges': 15 + read_pipeline,
            'collective_write_boundary_bits': 2204,
            'read_mux_cost': 'four aux lanes shared on compiler-exclusive edges; overlap faults',
        },
        'vm_capacity': {'banks': 128, 'rows_512bit': 16384, 'bytes': 1048576,
                        'logical_read_ports': 32, 'logical_write_ports': 32},
        'structural_candidates': dict(cap_pipeline=cap_pipeline, read_pipeline=read_pipeline,
            opt_in_default=False, production_calendar_qualified=False,
            read_router_leaves=64 if read_pipeline else 0,
            read_valid_leaves=8 if read_pipeline else 0,
            read_router_mapped_FF=52440 if read_pipeline else 0,
            read_router_max_FF_per_root=1100 if read_pipeline else 0,
            fsr_split_leaves=16, fsr_mapped_FF_per_root=690,
            current_required_memory_write_read_leaf_instances=562,
            current_required_memory_write_read_clock_roots=610,
            current_outer_clock_pin_count=682 if read_pipeline else 610,
            current_outer_raw_reset_pin_count=618 if read_pipeline else 546,
            extra_dependency_latency_ns=dict(capture=cap_pipeline/0.9, native_read=read_pipeline/1.2, WFC=3*read_pipeline/0.9),
            read_peak_legal_rows_per_stream_edge=30,
            return_prepare_mask_pipeline_FF=320,
            return_prepare_descriptor_age='stage9, one edge before unchanged stage10release; pending returnstorage integration proof',
            price='immutable model prices unchanged; added cycles must compose into actual programme before throughput qualification'),
        'schedule': 'all edge placement fixed by compiler; collision is sticky fault and never a delay',
        'physical_status': 'unqualified: outlines/pins/cuts/CTS/related-clock STA remain required',
        'price_status': 'immutable prices unchanged; no measured layer-rate improvement claimed',
    }


if __name__ == '__main__':
    import json
    print(json.dumps(model(), indent=2))
