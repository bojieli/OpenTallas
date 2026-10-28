#!/usr/bin/env python3
"""DIE-QC-5: FF hold structure from dump_hb.py pickle + proof taps.  Per region class: endpoint-path hold histogram,
HB4 k histogram, realistic per-capture-tap cell count vs the main BOUND.  usage: hold_hist.py PKL PROOF_DIR"""
import pickle, sys, json, math, collections
S = pickle.load(open(sys.argv[1], "rb"))
pd = sys.argv[2]
taps = {t["port"]: t for t in json.load(open(pd + "/tap_arrivals_FF.json"))["taps"]}
def cls(p):
    return "c_*" if p.startswith("c_") else ("sl_*_su_c" if p.endswith("su_c") else ("sl_*" if p.startswith("sl_") else "other"))
names = ["intra", "seam", "seam_nearest_INFO"]
for i, call in enumerate(S["calls"][:2]):
    nm = names[i]; ff = call["ff"]; hb = call["hb"]; fe = hb["ff_early_ps"]
    print("==", nm, "endpoint paths", len(ff), "ff_early", fe)
    H = collections.defaultdict(lambda: collections.Counter())
    K = collections.defaultdict(lambda: collections.Counter())
    capk = {}
    worst = collections.defaultdict(lambda: 1e9)
    for key, v in ff.items():
        a, b, tag = key[:3]
        h = v[1]
        part = tag if nm == "intra" else tag.split("->")[1]
        c = cls(part)
        H[c][max(-200, 25 * math.floor(h / 25))] += 1
        k = max(0, math.ceil(-h / fe - 1e-9)) if h < 0 else 0
        K[c][k] += 1
        capk[b] = max(capk.get(b, 0), k)
        worst[c] = min(worst[c], h)
    for c in sorted(H):
        n = sum(H[c].values())
        print("  %-10s paths %6d worst %7.1f  hold bins(25ps): %s" % (c, n, worst[c], dict(sorted(H[c].items()))))
        print("  %-10s k hist %s  share k>=3 %.1f%%" % ("", dict(sorted(K[c].items())), 100 * sum(v for k, v in K[c].items() if k >= 3) / n))
    if nm == "intra":
        # per capture tap: worst k; taps per partition
        pk = collections.defaultdict(list)
        for t, k in capk.items():
            pk[taps[t]["part"]].append(k)
        pb = call["part_bits"] or {}
        bound = sum(max(v) * pb.get(p, 0) for p, v in pk.items())
        # realistic: partition data pins split evenly over its capture taps, each at its own tap's worst k
        real = sum(pb.get(p, 0) * (sum(v) / len(v)) for p, v in pk.items())
        print("  BOUND (main: all part pins x part worst k) %.0f cells; per-capture-tap worst k (pins split evenly over taps) %.0f cells; total part pins %d"
              % (bound, real, sum(pb.get(p, 0) for p in pk)))
        cap_hist = collections.Counter(capk.values()); print("  capture-tap worst-k hist", dict(sorted(cap_hist.items())))
