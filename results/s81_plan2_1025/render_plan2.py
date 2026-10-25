"""S81-PLAN2 GEOM renders: (1) svc fold faces before/after gather B, (2) IR split per serdes window."""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base, new, out = sys.argv[1], sys.argv[2], sys.argv[3]
B, N = json.load(open(base)), json.load(open(new))
COL = {}
def col(n):
    k = n.split("_")[0]
    return {"attnh": "tab:red", "attn": "tab:blue", "hbm": "tab:green", "rsv": "tab:purple", "vid": "tab:orange"}.get(k, "tab:gray")
def fold(raw, ax, title):
    PA = {x["name"]: x for x in raw["partitions"]}
    T = raw["partition_types"]
    for i in range(8):
        H = PA[f"svc_{2*i+1}"]; th = T[H["type"]]; W = th["outline_um"][0]
        y = 8 - i
        ax.add_patch(Rectangle((0, y - 0.4), W, 0.8, fill=False, lw=0.5))
        for b in th["buses"]:
            if b["face"] != "S": continue
            a0, a1 = sorted(b["window_um"])
            nl = len(b["layers"]); d = b["width"] / (a1 - a0)
            ax.add_patch(Rectangle((a0, y - 0.35), a1 - a0, 0.7, color=col(b["name"]), alpha=0.6))
            ax.text((a0 + a1) / 2, y, f"{b['name']}\n{b['width']}b {d:.1f}/um {nl}L", ha="center", va="center", fontsize=5)
        for s in th.get("ft_slots", []):
            for k in ("in", "out"):
                if s[f"{k}_face"] == "S":
                    a0, a1 = sorted(s[f"{k}_window_um"])
                    ax.add_patch(Rectangle((a0, y - 0.4), a1 - a0, 0.8, color="k", alpha=0.4))
        ax.text(-20, y, f"svc_{2*i+1}/svc_{2*i}\n{H['type'].replace('dsdv_svc_','')}", ha="right", va="center", fontsize=6)
    ax.set_xlim(-420, 1460); ax.set_ylim(0.3, 8.7); ax.set_yticks([]); ax.set_title(title, fontsize=9); ax.set_xlabel("hi S face = lo N face, type x (um); black = ft windows (fixed)")
fig, axs = plt.subplots(2, 1, figsize=(16, 12), dpi=130)
fold(B, axs[0], "BEFORE (main 26028effc): attnh 1068 b x 2 beats on M7/M5")
fold(N, axs[1], "AFTER gather B: attnh 2133 b x 1 beat on M7/M5/M3 (face_layers), all bus windows re-laid at one density")
fig.tight_layout(); fig.savefig(out + "/s81_svc_fold_gatherB.png")
# IR
io = [w for w in N["die"]["io"] if w.get("iface") == "serdes"]
doms = {d["io"][0]: d for d in N["die"]["pg"]["domains"]}
PA = {x["name"]: x for x in N["partitions"]}
fig, axs = plt.subplots(3, 5, figsize=(22, 13), dpi=110); axs = axs.ravel()
for ax, w in zip(axs, io):
    p = PA[w["part"]]; T = N["partition_types"][p["type"]]; ow, oh = T["outline_um"]
    o = p["origin_um"]
    # orient-agnostic: partition rect in die coords
    rw, rh = (oh, ow) if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90") else (ow, oh)
    ax.add_patch(Rectangle(o, rw, rh, fill=False, lw=1.2, label="partition"))
    d = doms.get(w["name"])
    if d:
        r = d["rect_um"]; ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], color="gold", alpha=0.35, label="VDDPHY domain"))
        for c in d.get("core_strip_um", []):
            ax.add_patch(Rectangle(c[:2], c[2]-c[0], c[3]-c[1], color="tab:blue", alpha=0.25, label="core strip"))
        m = d.get("phy_macro_um")
        if m: ax.add_patch(Rectangle(m[:2], m[2]-m[0], m[3]-m[1], color="tab:red", alpha=0.5, label="PHY macro"))
    r = w["rect_um"]; ax.add_patch(Rectangle(r[:2], r[2]-r[0], r[3]-r[1], fill=False, ec="red", ls="--", lw=1, label="io window"))
    ax.set_xlim(o[0]-150, o[0]+rw+150); ax.set_ylim(o[1]-150, o[1]+rh+150); ax.set_aspect("equal")
    m = d.get("phy_macro_um") if d else None
    am = (m[2]-m[0])*(m[3]-m[1])/1e6 if m else 0
    ax.set_title(f"{w['name']} {w['part']} {p['type']} {p.get('orient','R0')}\nmacro {am:.2f} mm2" + (" PHY_SHORT" if m and am < 2.399 else "") + ("" if m else " UNSPLIT"), fontsize=7)
    ax.tick_params(labelsize=5)
axs[0].legend(fontsize=6, loc="upper right")
for ax in axs[len(io):]: ax.axis("off")
fig.tight_layout(); fig.savefig(out + "/s81_ir_split.png")
print("ok")
