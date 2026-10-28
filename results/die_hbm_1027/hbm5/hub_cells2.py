import json, sys, collections, bisect
P = json.load(open(sys.argv[1]))
F = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
for tn in ["q_hub_nw", "q_hub_ne"]:
    t = P["partition_types"][tn]; H = t["hard_cores"]; W = t["outline_um"][0]
    hard_cells = 0; pts = []
    hinst = [h["inst"] for h in H]
    for c in t["contents"]:
        cov = [h for h in H if h["inst"] == c["inst"] or h["inst"].startswith(c["inst"] + "_") or h["inst"].startswith(c["inst"] + ".")]
        if cov: continue
        x = c["origin_um"][0] + c["outline_um"][0] / 2; pts.append((x, c["cells"], "soft"))
    st = t["internal_stations"]; nb = 0
    for s in st:
        b = s["bits"]
        for r in s["regs_um"]:
            pts.append((r[0], b * F, "st")); nb += b      # flop + ~0.6 buf/inv per station bit (UNCHECKED factor)
    tot = sum(p[1] for p in pts); soft = sum(p[1] for p in pts if p[2] == "soft")
    print(tn, "W", W, "soft cells", int(soft), "station bit-regs", nb, "est station cells", int(tot - soft), "total", int(tot))
    pts.sort(); xs = [p[0] for p in pts]; cum = [0]
    for p in pts: cum.append(cum[-1] + p[1])
    def cells(a, b): return cum[bisect.bisect_left(xs, b)] - cum[bisect.bisect_left(xs, a)]
    for k in (2, 3, 4, 5):
        # equal-cell cuts
        cuts = []; j = 0
        for i in range(1, k):
            tgt = tot * i / k; j = bisect.bisect_left(cum, tgt); cuts.append(round(xs[min(j, len(xs) - 1)], 1))
        e = [0] + cuts + [W]
        print(" k", k, "cuts", cuts, "parts kcells", [int(cells(e[i], e[i + 1]) / 1000) for i in range(k)], "widths mm", [round((e[i + 1] - e[i]) / 1000, 2) for i in range(k)])
    big = sorted([p for p in pts if p[2] == "soft"], key=lambda p: -p[1])[:3]; print(" biggest soft", [(round(p[0]), p[1]) for p in big])
# k-way partition estimate: equal-cell x cuts, crossing bits per cut (conn from/to + regs path), F factor for buffers
for tn in ["q_hub_nw", "q_hub_ne"]:
    t = P["partition_types"][tn]; W = t["outline_um"][0]; H = t["hard_cores"]
    pts = []
    for c in t["contents"]:
        if any(h["inst"] == c["inst"] or h["inst"].startswith(c["inst"] + "_") or h["inst"].startswith(c["inst"] + ".") for h in H): continue
        pts.append((c["origin_um"][0] + c["outline_um"][0] / 2, c["cells"]))
    for s in t["internal_stations"]:
        for r in s["regs_um"]: pts.append((r[0], s["bits"] * F))
    pts.sort(); tot = sum(p[1] for p in pts)
    for k in (6, 7, 8):
        cuts = []; acc = 0; i = 1
        for x, c in pts:
            acc += c
            if acc >= tot * i / k and i < k: cuts.append(x + 0.01); i += 1
        e = [0] + cuts + [W]; parts = [int(sum(c for x, c in pts if e[j] <= x < e[j + 1]) / 1000) for j in range(k)]
        xb = []
        for cx in cuts:
            b = 0
            for s in t["internal_stations"]:
                xs = [s["from_um"][0]] + [r[0] for r in s["regs_um"]] + [s["to_um"][0]]
                b += s["bits"] * sum(1 for a, z in zip(xs, xs[1:]) if min(a, z) < cx <= max(a, z))
            xb.append(b)
        print(tn, "F", F, "k", k, "kcells", parts, "cut x", [round(c) for c in cuts], "cut bits", xb)
