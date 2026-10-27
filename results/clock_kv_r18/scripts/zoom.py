import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B, out, box = sys.argv[1], sys.argv[2], [float(v) for v in sys.argv[3].split(",")]
m = json.load(open(B + "/mesh.json")); xs, ys = m["xs"], m["ys"]
fig, ax = plt.subplots(figsize=(11, 8))
sp = m.get("strap_spans", {})
for i, x in enumerate(xs):
    s = sp.get(f"V:{i}:None") or [ys[0], ys[-1]]
    ax.plot([x, x], s, color="#3060c0", lw=1.4, alpha=.6)
for j, y in enumerate(ys):
    s = sp.get(f"H:{j}:None")
    if s: ax.plot(s, [y, y], color="#30a0c0", lw=1.0, alpha=.6)
dv = [d["site"] for d in m["drivers"].values()]
ax.scatter([p[0] for p in dv], [p[1] for p in dv], s=14, c="red", marker="s", label="mesh driver (leaf)")
for t in m["taps"]:
    c = "magenta" if t.get("band_tree") else "green"
    ax.plot([t["foot"][0], t["xy"][0]], [t["foot"][1], t["foot"][1]], color=c, lw=.8)
    ax.plot([t["xy"][0], t["xy"][0]], [t["foot"][1], t["xy"][1]], color=c, lw=.8)
    ax.scatter([t["xy"][0]], [t["xy"][1]], s=10, c=c, marker="o")
    ax.scatter([t["foot"][0]], [t["foot"][1]], s=10, c="k", marker="x")
for lo, hi in m["meta"]["band_trees"]["cover_um"]:
    ax.axhspan(lo, hi, color="#e0f0e0", alpha=.25, zorder=-1)
ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_aspect("equal")
ax.set_title(f"CLOCK-KV-R18 band_feed strap: band stubs (magenta) fed from DRIVEN mesh at the edge leaf row; mesh stubs green; x = stub foot; shaded = strap cover")
ax.legend(loc="upper right", fontsize=8); fig.tight_layout(); fig.savefig(out, dpi=110)
