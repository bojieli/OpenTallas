#!/usr/bin/env python3
"""Pre-RTL sizing of the service DMA single protected SRAM bank.

One bank is the minimum physical element; compose four banks per PC outside
this model. This is a timing/area budget, not a physical closure claim.
"""
import json
from pathlib import Path


def model():
    root = Path(__file__).resolve().parents[1]
    macro = 'ot_sram_1r1w_128x256_m1_r2c2'
    inventory = root / 'physical/asap7_memory_macros_v2' / macro / (macro + '.json')
    geometry = json.loads(inventory.read_text())['alignment_v2']['v2']
    # 4 lanes of 64 bits; two macro edges per sector. No arithmetic MACs.
    # Controller/ECC/four-entry elastic publication queue is a budget pending
    # synthesis. SRAM capacity itself is never implemented as flip-flops.
    return {
        'schema': 1, 'scope': 'HBM DMA protected SRAM bank, model before RTL',
        'macro': macro, 'inventory': str(inventory.relative_to(root)),
        'macro_instances_per_bank': 1, 'banks_per_pc': 4,
        'stored_groups': 32, 'sector_bits': 256,
        'payload_rows': [0, 31], 'sidecar_rows': [64, 95],
        'sidecar': '4x8 SECDED + fault/complement + valid/complement + row/complement',
        'macs_per_cycle': 0, 'compute_intensity_macs_per_byte': 0,
        'communication_intensity_macro_bytes_per_payload_byte': 2,
        'read_port': {'ports': 1, 'bits_per_edge': 256, 'payload_bytes_per_cycle': 16},
        'write_port': {'ports': 1, 'bits_per_edge': 256, 'payload_bytes_per_cycle': 16},
        'read_issue_interval_cycles': 2, 'write_issue_interval_cycles': 2,
        'latency_cycles': {'write_accept_to_sidecar_commit': 3,
                           'read_accept_to_publication': 5,
                           'registered_macro_launch': 1,
                           'macro_payload_and_sidecar': 2,
                           'ECC_decoder': 2, 'publication_register': 1,
                           'note': 'launch overlaps first edge; no double counting'},
        'four_bank_pc_payload_bytes_per_cycle': 64,
        'four_bank_pc_payload_GBps_at_1p2GHz': 76.8,
        'read_bandwidth_condition': 'independent groups, no output stalls; same-group write hazards stall',
        'boundary_bits_per_cycle_peak': {'write': 264, 'read_request': 7, 'publication': 259},
        'boundary_tracks_required': 530,
        'channel_capacity': {'pitch_um_budget': 0.064, 'width_um': 120,
                             'signal_layers': 2, 'tracks': 3750,
                             'qualification': 'budget only; real LEF pin fit and route required'},
        'geometry_um': geometry,
        'floorplan_slot_um': [120, 100],
        'macro_area_um2': geometry['area_um2'],
        'controller_ECC_queue_area_budget_um2': 2500,
        'slot_utilization_budget': (geometry['area_um2'] + 2500) / 12000,
        'replica_cost': {'ECC_encoders': 4, 'ECC_decoders': 4,
                         'publication_slots': 4, 'publication_bits': 1028,
                         'read_mux': '4:1 x257 at output, local to bank',
                         'write_demux': 'payload/parity 2:1 x256 at macro pin',
                         'reset': '32 valid bits and local control only; macro/data no reset',
                         'fanout': 'bank-local enable/address; no array-wide controls'},
        'single_user_token_contribution': '5-cycle first-sector fill + 2*(N-1) cycles per bank; four banks parallel; caller composes N',
        'physical_qualification': 'not launched until full-shape synthesis and real macro pin fit',
    }


if __name__ == '__main__':
    print(json.dumps(model(), indent=2, sort_keys=True))
