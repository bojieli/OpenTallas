#!/usr/bin/env python3
"""DIE-HBM-24/V1 estimate (12.14b, plan arithmetic, UNCHECKED until built): SFU partitions (b110/b111 lanes 0-8 row A,
b112 lanes 9-13 + b113 lanes 14/15 + opstores + ctl row C) re-homed next to their partners.  Same pair model / cost as
DIE-HBM-23 opt3.py (pairs = plan lanes end-to-end + the 92 UNPLANNED rows).  Run from hbm23/replan (inputs there)."""
import sys, json, os
here = os.getcwd(); sys.path.insert(0, here)
sys.argv = ["opt3.py", "1", "1", "3", "300"]
import opt3 as O
R = O.R
VL3A = ["NW_b102", "NW_b103", "NW_b111", "NW_su20", "NW_su21", "NW_spu1", "NW_b100", "NW_b110", "NW_su30", "NW_su31", "NW_b101"]
VL3C = ["NW_b113", "NW_su00", "NW_su01", "NW_spu0", "NW_su10", "NW_su11", "NW_b112"]
SFU = {"NW_b110", "NW_b111", "NW_b112", "NW_b113"}
far92 = {(x["src"], x["dst"]): x["unplanned_bits"] for x in R.far92}


def ev(name, A, C, size=None, merge=None):
    R.SIZE.clear(); R.SIZE.update(size or {})
    rect = R.apply_rows({"A": A, "C": C})
    if merge:  # cores of partition k moved into partition v: model k's rectangle = v's
        for k, v in merge.items():
            rect[k] = rect[v]; rect[R.mirror(k)] = rect[R.mirror(v)]
    c, d = O.cost(rect, True)
    far = []; farsfu = []
    for (a, b), bits in far92.items():
        e, g = R.rel(rect[a], rect[b])
        if e < R.MIN_EDGE and g > R.NEAR:
            far.append((a, b, bits, round(g)))
            if a in SFU or b in SFU or R.mirror(a) in SFU or R.mirror(b) in SFU:
                farsfu.append((a, b))
    # per-edge demand (all pairs incl planned) on edges touching SFU partitions
    over = []
    for (a, b), (pb, nb) in O.P.items():
        e, g = R.rel(rect[a], rect[b])
        if e >= R.MIN_EDGE and (pb + nb) > e * R.PPU:
            over.append((a, b, pb + nb, round(e * R.PPU)))
    return dict(name=name, cost=round(c), far_rows=len(far), far_sfu=len(farsfu), far_bits=sum(x[2] for x in far),
                over=over, **d)


out = []
out.append(ev("VL3d", VL3A, VL3C))
# V1a: b111 <-> spu1 slot swap in row A (widths swap: b111 1468.8, spu1 803.52)
A = list(VL3A); i, j = A.index("NW_b111"), A.index("NW_spu1"); A[i], A[j] = A[j], A[i]
out.append(ev("V1a b111<->spu1", A, VL3C, {"NW_b111": 1468.8, "NW_spu1": 803.52}))
# V1b: b113 <-> spu0 slot swap in row C (b113 1684.8, spu0 1857.6)
C = list(VL3C); i, j = C.index("NW_b113"), C.index("NW_spu0"); C[i], C[j] = C[j], C[i]
out.append(ev("V1b b113<->spu0", VL3A, C, {"NW_b113": 1684.8, "NW_spu0": 1857.6}))
out.append(ev("V1ab", A, C, {"NW_b111": 1468.8, "NW_spu1": 803.52, "NW_b113": 1684.8, "NW_spu0": 1857.6}))
# V1c: b113 cores into the hub (b113 left an empty pass-through)
out.append(ev("V1c b113->hub", VL3A, VL3C, None, {"NW_b113": "NW_hub"}))
out.append(ev("V1ac b111<->spu1 + b113->hub", A, VL3C, {"NW_b111": 1468.8, "NW_spu1": 803.52}, {"NW_b113": "NW_hub"}))
# V1d: cross-row: b113 to row A spu1 slot (h 1555.2, w 1468.8), spu1 to row C b113 slot (w 1857.6)
A2 = [("NW_b113" if n == "NW_spu1" else n) for n in VL3A]; C2 = [("NW_spu1" if n == "NW_b113" else n) for n in VL3C]
out.append(ev("V1d b113<->spu1 xrow", A2, C2, {"NW_b113": 1468.8, "NW_spu1": 1857.6}))
# V1e: cross-row b111 to row C spu0 slot; spu0 to row A b111 slot
A3 = [("NW_spu0" if n == "NW_b111" else n) for n in VL3A]; C3 = [("NW_b111" if n == "NW_spu0" else n) for n in VL3C]
out.append(ev("V1e b111<->spu0 xrow", A3, C3, {"NW_b111": 1684.8, "NW_spu0": 803.52}))
for r in out:
    print(r["name"], "cost", r["cost"], "far_rows", r["far_rows"], "far_sfu", r["far_sfu"], "far_bits", r["far_bits"],
          "moved", r["moved_nw"], "nonadj", r["nonadj_bits"], "over", r["over_bits"], [o for o in r["over"] if any(s in o[0] + o[1] for s in ("b11", "hub"))][:8])
json.dump(out, open(sys.argv_out if hasattr(sys, "argv_out") else os.environ.get("OUT", "/dev/null"), "w"), indent=1)
# V1h: whole SFU (b110 b111 b112 b113 hard cores + contents) into the hub; the 4 partitions left as empty pass-throughs
r = ev("V1h all SFU->hub", VL3A, VL3C, None, {k: "NW_hub" for k in SFU})
print(r["name"], "cost", r["cost"], "far_rows", r["far_rows"], "far_sfu", r["far_sfu"], "far_bits", r["far_bits"], "nonadj", r["nonadj_bits"])
R.SIZE.clear()
rect = R.apply_rows({"A": VL3A, "C": VL3C})
for k in SFU:
    rect[k] = rect["NW_hub"]; rect[R.mirror(k)] = rect["NE_hub"]
from collections import Counter
cat = Counter(); left = []
for (a, b), bits in far92.items():
    e, g = R.rel(rect[a], rect[b])
    if e < R.MIN_EDGE and g > R.NEAR:
        left.append((a, b, bits, round(g)))
for x in sorted(left, key=lambda x: -x[2]):
    print("  left", x)
