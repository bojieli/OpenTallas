# S81-LEAF-CYC quad2 (COORD 11-11: vn->quad <= 405 um per segment, Manhattan as G0 _hops_ok): per (type, quad, hi|ho)
# ONE shared site pair [m, q] (= the two shared stages kit_istations sites at the entries' centroid), to_um moved to the
# permuted lane pin (same local pin, new origin/orient).  q = 10-um grid point minimising the worst hop (vn pins -> m,
# m -> q, q -> lane pins), ties -> shortest lane fan-out; m = Manhattan minimax centre of the vn pins and q.  Reports the worst hop per type and every hop > 405.
import json, re, sys
plan, permf, sitesf, out = sys.argv[1:5]
G0 = sys.argv[5] if len(sys.argv) > 5 else None   # g0_report.json of a previous apply: uncovered vn->lane bundles to add
QMAX, LIM = 390.0, 405.0
P = json.load(open(plan))['partition_types']; perm = json.load(open(permf)); S = json.load(open(sitesf))
RX = re.compile(r"^core:u_lf\.u_vn\.u_[ab]\.(hq_|hr_|hw_)\w+\|(?:core:)?u_lf\.u_vp\.g_ln\[(\d+)\]\.u_l$")
M = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def loc(p, h):        # global pin -> module-local
    (ox, oy), (w, hh), o = h['origin_um'], h['outline_um'], h.get('orient', 'R0')
    x, y = p[0] - ox, p[1] - oy
    return (w - x if o in ('MY', 'R180') else x, hh - y if o in ('MX', 'R180') else y)


def glob(lc, h):
    (ox, oy), (w, hh), o = h['origin_um'], h['outline_um'], h.get('orient', 'R0')
    return [round(ox + (w - lc[0] if o in ('MY', 'R180') else lc[0]), 3),
            round(oy + (hh - lc[1] if o in ('MX', 'R180') else lc[1]), 3)]


MISS = {}
if G0 and G0 != 'ALL':
    MR = re.compile(r"type (\S+): internal core bundle (u_lf\.u_vn\.u_[ab])\.((?:hq_|hr_|hw_)\w+) -> core:(u_lf\.u_vp\.g_ln\[(\d+)\]\.u_l) >=")
    for x in json.load(open(G0))['findings']:
        mm_ = MR.search(x['msg'])
        if mm_:
            MISS.setdefault(mm_.group(1), set()).add((mm_.group(2), mm_.group(3), int(mm_.group(5))))
res, worst, fail, seg = {}, {}, [], {}
added = {}
for t, sites in S.items():
    ln = {int(h['inst'].split('g_ln[')[1].split(']')[0]): h for h in P[t]['hard_cores'] if '.g_ln[' in h['inst']}
    pr = perm[t]['perm']
    es = [dict(e) for e in P[t].get('internal_stations', [])]
    tpl = {}
    for e in es:
        m = RX.match(e['conn'])
        if m:
            tpl.setdefault(e['conn'].split('|')[0], (e, int(m.group(2))))
    want = MISS.get(t, set())
    if G0 == 'ALL':      # every vn h-port x every lane: the quad2 RTL stations all 16 lanes of each port
        have = {e['conn'] for e in es}
        want = {(k[5:].rsplit('.', 1)[0], k.rsplit('.', 1)[1], l) for k in tpl for l in range(16)
                if '%s|core:u_lf.u_vp.g_ln[%d].u_l' % (k, l) not in have}
    for vi, port, lane in sorted(want):
        k = 'core:%s.%s' % (vi, port)
        if k not in tpl:
            raise SystemExit('no template entry for %s %s' % (t, k))
        e0, l0 = tpl[k]; e = dict(e0)
        e['conn'] = '%s|core:u_lf.u_vp.g_ln[%d].u_l' % (k, lane)
        e['to_um'] = glob(loc(e0['to_um'], ln[l0]), ln[lane])          # same local pin, OLD slot of lane (moved below)
        e['capture'] = 'u_lf.u_vp.g_ln[%d].u_l' % lane if 'g_ln[' in str(e0.get('capture', '')) else e0.get('capture')
        e['launch'] = e0.get('launch') if 'g_ln[' not in str(e0.get('launch', '')) else 'u_lf.u_vp.g_ln[%d].u_l' % lane
        e['note'] = 'S81-LEAF-CYC 11-11: vn->lane bundle over reach after the lane permutation'
        es.append(e); added[t] = added.get(t, 0) + 1
    grp = {}
    for e in es:
        m = RX.match(e['conn'])
        if not m:
            continue
        lane = int(m.group(2)); c = 'ho' if m.group(1) == 'hw_' else 'hi'
        e['to_um'] = glob(loc(e['to_um'], ln[lane]), ln[pr[lane]])     # lane l now sits in slot pr[l]
        grp.setdefault((lane // 4, c), []).append(e)
    for (g, c), ge in grp.items():
        Q0 = sites[g]['site_um']; w = sum(int(e.get('bits', 1)) for e in ge)
        V = [sum(e['from_um'][i] * int(e.get('bits', 1)) for e in ge) / w for i in (0, 1)]
        F = [e['from_um'] for e in ge]; T = [e['to_um'] for e in ge]

        def center(pts):   # Manhattan minimax centre = Chebyshev centre in (x+y, x-y)
            us = [p[0] + p[1] for p in pts]; vs = [p[0] - p[1] for p in pts]
            u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
            return [(u + v) / 2, (u - v) / 2], max(max(us) - min(us), max(vs) - min(vs)) / 2

        def cost(q):       # worst of: vn pins -> m, m -> q (m = centre of vn pins + q), q -> lane pins
            return max(center(F + [q])[1], max(M(q, t) for t in T))
        xs = [p[0] for p in F + T]; ys = [p[1] for p in F + T]
        cand = [[min(xs) + 10 * i, min(ys) + 10 * j] for i in range(int((max(xs) - min(xs)) / 10) + 2)
                for j in range(int((max(ys) - min(ys)) / 10) + 2)]
        cq = min(cost(q) for q in cand)
        # among the near-optimal q keep the one closest to the quad centroid (shortest lane fan-out)
        q = min((q for q in cand if cost(q) <= max(cq, QMAX)), key=lambda q: (max(M(q, t) for t in T), M(q, Q0)))
        q = [round(q[0], 3), round(q[1], 3)]
        mm = [round(x, 3) for x in center(F + [q])[0]]
        for e in ge:
            e['regs_um'] = [mm, q]
            e['note'] = (e.get('note', '') + ' | S81-LEAF-CYC 11-11: REALISED quad2 stations (ot_s81sl_leaf CS_H%s_D 2 GS 2 G 4), '
                         'quad %d: stage sites vn pins/quad minimax point + quad site, +2 cycles declared'
                         % ('I' if c == 'hi' else 'O', g)).lstrip(' |')
            pts = [e['from_um'], mm, q, e['to_um']]
            hs = [M(a, b) for a, b in zip(pts, pts[1:])]
            s = seg.setdefault(t, [0, 0, 0])
            for i in range(3):
                s[i] = max(s[i], hs[i])
            worst[t] = max(worst.get(t, 0), max(hs))
            if max(hs) > LIM:
                fail.append((t[13:], g, c, round(max(hs))))
    res[t] = es
json.dump(res, open(out, 'w'))
print('worst Manhattan hop um [vn->m, m->q, q->lane]:', {k[13:]: [round(x) for x in v] for k, v in seg.items()})
print('added entries', added)
print('hops over', LIM, ':', len(fail), sorted(set(fail))[:40])
