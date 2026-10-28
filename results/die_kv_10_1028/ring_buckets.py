import json, sys, collections
r = json.load(open(sys.argv[1])); out = {}
BUCK = [300, 416, 573, 672, 800, 909, 1119, 1560]       # ring W (= port width + 1) bucket tops
fit = {int(k): v for k, v in r["fit_cells_per_ring"].items()}
for sc in ("now", "bound", "d4"):
    cls = collections.Counter(); waste = 0; bits = 0
    for z in r["scenarios"][sc]["classes_W>=250"]:
        W = z["W"] + 1; b = next(x for x in BUCK if x >= W)
        cls[(b, z["D"])] += z["inst"]; waste += (b - W) * fit[z["D"]]["b_per_bit"] * z["inst"]; bits += W * z["inst"]
    out[sc] = dict(classes=len(cls), list=sorted("%dd%dx%d" % (b, d, n) for (b, d), n in cls.items()),
                   pad_cells=round(waste), pad_pct_of_ring_bits=round(100 * waste / sum(fit[d]["b_per_bit"] * 0 + 1 for d in [4]) / 1, 0))
    tot = sum(fit[z["D"]]["b_per_bit"] * (z["W"] + 1) * z["inst"] for z in r["scenarios"][sc]["classes_W>=250"])
    out[sc]["pad_pct"] = round(100 * waste / tot, 1); out[sc].pop("pad_pct_of_ring_bits")
    print(sc, out[sc])
json.dump(dict(buckets_W=BUCK, scenarios=out), open(sys.argv[2], "w"), indent=1)
