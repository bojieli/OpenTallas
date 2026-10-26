#!/usr/bin/env python3
"""LG local (S) faces -> SU / SFU / HC engine ports: reach demand per quadrant (GEO-H, 2026-10-15).

For every VM bank of a whole-die candidate the three-stage LG chain is re-placed beside the actual bank
pins (ODB readback: RG7/WG3 for NW/NE, RG5/WG1 for SW/SE) with the chosen bank slot plan, using the
CLOSED leaf views: stage 0 = hfd_vm_lg_su10 (SU, read/write return 10/7), stage 1 = hfd_vm_lg_sfu14
(SFU, 14/11), stage 2 = ot_hbm_vm_lg_static_bank (HC tap, 18/15); R0 only, abutted westward with 5.4 um
clearance. LG0 origin: best separable-Manhattan spot with >= 5.4 um clearance to every candidate box
(all LG prototypes re-placed) and to chains already placed for earlier banks.

Each stage's local face (local_rq/wq/rr/w_done + local_read/local_write, 558 bits) must reach one client
engine per quadrant (global graph: SU_<q>, SFU_<q>, HC_<q> vm_*[bank]); every engine has geometry=null
and no source binding. The demand is therefore reported as the best single port point (median) and the
minimum number of contiguous bank groups k whose point-ports keep every local bit <= the reach limit.
A point port is optimistic (real engine faces spread the pins). No route/timing/PG/cut claim.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_vm_lg_face_search as fs
from hbm_ne_att_lg_tradeoff import axis_cost, blocked, CLR

LOCAL = ['local_rq', 'local_wq', 'local_rr', 'local_w_done', 'local_read', 'local_write']

def place_chain(pairs, bank_xy, bank_wh, leaf, obstacles, span=700.0, grid=2.16):
    (X, Y), (BW, BH), (LW, LH) = bank_xy, bank_wh, leaf
    gx = np.arange(-span - 3 * LW, BW + span, grid); gy = np.arange(-span, BH + span, grid)
    rel = [(o[0] - X, o[1] - Y, o[2] - X, o[3] - Y) for o in obstacles
           if o[0] < X + BW + span + 600 and o[2] > X - span - 600 and o[1] < Y + BH + span + 600 and o[3] > Y - span - 600]
    bad = blocked(gx - 2 * (LW + CLR), gy, 3 * LW + 2 * CLR, LH, rel + [(0, 0, BW, BH)])
    c = axis_cost([b[0] - l[0] for b, l in pairs], gx)[:, None] + axis_cost([b[1] - l[1] for b, l in pairs], gy)[None, :]
    c = np.where(bad, np.inf, c); i, j = np.unravel_index(np.argmin(c), c.shape)
    lx, ly = gx[i], gy[j]; d = [abs(b[0] - l[0] - lx) + abs(b[1] - l[1] - ly) for b, l in pairs]
    return (X + lx, Y + ly), sum(d), max(d)

def median_port(pts):
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts]); mx, my = np.median(xs), np.median(ys)
    d = np.abs(xs - mx) + np.abs(ys - my); return (float(mx), float(my)), float(d.sum()), float(d.max())

def min_groups(per_bank, order, limit):
    # fewest contiguous groups (in column order) whose median point-port keeps every bit within limit
    n = len(order); best = {0: (0, [])}
    for e in range(1, n + 1):
        for s in range(e):
            if s not in best: continue
            pts = [p for b in order[s:e] for p in per_bank[b]]
            if median_port(pts)[2] <= limit:
                cand = (best[s][0] + 1, best[s][1] + [order[s:e]])
                if e not in best or cand[0] < best[e][0]: best[e] = cand
    return best.get(n, (None, None))

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--su-lef', required=True); ap.add_argument('--sfu-lef', required=True); ap.add_argument('--hc-lef', required=True)
    ap.add_argument('--rg7-pins', required=True); ap.add_argument('--rg5-pins', required=True)
    ap.add_argument('--candidate', action='append', required=True, help='json[:name]')
    ap.add_argument('--plan', action='append', default=[], help='Q=RG,WSLOT e.g. NW=0,wq1')
    ap.add_argument('--limit-um', type=float, default=500.0); ap.add_argument('--out', required=True); a = ap.parse_args()
    lefs = [fs.lef_pins(p) for p in (a.su_lef, a.sfu_lef, a.hc_lef)]; leaf = lefs[0][0]; LW, LH = leaf
    banks = {'RG7': fs.bank_pins(a.rg7_pins), 'RG5': fs.bank_pins(a.rg5_pins)}
    plan = {'NW': (0, 'wq0'), 'NE': (0, 'wq0'), 'SW': (0, 'wq0'), 'SE': (0, 'wq0')}
    for p in a.plan: q, v = p.split('='); rg, w = v.split(','); plan[q] = (int(rg), w)
    out = dict(schema='opentallas.hbm.geo.lg_local_engine_reach.v1', limit_um=a.limit_um, plan={q: list(v) for q, v in plan.items()},
               inputs=dict(su_lef=a.su_lef, su_sha=fs.sha(a.su_lef), sfu_lef=a.sfu_lef, sfu_sha=fs.sha(a.sfu_lef), hc_lef=a.hc_lef,
                           hc_sha=fs.sha(a.hc_lef), rg7_pins=a.rg7_pins, rg7_sha=fs.sha(a.rg7_pins), rg5_pins=a.rg5_pins, rg5_sha=fs.sha(a.rg5_pins)),
               results={})
    for spec in a.candidate:
        path, _, want = spec.partition(':'); raw = json.loads(Path(path).read_text())
        cands = raw['candidates'] if 'candidates' in raw else [raw]
        for cand in cands:
            if want and cand['name'] != want: continue
            B = cand['boxes']; obst = [(b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']) for n, b in B.items()
                                       if b['role'] != 'LG_prototype' and not n.startswith('VM_')]
            vms = [(b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h']) for n, b in B.items() if n.startswith('VM_')]
            res = {}
            for q in ('SW', 'SE', 'NW', 'NE'):
                (BW, BH), bp = banks['RG7' if q.startswith('N') else 'RG5']; rg, w = plan[q]
                pairs = fs.plan_pairs(bp, lefs[0][1], rg, w); per = {s: {} for s in range(3)}; link = []; placed = []
                for b in range(8):
                    bx = B[f'VM_{q}_{b}']; assert abs(bx['w'] - BW) < 1e-6 and abs(bx['h'] - BH) < 1e-6, (q, bx, BW, BH)
                    others = [v for v in vms if abs(v[0] - bx['x']) > 1e-6 or abs(v[1] - bx['y']) > 1e-6]
                    (ox, oy), sm, mx = place_chain(pairs, (bx['x'], bx['y']), (BW, BH), leaf, obst + others + placed)
                    placed.append((ox - 2 * (LW + CLR), oy, ox + LW, oy + LH)); link.append((sm, mx))
                    for s in range(3):
                        sx = ox - s * (LW + CLR); lp = lefs[s][1]
                        per[s][b] = [(sx + xy[0], oy + xy[1]) for n, xy in lp.items() if n.split('[')[0] in LOCAL]
                order = sorted(range(8), key=lambda b: (round(B[f'VM_{q}_{b}']['x']), B[f'VM_{q}_{b}']['y']))
                eng = {}
                for s, name in enumerate(('SU', 'SFU', 'HC_tap')):
                    pts = [p for b in range(8) for p in per[s][b]]; port, sm, mx = median_port(pts)
                    k, groups = min_groups(per[s], order, a.limit_um)
                    eng[name] = dict(bits=len(pts), single_point_port=[round(port[0], 1), round(port[1], 1)], single_port_bit_um=round(sm, 1),
                                     single_port_max_um=round(mx, 1), min_groups_within_limit=k, groups=groups)
                res[q] = dict(bank_slot_plan=[f'rq{rg}', f'rr{rg}', w, fs.wdone(w)], vm_lg_link_bit_um=round(sum(x[0] for x in link), 1),
                              vm_lg_link_max_um=round(max(x[1] for x in link), 1), chains_abs=[[round(v, 3) for v in r] for r in placed], engines=eng)
                print(cand['name'], q, res[q]['bank_slot_plan'], res[q]['vm_lg_link_bit_um'], res[q]['vm_lg_link_max_um'],
                      {n: (e['single_port_max_um'], e['min_groups_within_limit']) for n, e in eng.items()})
            out['results'][cand['name']] = res
    out['scope'] = ('engine ports are idealised points (median); engines have no geometry/source binding in the global graph; '
                    'LG chains placed greedily bank by bank; no route/timing/PG/cut claim')
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')

if __name__ == '__main__': main()
