#!/usr/bin/env python3
"""Construct a 72-frame regional-endpoint candidate from the immutable G8 plan.

No master, source instance, orientation or active link is changed. The east
interior h10 frame moves into the west south pocket; readers, taps, service
columns and the inactive east reserve pair make room in both axes. This is a
source/geometry candidate, never a routed timing or calendar qualification.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

GAP = 86.4
SEAL = 100.0
WIDTHS = {"main": 3240.0, "fallback": 3326.4}


def audit_rectangles(rectangles, width=33000.0, height=26000.0):
    errors = []
    minimum = (math.inf, None)
    for i, b in enumerate(rectangles):
        if min(b['x'], b['y']) < SEAL - 1e-6 or b['x'] + b['w'] > width - SEAL + 1e-6 or b['y'] + b['h'] > height - SEAL + 1e-6:
            errors.append(dict(kind='seal', block=b['name']))
        for c in rectangles[i + 1:]:
            sep = max(c['x'] - b['x'] - b['w'], b['x'] - c['x'] - c['w'], c['y'] - b['y'] - b['h'], b['y'] - c['y'] - c['h'])
            if sep < minimum[0]:
                minimum = (sep, [b['name'], c['name']])
            if sep < GAP - 1e-5:
                errors.append(dict(kind='clearance', pair=[b['name'], c['name']], separation_um=round(sep, 6)))
    return dict(errors=errors, minimum_clearance_um=round(minimum[0], 6), minimum_pair=minimum[1])


def construct(placement, original_plan, variant):
    pk, plan = copy.deepcopy(placement), copy.deepcopy(original_plan)
    old = {b['name']: b for b in placement['best']['blocks']}
    by = {b['name']: b for b in pk['best']['blocks']}
    ep_width = WIDTHS[variant]
    # The existing full h10 is moved without rotating or resizing its qualified envelope.
    by['h10_11'].update(x=old['link_0_4']['x'], y=SEAL)
    reader_x = by['h10_11']['x'] + by['h10_11']['w'] + GAP
    reader_dx = reader_x - old['idx_01']['x']
    for i in range(4):
        by[f'idx_{i:02}']['x'] = round(old[f'idx_{i:02}']['x'] + reader_dx, 6)
    tap_x = max(by[f'idx_{i:02}']['x'] + by[f'idx_{i:02}']['w'] for i in range(4)) + GAP
    tap_dx = tap_x - old['etap_00']['x']
    for i in range(8):
        by[f'etap_{i:02}']['x'] = round(old[f'etap_{i:02}']['x'] + tap_dx, 6)
    service_dx = reader_x - old['svc_full_0']['x']
    for i in range(16):
        by[f'svc_full_{i}']['x'] = round(old[f'svc_full_{i}']['x'] + service_dx, 6)
    by['iqf_00']['y'] = round(by['h10_11']['y'] + by['h10_11']['h'] + GAP, 6)
    ep_street = 172.8 if variant == 'main' else 129.6
    for row in range(2):
        by[f'end_parent_{row}']['w'] = ep_width
        by[f'end_parent_{row + 2}'].update(w=ep_width, x=round(by[f'end_parent_{row}']['x'] + ep_width + ep_street, 6))
    east_edge = max(by[f'end_parent_{i}']['x'] + by[f'end_parent_{i}']['w'] for i in range(4))
    for i, reserve in enumerate(pk['reserves']):
        assert reserve['name'] == f'link_1_{i + 4}'
        reserve.update(x=round(east_edge + GAP, 6), y=round(old['h10_11']['y'] + i * (reserve['h'] + GAP), 6))
    audit = audit_rectangles(pk['best']['blocks'] + pk['reserves'])
    assert not audit['errors'], audit
    assert sum(b['name'].startswith('h9_') for b in by.values()) == 60
    assert sum(b['name'].startswith('h10_') for b in by.values()) == 12
    assert len(by) == len(old) and set(by) == set(old)
    moves = {n: dict(before=[o[k] for k in ('x', 'y', 'w', 'h')], after=[by[n][k] for k in ('x', 'y', 'w', 'h')])
             for n, o in old.items() if any(abs(o[k] - by[n][k]) > 1e-6 for k in ('x', 'y', 'w', 'h'))}
    mapping = original_plan['facts']['physical72']['block_mapping']
    for b in plan['blocks']:
        slot = mapping.get(b['name'])
        if slot is None:  # G7-added Engram and taps were not in the original mapping.
            candidates = [n for n, g in old.items() if all(abs(b[k] - g[k]) < 1e-4 for k in ('x', 'y', 'w', 'h'))]
            assert len(candidates) == 1, (b['name'], candidates)
            slot = candidates[0]
        b.update({k: by[slot][k] for k in ('x', 'y', 'w', 'h')})
    # Reproject the existing face seed fraction. Actual leaf/parent LEF pin reprojection
    # remains mandatory in rvcase; no claim about a physical pin follows from this step.
    for link in plan['links']:
        for j, ep in enumerate(link['e']):
            ob, nb = original_plan['blocks'][ep[0]], plan['blocks'][ep[0]]
            face = link['endpoint_faces'][j]
            tx, ty = (ep[2] - ob['x']) / ob['w'], (ep[3] - ob['y']) / ob['h']
            ep[2] = round(nb['x'] + (0 if face == 'W' else nb['w'] if face == 'E' else tx * nb['w']), 4)
            ep[3] = round(nb['y'] + (0 if face == 'S' else nb['h'] if face == 'N' else ty * nb['h']), 4)
        for field in ('sp', 'h', 's', 'L', 'station_dirs'):
            link.pop(field, None)
    plan['blockages'] = copy.deepcopy(pk['reserves'])
    physical = plan['facts']['physical72']
    physical.update(owner_adopted=False, routing='PENDING regional candidate macro-free routing', calendar='PENDING exact moved-frame/station ages; prior calendar invalid')
    capacity = plan['facts'].pop('stage_map', None)
    if capacity:
        capacity['bound_by'] = 'CAPACITY INVENTORY ONLY; previous calendar invalid, no rate qualification'
        plan['facts']['stage_map_capacity_only'] = capacity
    for key in ('relays', 'relay_bit_stages', 'bit_mm', 'relay_channels_seed', 'worst_cut', 'over_reach_bits', 'cut_windows_over_limit'):
        plan['facts'].pop(key, None)
    packet = dict(variant=variant, end_parent_w_um=ep_width, end_parent_intercolumn_street_um=ep_street,
                  other_slice_streets_um=172.8, seal_ring_um=SEAL, die_um=[33000, 26000], n_frames=72,
                  active_links=len(plan['links']), moved_slots=moves, geometry=audit,
                  ml_landing_relay='PENDING exact existing E2 parent ML placement/source integration; no extra edge assumed',
                  adoption='SOURCE/GEOMETRY CANDIDATE ONLY; native endpoint, parent, actual pins, relay bodies, cut capacity, clocks, calendar and die STA owed')
    pk['regional_repack_1021'] = packet
    physical['regional_repack_1021'] = packet
    pk['scope'] = packet['adoption']
    return pk, plan, packet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--placement', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--variant', choices=WIDTHS, required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    placement, plan = [json.loads(Path(p).read_text()) for p in (args.placement, args.plan)]
    pk, p, record = construct(placement, plan, args.variant)
    record['inputs'] = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (args.placement, args.plan)}
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    for name, data in [('placement.json', pk), ('plan_unrouted.json', p), ('geometry.json', record)]:
        (out / name).write_text(json.dumps(data, indent=1) + '\n')
    print(json.dumps(record, sort_keys=True))


if __name__ == '__main__':
    main()
