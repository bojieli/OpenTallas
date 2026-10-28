# DIE-QC-18: decomposition of a step: sink mid spread (trunk) vs widest cluster local tree, per corner
import json, sys
D, g = sys.argv[1], sys.argv[2]
o = json.load(open("%s/ocv_%s.json" % (D, g))); d = json.load(open("%s/trunk_%s_built.json" % (D, g)))
CI = d["summary"]["child_ins"]; G = json.load(open(D + "/" + d["cl"])); r2c = {r.replace("\\", ""): c["name"] for c in G["clusters"] for r in c["regs"]}
print(D, g, {C: (o[C]["nominal_spread"], o[C]["ocv_inclusive_spread"], o[C]["worst_pair"]) for C in o})
for C, ci in (("TT", 0), ("FF", 1)):
    R = {}
    for l in open("%s/arr_%s_%s.txt" % (D, g, C)):
        p = l.split()
        if not p or p[0] != "S" or p[2].startswith("ICG"): continue
        i = p[1].rsplit("/", 1)[0].replace("\\", "")
        if p[2] in CI: nm = i; v = float(p[4]) + CI[p[2]][ci]
        else:
            nm = r2c.get(i); v = float(p[4])
            if nm is None: continue
        R.setdefault(nm, []).append(v)
    mids = sorted(((min(v) + max(v)) / 2, n) for n, v in R.items()); w = sorted((max(v) - min(v), n) for n, v in R.items())
    print("  %s mid spread %.1f (%s %.1f .. %s %.1f) widths top3 %s insertion max %.1f" % (C, mids[-1][0] - mids[0][0], mids[0][1][-10:], mids[0][0], mids[-1][1][-10:], mids[-1][0], [(round(a, 1), b[-8:]) for a, b in w[-3:]], max(max(v) for v in R.values())))
