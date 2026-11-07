#!/usr/bin/env python3
"""S81-TYPES-2 leaf vs/ve_m facing form, per row (from TYPE-CONS-5 leafmv.py, pilot t27/t42 vM).
Rule: vs pin edge faces ve_m pin edge, same mirror state, vs_x = ve_m_x -40 (R0/MX) or +40 (MY/R180), gap >= 17.28.
Opposite mirror: flip vs in x.  No site at the ideal x: slide d um and require gap >= 0.21*d + 4 (5.3 pins/um, 25.5 M6 tr/um).
vn_a/b within 24 um of a VP macro: shift vn away to 41 um (t27 vN).  usage: leaf_facing.py PLAN TYPE -> one JSON line"""
import json, re, sys
G = 8.64; EDGE = 4.32; MGAP = 8.64
plan = json.load(open(sys.argv[1])); T = sys.argv[2]; t = plan['partition_types'][T]; W, H = t['outline_um']
hc = {h['inst'].split('.', 1)[-1]: dict(o=list(h['origin_um']), s=list(h['outline_um']), r=h['orient'], inst=h['inst']) for h in t['hard_cores']}
BUS = {('u_ve.u_m', 'u_vs'): 742, ('u_vn.u_a', 'u_vn.u_b'): 398, ('u_ve.u_m', 'u_ve.u_s'): 386, ('u_vq', 'u_vs'): 271, ('u_vs', 'u_vsw'): 265, ('u_ve.u_s', 'u_vs'): 99}
sites = set()
for s in t.get('ft_slots', []):
    for st in s.get('bit_sites_um') or []:
        for p in st:
            sites.add((int(p[0] // G), int(p[1] // G)))
sites = [(a * G, b * G, (a + 1) * G, (b + 1) * G) for a, b in sites]
def rect(o, s): return (o[0], o[1], o[0] + s[0], o[1] + s[1])
def inter(a, b, g=0): return a[0] < b[2] + g and b[0] < a[2] + g and a[1] < b[3] + g and b[1] < a[3] + g
def free(n, o, pos):
    r = rect(o, hc[n]['s'])
    if r[0] < EDGE or r[1] < EDGE or r[2] > W - EDGE or r[3] > H - EDGE: return False
    for m, p in pos.items():
        if m != n and inter(r, rect(p, hc[m]['s']), MGAP - 0.01): return False
    return not any(inter(r, x) for x in sites)
def cen(n, p): return (p[n][0] + hc[n]['s'][0] / 2, p[n][1] + hc[n]['s'][1] / 2)
def cost(p):
    return sum(w * (abs(cen(a, p)[0] - cen(b, p)[0]) + abs(cen(a, p)[1] - cen(b, p)[1])) for (a, b), w in BUS.items())
snap = lambda v: round(v / G) * G
FLIP = {'R0': 'MY', 'MY': 'R0', 'MX': 'R180', 'R180': 'MX'}
M, S = 'u_ve.u_m', 'u_vs'
rm, rs = hc[M]['r'], hc[S]['r']
mir = rm in ('MY', 'R180'); flip = mir != (rs in ('MY', 'R180')); up = rm in ('R0', 'MY')
assert up == (rs in ('R0', 'MY')), (T, rm, rs)
off = 40 if mir else -40
def relocate(n, tmp):
    o = tmp[n]
    for d in range(0, 120):
        for i in range(-d, d + 1):
            for j in {-(d - abs(i)), d - abs(i)}:
                q = [hc[n]['o'][0] + round((snap(o[0]) - hc[n]['o'][0]) / G) * G + i * G, hc[n]['o'][1] + round((snap(o[1]) - hc[n]['o'][1]) / G) * G + j * G]
                if free(n, q, tmp): return q
    return None
def attempt(anchor):
    base = {n: list(h['o']) for n, h in hc.items()}; best = None
    for k in range(0, 16):
        for sg in ((1, -1) if k else (1,)):
            dx = sg * k * G
            for g in (17.28, 25.92, 34.56, 51.84, 69.12):
                if g < 0.21 * abs(dx) + 4: continue
                if anchor == 'vs':
                    n = S; x = snap(base[M][0] + off) + dx
                    y = snap(base[M][1] - g - hc[S]['s'][1]) if up else snap(base[M][1] + hc[M]['s'][1] + g)
                else:
                    n = M; x = snap(base[S][0] - off) + dx
                    y = snap(base[S][1] + hc[S]['s'][1] + g) if up else snap(base[S][1] - g - hc[M]['s'][1])
                o = [x, y]; r = rect(o, hc[n]['s'])
                if r[0] < EDGE or r[1] < EDGE or r[2] > W - EDGE or r[3] > H - EDGE or any(inter(r, s) for s in sites): continue
                block = [m for m in base if m != n and inter(r, rect(base[m], hc[m]['s']), MGAP - 0.01)]
                if any(b.startswith('u_vp') and n == S and False for b in block): continue
                p = dict(base); p[n] = o; ok = True
                for b in block: del p[b]
                for b in sorted(block, key=lambda m: -hc[m]['s'][0] * hc[m]['s'][1]):
                    tmp = dict(p); tmp[b] = base[b]; q = relocate(b, tmp)
                    if not q: ok = False; break
                    p[b] = q
                if not ok: continue
                c = (round(abs(dx), 2), g, len(block), cost(p))
                if best is None or c < best[0]: best = (c, p, n, dx, g, block)
    return best
a = attempt('vs'); mode = 'vs_moves'
if not a: a = attempt('m'); mode = 'm_moves'
if not a: print(json.dumps(dict(type=T, fail='no site', flip=flip, ft=len(sites)))); sys.exit(0)
_, p, n, dx, g, block = a
for m in ('u_vsw', 'u_vq'):
    if m == n: continue
    best = (cost(p), p[m])
    for i in range(-60, 61):
        for j in range(-60, 61):
            q = [hc[m]['o'][0] + (round((snap(p[m][0]) - hc[m]['o'][0]) / G) + i) * G, hc[m]['o'][1] + (round((snap(p[m][1]) - hc[m]['o'][1]) / G) + j) * G]
            if not free(m, q, p): continue
            pp = dict(p); pp[m] = q; cc = cost(pp)
            if cc < best[0] - 500: best = (cc, q)
    p[m] = best[1]
# vn / VP channel
vp = [m for m in hc if m.startswith('u_vp_g_ln') or m.startswith('u_vp.')]
vn = [m for m in hc if m.startswith('u_vn')]
def xgap(a, b):
    ra, rb = rect(p[a], hc[a]['s']), rect(p[b], hc[b]['s'])
    if ra[1] < rb[3] and rb[1] < ra[3]: return rb[0] - ra[2] if rb[0] >= ra[2] else ra[0] - rb[2]
    return None
gaps = [(xgap(a, b), a, b) for a in vn for b in hc if b not in vn and 'vp' in b and 'ln' in b]
gaps = [x for x in gaps if x[0] is not None and x[0] >= 0]
g0 = min(gaps)[0] if gaps else None; shift = 0
for a in vn:
    ga = [x for x in gaps if x[1] == a]
    if not ga or min(ga)[0] >= 24: continue
    side = -1 if p[min(ga)[2]][0] > p[a][0] else 1
    # both vn stay x-aligned when both can move; else the hot one alone (398-wire vn bus jogs at most 25.92)
    for k in (3, 2, 1):
        q = [p[a][0] + side * k * G, p[a][1]]
        if free(a, q, p):
            p = dict(p); p[a] = q; shift = side * k * G; break
out = {}
for k, v in p.items():
    dxx, dyy = v[0] - hc[k]['o'][0], v[1] - hc[k]['o'][1]
    if abs(dxx) > 1e-6 or abs(dyy) > 1e-6 or (k == S and flip):
        out[hc[k]['inst']] = [round(v[0], 3), round(v[1], 3)] + ([FLIP[rs]] if k == S and flip else [])
env = ','.join(f"{i}:{v[0]}:{v[1]}" + (f":{v[2]}" if len(v) > 2 else '') for i, v in out.items())
print(json.dumps(dict(type=T, mode=mode, flip=flip, dx=round(dx, 2), gap=g, block=block, vn_gap=g0 and round(g0, 2), vn_shift=round(shift, 2), cost0=round(cost({n: h['o'] for n, h in hc.items()})), cost=round(cost(p)), ft=len(sites), moves=out, env=env, pos={k: v for k, v in p.items()})))
