#!/usr/bin/env python3
"""Sizing record for the opt-in 32-PC static landing mechanism (not die qualification)."""
import json
from pathlib import Path
import re


def model(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    lef = root / 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef'
    width, height = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef.read_text()).groups())
    return dict(schema='opentallas.hbm.static-landing.v1', opt_in=True,
        pcs=32, banks=2, sectors_per_bank_per_pc=64, sector_bits=256,
        macro='ot_sram_1r1w_128x256_m1_r2c2', macro_count=32,
        macro_area_um2=width*height, array_area_um2=32*width*height,
        capacity_bytes=32*128*32, fill_bytes_per_cycle=1024,
        drain_bytes_per_cycle=1024, drain_cycles_per_block=64,
        read_latency_cycles=1, read_issue_interval_cycles=1,
        block_boundary_bits=2, payload_boundary_bits=8192,
        fill_boundary_bits=32*(256+6+1), macs_per_cycle=0,
        valid_state_bits=2*32*64, replica_mux='32 independent 1R1W macros; no payload crossbar',
        fanout='start/bank to 32 macros; PC-local write enables and addresses',
        routing_tracks_needed=8192, routing_capacity=None, slot_fit=None,
        composed_latency='one macro read edge; 64 fixed issue slots per block; prefetch latency external',
        token_delta_cycles=None, adopted=False, qualification='mechanism only; band ABI, native loader, SM/WB and compiler calendar joins absent')


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
