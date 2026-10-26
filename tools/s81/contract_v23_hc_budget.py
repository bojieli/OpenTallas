#!/usr/bin/env python3
"""S81 die contract v23 candidate (S-DIE r12 2026-10-15): full HC corridor budget = v22 return columns + NORM NT strips.

v22 (contract_v22_hc_ret.py) grows every cth row by 12.96 um for the four-column return (ctra/ctrb).  The NORM tree
variant (S-NORM; local-split grants on main 5c3c7fd7a: ctfxs_nt in the ctfx_nt slot + new ctfl_nt row) costs another
19.44 um per cth row vs the serial v20 cth (cth_nt 777.60 vs 758.16).  v23 carries BOTH, so the die screens the real
corridor that remains: sp_hc_s (10 rows) +194.4, sp_hc_t (12 rows) +233.28 on top of v22, i.e. the hc_corridor
1226.88 -> 799.2 um (--hc-corr 799.20).  Screen candidate: granted only when that GEN is legal with pin_align FAIL 0
and the corridor stations / cut pass; otherwise the NT height must be found inside cth (or the die changes).
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NT_GROW = 19.44
ROWS = {'sp_hc_s': 10, 'sp_hc_t': 12}


def build(base):
    c = copy.deepcopy(base)
    assert c.get('v22_hc_return_columns'), 'v23 builds on the v22 HC return-column contract'
    slots = {s['name']: s for s in c['slots']}
    corr_in = float(c['v22_hc_return_columns']['hc_corridor_um'][1])
    rec = dict(status='CANDIDATE_SCREEN_NOT_GRANTED',
               basis=['v22 four-column return +12.96/row', 'NORM NT swap +19.44/row (cth_nt 777.60 vs serial 758.16, '
                      's81_v21_gen18.json v21_gen18.hc_norm_local_split.die_cost)'],
               cth_h_um=[758.16, round(771.12 + NT_GROW, 3)], nt_growth_um=NT_GROW, slabs={})
    total = 0.0
    for parent, rows in ROWS.items():
        slab = slots[parent]
        d = round(rows * NT_GROW, 3)
        total += d
        slab['outline']['h'] = round(slab['outline']['h'] + d, 3)
        slab['version'] = 23
        slab['v23_norm_nt_growth_um'] = d
        rec['slabs'][parent] = dict(growth_um=d, outline=slab['outline'])
    rec['hc_corridor_um'] = [corr_in, round(corr_in - total, 3)]
    rec['generator_option'] = '--hc-corr %.2f' % (corr_in - total)
    lay = c['sub_layouts']['ot_s81_hc_cth']
    lay['outline']['h'] = round(lay['outline']['h'] + NT_GROW, 3)
    lay['note'] = lay.get('note', '') + (' | v23: NORM NT rows (ctfxs_nt + ctfl_nt, pins physical/s81_die_pins/'
                                         'v22_hc_local_split) budgeted: cth %.2f' % lay['outline']['h'])
    c['version'] = 23
    c['v23_hc_corridor_budget'] = rec
    c['changelog'].append('v23 candidate: HC corridor budget = return columns + NORM NT strips; cth %.2f, hc_s +194.4 / '
                          'hc_t +233.28, hc_corridor %.2f.' % (lay['outline']['h'], corr_in - total))
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='results/arch/hier_contract_1011/s81_v22_hc_ret.json')
    ap.add_argument('--output', default='results/arch/hier_contract_1011/s81_v23_hc_budget.json')
    a = ap.parse_args()
    out = build(json.loads((ROOT / a.input).read_text()))
    (ROOT / a.output).write_text(json.dumps(out, indent=1) + '\n')
    print(a.output, json.dumps(out['v23_hc_corridor_budget']))


if __name__ == '__main__':
    main()
