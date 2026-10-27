import json, math, sys
import numpy as np
T, stab = sys.argv[1], sys.argv[2]
N = json.load(open(f"{T}/tree_nodes.json")); by = {n["tag"]: n for n in N}
rows = [r for r in json.load(open(stab))["rows"] if "error" not in r]; D0 = {"TT": 34.0, "FF": 27.2}
def cf(c):
    rr = sorted([r for r in rows if r["w"] == "16w" and r["mult"] == 2 and r["corner"] == c], key=lambda r: r["L"])
    return np.polyfit([0.0] + [r["L"] for r in rr], [D0[c]] + [r["stage_ps"] for r in rr], 2)
X = 8760.96
lf = next(n for n in N if not n["kids"])
path = []
n = lf
while n.get("parent"): path.append(n); n = by[n["parent"]]
for c in ("TT", "FF"):
    f = cf(c); base = new = 0.0; k = 0
    for e in path:
        p = by[e["parent"]]
        L = abs(p["xy"][0] - e["xy"][0]) + abs(p["xy"][1] - e["xy"][1])
        vert = abs(p["xy"][0] - X) < 1e-6 and abs(e["xy"][0] - X) < 1e-6 and L > 0
        def d(L):
            n_ = max(1, math.ceil(L / 450 - 1e-9)); return n_ * float(np.polyval(f, L / n_))
        base += d(L); new += d(L + (2 * 8.64 if vert else 0)); k += vert
    print(c, "trunk vertical edges on path", k, "insertion %.2f -> %.2f (+%.2f) with 2x8.64 riser per trunk edge" % (base, new, new - base))
