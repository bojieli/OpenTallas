#!/usr/bin/env python3
"""Sizing record for the opt-in 32-PC static landing mechanism (not die qualification)."""
import json
from pathlib import Path
import re


def model(root=None, groups=4):
    if groups not in (1, 4):
        raise ValueError('groups must be 1 or 4')
    root = Path(root or Path(__file__).resolve().parents[1])
    lef = root / 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
    width, height = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef.read_text()).groups())
    return dict(schema='opentallas.hbm.static-landing.v1', opt_in=True,
        pcs=32, banks=2, sectors_per_bank_per_pc=64, sector_bits=256,
        macro='ot_sram_1r1w_128x256_m1_r2c2', macro_count=32,
        macro_area_um2=width*height, array_area_um2=32*width*height,
        capacity_bytes=32*128*32, fill_bytes_per_cycle=1024,
        drain_groups=groups, drain_bytes_per_cycle=1024//groups, drain_cycles_per_block=64*groups,
        read_latency_cycles=1, read_issue_interval_cycles=1,
        block_boundary_bits=2, payload_boundary_bits=8192//groups,
        fill_boundary_bits=32*(256+6+1+1+16),
        landing_input_bits=8998, landing_output_bits=30+8192//groups,
        delivery_input_bits=9014, delivery_output_bits=2252,
        fill_port_bits=dict(fill_v=32,fill_bank=32,fill_slot=192,fill_epoch=512,fill_data=8192),
        dq_bits=8*281, dq_sector_mapping='base+slot*32+group*8+bank',
        drain_output_port_bits=dict(out_v=1,out_bank=1,out_slot=6,out_group=2,out_epoch=16,out_data=8192//groups), macs_per_cycle=0,
        valid_state_bits=2*32*64, replica_mux='32 independent 1R1W macros; group4: eight local 4:1 sector muxes; only selected 8 PCs read each cycle',
        fanout='start/bank to 32 macros; PC-local write enables and addresses',
        routing_tracks_needed=8192//groups, routing_capacity=None, slot_fit=None,
        composed_latency='one macro read edge; 256 fixed group issue slots per block (group4); prefetch latency external',
        token_delta_cycles=None, adopted=False, qualification='mechanism only; band ABI, native loader, SM/WB and compiler calendar joins absent')


def verify_port_counts(root=None):
    import sys
    root = Path(root or Path(__file__).resolve().parents[1])
    sys.path.insert(0, str(root / 'tools'))
    import hbm_die_views as views
    result = {}
    for top, expected in [('ot_hbm_svc_static_landing', (8998, 2078)),
                          ('ot_hbm_svc_static_vm_delivery', (9014, 2252))]:
        path = root / 'rtl/hbm_accel/loader/service_native' / (top + '.sv')
        ports = views.L.parse_module(str(path), top)['ports']
        counts = {direction: sum(width for d, width in ports.values() if d == direction)
                  for direction in ('input', 'output')}
        assert tuple(counts.values()) == expected, (top, counts, expected)
        result[top] = dict(counts=counts, ports=ports)
    assert sum(model(root)['fill_port_bits'].values()) == 8960
    return result


if __name__ == '__main__':
    print(json.dumps(dict(model=model(), source_ports=verify_port_counts()), indent=2))
