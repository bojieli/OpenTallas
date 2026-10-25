import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = sys.argv[1]; outp = sys.argv[2]
P = json.load(open(os.path.join(d, "die_plan.json")))
t = P["partition_types"]["q_hub_nw"]; W, H = t["outline_um"]
fig, ax = plt.subplots(figsize=(24, 8))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
new = {"u_hb_coll_Q_body_core": "gold", "u_hb_coll_Q_edge": "orange", "u_hb_coll_Q_vm": "violet"}
for c in t["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    ax.add_patch(Rectangle((x, y), w, h, fc=new.get(c["inst"], "lightsteelblue"), ec="navy", lw=0.6))
    if c["inst"] in new:
        pins = json.load(open(os.path.join(d, c["pins_file"])))
        ax.plot([x + p["x"] for p in pins[::8]], [y + p["y"] for p in pins[::8]], ",", color="crimson")
    if w * h > 0.004 * W * H or c["inst"] in new:
        ax.text(x + w / 2, y + h / 2, c["inst"].replace("u_hb_", ""), fontsize=6, ha="center", va="center")
for c in t["contents"]:
    if c["inst"] == "u_tkx_tx_Q":
        x, y = c["origin_um"]; w, h = c["outline_um"]
        ax.add_patch(Rectangle((x, y), w, h, fc="lime", ec="darkgreen", lw=1.2)); ax.text(x + w / 2, y + h / 2, "TX", fontsize=8, ha="center")
for s in t["internal_stations"]:
    n = s.get("note", "")
    if "HUBNW" not in n: continue
    pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]
    if s["conn"] == "bus:L74_o": col, lw = "red", 1.6
    elif s["conn"] == "bus:L13_i" and ("tkx" in s["capture"] or "tkw" in s["capture"]): col, lw = "magenta", 1.2
    elif s["conn"].endswith("u_tkx_tx_Q"): col, lw = "darkgreen", 0.8
    elif "R3-INTERNAL" in n.split("|")[0]: col, lw = "teal", 0.4
    else: col, lw = "0.6", 0.3
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=col, lw=lw, alpha=0.8)
    ax.plot([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], ".", color=col, ms=2)
for pr in P["ports"]:
    if pr["id"] in ("L74_0", "L13_0"):
        a, b = pr["window_um"]
        hub = [p for p in P["partitions"] if p["name"] == "NW_hub"][0]
        ox, oy = hub["origin_um"]
        if pr["face"] in "NS": ax.plot([a - ox, b - ox], [0, 0], "-", color="red", lw=5)
        else: ax.plot([W, W], [a - oy, b - oy], "-", color="magenta", lw=5)
# HUBNW2: reserved face segments (body N -> TX for the TKM source bits, edge W -> link windows)
try:
    R = json.load(open(os.path.join(d, "q_hub_nw_report.json")))
    hc = {c["inst"]: c for c in t["hard_cores"]}
    for k, v in R.get("pieces", {}).items():
        sg = v.get("reserved_segment")
        if not sg: continue
        x, y = hc[k]["origin_um"]; w, h = hc[k]["outline_um"]; a, b = sg["segment"]
        xy = dict(N=([x + a, x + b], [y + h, y + h]), S=([x + a, x + b], [y, y]),
                  E=([x + w, x + w], [y + a, y + b]), W=([x, x], [y + a, y + b]))[sg["face"]]
        ax.plot(*xy, "-", color="lime" if sg["tag"] == "tkm" else "blue", lw=4, alpha=0.7)
        ax.text(xy[0][0], xy[1][0] + 12, "%s %d pins (%s face)" % (sg["tag"], sg["pins"], sg["face"]), fontsize=7)
except (OSError, KeyError):
    pass
ax.set_xlim(-50, W + 50); ax.set_ylim(-50, H + 50); ax.set_aspect("equal")
ax.set_title("q_hub_nw %gx%g: gold body_core, orange edge, violet vm, lime TX; red = L74 1171-b beat chain TX->L74_o (S face window), magenta = L13 tkx return, green = body->TX, teal = new, grey = rerouted" % (W, H), fontsize=9)
fig.tight_layout(); fig.savefig(outp, dpi=110)
# zoom on the W end
ax.set_xlim(-30, 1500); ax.set_ylim(-30, 1700); fig.set_size_inches(13, 14); fig.tight_layout(); fig.savefig(outp.replace(".png", "_west.png"), dpi=110)
