#!/usr/bin/env python3
"""H-DIE grants v7 step 3 (2026-10-15 ~19:45, H-SU via coordinator): SFU 4-leaf split.
 (1) sfu_<q><g> (16): cell ot_hgi_sfu_lg_pair_leaf (main 72130e7c9), outline 216 x 216 (was a 500 x 800 request box; the
     leaf is two 1,112-b register ranks), placed in the old box at the edge facing its VM bank pair (vmb_<q><2g>),
     vertically centred.  Pins: lg_* on the face toward the bank pair (M4), c_* on the opposite face (toward the core
     relays, M4), clk/rst_n N M5.  Clock = the pair's LG clock clk_lg[g] (stream 1200 MHz).
 (2) SFU core (~1.6 mm2): NO free 1.6 mm2 rectangle exists anywhere in the compact660_v5 band rows (searched 1250x1300,
     1000x1600, 800x2000, 600x2700, 2000x800, 2700x600 against every plan block and die slot).  PROPOSAL (needs H-SM:
     the SM slot is 11.3 mm2 for ~1.2 mm2 std + 132 small SRAMs in synthesis): shrink the two SM rows that touch each
     band by 420 um on their band side, opening a 400-um strip under/over the band; SFU core = 4000 x 400 at the middle of
     the strip between pairs 1 and 2.  Recorded as sfu_core_request_v7 status PROPOSED; no slot until H-SM answers.
 (3) R per pair: from the proposed core the leaf->core Manhattan distance gives R = ceil(d / 480) - 1 (recorded).
"""
import json, math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
GF = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
P = json.loads((ROOT / 'results/arch/hbm_die_v15/compact660_v5/compact.P.json').read_text())
G = json.loads(GF.read_text()); S = {s['name']: s for s in G['slots']}
L = 216.0
core = {}
for q in ('SW', 'SE', 'NW', 'NE'):
    north = q[0] == 'N'
    sm = [P[f'sm_{q}{k}'] for k in range(8)]
    band_lo = min(P[f'su_{q}{g}']['y'] for g in range(4))
    band_hi = max(P[f'su_{q}{g}']['y'] + P[f'su_{q}{g}']['h'] for g in range(4))
    xs = [P[f'sfu_{q}{g}']['x'] for g in range(4)]
    cx = (sorted(xs)[1] + sorted(xs)[2]) / 2 + 250
    cy = (band_hi + 20 + 200) if north else (band_lo - 20 - 200)
    core[q] = dict(x=round(cx - 2000, 3), y=round(cy - 200, 3), w=4000.0, h=400.0)
rows = []
for s in G['slots']:
    if not s['name'].startswith('sfu_') or s['parent'] != 'die':
        continue
    q, g = s['name'][4:6], int(s['name'][6])
    b, v = P[s['name']], P[f'vmb_{q}{2 * g}']
    toward_e = v['x'] > b['x']
    x = b['x'] + (b['w'] - L if toward_e else 0); y = b['y'] + (b['h'] - L) / 2
    lgf, cf = ('E', 'W') if toward_e else ('W', 'E')
    def span(n):
        c = L / 2; return [round(c - n * 0.048, 3), round(c + n * 0.048, 3)]
    s.update(cell='ot_hgi_sfu_lg_pair_leaf', source='rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv', kind='tile',
             grant='real_rtl_pins_v7', version=7, outline=dict(w=L, h=L),
             origin=dict(x=round(x, 3), y=round(y, 3), orient='R0'),
             clock_domain=f'stream 1200 MHz: clk_lg[{g}] of vm {q}',
             pins=[dict(name='clk', face='N', layer='M5', span_um=[107.952, 108.048]),
                   dict(name='rst_n', face='N', layer='M5', span_um=[108.048, 108.144])] +
                  [dict(name=n, face=lgf, layer='M4', span_um=sp) for n, sp in
                   (('lg_rq[33:0]', [10.0, 13.264]), ('lg_wq[561:0]', [14.0, 67.952]), ('lg_rr[513:0]', [70.0, 119.344]),
                    ('lg_w_done[1:0]', [120.0, 120.192]))] +
                  [dict(name=n, face=cf, layer='M4', span_um=sp) for n, sp in
                   (('c_rq[33:0]', [10.0, 13.264]), ('c_wq[561:0]', [14.0, 67.952]), ('c_rr[513:0]', [70.0, 119.344]),
                    ('c_w_done[1:0]', [120.0, 120.192]))])
    for p in s['pins']:
        p['offset'] = round(sum(p['span_um']) / 2, 3)
    c = core[q]; d = abs(x + L / 2 - (c['x'] + c['w'] / 2)) + abs(y + L / 2 - (c['y'] + c['h'] / 2))
    rows.append(dict(leaf=s['name'], dist_um=round(d), R=max(0, math.ceil(d / 480) - 1)))
G['sfu_core_request_v7'] = dict(status='PROPOSED (needs H-SM: shrink the band-side SM rows by 420 um)', core_boxes=core,
                                leaf_R=rows, R_padded=max(r['R'] for r in rows),
                                note='core LG_PATH = 1 + max R; all pairs padded to equal R (H-SU rule)')
G['grants_v7_1945'] = dict(date='2026-10-15', owner='H-DIE', changes=['sfu leaves x16 216x216 real RTL pins',
                                                                       'SFU core: no free area, PROPOSED strip (H-SM)'])
GF.write_text(json.dumps(G, indent=1) + '\n')
print(json.dumps(G['sfu_core_request_v7'], indent=0)[:1500])
