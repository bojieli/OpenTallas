#!/usr/bin/env python3
"""S81-LP-3 (2026-10-29) ESTIMATE BEFORE BUILD (12.14b) for the 3 cut LP parents with 4 hard lane children
(s_0S_LP lepw_mus, s_0N_LP lepw_mu, s_7N_LP lepe_mu).  No build: reads die_plan.json bus / ft windows and the lane
kit geometry (variant B 302.4 x 630.72, link pins rx 515 @0.24 from x=6.156, tx 512 right-aligned), and reports
  * the lane-row fit along the link face with the type's plan windows as they are (ft corridors on the same face);
  * the sideways landing distance |window bit x - lane pin x| summed over the rx/tx bits (current windows);
  * a proposed layout (lanes + one ft street) and the moved windows (coll_iK under lane K rx, coll_oK under lane K tx).
    python3 parent_estimate.py OUT.json
"""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
p = json.load(open(R / 'physical/die_plan/s81/die_plan.json'))
LW, LH, ST = 302.4, 630.72, 0.24
RX0, NRX, NTX = 6.156, 515, 512
TX0 = LW - 4.32 - 1.2 - 511 * ST
TYPES = {'s_0S_LP': 'dsdv_slice_lepw_mus_LP__t2', 's_0N_LP': 'dsdv_slice_lepw_mu_LP__t2', 's_7N_LP': 'dsdv_slice_lepe_mu_LP__t2'}
EDGE = 4.32
out = {}
for inst, t in TYPES.items():
    T = p['partition_types'][t]
    W, H = T['outline_um']
    coll = {b['name']: b for b in T['buses'] if b['name'].startswith('coll_')}
    face = {b['face'] for b in coll.values()}
    assert len(face) == 1
    face = face.pop()
    # every other window on the link face (ft + non-lane buses) that a lane row would cover
    other = [(b['name'], b['window_um']) for b in T['buses'] if b['face'] == face and not b['name'].startswith('coll_')]
    for f in T['ft_slots']:
        if face in (f['in_face'], f['out_face']):
            other.append((f['name'], f['in_window_um'] if f['in_face'] == face else f['out_window_um']))
    other.sort(key=lambda o: o[1][0])
    # current layout: lane K centred under its coll_iK..coll_oK window pair is impossible when they are not adjacent;
    # take the best uniform 4-across row (lanes abutting streets s) and measure the sideways landing distance
    s = (W - 2 * EDGE - 4 * LW) / 3
    xs = [EDGE + k * (LW + s) for k in range(4)]
    side = 0.0
    for k, x in enumerate(xs):
        wi, wo = coll[f'coll_i{k}']['window_um'], coll[f'coll_o{k}']['window_um']
        ci, co = (wi[0] + wi[1]) / 2, (wo[0] + wo[1]) / 2
        side += abs(ci - (x + RX0 + NRX * ST / 2)) * NRX + abs(co - (x + TX0 + NTX * ST / 2)) * NTX
    blocked = [o for o in other if any(x < o[1][1] and o[1][0] < x + LW for x in xs)]
    # proposed: L0 L1 | street (all link-face ft/other windows, packed) | L2 L3
    need = sum(o[1][1] - o[1][0] for o in other)
    street = max(need + 2 * 6.0, 0) if other else 0.0
    rest = W - 2 * EDGE - 4 * LW - street
    g = rest / 3 if other else rest / 3
    px = [EDGE, EDGE + LW + g]
    sx = px[1] + LW + g / 2
    px += [sx + street + g / 2, sx + street + g / 2 + LW + g]
    assert px[3] + LW <= W - EDGE + 1e-6, (inst, px)
    moved = {}
    for k, x in enumerate(px):
        moved[f'coll_i{k}'] = [round(x + RX0, 3), round(x + RX0 + (NRX - 1) * ST, 3)]
        moved[f'coll_o{k}'] = [round(x + TX0, 3), round(x + TX0 + (NTX - 1) * ST, 3)]
    o0 = sx + 6.0
    street_windows = {}
    for n, (a, b) in other:
        street_windows[n] = [round(o0, 3), round(o0 + (b - a), 3)]
        o0 += b - a
    side_new = 0.0   # windows exactly under the lane pins: the landing is vertical only
    lane_area = 4 * LW * LH
    out[inst] = dict(type=t, outline_um=[W, H], link_face=face, lane_orient='R0' if face == 'S' else 'MX',
                     uniform_row_x_um=[round(x, 2) for x in xs], uniform_street_um=round(s, 2),
                     link_face_other_windows=other, uniform_row_covers=[o[0] for o in blocked],
                     sideways_bit_um_current=round(side), sideways_mean_um_per_bit=round(side / (4 * (NRX + NTX)), 1),
                     proposed=dict(lane_x_um=[round(x, 3) for x in px], lane_gap_um=round(g, 2),
                                   street_um=[round(sx, 3), round(sx + street, 3)], street_width_um=round(street, 2),
                                   moved_coll_windows=moved, moved_street_windows=street_windows,
                                   sideways_bit_um=side_new),
                     lane_area_mm2=round(lane_area / 1e6, 4), parent_area_mm2=round(W * H / 1e6, 4),
                     area_left_mm2=round((W * H - lane_area) / 1e6, 4))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k, v in out.items():
    print(k, v['link_face'], 'covers', v['uniform_row_covers'], 'sideways mean um/bit', v['sideways_mean_um_per_bit'],
          'proposed lanes', v['proposed']['lane_x_um'], 'gap', v['proposed']['lane_gap_um'], 'street', v['proposed']['street_um'])
