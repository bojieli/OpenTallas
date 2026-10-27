"""KV-CORE-SLICE-1 render: one panel per sliced core type, core frame (R0 master), same um scale for every panel."""
import json, sys, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

d = json.load(open(sys.argv[1]))
rows = [(m, r) for m, r in d["types"].items() if "out_of_slice" not in r]
order = ["qkd_ahub", "qkd_kvs_ctl", "kv3_pv_pair", "ot_qwen_tp8_pv_join_t", "qkd_kvs_pc", "qkd_kvs_pc_h_head_p"]
rows.sort(key=lambda t: (order.index(t[0]) if t[0] in order else 99, t[0]))
n = len(rows); nc = 6; nr = math.ceil(n / nc)
fig, axs = plt.subplots(nr, nc, figsize=(nc * 4.2, nr * 3.6))
S = 620.0
for ax, (m, r) in zip(axs.flat, rows):
    w, h = r["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.2, ec="k"))
    if r.get("outline_delta"):
        ow, oh = r["outline_delta"]["old_um"]
        ax.add_patch(Rectangle((w - ow, 0), ow, oh, fill=False, lw=0.8, ec="0.6", ls="--"))
    e = r.get("entry")
    if e:
        x0, y0, x1, y1 = e["island_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="red", alpha=0.9))
        for p in e["pins"]:
            fx, fy = p["from_"][1], p["from_"][2]
            ax.plot([fx], [fy], "x", color="0.4", ms=5)
        ct = r.get("core_tree") or {}
        for q in ct.get("islands", []):
            cx, cy = q["centre_um"]
            ax.plot([e["xy_um"][0], cx, cx], [e["xy_um"][1], e["xy_um"][1], cy], "-", color="orange", lw=0.8)
            a0, b0, a1, b1 = q["rect_um"]
            ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, color="orange", alpha=0.9))
    for q in ((r.get("die_islands") or {}).get("points") or []):
        a0, b0, a1, b1 = q["rect_um"]
        ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, color="tab:blue", alpha=0.9))
    for pc in r.get("phy_clocks") or []:
        ax.plot([pc["xy"][0]], [pc["xy"][1]], "s", color="purple", ms=5)
    im = r.get("insertion_model") or {}
    tr = r.get("trunk")
    ttl = f"{m}\n{w:g}x{h:g} n={r['instances']}"
    if e:
        ttl += f" grid {ct.get('grid')} pred {im.get('pred_TT_ps')}" + (f" +{tr['n']}xBUF" if tr else "")
    else:
        ttl += " ck_phy (PHY domain)"
    ax.set_title(ttl, fontsize=7)
    ax.set_xlim(-10, S); ax.set_ylim(-10, S * 0.75); ax.set_aspect("equal"); ax.tick_params(labelsize=5)
for ax in list(axs.flat)[n:]:
    ax.axis("off")
fig.suptitle("KV-CORE-SLICE-1 per-type core slice (core frame, um). red = 12.8a centre entry island (M9->M5 stack, ck/rst M5 pins); "
             "orange = in-core H-tree islands + trunk; blue = R15 die pushdown islands; grey x = old face clock/reset pin; "
             "purple = ck_phy (stays at PHY face); dashed = old outline", fontsize=9)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(sys.argv[2], dpi=110)
print("wrote", sys.argv[2])
