#!/usr/bin/env python3
"""Apply the granted native HC leaf dimensions to an actual die contract.

The v19 baseline stays immutable. The generated candidate is consumed by the
normal --contract option; this is a placement grant, not timing qualification.
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROW = 17.28

def build(base):
    c = copy.deepcopy(base)
    if c.get('v20_hc_native_geometry'):
        return c
    slots = {s['name']: s for s in c['slots']}
    receipt = {'status': 'CANDIDATE_NATIVE_VIEWS_REQUIRED', 'cth_growth_um': GROW,
               'source_grants': ['el1011-s81die.log 2026-10-14 23:12 ctnl',
                                 'el1011-s81die.log 2026-10-14 21:45/22:21 crootr_f v6'],
               'qualification': 'real successor binding, pin timing, die TT/FF/DRC and native composition remain required',
               'slabs': {}}
    for parent, rows in [('sp_hc_s', 10), ('sp_hc_t', 12)]:
        slab = slots[parent]
        delta = round(rows * GROW, 3)
        slab['outline']['h'] = round(slab['outline']['h'] + delta, 3)
        slab['origin']['y'] = round(slab['origin']['y'] - delta, 3)
        slab['grow_down_um'] = delta
        slab['version'] = 20
        # Keep every W/E external pin at its original die y. South-facing
        # chain ports follow the moved south edge; north edge stays fixed.
        for p in slab.get('pins', []):
            if p.get('face') in ('W', 'E'):
                p['offset'] = round(p['offset'] + delta, 4)
        children = [s for s in c['slots'] if s.get('parent') == parent]
        for child in children:
            child['origin']['y'] = round(child['origin']['y'] + delta, 3)
        tiles = [s for s in children if s.get('cell') == 'ot_s81_hc_cth']
        for x in sorted({s['origin']['x'] for s in tiles}):
            column = sorted([s for s in tiles if s['origin']['x'] == x],
                            key=lambda s: -s['origin']['y'])
            for i, tile in enumerate(column):
                tile['outline']['h'] = round(tile['outline']['h'] + GROW, 3)
                tile['origin']['y'] = round(tile['origin']['y'] - (i + 1) * GROW, 3)
                tile['version'] = 20
        receipt['slabs'][parent] = {'growth_down_um': delta, 'cth_instances': len(tiles),
                                    'outline': slab['outline'], 'origin': slab['origin']}
    layout = c['sub_layouts']['ot_s81_hc_cth']
    shift = 0.0
    for row in layout['rows']:
        row['y'] = round(row['y'] + shift, 3)
        if row['cell'] == 'ot_s81_hc_ctnl':
            row['h'] = 99.36
            row['per_column_leaf_heights_um'] = [95.04, 95.04, 99.36, 99.36]
            shift += 4.32
    assert abs(shift - GROW) < 1e-6
    layout['outline']['h'] = round(layout['outline']['h'] + shift, 3)
    layout['note'] = ('v20 native ctnl_l2/l3 grant: four 99.36-um row reservations; '
                      'l0/l1 keep 95.04-um views. Child native pin files must use these origins.')
    for name, insertion, spread in [('sp_hc_s/crootr_c0/f', 394.9, 78.9),
                                     ('sp_hc_s/crootr_c2/f', 375.6, 59.6)]:
        leaf = slots[name]
        old_h = leaf['outline']['h']
        leaf['outline']['h'] = 345.6
        leaf['version'] = 20
        leaf['target_insertion_ps'] = insertion
        leaf['clock_evidence'] = {'kind': 'pre_route_cts', 'spread_ps': spread,
                                  'source': 'S-ELEM final v6 gates 056c994dd (west394.9/78.9; east375.6/59.6)'}
        leaf['slot_change'] = {'bottom_anchored': True, 'free_y_channel_um': round(old_h - 345.6, 3),
                               'fixed_cycles_added': 0, 'native_successor_required': True}
    c['version'] = 20
    c['v20_hc_native_geometry'] = receipt
    c['changelog'].append('v20 HC native geometry: ctnl row pitch99.36; hc_s/t grow down172.8/207.36; crootr_f bottom345.6 and252.72 y-wire channel.')
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='results/arch/hier_contract_1011/s81.json')
    ap.add_argument('--output', default='results/arch/hier_contract_1011/s81_v20_hc.json')
    a = ap.parse_args()
    c = build(json.loads((ROOT / a.input).read_text()))
    out = ROOT / a.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(c, indent=1) + '\n')
    print(json.dumps(c['v20_hc_native_geometry'], sort_keys=True))

if __name__ == '__main__':
    main()
