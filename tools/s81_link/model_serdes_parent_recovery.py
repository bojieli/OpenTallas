#!/usr/bin/env python3
"""Size the real SerDes parent from committed child views; never qualify a stub."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRID = 43.2


def ceil_grid(value):
    return round(math.ceil((value - 1e-8) / GRID) * GRID, 6)


def model():
    children = []
    y = ceil_grid(GRID + 2250 + GRID)
    for name in ('kp4_dsyn', 'kp4_ddly', 'kp4_dchn', 'kp4_dout', 'rate_match', 'kp4_enc'):
        top = 'ot_s81_' + name
        path = ROOT / f'physical/ref_tile/s81lk_{name}/views/{top}/{top}.lef'
        raw = path.read_bytes()
        w, h = map(float, re.search(rb'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', raw).groups())
        children.append(dict(top=top, view=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(),
                             at_um=[GRID, y], outline_um=[w, h], area_um2=w*h))
        y = ceil_grid(y + h + GRID)
    height = y
    # Four-slot ring payload lower bound from the recovered predecessor. This
    # deliberately over-reserves a successor that uses ordinary per-edge relays.
    cut_bits = 4 * (544 + 320)
    track_pitch = .048
    corridor = cut_bits * track_pitch
    width = ceil_grid(GRID + max(c['outline_um'][0] for c in children) + corridor + GRID)
    for c in children:
        assert all(abs(v / GRID - round(v / GRID)) < 1e-7 for v in c['at_um'])
    assert width - GRID - max(c['outline_um'][0] for c in children) >= corridor + GRID - 1e-6
    return dict(schema='opentallas.serdes_parent_recovery.v1', status='BLOCKED_NOT_A_PHYSICAL_OR_CYCLE_PASS',
                analog=dict(outline_um=[250, 2250], at_um=[GRID, GRID], area_um2=562500,
                            note='Unshrunk analog model only; all digital children remain real.'),
                children=children, candidate=dict(outline_um=[width, height],
                    area_um2=width*height, digital_child_area_um2=sum(c['area_um2'] for c in children),
                    grid_um=GRID, minimum_child_gap_um=GRID,
                    vertical_track_lower_bound=dict(bits=cut_bits, pitch_um=track_pitch, channel_um=corridor),
                    note='Conservative channel reserve, not GRT proof. Relay placement and PG/via capacity remain open.'),
                current_die_slot_um=[259.2, 3596.4],
                area_delta_per_slot_mm2=(width*height-259.2*3596.4)/1e6,
                arithmetic=dict(mac_per_cycle=0, payload_bits_per_cycle=512, bytes_per_cycle=64,
                    encoded_bits_per_cycle=544, decoder_raw_cycles=60,
                    predecessor_candidate_cycles=74, predecessor_added_vs68_cycles=6,
                    successor_cycles=None, measured_throughput=None,
                    note='No rate credit. Actual per-edge relay layout determines successor compiler offsets.'),
                blockers=['Die lead must assign legal wider/taller slot for all release replicas; no outline change implied.',
                    'Replace predecessor data multicycles with physically timed per-edge relay transport.',
                    'Native rate_match capture budget failed five pins at 458ps in historical audit; remeasure current view.',
                    'Harden real two-domain reset/status glue and retain gray FIFO CDC; asynchronous data must not use synchronous landing.',
                    'PMA TX forwarded clock and per-cycle wires must be implemented with <=405um hops.',
                    'Run real framed traffic at Verilator5.050 with fail witnesses, native-pin/wire audit, then critical gate review.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = model()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], candidate=result['candidate']['outline_um'],
                         delta_mm2=result['area_delta_per_slot_mm2'])))
