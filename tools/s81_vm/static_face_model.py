"""Analytical sizing of the real static VM edge services; no physical/rate claim."""
from __future__ import annotations


def model(entries: int = 8) -> dict:
    if entries < 2 or entries & (entries - 1):
        raise ValueError('capture entries must be a power of two >= 2')
    lane_state = entries * (1 + 10 + 16 + 512)
    return {
        'schema': 'opentallas.s81-static-vm-face-model.v1',
        'macs_per_cycle': 0,
        'capture': {
            'roots': 128, 'lanes': 16, 'entries_per_lane': entries,
            'row_bits': 512, 'elements_per_serial_cycle_max': 256,
            'rows_per_serial_cycle_max': 16,
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
            'latency_serial_cycles': 15,
            'read_lane_rule': 'paired rows must have different low-two-bit lanes',
        },
        'outbound': {
            'query_or_gather_rows_per_serial_cycle_max': 1,
            'collective_rows_read_per_stream_cycle_max': 1,
            'collective_rows_write_per_stream_cycle_max': 4,
            'collective_read_pin_latency_stream_cycles': 12,
            'collective_write_boundary_bits': 2204,
            'read_mux_cost': 'four aux lanes shared on compiler-exclusive edges; overlap faults',
        },
        'vm_capacity': {'banks': 128, 'rows_512bit': 16384, 'bytes': 1048576,
                        'logical_read_ports': 32, 'logical_write_ports': 32},
        'schedule': 'all edge placement fixed by compiler; collision is sticky fault and never a delay',
        'physical_status': 'unqualified: outlines/pins/cuts/CTS/related-clock STA remain required',
        'price_status': 'immutable prices unchanged; no measured layer-rate improvement claimed',
    }


if __name__ == '__main__':
    import json
    print(json.dumps(model(), indent=2))
