#!/usr/bin/env python3
"""HBM-MU-QUAD-3 delta (L2): off-lattice hard cores that the per-core snap of delta.py could not move (tightly packed
quad buddies at 8.64-um gaps with a common 4.32-um residue) are moved as RIGID CLUSTERS: connected components of the
remaining off-lattice cores (boxes within one lattice step) shift by one common delta onto the lattice, if no member
overlaps a non-member or leaves the outline; station ends / taps on members move with them.  Usage: lat2.py PLAN_DIR"""
import json, math, sys, pathlib, hashlib
pd = pathlib.Path(sys.argv[1]); P = json.load(open(pd / 'die_plan.json')); G = float(P['die']['grid_um'])
rep = json.load(open(pd / 'delta_report.json'))
off = lambda v: abs(v / G - round(v / G)) > 1e-6  # noqa: E731
def box(h, d=(0, 0)):
    x, y = h['origin_um']; dx, dy = h.get('track_offset_um', [0, 0])
    return (x + dx + d[0], y + dy + d[1], x + dx + d[0] + h['outline_um'][0], y + dy + d[1] + h['outline_um'][1])
ov = lambda a, b: a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6  # noqa: E731
near = lambda a, b: a[0] < b[2] + G + 1e-6 and b[0] < a[2] + G + 1e-6 and a[1] < b[3] + G + 1e-6 and b[1] < a[3] + G + 1e-6  # noqa: E731
out = dict(moved=[], fail=[])
for tn, t in P['partition_types'].items():
    hc = t.get('hard_cores', [])
    bad = [h for h in hc if off(h['origin_um'][0]) or off(h['origin_um'][1])]
    if not bad:
        continue
    comp, seen = [], set()
    for h in bad:
        if id(h) in seen: continue
        st, c = [h], []
        seen.add(id(h))
        while st:
            u = st.pop(); c.append(u)
            for v in bad:
                if id(v) not in seen and near(box(u), box(v)):
                    seen.add(id(v)); st.append(v)
        comp.append(c)
    W, H = t['outline_um']
    for c in comp:
        ids = {id(h) for h in c}
        others = [box(h) for h in hc if id(h) not in ids]
        h0 = c[0]; ox, oy = h0['origin_um']
        cands = sorted({(fx(ox / G) * G - ox, fy(oy / G) * G - oy) for fx in (math.floor, math.ceil) for fy in (math.floor, math.ceil)},
                       key=lambda d: abs(d[0]) + abs(d[1]))
        done = None
        for d in cands:
            d = (round(d[0], 3), round(d[1], 3))
            if any(off(h['origin_um'][0] + d[0]) or off(h['origin_um'][1] + d[1]) for h in c):
                continue
            bs = [box(h, d) for h in c]
            if any(b[0] < -1e-6 or b[1] < -1e-6 or b[2] > W + 1e-6 or b[3] > H + 1e-6 for b in bs):
                continue
            if any(ov(b, o) for b in bs for o in others):
                continue
            done = d; break
        if done is None:
            # fallback: members one by one (each its own nearest lattice delta), against the current boxes
            ok_all = True
            for h in c:
                cur = [box(g) for g in hc if g is not h]
                ox, oy = h['origin_um']
                ds = sorted({(round(fx(ox / G) * G - ox, 3), round(fy(oy / G) * G - oy, 3)) for fx in (math.floor, math.ceil)
                             for fy in (math.floor, math.ceil)}, key=lambda d: abs(d[0]) + abs(d[1]))
                d = next((d for d in ds if not any(ov(box(h, d), o) for o in cur)
                          and box(h, d)[0] >= -1e-6 and box(h, d)[1] >= -1e-6 and box(h, d)[2] <= W + 1e-6 and box(h, d)[3] <= H + 1e-6), None)
                if d is None:
                    ok_all = False; out['fail'].append(dict(type=tn, core=h['inst'])); continue
                b0 = box(h)
                h['origin_um'] = [round(ox + d[0], 3), round(oy + d[1], 3)]
                for tp in t.get('clock', {}).get('taps', []):
                    if tp['name'] == h['inst'] or tp['name'].startswith(h['inst'] + '.'):
                        tp['xy'] = [round(tp['xy'][0] + d[0], 4), round(tp['xy'][1] + d[1], 4)]
                n = 0
                for s in t.get('internal_stations', []):
                    for key in ('from_um', 'to_um'):
                        p = s[key]
                        if b0[0] - 1e-3 <= p[0] <= b0[2] + 1e-3 and b0[1] - 1e-3 <= p[1] <= b0[3] + 1e-3:
                            s[key] = [round(p[0] + d[0], 4), round(p[1] + d[1], 4)]; n += 1
                out['moved'].append(dict(type=tn, d=d, cores=1, station_ends=n, member_fallback=h['inst']))
            continue
        bs0 = [box(h) for h in c]
        for h in c:
            h['origin_um'] = [round(h['origin_um'][0] + done[0], 3), round(h['origin_um'][1] + done[1], 3)]
            for tp in t.get('clock', {}).get('taps', []):
                if tp['name'] == h['inst'] or tp['name'].startswith(h['inst'] + '.'):
                    tp['xy'] = [round(tp['xy'][0] + done[0], 4), round(tp['xy'][1] + done[1], 4)]
        n = 0
        for s in t.get('internal_stations', []):
            for key in ('from_um', 'to_um'):
                p = s[key]
                if any(b[0] - 1e-3 <= p[0] <= b[2] + 1e-3 and b[1] - 1e-3 <= p[1] <= b[3] + 1e-3 for b in bs0):
                    s[key] = [round(p[0] + done[0], 4), round(p[1] + done[1], 4)]; n += 1
        out['moved'].append(dict(type=tn, d=done, cores=len(c), station_ends=n))
rep['L2_clusters'] = out
s = json.dumps(P, indent=1) + '\n'
(pd / 'die_plan.json').write_text(s); (pd / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(pd / 'delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], moved=[(m['type'], m['d'], m['cores']) for m in out['moved']], fail=out['fail'])))
