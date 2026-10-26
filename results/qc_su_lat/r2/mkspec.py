#!/usr/bin/env python3
"""QC-SU-LAT-R2 structured-clock spec generator (METHODOLOGY 12.8b): centre clock entry (island) -> equal-load leaf
clusters (recursive median bisection, <= TAPMAX sinks) -> star of IDENTICAL trunk chains: every path has the same N
stages and the same stage length s (Manhattan, buffer to buffer), so wire and cells match by construction (no padding).
Stage points are solved explicitly (free of macro+halo and the island).  Usage: mkspec.py GEO OUT IX IY [SEG] [TAPMAX]"""
import sys, math, itertools, json
geo, out, ix, iy = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
SEG = float(sys.argv[5]) if len(sys.argv) > 5 else 110.0; TAPMAX = int(sys.argv[6]) if len(sys.argv) > 6 else 280
HALO, ISL = 4.32, 8.64
sinks, macros = [], []
for ln in open(geo):
    f = ln.split()
    if not f: continue
    if f[0] == 'CORE': cx0, cy0, cx1, cy1 = map(float, f[1:5])
    elif f[0] == 'MACRO': macros.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    elif f[0] == 'SINK': sinks.append((float(f[1]), float(f[2])))
blk = [(a - HALO, b - HALO, c + HALO, d + HALO) for _, (a, b, c, d), _ in macros]
blk.append((ix - ISL / 2 - 1.0, iy - ISL / 2 - 1.0, ix + ISL / 2 + 1.0, iy + ISL / 2 + 1.0))
def free(p, m=0.6):
    x, y = p
    if not (cx0 + 1 <= x <= cx1 - 3 and cy0 + 1 <= y <= cy1 - 1): return False
    return not any(a - m < x < c + m and b - m < y < d + m for a, b, c, d in blk)
def snap(p):
    if free(p): return p
    best = None
    for r in [i * 0.5 for i in range(1, 400)]:
        for dx, dy in [(r, 0), (-r, 0), (0, r), (0, -r)]:
            q = (p[0] + dx, p[1] + dy)
            if free(q): return q
    raise SystemExit('no free point near %s' % (p,))
d1 = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
# root buffer: just east of the island (entry), in the channel
R = snap((ix + ISL / 2 + 2.0, iy))
# equal-load clusters by recursive median bisection of the core rectangle
k = math.ceil(len(sinks) / TAPMAX)
def bis(rect, pts, k):
    if k == 1: return [(rect, pts)]
    x0, y0, x1, y1 = rect
    ax = 0 if (x1 - x0) >= (y1 - y0) else 1
    pts = sorted(pts, key=lambda p: p[ax]); k1 = k // 2; n1 = round(len(pts) * k1 / k)
    cut = (pts[n1 - 1][ax] + pts[n1][ax]) / 2
    if ax == 0: r1, r2 = (x0, y0, cut, y1), (cut, y0, x1, y1)
    else: r1, r2 = (x0, y0, x1, cut), (x0, cut, x1, y1)
    return bis(r1, pts[:n1], k1) + bis(r2, pts[n1:], k - k1)
cl = bis((0.0, 0.0, cx1 + HALO, cy1 + HALO), sinks, k)
taps = []
for i, (rect, pts) in enumerate(cl):
    c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    taps.append({'name': 'L%02d' % i, 'rect': rect, 'n': len(pts), 'T': snap(c)})
# macro clock leaves: the cluster containing the free point beside the macro clock pin moves its tap point there
mac = []
for name, (a, b, c, d), ck in macros:
    site = snap((ck[0] - HALO - 1.0, ck[1]) if abs(ck[0] - a) < abs(ck[0] - c) else (ck[0] + HALO + 1.0, ck[1]))
    t = min(taps, key=lambda t: 0 if (t['rect'][0] <= site[0] <= t['rect'][2] and t['rect'][1] <= site[1] <= t['rect'][3]) else 1 + d1(t['T'], site))
    if 'mac' in t: t = min((u for u in taps if 'mac' not in u), key=lambda u: d1(u['T'], site))
    t['T'] = site; t['mac'] = name; mac.append((name.replace('\\', ''), t['name'], site))
L0 = max(d1(R, t['T']) for t in taps)
def diamond(c, r, step=1.0):
    n = max(8, int(4 * r / step))
    for j in range(n):
        u = 4.0 * r * j / n; q, w = divmod(u, r)
        dx, dy = [(r - w, w), (-w, r - w), (-(r - w), -w), (w, -(r - w))][int(q) % 4]
        p = (c[0] + dx, c[1] + dy)
        if free(p): yield p
def solve(T):
    # N-1 intermediate points, every hop exactly s (tol 0.75 um); prefer points near the straight R->T interpolation
    best = None
    if N == 2:
        for p in diamond(R, s):
            if abs(d1(p, T) - s) < 0.75:
                e = d1(p, ((R[0] + T[0]) / 2, (R[1] + T[1]) / 2))
                if best is None or e < best[0]: best = (e, [p])
    elif N == 3:
        A = list(diamond(R, s)); B = list(diamond(T, s))
        for p in A:
            for q in B:
                if abs(d1(p, q) - s) < 0.75:
                    e = d1(p, (R[0] + (T[0] - R[0]) / 3, R[1] + (T[1] - R[1]) / 3)) + d1(q, (R[0] + 2 * (T[0] - R[0]) / 3, R[1] + 2 * (T[1] - R[1]) / 3))
                    if best is None or e < best[0]: best = (e, [p, q])
    else: raise SystemExit('N=%d unsupported' % N)
    return None if best is None else best[1]
# L* = smallest common path length (2-um steps from the longest direct distance) for which EVERY path has a free
# equal-stage solution (macros force detours around their rows; every path is then built to that one length)
L = L0
while True:
    N = max(2, math.ceil(L / SEG)); s = L / N
    sol = [solve(t['T']) for t in taps]
    if all(x is not None for x in sol): break
    L += 2.0
    if L > 2.5 * L0: raise SystemExit('no common length')
for t, x in zip(taps, sol): t['P'] = x + [t['T']]
o = ['# QC-SU-LAT-R2 %s: structured clock (METHODOLOGY 12.8b) GENERATED by mkspec.py from %s' % (sys.argv[0].split('/')[-1], geo),
     '# entry: island centre (%.3f, %.3f) 8.64 um (M9->M5 stack, M5 ck pin there); root (%.2f, %.2f)' % (ix, iy, R[0], R[1]),
     '# %d equal-load leaf clusters (%d..%d sinks), star of identical chains: %d stages x %.2f um Manhattan per path (OT_MSCTS_EXPLICIT=1), L* %.1f um' % (len(taps), min(t['n'] for t in taps), max(t['n'] for t in taps), N, s, L),
     'set ot_ms_port ck', 'set ot_ms_root {%.3f %.3f}' % R, 'set ot_ms_taps {']
for t in taps:
    pts = ' '.join('%.3f %.3f' % p for p in [R] + t['P'])
    o.append(' {%s {%s} {{%.3f %.3f %.3f %.3f}}}' % (t['name'], pts, *t['rect']))
o.append('}'); o.append('set ot_ms_macros {')
for name, tap, site in mac:
    g = name.replace('[', '*').replace(']', '*')
    o.append(' {%s %s {%.3f %.3f}}' % (g, tap, *site))
o.append('}')
open(out, 'w').write('\n'.join(o) + '\n')
far = max(d1((ix, iy), p) for p in sinks); fare = max(math.hypot(ix - p[0], iy - p[1]) for p in sinks)
json.dump({'entry': [ix, iy], 'root': R, 'N': N, 's': s, 'Lstar': L, 'clusters': [[t['name'], t['n']] for t in taps], 'max_entry_to_sink_manhattan': far, 'max_entry_to_sink_euclid': fare, 'sinks': len(sinks)}, open(out + '.json', 'w'))
print(o[1]); print(o[2]); print('max entry->sink manhattan %.1f euclid %.1f' % (far, fare))
