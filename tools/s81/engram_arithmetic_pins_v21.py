#!/usr/bin/env python3
"""v21 Engram MIX arithmetic leaf pins (S-ELEM-C 2026-10-15): the v20 rule (registered operands/control on S,
registered arithmetic outputs on N, independent W stream clock/reset, M5 at 2 tracks) on outlines RIGHT-SIZED from
the measured mapped cell area (results/arch/s81_mix4_sizing_1015/summary.json, target util ~0.5) instead of one
181.44 x 129.6 frame for every master (chunk8 sat at 14 %, MIX4 would have needed ~3.1 mm2), plus the seventh
arithmetic master ot_s81_engram_sum (no v20 contract).  Heights are whole 0.27 um rows, widths whole 0.054 um sites.
"""
import json, hashlib
from pathlib import Path
import v19_pins_1014 as V
R = Path(__file__).resolve().parents[2]
INVENTORY = R / 'results/rtl/s81_engram_mix_1014/leaf_inventory.json'
SIZING = R / 'results/arch/s81_mix4_sizing_1015/summary.json'
# r2 (05:15 gates): ORFS synthesis area is 1.26-1.38x the mapped-root area (util 67-72 % on r1 outlines, 3 gate
# FAILs > 70 %); outlines re-sized to util ~0.51 of the ORFS-synthesised area (heights whole 2.16 um)
OUTLINE = {'mul4': [181.44, 120.96], 'add8': [181.44, 99.36], 'norm': [181.44, 95.04], 'sigmoid': [181.44, 110.16],
           'chunk8': [90.72, 90.72], 'sum': [90.72, 99.36], 'signed_sqrt': [64.8, 43.2]}
SYNTH = {'mul4': 11242, 'add8': 9276, 'norm': 8833, 'sigmoid': 10186, 'chunk8': 4265, 'sum': 4585, 'signed_sqrt': 1155}


def main():
    inv = json.loads(INVENTORY.read_text()); siz = json.loads(SIZING.read_text())
    area = {r['top']: r['area_um2'] for r in siz['root_rows']}
    out = R / 'physical/s81_die_pins/v21_engram_arithmetic'; out.mkdir(exist_ok=True); receipt = []
    for suffix, ol in OUTLINE.items():
        name = 'ot_s81_engram_' + suffix; ip = inv[name]; pp = {}; cursor = {'S': 4.032, 'N': 4.032}
        for p, v in ip['ports'].items():
            n = v['bits']
            if p in ['clk', 'arst_n']:
                continue
            f = 'S' if v['direction'] == 'input' else 'N'; start = cursor[f]
            pp[p] = [[f, 'M5', round(start + .096 * i, 3), .084] for i in range(n)]; cursor[f] += .096 * n + .96
        assert max(cursor.values()) <= ol[0] - 4.0, (name, cursor, ol)
        pp['clk'] = [['W', 'M4', 4.032, .084]]; pp['arst_n'] = [['W', 'M4', 4.992, .084]]
        V.write(out, name, ol, pp, 'clk', 'registered operands/control S; registered arithmetic outputs N; independent W stream root/reset',
                'v21_engram_arithmetic', {'source': 'tools/s81/engram_arithmetic_pins_v21.py', 'source_parameters': ip['parameters'],
                                          'clock_entries': {'stream': ['clk']}, 'reset_entries': {'stream': ['arst_n']},
                                          'adoption': 'actual source native CTS/TT/FF/DRC required; no parent/reach/calendar qualification implied'})
        assert {p: len(v) for p, v in pp.items()} == {p: v['bits'] for p, v in ip['ports'].items()}
        a = area[name]
        receipt.append({'master': name, 'outline_um': ol, 'mapped_area_um2': a, 'orfs_synth_area_um2': SYNTH[suffix],
                        'util': round(SYNTH[suffix] / (ol[0] * ol[1]), 3),
                        'port_bits': sum(v['bits'] for v in ip['ports'].values()), 'params': ip['parameters']})
    (out / 'receipt.json').write_text(json.dumps({'source_inventory': str(INVENTORY.relative_to(R)),
        'inventory_sha256': hashlib.sha256(INVENTORY.read_bytes()).hexdigest(), 'sizing_sha256': hashlib.sha256(SIZING.read_bytes()).hexdigest(),
        'masters': receipt, 'supersedes': 'v20_engram_arithmetic outlines (one 181.44x129.6 frame); same pin rule',
        'qualification': 'native leaf assignment only; parent/reach/calendar open'}, indent=1) + '\n')
    for r in receipt: print(r['master'], r['outline_um'], r['util'])


if __name__ == '__main__':
    main()
