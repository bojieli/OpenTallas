#!/usr/bin/env python3
"""DIE-HBM-23 re-plan estimate v3 (12.14b): same row model as DIE-HBM-22 replan_est.py, but a BUILD-REALISTIC cost.
Lesson from the VB2 event build (G0 FAIL; 41-43 lanes unroutable): a NEAR (gap <= 1200 um) pair is not free - it needs a
pass-through chain through neighbours whose faces are already full (hub|b0xx, b000|b010).  So here every non-ADJ pair
costs bits x (PEN + gap/1000), ADJ edges over 6 pins/um are over-subscribed (x2), and each moved partition costs MOVEPEN
(every lane touching it is re-routed).  usage: opt3.py SEEDS ITERS [PEN] [MOVEPEN]"""
import sys, json, math, random
SEEDS, ITERS = int(sys.argv[1]), int(sys.argv[2])
PEN = float(sys.argv[3]) if len(sys.argv) > 3 else 3.0
MOVEPEN = float(sys.argv[4]) if len(sys.argv) > 4 else 300.0
sys.argv = ["x", "lanes.json", "rows103.json", "rows_h8b.json"]
import replan_est as R
rowset = set(R.A0) | set(R.C0) | {R.mirror(n) for n in R.A0 + R.C0}
P = {k: v for k, v in R.pairs.items() if k[0] in rowset or k[1] in rowset}


def cost(rect, detail=False):
    c = 0.0
    adj = non = over = 0
    for (a, b), (pb, nb) in P.items():
        w = pb + nb
        e, g = R.rel(rect[a], rect[b])
        if e >= R.MIN_EDGE:
            adj += w
            if w > e * R.PPU:
                c += (w - e * R.PPU) * 2.0; over += w - e * R.PPU
            continue
        non += w
        c += w * (PEN + g / 1000.0)
    mv = sum(1 for n in rect if n in R.rect0 and n.startswith("NW") and n in rowset and
             (abs(rect[n][0] - R.rect0[n][0]) > 0.01 or abs(rect[n][1] - R.rect0[n][1]) > 0.01))
    c += MOVEPEN * mv
    return (c, dict(adj_bits=adj, nonadj_bits=non, over_bits=round(over), moved_nw=mv)) if detail else c


def run(A, C, iters, seed):
    rnd = random.Random(seed)
    cur = (list(A), list(C)); cc = cost(R.apply_rows({"A": cur[0], "C": cur[1]}))
    best = (cc, [list(cur[0]), list(cur[1])]); T = 3000.0
    for _ in range(iters):
        r = 0 if rnd.random() < 0.5 else 1
        L = list(cur[r])
        i1, i2 = rnd.sample(range(len(L)), 2)
        if rnd.random() < 0.5:
            L[i1], L[i2] = L[i2], L[i1]
        else:
            L.insert(i2, L.pop(i1))
        new = (L, cur[1]) if r == 0 else (cur[0], L)
        try:
            nc = cost(R.apply_rows({"A": new[0], "C": new[1]}))
        except AssertionError:
            continue
        if nc < cc or rnd.random() < math.exp((cc - nc) / T):
            cur, cc = (list(new[0]), list(new[1])), nc
            if cc < best[0]:
                best = (cc, [list(cur[0]), list(cur[1])])
        T *= 0.9995
    return best


if __name__ == "__main__":
    out = {}
    base = R.apply_rows({"A": R.A0, "C": R.C0})
    out["base"] = cost(base, True)[1]
    V = json.load(open("VB2.json"))
    R.SIZE.update(V.get("size", {}))
    out["VB2"] = cost(R.apply_rows({"A": V["A"], "C": V["C"]}), True)[1]
    R.SIZE.clear()
    import os
    MODE = os.environ.get("MODE", "A")
    A0, C0 = list(R.A0), list(R.C0)
    if MODE == "B":      # VB2 row sets: b110/b111 into row C (h 1572.48), fillers spu0 466.56 / spu1 2687.04
        R.SIZE.update({"NW_spu0": 466.56, "NW_spu1": 2687.04})
        A0 = [n for n in A0 if n not in ("NW_b110", "NW_b111")]; C0 = C0 + ["NW_b111", "NW_b110"]
    res = []
    for s in range(SEEDS):
        c, (A, C) = run(A0, C0, ITERS, s)
        d = cost(R.apply_rows({"A": A, "C": C}), True)[1]
        res.append(dict(seed=s, cost=round(c), A=A, C=C, **d))
    res.sort(key=lambda x: x["cost"])
    out["opt"] = res
    json.dump(dict(MODE=MODE, PEN=PEN, MOVEPEN=MOVEPEN, **out), open(f"opt3_{MODE}_P{PEN:g}_M{MOVEPEN:g}.json", "w"), indent=1)
    print("base", out["base"]); print("VB2", out["VB2"])
    for r in res[:3]:
        print(r)
