#!/usr/bin/env python3
"""Die-wide street audit on a ROUTED plan (link 'h' segments carry bits): streets.py PLAN [--min 0.6] [--step 25]
For every H street (vertical cut at x, free y-gap between two bodies) and V street (horizontal cut at y, free x-gap),
bits = lane bits whose route segment crosses the cut inside the gap; ratio = bits / (gap * tracks/um after adjustment).
Tracks (cap29+: M2-M3 0.50, M4-M5 0.30, M6-M8 0.10, M9 signal no PG): H = M4 14.58 + M6 14.06 + M8 11.25 = 39.9/um;
V = M3 13.9 + M5 14.58 + M7 14.06 + M9 12.5 = 55.0/um.  Prints one row per street (bounding body pair), worst cut."""
import json, sys, argparse, collections
ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--min', type=float, default=0.6)
ap.add_argument('--step', type=float, default=25.0); ap.add_argument('--json'); v = ap.parse_args()
P = json.load(open(v.plan)); W, H = P['facts']['die_um']; B = P['blocks'] + P.get('blockages', [])
HF = 0.7 / 0.048 + 0.9 / 0.064 + 0.9 / 0.08
VF = 0.5 / 0.036 + 0.7 / 0.048 + 0.9 / 0.064 + 1.0 / 0.080
hs, vs = [], []   # horizontal segs (x0,x1,y,b), vertical segs (y0,y1,x,b)
for L in P['links']:
    for x0, y0, x1, y1, b in L.get('h', []):
        if abs(y1 - y0) < 1e-6 and abs(x1 - x0) > 1e-6: hs.append((min(x0, x1), max(x0, x1), y0, b, L['i']))
        elif abs(x1 - x0) < 1e-6 and abs(y1 - y0) > 1e-6: vs.append((min(y0, y1), max(y0, y1), x0, b, L['i']))
        elif abs(x1 - x0) > 1e-6:  # diagonal: count both
            hs.append((min(x0, x1), max(x0, x1), (y0 + y1) / 2, b, L['i'])); vs.append((min(y0, y1), max(y0, y1), (x0 + x1) / 2, b, L['i']))
def gaps(c, axis):  # free intervals along the other axis at coordinate c
    if axis == 'x':
        bl = sorted([b for b in B if b['x'] < c < b['x'] + b['w']], key=lambda b: b['y']); lo, hi, k0, k1 = 0.0, H, 'y', 'h'
    else:
        bl = sorted([b for b in B if b['y'] < c < b['y'] + b['h']], key=lambda b: b['x']); lo, hi, k0, k1 = 0.0, W, 'x', 'w'
    out = []; cur = lo; prev = 'EDGE'
    for b in bl:
        if b[k0] > cur + 1: out.append((cur, b[k0], prev, b['name']))
        if b[k0] + b[k1] > cur: cur = b[k0] + b[k1]; prev = b['name']
    if hi > cur + 1: out.append((cur, hi, prev, 'EDGE'))
    return out
best = {}
for axis, segs, F, span in (('x', hs, HF, W), ('y', vs, VF, H)):
    for k in range(int(span / v.step) + 1):
        c = k * v.step
        for f0, f1, lo, hi in gaps(c, axis):
            w = f1 - f0
            if w < 20: continue
            bits = 0; lk = collections.Counter()
            for a0, a1, t, b, li in segs:
                if a0 < c < a1 and f0 - 1 <= t <= f1 + 1: bits += b; lk[li] += b
            r = bits / (w * F)
            key = ('H' if axis == 'x' else 'V', lo, hi)
            if key not in best or r > best[key]['ratio']:
                best[key] = dict(dir=key[0], lo=lo, hi=hi, at=c, f0=round(f0, 1), f1=round(f1, 1), w=round(w, 1), bits=bits,
                                 tracks=round(w * F), ratio=round(r, 3), w06=round(bits / (0.6 * F), 1), top=lk.most_common(6))
rows = sorted(best.values(), key=lambda r: -r['ratio'])
for r in rows:
    if r['ratio'] >= v.min:
        print(f"{r['dir']} {r['lo']:>9s}|{r['hi']:<9s} @{'x' if r['dir']=='H' else 'y'}={r['at']/1e3:6.2f} gap {r['f0']:.1f}-{r['f1']:.1f} w {r['w']:6.1f} bits {r['bits']:6d} tracks {r['tracks']:6d} ratio {r['ratio']:.2f} w06 {r['w06']:.0f} top {[(a, b) for a, b in r['top'][:3]]}")
if v.json: json.dump(rows, open(v.json, 'w'), indent=0)
