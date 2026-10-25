import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
# render_q_hub_ne.py PLAN_DIR OUT.png : q_hub_ne (PATH-HBM/NE2 10-25) pieces, pins, new/rerouted station chains
d = sys.argv[1]; outp = sys.argv[2]
P = json.load(open(os.path.join(d, "die_plan.json")))
t = P["partition_types"]["q_hub_ne"]; W, H = t["outline_um"]
fig, ax = plt.subplots(figsize=(24, 8))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
new = {"u_hb_coll_Q_body_n2": "gold", "u_hb_coll_Q_vm": "violet"}
for c in t["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    ax.add_patch(Rectangle((x, y), w, h, fc=new.get(c["inst"], "lightsteelblue"), ec="navy", lw=0.6))
    if c["inst"] in new:
        pins = json.load(open(os.path.join(d, c["pins_file"])))
        ax.plot([x + p["x"] for p in pins[::4]], [y + p["y"] for p in pins[::4]], ".", color="crimson", ms=1)
    if w * h > 0.004 * W * H or c["inst"] in new or "coll" in c["inst"]:
        ax.text(x + w / 2, y + h / 2, c["inst"].replace("u_hb_", ""), fontsize=6, ha="center", va="center")
for c in t["contents"]:
    if "origin_um" in c and not any(h["inst"] == c["inst"] for h in t["hard_cores"]) and c["inst"] in (
            "u_hcollrs_Q", "u_hcollks_Q_p0", "u_hcollks_Q_p1", "u_hcollks_Q_p2", "u_hcollks_Q_p3", "u_hleaf_Q", "u_obs_Q",
            "u_cic_Q", "u_cxrc_Q_s", "u_fr_Q"):
        x, y = c["origin_um"]; w, h = c["outline_um"]
        ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="green", lw=0.8)); ax.text(x, y + h, c["inst"], fontsize=5, color="green")
for s in t["internal_stations"]:
    n = s.get("note", "")
    if "NE2" not in n: continue
    pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]
    col, lw = ("teal", 0.6) if "R3-INTERNAL" in n.split("|")[0] else ("0.6", 0.3)
    if "u_hb_coll_Q_vm" in s["conn"] or s.get("capture") == "u_hb_coll_Q_vm": col, lw = "purple", 1.0
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "-", color=col, lw=lw, alpha=0.8)
    ax.plot([p[0] for p in s["regs_um"]], [p[1] for p in s["regs_um"]], ".", color=col, ms=3)
ax.set_xlim(-50, W + 50); ax.set_ylim(-50, H + 50); ax.set_aspect("equal")
ax.set_title("q_hub_ne %gx%g (type-local; NE_hub is MY): gold body_n2, violet vm; teal = new chains, purple = body<->vm / vm, grey = rerouted, green = leaf partners" % (W, H), fontsize=9)
fig.tight_layout(); fig.savefig(outp, dpi=110)
ax.set_xlim(-30, 3400); ax.set_ylim(-30, H + 30); fig.set_size_inches(16, 12); fig.tight_layout(); fig.savefig(outp.replace(".png", "_west.png"), dpi=110)
