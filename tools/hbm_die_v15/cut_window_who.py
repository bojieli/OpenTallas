#!/usr/bin/env python3
"""Who crosses a pin_cut window (H-DIE-V790 10-16): same routing model as pin_cut.run (pin samples, half HV/half VH,
lanes), but returns the per-link / per-class bits crossing ONE window.

    cut_window_who.py PLAN h Y X0      -> horizontal line y=Y, window x in [X0, X0+1000)
    cut_window_who.py PLAN v X Y0      -> vertical line x=X, window y in [Y0, Y0+1000)
"""
import collections, glob, json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); import hbm_globalfp as F

STEP, WIN = 100.0, 1000.0


def who(d, axis, c, w0):
    d = Path(d)
    pins = json.loads(Path(glob.glob(str(d / 'pins' / '*.pins.json'))[0]).read_text())
    lanes = json.loads((d / 'lanes.json').read_text())
    ends = collections.defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append((b, f, p))
    line = int(round(c / STEP)); lo, hi = int(w0 // STEP), int(w0 // STEP) + int(WIN // STEP)
    per = collections.Counter()
    for lk, e in ends.items():
        if len(e) != 2:
            continue
        (b1, f1, p1), (b2, f2, p2) = e

        def samples(f, p):
            n = max(1, int(p['span_um'] // STEP) + 1)
            return [((p['x'] + (k + .5) / n * p['span_um'] - p['span_um'] / 2, p['y']) if f in 'NS'
                     else (p['x'], p['y'] + (k + .5) / n * p['span_um'] - p['span_um'] / 2)) for k in range(n)]
        s1, s2 = samples(f1, p1), samples(f2, p2)
        n = max(len(s1), len(s2)); wb = p1['bits'] / n / 2
        for k in range(n):
            a = s1[k * len(s1) // n]; cc = s2[k * len(s2) // n]
            for (u, v) in ((a, cc), (cc, a)):
                ly = lanes.get(lk)
                if isinstance(ly, dict) and 'v' in ly:
                    lx = ly['v']; sH = [(u[0], lx, u[1]), (lx, v[0], v[1])]; sV = [(lx, u[1], v[1])]
                elif isinstance(ly, dict):
                    y = ly['h']; sH = [(u[0], v[0], y)]; sV = [(u[0], u[1], y), (v[0], y, v[1])]
                else:
                    sH = [(u[0], v[0], u[1])]; sV = [(v[0], u[1], v[1])]
                if axis == 'h':
                    for (x, y0, y1) in sV:
                        y0, y1 = sorted((y0, y1))
                        if math.ceil(y0 / STEP) <= line <= math.floor(y1 / STEP) and lo <= int(x // STEP) < hi:
                            per[lk] += wb
                else:
                    for (x0, x1, y) in sH:
                        x0, x1 = sorted((x0, x1))
                        if math.ceil(x0 / STEP) <= line <= math.floor(x1 / STEP) and lo <= int(y // STEP) < hi:
                            per[lk] += wb
    cls = collections.Counter()
    for lk, b in per.items():
        cls[lk.split(':')[-1]] += b
    tot = sum(per.values())
    return dict(axis=axis, line_um=c, window_um=[w0, w0 + WIN], bits=round(tot, 1), ratio=round(tot / (F.TRK * WIN), 4),
                by_class={k: round(v, 1) for k, v in cls.most_common()},
                top_links={k: round(v, 1) for k, v in per.most_common(25)})


if __name__ == '__main__':
    r = who(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
    print(json.dumps(r, indent=1))
