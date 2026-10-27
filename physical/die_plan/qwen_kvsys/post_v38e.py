#!/usr/bin/env python3
"""KV-P8-HUB 10-24: hub_Ei feedthrough jogs spread (ROUTABILITY; COORD via KV-P8 item (3)).

hub_Ei is a pure feedthrough partition: 76 ft slots, 7,219 bits, no logic but 4 fault leaves.  Every straight slot
(E<->W with different in / out window heights) takes check.zroute's Z through the MIDPOINT, so all jogs share the one
column x = W/2, and the stations (face_flops.tcl: station j of k at L*j/k on that route) of the W->E slots that step
DOWN (ft63 / ft64, 1,118 b each, W 775-1209 -> E 354-787) and the E->W slots that step UP (ft24-ft27 / ft30 / ft31,
E 797-1069 -> W 1230-1501) put their jog wires across each other in one ~50 x 50 um spot at the type centre.  Read-only
GRT probe on a copy of the CTS state of trial (b) (Ei_b_grid400s, 5 congestion iterations): total overflow 9,723 with
7.5 % average use (M2 2,175 / M3 2,726 / M4 1,789 / M5 1,312 / M6 936 / M7 785), ALL of it in (600-700, 800-850); the
grid-400 run (g4) did not converge either (9.4-9.8k for 17 iterations).  So: not a capacity problem (worst cut 0.26 at
G0) but a crossing hot spot made by the plan's station sites.

Fix (plan geometry only; no window, width, station-count or cycle change): every jogging straight slot gets its own
jog column x_j and FIRM station sites regs_um (k points, station 0 = the in-window face flop; a 3-station slot puts
stations 1 and 2 at the jog corners (x_j, y_in) / (x_j, y_out) so the column is FIRM, others equal arclength along
window -> (x_j, y_in) -> (x_j, y_out) -> window, as face_flops.tcl would do for that route).  x_j is chosen
by coordinate descent (widest slot first, up to 6 passes), from the 8.64-um lattice inside [BAND, W - BAND], minimising
    sum_bits(route crossings with the routes already placed) + LOAD x sum over 43.2-um bins of the over-0.6 V-demand,
subject to every hop <= ft_station_max_um (750).  Turning slots (N<->W, W<->N) keep their L (check.zroute) and count as
fixed routes; so do straight slots without a jog.  Writes partition_types.kv3_hub_Ei.ft_slots[].regs_um only, and a
per-bin demand table (bits / derated tracks, before -> after) to stderr with --table.
usage: post_v38e.py die_plan.json PLAN_DIR [--table] > die_plan.json"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

G = 8.64
BAND = 3 * G
BIN = 43.2
LOAD = 4.0
TN = 'kv3_hub_Ei'
# derated tracks per um (GRT-0053 of the hub_Ei probe: M3 -25.7 %, M5 -26.0 %, M7 -32.4 %; M4 -25.7 %, M6 -32.2 %);
# M2 / M1 are left to the cells (pin access)
V_TPU = (1 - 0.257) / 0.036 + (1 - 0.260) / 0.048 + (1 - 0.324) / 0.064
H_TPU = (1 - 0.257) / 0.048 + (1 - 0.322) / 0.064


def tools(pdir):
    sys.path.insert(0, str(Path(pdir).resolve().parents[2] / 'tools/die_plan'))
    import check as C
    import schema as S
    return C, S


def segs(pts):
    return [(p, q) for p, q in zip(pts, pts[1:]) if abs(p[0] - q[0]) + abs(p[1] - q[1]) > 1e-6]


def cross(s, t):
    """an axis-parallel H segment crosses a V segment strictly inside both."""
    (a, b), (c, d) = s, t
    if a[1] == b[1] and c[0] == d[0]:
        h, v = (a, b), (c, d)
    elif a[0] == b[0] and c[1] == d[1]:
        h, v = (c, d), (a, b)
    else:
        return False
    x0, x1 = sorted((h[0][0], h[1][0]))
    y0, y1 = sorted((v[0][1], v[1][1]))
    return x0 < v[0][0] < x1 and y0 < h[0][1] < y1


def demand(routes, W, H):
    """{(bx, by): [V bits, H bits]} per BIN x BIN bin.  A route is (pts, bits, span_in, span_out): its first leg
    carries the bundle spread over the in-window span, its last leg over the out-window span, and its jog leg over
    the narrowest width that holds it at 0.6 of the derated tracks (bits / (0.6 x tracks per um))."""
    d = defaultdict(lambda: [0.0, 0.0])
    for pts, w, sp_in, sp_out in routes:
        sg = segs(pts)
        for i, (p, q) in enumerate(sg):
            vert = p[0] == q[0]
            tpu = V_TPU if vert else H_TPU
            sp = sp_in if i == 0 else sp_out if i == len(sg) - 1 else w / (0.6 * tpu)
            sp = max(sp, w / (0.6 * tpu) if i not in (0, len(sg) - 1) else 1e-3)
            c = p[0] if vert else p[1]
            lo, hi = c - sp / 2, c + sp / 2
            a0, a1 = sorted((p[1], q[1]) if vert else (p[0], q[0]))
            for kc in range(max(0, int(lo // BIN)), int(hi // BIN) + 1):
                f = (min(hi, (kc + 1) * BIN) - max(lo, kc * BIN)) / sp
                if f <= 0:
                    continue
                for ka in range(max(0, int(a0 // BIN)), int(min(a1, (W if not vert else H) - 1e-6) // BIN) + 1):
                    key = (kc, ka) if vert else (ka, kc)
                    d[key][0 if vert else 1] += w * f
    return d


def ratios(d):
    cap_v, cap_h = BIN * V_TPU, BIN * H_TPU
    return {k: (v / cap_v, h / cap_h) for k, (v, h) in d.items()}


def plen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def at(pts, s):
    for p, q in zip(pts, pts[1:]):
        L = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if s <= L + 1e-9:
            f = s / L if L else 0.0
            return [round(p[0] + f * (q[0] - p[0]), 3), round(p[1] + f * (q[1] - p[1]), 3)]
        s -= L
    return [round(pts[-1][0], 3), round(pts[-1][1], 3)]


def plan_routes(raw, pdir):
    C, S = tools(pdir)
    P = S.Plan(raw)
    t = P.types[TN]
    W, H = t['outline_um']
    bt = C._bus_targets(P, TN)
    smax = float(P.budgets.get('ft_station_max_um', 750.0))
    span = {}
    insts = {n for n, p_ in P.parts.items() if p_['type'] == TN}
    for pr in P.ports.values():
        for side in ('src', 'dst'):
            if pr[side]['part'] in insts and 'window_um' in pr:
                span[pr[side]['bus']] = abs(pr['window_um'][1] - pr['window_um'][0])
    fixed, free = [], []
    for s in t['ft_slots']:
        s['_sp'] = (span.get(s['name'] + '_i', 1.0), span.get(s['name'] + '_o', 1.0))
        a, b = bt[s['name'] + '_i'][1], bt[s['name'] + '_o'][1]
        z = C.zroute(a, b, s['in_face'], s['out_face'])
        if len(z) == 4 and s['in_face'] in 'EW' and s['out_face'] in 'EW':
            free.append((s, a, b, z))
        else:
            fixed.append((s, a, b, z))
    return P, W, H, smax, fixed, free


def site_regs(route, k):
    """k station sites: a 3-station Z slot puts stations 1 / 2 AT the two jog corners, so the jog column is FIRM (the
    router sees a straight vertical between them); otherwise equal arclength along the route."""
    if k == 3 and len(route) == 4:
        return [[round(p[0], 3), round(p[1], 3)] for p in route[:3]]
    L = plen(route)
    return [at(route, L * j / k) for j in range(k)]


def hops_ok(route, k, smax):
    regs = site_regs(route, k) + [list(route[-1])]
    return all(abs(p[0] - q[0]) + abs(p[1] - q[1]) <= smax + 1e-6 for p, q in zip(regs, regs[1:]))


def assign(raw, pdir, passes=6):
    """coordinate descent: widest slot first, each slot re-chooses its jog column given every other route."""
    P, W, H, smax, fixed, free = plan_routes(raw, pdir)
    base = [(z, s['width']) + s['_sp'] for s, a, b, z in fixed + free]
    cap_v, cap_h = BIN * V_TPU, BIN * H_TPU
    spn = {s['name']: s['_sp'] for s, a, b, z in free}
    xs = [round(BAND + i * G, 6) for i in range(int((W - 2 * BAND) / G) + 1)]
    order = sorted(free, key=lambda e: -e[0]['width'])
    cur = {s['name']: z for s, a, b, z in free}

    def cost_of(name, r, w):
        others = [(z, s['width']) + s['_sp'] for s, a, b, z in fixed] + \
            [(cur[q['name']], q['width']) + q['_sp'] for q, a, b, z in free if q['name'] != name]
        nc = sum(min(w, o[1]) for o in others for s1 in segs(r) for s2 in segs(o[0]) if cross(s1, s2))
        me = (r, w) + spn[name]
        dd = demand(others, W, H)
        mine = demand([me], W, H)
        ov = 0.0
        for key, (v, h) in mine.items():
            v0, h0 = dd[key] if key in dd else (0.0, 0.0)
            ov += max(0.0, (v0 + v) / cap_v - 0.6) - max(0.0, v0 / cap_v - 0.6)
            ov += max(0.0, (h0 + h) / cap_h - 0.6) - max(0.0, h0 / cap_h - 0.6)
        return LOAD * cap_v * ov + 1e-3 * nc, nc
    for _ in range(passes):
        moved = False
        for s, a, b, z in order:
            k = int(s.get('stations', 1))
            best = None
            for x in xs:
                r = [a, (x, a[1]), (x, b[1]), b]
                if not hops_ok(r, k, smax):
                    continue
                c, nc = cost_of(s['name'], r, s['width'])
                c += 1e-3 * abs(x - W / 2)
                if best is None or c < best[0] - 1e-9:
                    best = (c, r, nc)
            if best[1] != cur[s['name']]:
                cur[s['name']], moved = best[1], True
        if not moved:
            break
    out = {s['name']: (cur[s['name']][1][0], cur[s['name']], cost_of(s['name'], cur[s['name']], s['width'])[1])
           for s, a, b, z in free}
    placed = [(z, s['width']) + s['_sp'] for s, a, b, z in fixed] + [(cur[s['name']], s['width']) + s['_sp'] for s, a, b, z in free]
    return P, W, H, base, placed, out


def table(routes, W, H):
    rr = ratios(demand(routes, W, H))
    worst_v = max(rr.items(), key=lambda kv: kv[1][0])
    worst_h = max(rr.items(), key=lambda kv: kv[1][1])
    n_over = sum(1 for v, h in rr.values() if max(v, h) > 0.6)
    xc = sum(min(r1[1], r2[1]) for i, r1 in enumerate(routes) for r2 in routes[i + 1:]
             for s1 in segs(r1[0]) for s2 in segs(r2[0]) if cross(s1, s2))
    return dict(worst_v=(round(worst_v[1][0], 3), [round(worst_v[0][0] * BIN, 1), round(worst_v[0][1] * BIN, 1)]),
                worst_h=(round(worst_h[1][1], 3), [round(worst_h[0][0] * BIN, 1), round(worst_h[0][1] * BIN, 1)]),
                bins_over_0p6=n_over, crossing_bits=xc)


def main():
    raw = json.loads(Path(sys.argv[1]).read_text())
    pdir = sys.argv[2]
    P, W, H, base, placed, out = assign(raw, pdir)
    t = raw['partition_types'][TN]
    for s in t['ft_slots']:
        s.pop('_sp', None)
        if s['name'] in out:
            s['regs_um'] = site_regs(out[s['name']][1], int(s.get('stations', 1)))
    raw['note'] = raw.get('note', '') + (' | v3.8e (KV-P8-HUB 10-24): hub_Ei straight ft slots get their own jog column '
                                         '+ FIRM station regs_um (post_v38e.py, crossing hot spot at the centre)')
    if '--table' in sys.argv:
        print('before', json.dumps(table(base, W, H)), file=sys.stderr)
        print('after ', json.dumps(table(placed, W, H)), file=sys.stderr)
        for n, (x, r, nc) in sorted(out.items(), key=lambda kv: int(kv[0][2:])):
            s = next(q for q in t['ft_slots'] if q['name'] == n)
            print(f"{n}\t{s['width']}\t{s['in_face']}->{s['out_face']}\tjog x {x:.2f}\ty {r[0][1]:.0f}->{r[-1][1]:.0f}"
                  f"\tcross {nc}\tregs {s['regs_um']}", file=sys.stderr)
    json.dump(raw, sys.stdout, indent=1)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
