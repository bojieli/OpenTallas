import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
# svcrender.py OUT.png TYPE LABEL1 PLAN1 LABEL2 PLAN2 ... : hard cores (N face red = 580-pin ib face, W face green = 590-pin ld_w),
# SRAMs orange, landing bands purple, ft station regs black dots, reset relays grey
out, tn = sys.argv[1], sys.argv[2]; pairs = list(zip(sys.argv[3::2], sys.argv[4::2]))
fig, axs = plt.subplots(1, len(pairs), figsize=(6 * len(pairs), 11))
for ax, (lab, pf) in zip(axs, pairs):
    t = json.load(open(pf))["partition_types"][tn]; W, H = t["outline_um"]
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; o = h.get("orient", "R0")
        attn = "attn" in h["lef"]
        ax.add_patch(plt.Rectangle((x, y), w, hh, color="tab:blue" if attn else "tab:cyan", alpha=.45, lw=0))
        if attn:
            ny = y if o == "MX" else y + hh
            ax.plot([x, x + w], [ny, ny], color="red", lw=1.6)
            ax.plot([x, x], [y, y + hh], color="green", lw=1.2)
    for c in t.get("contents") or []:
        if "origin_um" in c:
            x, y = c["origin_um"]; w, hh = c["outline_um"]; ax.add_patch(plt.Rectangle((x, y), w, hh, color="tab:orange", alpha=.6, lw=0))
    lc = t["clock"].get("landing_contract") or {}
    for b in (lc.get("bands") or {}).values():
        for r in (b.get("rects_um") or [b.get("rect_um")] if b.get("rect_um") or b.get("rects_um") else []):
            ax.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="purple", alpha=.5, lw=0))
    rel = (lc.get("collector_tree") or {}).get("relays") or []
    if rel: ax.scatter([r["xy"][0] for r in rel], [r["xy"][1] for r in rel], s=1, color="grey")
    for f in t.get("ft_slots") or []:
        ax.scatter([p[0] for p in f["regs_um"]], [p[1] for p in f["regs_um"]], s=6, color="black")
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.set_title("%s %s" % (tn, lab), fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=110)
