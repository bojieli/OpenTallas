"""Name the nets of flagged fabric rows: per (y_row, layer, 1-mm x bin) the track-um by net group (net name with bit/hop indices
stripped -> <kind>:<part>:<slot>) and the share of the row capacity.  usage: rownets.py RUN PITCH_JSON 'y:L:xmm' ... """
import json, sys, re
from collections import defaultdict
run, pit = sys.argv[1], json.load(open(sys.argv[2])); Q = []
for a in sys.argv[3:]:
    y, L, xm = a.split(':'); Q.append((round(float(y), 3), L, int(float(xm))))
d = {q: defaultdict(float) for q in Q}; net = None
grp = lambda n: re.sub(r'(__\d+)+$', '', n)
with open(f'{run}/fabric.guide') as f:
    for ln in f:
        p = ln.split()
        if len(p) == 1 and p[0] not in '()': net = p[0]; continue
        if len(p) < 5: continue
        x0, y0, x1, y1 = (int(v) / 1000 for v in p[:4])
        for q in Q:
            if p[4] != q[1] or round(y0, 3) != q[0]: continue
            s, e = max(x0, q[2] * 1000.0), min(x1, (q[2] + 1) * 1000.0)
            if e > s: d[q][grp(net)] += e - s
for q in Q:
    cap = 1000.0 * 9.6 / pit[q[1]]; tot = sum(d[q].values())
    top = sorted(d[q].items(), key=lambda kv: -kv[1])[:12]
    print(json.dumps(dict(row=q[0], layer=q[1], x_mm=q[2], usage=round(tot / cap, 3), top=[(k, round(v / cap, 3)) for k, v in top])))
