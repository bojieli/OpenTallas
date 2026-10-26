#!/usr/bin/env python3
"""TYPE-REDUCE-3 10-25: parent re-place probe for the HBM held groups (TYPE-REDUCE-2 face_defer.json).
For each held (module, outline): every member's own table is a template candidate; per member and whole-instance
orient (R0/MX/MY/R180) the instance may also MOVE inside its parent by the L1-optimal shift (median of the per-pin
old-new offsets, snapped to 0.864 um x / 1.08 um y), with partners left where they are.  Reports pins > 405 um
(|old placed pin - new placed pin|, the TYPE-REDUCE-2 metric), the shift, and whether the moved box stays inside the
parent and clear of every other hard core of that parent.  Read-only; run from the repo root."""
import collections, json, re, sys
P = 'physical/die_plan/hbm_arch/B2n'
plan = json.load(open(f'{P}/die_plan.json'))
held = json.load(open('results/type_reduce2_hbm_1025/face_defer.json'))
T = plan['partition_types']
OR = ('R0', 'MX', 'MY', 'R180')
REACH, SX, SY = 405.0, 0.864, 1.08
def xf(o, w, h, x, y):
    if o in ('MY', 'R180'): x = w - x
    if o in ('MX', 'R180'): y = h - y
    return x, y
def load(pf):
    d = json.load(open(f'{P}/{pf}')); d = d['pins'] if isinstance(d, dict) else d
    return {p['name']: (float(p['x']), float(p['y'])) for p in d}
def med(v):
    v = sorted(v); return v[(len(v) - 1) // 2]
def clear(tn, inst, box):
    W, H = T[tn]['outline_um']; x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H: return 'outside parent'
    for hc in T[tn].get('hard_cores') or []:
        if hc['inst'] == inst: continue
        a, b = hc['origin_um']; cw, ch = hc['outline_um']
        if a < x1 and a + cw > x0 and b < y1 and b + ch > y0: return f'overlaps {hc["inst"]}'
    return 'clear'
res = {}
for m in held:
    mem = [(tn, hc) for tn, t in sorted(T.items()) for hc in (t.get('hard_cores') or []) if hc['module'] == m]
    if not mem: continue
    w, h = mem[0][1]['outline_um']
    tabs = [load(hc['pins_file']) for _tn, hc in mem]
    best = None
    for k, tk in enumerate(tabs):
        rows, far_tot, moved = [], 0, 0
        for (tn, hc), tab in zip(mem, tabs):
            cand = []
            for o in OR:
                new = {n: xf(o, w, h, *tk[n]) for n in tab}
                d0 = [abs(tab[n][0] - new[n][0]) + abs(tab[n][1] - new[n][1]) for n in tab]
                f0 = sum(1 for v in d0 if v > REACH)
                dx = round(med(tab[n][0] - new[n][0] for n in tab) / SX) * SX
                dy = round(med(tab[n][1] - new[n][1] for n in tab) / SY) * SY
                d1 = [abs(tab[n][0] - new[n][0] - dx) + abs(tab[n][1] - new[n][1] - dy) for n in tab]
                f1 = sum(1 for v in d1 if v > REACH)
                ox, oy = hc['origin_um']
                cl = clear(tn, hc['inst'], (ox + dx, oy + dy, ox + dx + w, oy + dy + h)) if (dx or dy) else 'clear'
                cand.append((f0, 0, sum(d0), o, 0.0, 0.0, max(d0), 'clear'))
                if cl == 'clear': cand.append((f1, 1, sum(d1), o, dx, dy, max(d1), cl))
                else: cand.append((10**9, 1, sum(d1), o, dx, dy, max(d1), cl))
            f, mv, _s, o, dx, dy, mx, cl = min(cand)
            if f >= 10**9: f = min(c[0] for c in cand if c[0] < 10**9)
            far_tot += f; moved += mv
            rows.append(dict(type=tn, inst=hc['inst'], orient=o, shift_um=[round(dx, 3), round(dy, 3)], pins_over=f,
                             max_um=round(mx, 1), clear=cl,
                             blocked_moves=[f'{c[3]} {c[7]}' for c in cand if c[7] != 'clear']))
        key = (far_tot, moved)
        if best is None or key < best[0]: best = (key, k, rows)
    (far, moved), k, rows = best
    res[f"{m}|{w:g}x{h:g}"] = dict(members=len(mem), template=f'{mem[k][0]}/{mem[k][1]["inst"]}', pins_over_405=far,
                                   moved=moved, rows=rows)
json.dump(res, open(sys.argv[1], 'w'), indent=1)
for g, v in res.items():
    print(f"{g}: {v['members']} members, template {v['template']}, pins>405 {v['pins_over_405']}, moved {v['moved']}")
    for r in v['rows']:
        if r['pins_over'] or r['shift_um'] != [0, 0] or r['blocked_moves']:
            print(f"   {r['type']}/{r['inst']} {r['orient']} shift {r['shift_um']} far {r['pins_over']} max {r['max_um']} {r['blocked_moves'][:2]}")
