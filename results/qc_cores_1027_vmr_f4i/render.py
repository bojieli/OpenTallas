import sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
geo, out, title = sys.argv[1], sys.argv[2], sys.argv[3]; W = [float(v) for v in sys.argv[4].split(",")]
L = [l.split() for l in open(geo)]
fig, ax = plt.subplots(1, 2, figsize=(20, 9), gridspec_kw={"width_ratios": [1.2, 1]})
col = {"macro": "#b0b0b0", "tap": "#999999", "clk": "#d62728", "cell": "#1f77b4", "blk": "#ff7f0e", "pad": "#2ca02c"}
for a, full in ((ax[0], True), (ax[1], False)):
    for l in L:
        k = l[0]; x0, y0, x1, y1 = map(float, l[1:5])
        if k == "core": a.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fill=False, ec="k", lw=1)); continue
        if not full and (x1 < W[0] or x0 > W[2] or y1 < W[1] or y0 > W[3]): continue
        if full and k == "pad": continue
        if full and k == "cell": a.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=col[k], ec="none", alpha=0.6)); continue
        a.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=col[k], ec="k" if (not full and k in ("cell","clk")) else "none",
                              lw=0.3, alpha=0.35 if k == "blk" else 0.8))
        if not full and k in ("cell", "clk") and l[5] == "_10830_": a.text(x0, y1, "_10830_", fontsize=7, color="m")
    if full: a.set_xlim(0, 251); a.set_ylim(0, 216); a.set_title(title + " - whole core (orange = 56 keep-out bands, grey = SRAM, red = clock cells)")
    else: a.set_xlim(W[0], W[2]); a.set_ylim(W[1], W[3]); a.set_title("window x%.0f-%.0f y%.0f-%.0f: cells (blue), keep-out (orange), PG M3 via pads (green)" % tuple(W))
    a.set_aspect("equal")
plt.tight_layout(); plt.savefig(out, dpi=110)
