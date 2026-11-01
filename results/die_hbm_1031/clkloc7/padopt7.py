# HBM-CLKLOC-7 copy of DIE-S81-43 padopt3.py (residual tap pads, METHODOLOGY 12.8d2, CLOCK-RESIDUAL ledger): greedy pads on
# the earliest LAUNCH grid tap of the worst over-W pair of the bytag2 pair dump (pairs > 100 ps); never on core taps
# (__clk_c*); MAXK*dL < W_gate - 100 so a pair below the dump floor cannot cross W.  usage: DUMP REGIONS W dE dL MAXK OUT
import json, sys, collections, os
CORE = os.environ.get("CORE") == "1"   # CLKLOC-7: CORE=1 also pads early core taps (die-side pad before the core clock port)
dump, regions, W, dE, dL, MAXK, out = sys.argv[1], sys.argv[2].split(","), *map(float, sys.argv[3:6]), int(sys.argv[6]), sys.argv[7]
F = json.load(open(dump)); pad = {}; FLOOR = float(os.environ.get("FLOOR", "100")); assert MAXK * dL < 160 - FLOOR
for r in regions:
    P = list({(v, a, b) for v, a, b, t in F if t == r})
    k = collections.Counter(); nd = lambda p: p[0] + dL * k[p[2]] - dE * k[p[1]]; ok = True
    while True:
        w = max(P, key=nd)
        if nd(w) <= W: break
        if ("__clk_c" in w[1] and not CORE) or k[w[1]] >= MAXK: ok = False; break
        k[w[1]] += 1
    w = max(P, key=nd)
    print(r, dict(need_before=max(P)[0], need_after=round(nd(w), 2), ok=ok, padded=len(k), pads=sum(k.values()), worst=w[1:], over160_after=sum(nd(p) > 160 for p in P)))
    pad.update(k)
json.dump(dict(pad=pad), open(out, "w"), indent=1, sort_keys=True); print("total pads", sum(pad.values()), "taps", len(pad))
