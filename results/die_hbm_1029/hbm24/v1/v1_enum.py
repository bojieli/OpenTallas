#!/usr/bin/env python3
"""DIE-HBM-24/V1 slot-permutation estimate: the 4 SFU partitions (b110 b111 b112 b113) and the 2 empty pass-throughs
(spu0 spu1) are permuted over their own 6 slots (row A: b111@1416 803.52, spu1@6117 1468.8, b110@8320 414.72; row C:
b113@0 1857.6, spu0@5901 1684.8, b112@12147 1209.6) -- slot geometry fixed, so NO other partition moves (VB2 lesson).
Fit: hard-core area <= 0.85 x slot area and core column fit (388.8-um lane cores).  Cost = DIE-HBM-23 opt3 cost.
Run from hbm23/replan.  Plan arithmetic only (UNCHECKED)."""
import sys, os, json, itertools
sys.path.insert(0, os.getcwd())
sys.argv = ["opt3.py", "1", "1", "3", "300"]
import opt3 as O
R = O.R
VL3A = ["NW_b102", "NW_b103", "NW_b111", "NW_su20", "NW_su21", "NW_spu1", "NW_b100", "NW_b110", "NW_su30", "NW_su31", "NW_b101"]
VL3C = ["NW_b113", "NW_su00", "NW_su01", "NW_spu0", "NW_su10", "NW_su11", "NW_b112"]
SL = [("A", "NW_b111", 803.52), ("A", "NW_spu1", 1468.8), ("A", "NW_b110", 414.72),
      ("C", "NW_b113", 1857.6), ("C", "NW_spu0", 1684.8), ("C", "NW_b112", 1209.6)]
CORE = {"NW_b110": 0.54e6, "NW_b111": 0.67e6, "NW_b112": 0.67e6, "NW_b113": 1.38e6, "NW_spu0": 0, "NW_spu1": 0}
MINW = {"NW_b110": 400.0, "NW_b111": 400.0, "NW_b112": 790.0, "NW_b113": 1200.0, "NW_spu0": 0, "NW_spu1": 0}
far92 = {(x["src"], x["dst"]): x["unplanned_bits"] for x in R.far92}
parts = [s[1] for s in SL]
res = []
for perm in itertools.permutations(parts):
    ok = True; size = {}; A = list(VL3A); C = list(VL3C)
    for (row, slot, w), p in zip(SL, perm):
        h = 1555.2 if row == "A" else 1572.48
        if CORE[p] > 0.85 * w * h or w < MINW[p]:
            ok = False; break
        size[p] = w
        L = A if row == "A" else C
        L[[*VL3A, *VL3C].index(slot) - (0 if row == "A" else len(VL3A))] = p
    if not ok:
        continue
    R.SIZE.clear(); R.SIZE.update(size)
    rect = R.apply_rows({"A": A, "C": C})
    c, d = O.cost(rect, True)
    far = [(a, b) for (a, b) in far92 if R.rel(rect[a], rect[b])[0] < R.MIN_EDGE and R.rel(rect[a], rect[b])[1] > R.NEAR]
    res.append(dict(cost=round(c), far_rows=len(far), A=A, C=C, size=size, **d))
res.sort(key=lambda r: (r["far_rows"], r["cost"]))
for r in res[:8]:
    print(r["far_rows"], r["cost"], r["moved_nw"], r["over_bits"], "A", [n[3:] for n in r["A"][2:8]], "C", [n[3:] for n in r["C"]])
base = [r for r in res if r["A"] == VL3A and r["C"] == VL3C]
print("base", base[0]["far_rows"] if base else None, base[0]["cost"] if base else None, "n", len(res))
json.dump(res[:30], open(os.environ.get("OUT", "/dev/null"), "w"), indent=1)
