"""M9 signal demand per 450-um window from GRT guides (die probe nets: clk+rst spine), vs free M9 tracks of the 12.96@34.56 PG."""
import sys, json, collections
G, straps = sys.argv[1], sys.argv[2]
DBU = 1000.0; WIN = 450.0
FREE_PER_UM = 2 * (4.32 - 2 * 1.0) / 34.56 / 0.08   # GEOM-25 basis: tracks/um of free M9 (2.32 um per 34.56 at 0.08 pitch)
recs = []; net = None
for ln in open(G):
    t = ln.split()
    if len(t) == 1 and t[0] not in ("(", ")"): net = t[0]
    elif len(t) == 5 and t[4] == "M9":
        x0, y0, x1, y1 = (float(v) / DBU for v in t[:4]); recs.append((net, x0, y0, x1, y1))
print("M9 guide rects", len(recs), "nets", len({r[0] for r in recs}))
# vertical cut demand: for each window (ix, iy), number of distinct nets whose M9 guide crosses the window's mid-y line
cut = collections.defaultdict(set); length = collections.defaultdict(float)
X1 = max(r[3] for r in recs); Y1 = max(r[4] for r in recs)
for n, x0, y0, x1, y1 in recs:
    for ix in range(int(x0 // WIN), int((x1 - 1e-6) // WIN) + 1):
        for iy in range(int(y0 // WIN), int((y1 - 1e-6) // WIN) + 1):
            ym = (iy + 0.5) * WIN
            if y0 <= ym <= y1: cut[(ix, iy)].add(n)
            length[(ix, iy)] += max(0.0, min(y1, (iy + 1) * WIN) - max(y0, iy * WIN))
free = FREE_PER_UM * WIN
S = json.load(open(straps)); m9 = [s for s in S if s[0] == "M9"]
clk = collections.Counter()
for s in m9:
    ix = int(s[1] // WIN)
    for iy in range(int(s[2] // WIN), int(s[3] // WIN) + 1): clk[(ix, iy)] += 1
worst = sorted(((len(v), k) for k, v in cut.items()), reverse=True)[:5]
worstL = sorted(((v / (free * WIN), k) for k, v in length.items()), reverse=True)[:5]
both = max(((len(cut.get(k, ())) + clk.get(k, 0)) / free, k) for k in set(cut) | set(clk))
print("free M9 tracks per 450-um window %.1f (gate 0.6 x free = %.1f)" % (free, 0.6 * free))
print("worst cut-crossing nets per window", [(n, k, "%.3f of free" % (n / free)) for n, k in worst])
print("worst M9 length share of free per window", [("%.4f" % r, k) for r, k in worstL])
print("worst incl. clock-mesh M9 straps: %.3f of free at %s" % both)
print("windows with demand", len(cut), "max clock straps per window", max(clk.values()))
