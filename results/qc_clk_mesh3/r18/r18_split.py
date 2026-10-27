import json, sys, statistics as S
r2 = json.load(open(sys.argv[1])); pu = json.load(open(sys.argv[2]))
tap = {t["part"]: t for t in r2["taps"]}
W = max(t["entry"][0] for t in r2["taps"]); H = max(t["entry"][1] for t in r2["taps"])
XC, YC = float(sys.argv[3]), float(sys.argv[4])
cls = {}
for r in pu["rows"]:
    a, b = tap[r["a"]]["entry"], tap[r["b"]]["entry"]
    sx = (a[0] - XC) * (b[0] - XC) < 0; sy = (a[1] - YC) * (b[1] - YC) < 0
    k = ("crossX" if sx else "") + ("crossY" if sy else "") or "same_half"
    cls.setdefault(k, []).append(r)
for k, v in sorted(cls.items()):
    for c in ("FF",):
        x = sorted(r[c]["mesh_mc_var_ps"] for r in v)
        print(f"{k:12s} n {len(v):4d} FF mesh_mc_var med {S.median(x):6.2f} p90 {x[int(.9*(len(x)-1))]:6.2f} max {x[-1]:6.2f}")
w = sorted(pu["rows"], key=lambda r: -r["FF"]["mesh_mc_var_ps"])[:8]
for r in w:
    print(r["a"], tap[r["a"]]["entry"], r["b"], tap[r["b"]]["entry"], r["FF"]["mesh_mc_var_ps"])
