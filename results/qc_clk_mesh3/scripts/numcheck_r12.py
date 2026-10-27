import json, glob
out = {}
for n in ("isl",):
    S = {}
    for c in ("TT", "FF"):
        S[c] = {}
        for f in glob.glob(f"{n}/{c}_s*.json"):
            d = json.load(open(f)); S[c][d["sample"]] = d["tap_arr_ps"]
    pu = json.load(open(f"{n}/sta_in/pair_unc.json"))
    rows = {r["a"] + "|" + r["b"]: r for r in pu["rows"]}
    reg = {c: json.load(open(f"{n}/sta/regchar/{c}.json")) for c in ("TT", "FF")}
    plan = json.load(open("../inputs/candidate_oneqc0733.json"))
    taps = set(S["TT"][0])
    dirs = {(p["src"]["part"], p["dst"]["part"]) for p in plan["ports"] if p["src"]["part"] != p["dst"]["part"] and p["src"]["part"] in taps and p["dst"]["part"] in taps}
    wh = ws = 1e9; worst = None
    for a, b in dirs:
        row = rows["|".join(sorted((a, b)))]
        d0 = S["FF"][0]
        var = max(abs((s[a] - s[b]) - (d0[a] - d0[b])) for s in S["FF"].values())
        assert abs(var - row["FF"]["mesh_mc_var_ps"]) < 0.01
        U = row["FF"]["aocv_random_ps"] + row["FF"]["aocv_distance_ps"] + var
        h = (d0[a] + reg["FF"]["clkq_min_nowire_ps"]) - (d0[b] + reg["FF"]["hold_ps"]) - 25.0 - U
        if h < wh: wh, worst = h, (a, b)
        t0 = S["TT"][0]
        varT = max(abs((s[a] - s[b]) - (t0[a] - t0[b])) for s in S["TT"].values())
        UT = row["TT"]["aocv_random_ps"] + row["TT"]["aocv_distance_ps"] + varT
        st = 833.333 - 60.0 - (t0[a] + reg["TT"]["clkq_max_wire_ps"]) + (t0[b] - reg["TT"]["setup_ps"]) - UT
        ws = min(ws, st)
    # whole-pair U (r3 method) max recomputed
    tot = {c: max(max(abs(s[r["a"]] - s[r["b"]]) for s in S[c].values()) + r[c]["aocv_random_ps"] + r[c]["aocv_distance_ps"] for r in pu["rows"]) for c in ("TT", "FF")}
    print(n, "ordered", len(dirs), "nsamples", len(S["TT"]), len(S["FF"]), "TTsetup %.2f FFhold %.2f worst %s" % (ws, wh, worst), "pairU max TT %.2f FF %.2f" % (tot["TT"], tot["FF"]),
          "nominal spread TT %.2f FF %.2f" % (max(S["TT"][0].values()) - min(S["TT"][0].values()), max(S["FF"][0].values()) - min(S["FF"][0].values())))
