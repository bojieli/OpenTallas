#!/usr/bin/env python3
"""Size fresh native service bands; never rescale or overwrite legacy masters.

This is the pre-RTL allocation, not a generated functional macro abstract.
Actual module partition, mapped occupancy, clocks and routing remain gates.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVC = ROOT / 'physical/hbm_accel_die_views/svc'


def plan(height=388.8):
    geometry_path = SVC / 'svc_geometry.json'
    stages_path = SVC / 'seg_stages.json'
    geometry = json.loads(geometry_path.read_text())
    stages = json.loads(stages_path.read_text())
    pitch, hop, width = .096, 380., 8500.
    # Existing K256/R10 data codec and independent K13/R6 identity codec.
    packet, request, reverse = 266 + 19, 16 * 7, 16 * 2
    crossing = 18 * packet + request + reverse
    capacity = 2 * math.floor(height / pitch)
    families = {}
    for family, old in stages['families'].items():
        pc_x = geometry['hfd_svc_' + family]['pc_x']
        segments = []
        for segment in old['segments']:
            segments.append(dict(name=segment['name'].replace('_s', '_native_s'),
                x0_um=segment['x0'], x1_um=segment['x1'], height_um=height,
                legacy_units=list(segment['units']),
                PC_indices=[int(u[2:]) for u in segment['units'] if u.startswith('pc')],
                occupancy_qualified=False))
        families[family] = dict(segments=segments,
            collector=dict(x0_um=4000, x1_um=4500, y0_um=160, y1_um=height,
                note='provisional logic region above bank rows; mapped fit not yet qualified'),
            PC_to_collector_horizontal_hops=[math.ceil(abs(x - width / 2) / hop) for x in pc_x],
            output_stations=[dict(port=p, segment=segments[p]['name'], line_bits=1099,
                credit_bits=1, initial_credits=64) for p in range(8)])
    return dict(schema='opentallas.hbm_svc_native_plan.v1', status='PRE_RTL_UNQUALIFIED',
        source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (geometry_path, stages_path, Path(__file__))},
        geometry=dict(width_um=width, legacy_height_um=259.176, height_um=height,
            replicas=4, added_band_reservation_mm2=4 * width * (height - 259.176) / 1e6),
        communication=dict(MACs_per_cycle=0, return_bytes_per_PC_cycle=32,
            group_sectors=34, data_codeword_bits=266, identity_codeword_bits=19,
            sector_packet_bits=packet, maximum_half_sectors=18,
            request_bits_per_half=request, reverse_pop_bits_per_half=reverse,
            collector_tracks_per_half=crossing, M4_M6_capacity_estimate=capacity,
            remaining_before_legacy_clock_shields=capacity-crossing,
            line_boundary_bits=8792, credit_boundary_bits=8),
        implementation=dict(selected_banks='one local primary bank perPC plus selected adjacent pair sidechannel',
            identity_protection='separate K13/R6 SECDED for valid and j12; candidate not yet implemented',
            replica_mux_cost='32 local bank selectors plus two per-half pair selectors; mapped inventory pending',
            added_cycles=None,
            latency_composition='12 horizontal relay hops each way worstcase before vertical/cross-face stages; 8 index layers, no overlap credited'),
        families=families, adopted=False,
        remaining_gates=['actual modular RTL and exact component gate',
            'legacy crossnet inventory and whole-band cell fit',
            'metadata codec pipeline and transaction identity gate',
            'native lease and WB fence composition', 'loaded clock and corner/DRC qualification'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--height', type=float, default=388.8)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(plan(args.height), indent=2) + '\n')
