#!/usr/bin/env python3
"""S81 die contract v22 candidate (S-DIE r11 2026-10-15): HC four-column return successor (IDLE-S request 07:15).

Per cth row the ctra strip (576.72 x 21.6) becomes 4 column leaves ot_s81_hc_ctra_column COLUMN 0..3 of 144.18 x 30.24
and the ctrb strip becomes 4 x ot_s81_hc_ctrb_column 144.18 x 25.92 (x = 144.18 * column): cth 758.16 -> 771.12.
Die absorption: sp_hc_s (10 rows) +129.6 and sp_hc_t (12 rows) +155.52 come out of the hc_corridor
(--hc-corr 1512 -> 1226.88): hc_t keeps its floor and grows up, hc_s keeps its top (N band) and grows down, so no
other slab moves.  Screen candidate: granted only when that GEN is legal (corridor stations + cut).
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROW = 12.96
ROWS = {'sp_hc_s': 10, 'sp_hc_t': 12}
CORR_OLD = 1512.0


def build(base):
    c = copy.deepcopy(base)
    slots = {s['name']: s for s in c['slots']}
    rec = dict(status='CANDIDATE_SCREEN_NOT_GRANTED', request='el1011-s81die.log 2026-10-15 07:15:19 IDLE-S',
               branch='claude/s81-return-columns-1015 @20c63c643', cth_growth_um=GROW, slabs={},
               cost=dict(fixed_cycles='+1 on HC return data/valid (S-FUNC schedule)', extra_input_sink_bits=1536,
                         std_area_um2=dict(A=[2431, 2396, 2306, 2311], B=[1916, 1918, 1875, 1830])))
    total = 0.0
    for parent, rows in ROWS.items():
        slab = slots[parent]
        d = round(rows * GROW, 3)
        total += d
        slab['outline']['h'] = round(slab['outline']['h'] + d, 3)
        slab['version'] = 22
        slab['v22_hc_return_columns_growth_um'] = d
        rec['slabs'][parent] = dict(growth_um=d, outline=slab['outline'],
                                    direction='down (top kept at the N band)' if parent == 'sp_hc_s'
                                    else 'up (floor kept)')
    rec['hc_corridor_um'] = [CORR_OLD, round(CORR_OLD - total, 3)]
    rec['generator_option'] = '--hc-corr %.2f' % (CORR_OLD - total)
    lay = c['sub_layouts']['ot_s81_hc_cth']
    rows_new, shift = [], 0.0
    for row in lay['rows']:
        row = dict(row, y=round(row['y'] + shift, 3))
        if row['tile'] in ('ctra', 'ctrb'):
            h = 30.24 if row['tile'] == 'ctra' else 25.92
            cell = 'ot_s81_hc_%s_column' % row['tile']
            shift += h - row['h']
            row.update(cell=cell, h=h, w=144.18, per_col=True, x_cols=[0.0, 144.18, 288.36, 432.54],
                       params='COLUMN = column index', replaces='%s 576.72 x %.2f strip' % (row['tile'], row['h']))
            row['tile'] = row['tile'] + '_column[c]'
        rows_new.append(row)
    assert abs(shift - GROW) < 1e-6, shift
    lay['rows'] = rows_new
    lay['outline']['h'] = round(lay['outline']['h'] + GROW, 3)
    lay['note'] = (lay.get('note', '') + ' | v22: ctra/ctrb strips -> 4 return-column leaves each (IDLE-S); merge '
                   'register (rv_delay, clk_merge) must live in column 0 of A (no cth glue).')
    c['version'] = 22
    c['v22_hc_return_columns'] = rec
    c['changelog'].append('v22 candidate: HC four-column return (ctra 4x144.18x30.24, ctrb 4x144.18x25.92), cth +12.96, '
                          'hc_s +129.6 / hc_t +155.52 from the hc_corridor (1226.88).')
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', default='results/arch/hier_contract_1011/s81_v21_gen18.json')
    ap.add_argument('--output', default='results/arch/hier_contract_1011/s81_v22_hc_ret.json')
    a = ap.parse_args()
    out = build(json.loads((ROOT / a.input).read_text()))
    (ROOT / a.output).write_text(json.dumps(out, indent=1) + '\n')
    print(a.output, json.dumps(out['v22_hc_return_columns']))


if __name__ == '__main__':
    main()
