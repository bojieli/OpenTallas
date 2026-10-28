import json, statistics as st, collections, sys
Q = "/srv/opentallas-scratch2/claude/die-qc16-1028"
t = json.load(open(f"{Q}/trial12/clock/tree.json"))
ev = json.load(open(f"{Q}/ev/qc_k2b_p12_a0early.json")); T = ev["partition_types"]; parts = {p["name"]: p for p in ev["partitions"]}
for C, k in (("TT", 0), ("FF", 1)):
    arr = {}
    for ln in open(f"{Q}/c12_{C}/arr_{C}.txt"):
        f = ln.split()
        if f[0] == "T": arr[f[1]] = float(f[2])
    by = collections.defaultdict(lambda: ([], []))
    for x in t["taps"]:
        if not x["part"].startswith("c_"): continue
        by[x["part"]][1 if x["tap"].startswith("clk_c") else 0].append((x["tap"], arr[x["port"]]))
    need = {"nk": (486.0, 436.5)[k], "nl": (546.0, 491.5)[k]}
    got = collections.defaultdict(list); err = []
    for pn, (g, c) in by.items():
        gm = st.mean(a for _, a in g)
        tp = [x for x in T[parts[pn]["type"]]["clock"]["taps"] if x.get("kind") == "core"]
        mods = {h["inst"]: h["module"] for h in T[parts[pn]["type"]]["hard_cores"]}
        for (nm, a), x in zip(sorted(c, key=lambda z: int(z[0][5:])), tp):
            v = mods[x["name"].split(".")[0]][9:11]
            got[v].append(gm - a); err.append(gm - a - need[v])
    for v, L in got.items():
        print(C, v, "n", len(L), "achieved early min/med/max %.0f/%.0f/%.0f need %.1f" % (min(L), st.median(L), max(L), need[v]))
    print(C, "shortfall (need - achieved) min/med/max %.0f/%.0f/%.0f" % (-max(err), -st.median(err), -min(err)))
