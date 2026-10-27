"""R28 wide-pair PG grid: mesh clock metal + drawn VSS shields vs PG with the ASAP7 wide-metal spacing table."""
import json, sys, bisect
from pathlib import Path
import schema, die_infra as I, die_clock_128 as C, die_clock_mesh as D
P = schema.Plan(schema.load(sys.argv[1]), Path(sys.argv[1]))
m = json.load(open(sys.argv[2])); nd = D.NDR[m["ndr"]]
r = I.pg_rects(P, C.pg_grid(P))
lines = {}
for n, L, x0, y0, x1, y1 in r:
    V = L == "M9"
    lines.setdefault(L, []).append(((x0, x1) if V else (y0, y1), n))
for L in lines: lines[L].sort()
segs = [("M8", s["x0"], s["y"], s["x1"], s["y"], "ck", "mesh") for s in m["M8"]] + \
       [("M9", s["x"], s["y0"], s["x"], s["y1"], "ck", "mesh") for s in m["M9"]]
bad = {}; minsp = {}
for s in C.clock_shapes(segs, nd, "VSS"):
    L, net, kind, p0, p1, a0, a1 = s
    arr = lines[L]; i = bisect.bisect_left(arr, ((p0 - 5, 0), ""))
    for (q0, q1), pn in arr[max(0, i - 2): i + 6]:
        if pn == net: continue
        g = max(q0 - p1, p0 - q1)
        need = I.pg_spacing(max(q1 - q0, p1 - p0), a1 - a0)
        k = f"{L}:{kind}:{pn}"
        minsp[k] = min(minsp.get(k, 9e9), round(g, 4))
        if g < need - 1e-6: bad[k] = bad.get(k, 0) + 1
f = {L: round(sum(q1 - q0 for (q0, q1), _ in lines[L]) / (P.H if L == "M8" else P.W), 4) for L in lines}
print(json.dumps(dict(violations=bad, min_gap_um=minsp, metal_fraction=f, verdict="PASS" if not bad else "FAIL")))
