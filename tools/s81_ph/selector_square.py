#!/usr/bin/env python3
"""Source-bound square selector composition. Planning only until all gates exist.

R0 placements deliberately avoid assuming MY from placeholder orientation lists.
The old die outline is not silently enlarged: integration remains blocked until a
new selector slot and actual station/control implementation are qualified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '1dc5e37d5476277c7413c341b42e09d2dd405bd5'
PARAMS = dict(SAFE=1, PIPE2=1, CMP_RETIME=1, QIO=1, FRPR=1,
              MRG_PIPE=1, RQPIPE=1, SLAT=4, SEARCH_PIPE=1)
QUARTER = 'physical/s81_ph_views/ports/contract_selsq_ckS/dsfd_selt_q2/ports.json'
CONTROL = 'physical/s81_ph_views/ports/contract/dsfd_selt_c/ports.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def center(pin, x, y):
    return (x + (pin[2] + pin[4]) / 2, y + (pin[3] + pin[5]) / 2)


def build(root=ROOT):
    q = json.loads((root / QUARTER).read_text())
    c = json.loads((root / CONTROL).read_text())
    if [q['w_um'], q['h_um']] != [432.0, 280.8]:
        raise ValueError('square source contract must be 432 x 280.8')
    # On the 10.8 um x / 2.16 um y grid. A 43.2 um corridor separates
    # quarter rows and provides explicit station area rather than abutment fiction.
    qx, cx, pitch = 6.544, 481.744, 324.0
    rx, cy = cx + c['w_um'] + 43.2, 140.4
    tiles = [dict(inst=f'u_q{g}', master='dsfd_selt_q2', x=(qx if g % 2 == 0 else rx), y=(g//2)*pitch,
                  orient='R0', lane_order=['SW', 'SE', 'NW', 'NE'][g]) for g in range(4)]
    tiles.append(dict(inst='u_c', master='dsfd_selt_c', x=cx, y=cy, orient='R0'))
    bundles = []
    for g in range(4):
        for qp, cp, width, forward in [('t_s', 'f_s', 865, True), ('t_o', 'f_o', 354, True),
                                       ('f_c', 't_c', 66, False), ('f_cr', 't_cr', 1, False)]:
            lengths = []
            for b in range(width):
                a = center(q['ports'][qp]['pins'][b], tiles[g]['x'], tiles[g]['y'])
                z = center(c['ports'][cp]['pins'][g*width+b], cx, cy)
                lengths.append(abs(a[0]-z[0])+abs(a[1]-z[1]))
            worst = max(lengths)
            stations = max(0, math.ceil(worst / 430.56)-1)
            bundles.append(dict(quarter=g, width=width,
                src=[f'u_q{g}', qp] if forward else ['u_c', f'{cp}[{g*width}+:{width}]'],
                dst=['u_c', f'{cp}[{g*width}+:{width}]'] if forward else [f'u_q{g}', qp],
                length_um_max=round(worst, 3), minimum_stations=stations,
                equal_segment_um_lower_bound=round(worst/(stations+1), 3),
                final_pin_segment_target_um=100, geometry_status='station placement required'))
    height = pitch+q['h_um']
    area = 4*q['w_um']*q['h_um']+c['w_um']*c['h_um']
    old_outline = [5270.376, 321.816]
    return dict(schema='opentallas.s81.selector-square.v1', variant='square_frpr',
        source_commit=SOURCE, default_enabled=False, qualified=False, params=PARAMS,
        tiles=tiles, tile_area_um2=area, local_outline_um=[rx+q['w_um'], height],
        existing_slab_outline_um=old_outline, existing_slab_height_deficit_um=height-old_outline[1],
        source_contracts={p: digest(root/p) for p in (QUARTER, CONTROL)},
        clock_map={t['inst']+'/ck': 'ck' for t in tiles},
        reset_map={t['inst']+'/rst': 'rst' for t in tiles},
        die_ports=dict(lanes={f'i{t["lane_order"]}': [t['inst'], 'lane'] for t in tiles[:4]},
                       vd=['u_c', 'vd'], vf=['u_c', 'vf']),
        bundles=bundles, interface_bits=4*(515+865+354+66+1),
        internal_bundle_bits=4*(865+354+66+1),
        lane_bits_per_cycle=4*515, memory=dict(replicas=24, bytes_per_read_port_cycle=32,
            logical_quarter_read_bits=768, macros_per_quarter=6), macs_per_cycle=0,
        latency=dict(measured_tail_minus_native_mean_cycles=174,
            measured_tail_minus_native_max_cycles=310, baseline_mean_cycles=127,
            measured_increment_over_127_cycles=47,
            inherited_recipe_total_65_status='UNVERIFIED baseline attribution',
            added_composition_cycles_status='UNPRICED pending station implementation and minimum exactness gate'),
        qualification_problems=[
            'square quarter live routed TT/FF/DRC/LEF MATCH and SS/TT/FF ETMs pending',
            'selector control hardview must match MRG_PIPE=1 RQPIPE=1 SLAT=4 XDX=1 SEARCH_PIPE=1',
            'R0 quarter/control seam stations are not implemented or placed; existing direct RTL is insufficient',
            'clock roots, source latency and cross-root lockups require measured qualification',
            'new slab height does not fit existing selector die slot; generator floorplan change required',
            'lane chains and VM output station geometry require full die composition',
            'minimum full-width transaction gate with actual seam latencies and finite credits required',
            'routing tracks and PDN/grid proofs require actual hardened LEFs, not placeholder orientations'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--require-qualified', action='store_true')
    a = ap.parse_args()
    result = build(a.root)
    if a.require_qualified:
        raise ValueError('UNQUALIFIED square selector: ' + '; '.join(result['qualification_problems']))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=1)+'\n')
    print(f"UNQUALIFIED: {len(result['tiles'])} tiles, {len(result['bundles'])} bundles")


if __name__ == '__main__':
    main()
