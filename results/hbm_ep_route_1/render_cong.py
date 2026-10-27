import sys, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
T = sys.argv[1]
fig, ax = plt.subplots(figsize=(9, 12)); ax.add_patch(plt.Rectangle((0, 0), 250.56, 375.84, fill=False, lw=1.5))
for l in open(T + "eproute_pins.csv"):
    f = l.strip().split(",")
    if f[0] == "macro":
        x, y, w, h = map(float, f[3:7]); ax.add_patch(plt.Rectangle((x, y), w, h, fc="#dddddd", ec="gray"))
for l in open(T + "eproute_cong.txt"):
    d, cap, use, cg, x0, y0, x1, y1 = l.split(); x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
    ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fc=("r" if d == "Horizontal" else "b"), ec="none", alpha=min(1, 0.15 + 0.1 * int(cg))))
col = {"N": "g", "S": "m", "E": "c", "W": "orange"}
for q in json.load(open(T + "pins.json")): ax.plot(q["x"], q["y"], ".", color=col[q["face"]], ms=1.5)
ax.plot(125.28, 187.92, "b*", ms=14)
ax.set_aspect("equal"); ax.set_xlim(-5, 256); ax.set_ylim(-5, 381)
ax.set_title("HBM-EP-ROUTE-1 hfd_ep_static GRT FAIL: GRT-0116 total overflow 64,245 (M2 26,395 / M3 31,007 / M4 5,339 / M5 1,504)\n"
             "first 20,000 congestion items of congestion.rpt (red = H, blue = V; alpha ~ overflow); SRAM grey; pins by face (S magenta, W orange, E cyan, N green)", fontsize=7)
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=120)
