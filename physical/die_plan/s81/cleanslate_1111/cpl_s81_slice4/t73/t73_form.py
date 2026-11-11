#!/usr/bin/env python3
"""CPL-S81-SLICE-4 t73 hand form ST2 (two straight N-S ft streets).  Writes the positions delta, the ft station
re-site (regs_um[1:] + bit_sites rows translated rigidly, regs_um[0] = in-face flop unchanged), the band move and an
intent SVG.  usage: t73_form.py BASE_PLAN OUTDIR [--draw-only]"""
import json, sys, os
T = "ot_s81sl_leaf__t73"
POS = {  # inst: (x, y, orient)  -- orients unchanged
    "u_lf.u_ve.u_m": (155.52, 43.2, "R180"),
    "u_lf.u_vsw": (103.68, 423.36, "MX"),
    "u_lf.u_ve.u_s": (449.28, 43.2, "R180"),
    "u_lf.u_vs": (449.28, 423.36, "R180"),
    "u_lf.u_rxsf": (449.28, 630.72, "MX"),
    "u_lf.u_rxsb": (449.28, 812.16, "MX"),
    "u_lf.u_vq": (768.96, 43.2, "R180"),
}
STREETS = {"W (ft7)": (0, 103.68), "A (ft8, ft0-3)": (328.32, 449.28), "B (ft4-6, ft9)": (622.08, 768.96)}
FTX = {"ft7": 51.84, "ft8": 384.48, "ft0": 414.72, "ft1": 423.36, "ft2": 432.0, "ft3": 440.64,
       "ft4": 630.72, "ft5": 639.36, "ft6": 660.96, "ft9": 704.16}
BANDS = {"ft8_i": [332.64, 17.28, 356.4, 254.556]}
base, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
t = json.load(open(base))["partition_types"][T]
W, H = t["outline_um"][:2]
hc = {h["inst"]: h for h in t["hard_cores"]}
for i, (x, y, o) in POS.items():
    assert hc[i]["orient"] == o, (i, hc[i]["orient"])
json.dump({T: {i: [x, y, o] for i, (x, y, o) in POS.items()}}, open(f"{out}/t73_pos.json", "w"), indent=1)
ft = {}
for f in t["ft_slots"]:
    x = FTX[f["name"]]
    n = len(f["regs_um"]); y0 = f["regs_um"][0][1]
    win = lambda w: (w[0] + w[1]) / 2
    jin = abs(f["regs_um"][0][0] - x); jout = abs(win(f["out_window_um"]) - x)
    h = (jin + jout + H) / n; sg = -1 if y0 > H / 2 else 1
    ys = [y0 + sg * ((h - jin) + (k - 1) * h) for k in range(1, n)]
    ys = [round(round(y / 0.27) * 0.27, 3) for y in ys]
    regs = [list(f["regs_um"][0])] + [[x, y] for y in ys]
    rows = []
    for r_old, r_new, row in zip(f["regs_um"][1:], regs[1:], f["bit_sites_um"]):
        dx = r_new[0] - r_old[0]; dy = r_new[1] - r_old[1]
        rows.append([[round(p[0] + dx, 3), round(p[1] + dy, 3)] for p in row])
    ft[f["name"]] = {"regs_um": regs, "bit_sites_um": rows}
json.dump({T: ft}, open(f"{out}/t73_ft.json", "w"))
json.dump({T: BANDS}, open(f"{out}/t73_bands.json", "w"), indent=1)
# legality pre-check: core-core gap >= 34.56, inside outline, streets clear
box = {i: (POS[i][0] if i in POS else h["origin_um"][0], POS[i][1] if i in POS else h["origin_um"][1]) for i, h in hc.items()}
box = {i: (x, y, x + hc[i]["outline_um"][0], y + hc[i]["outline_um"][1]) for i, (x, y) in box.items()}
bad = []
ks = sorted(box)
for a in range(len(ks)):
    for b in range(a + 1, len(ks)):
        p, q = box[ks[a]], box[ks[b]]
        g = max(q[0] - p[2], p[0] - q[2], q[1] - p[3], p[1] - q[3])
        if g < 34.56 - 1e-6: bad.append((ks[a], ks[b], round(g, 2)))
for nm, (x0, x1) in STREETS.items():
    for i, r in box.items():
        if r[0] < x1 - 1e-6 and r[2] > x0 + 1e-6: bad.append(("street", nm, i))
print("gap/street problems:", bad)
# intent SVG
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
fig, axs = plt.subplots(1, 2, figsize=(20, 9))
for ax, tag in zip(axs, ("before (BASE_1200)", "after ST4 (hand form)")):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for i, h in hc.items():
        x, y = (h["origin_um"] if tag.startswith("before") else box[i][:2])
        w, hh = h["outline_um"]
        ax.add_patch(Rectangle((x, y), w, hh, fc="#c9d6e8" if "g_ln" not in i else "#e8e0c9", ec="k", lw=.6))
        if "g_ln" not in i: ax.text(x + w / 2, y + hh / 2, i.replace("u_lf.", ""), ha="center", va="center", fontsize=7)
    for f in t["ft_slots"]:
        for k, win in (("in", f["in_window_um"]), ("out", f["out_window_um"])):
            fy = 0 if f[k + "_face"] == "S" else H
            ax.plot(win, [fy, fy], lw=4, color="tab:orange" if k == "in" else "tab:blue")
        regs = f["regs_um"] if tag.startswith("before") else ft[f["name"]]["regs_um"]
        oc = [(f["out_window_um"][0] + f["out_window_um"][1]) / 2, 0 if f["out_face"] == "S" else H]
        pts = regs + [oc]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "-o", ms=2.5, lw=.9 + f["width"] / 400, color="tab:red", alpha=.75)
        ax.text(regs[0][0], regs[0][1] + (12 if regs[0][1] < 1 else -28), f"{f['name']}\n{f['width']}b", fontsize=6, ha="center")
    if not tag.startswith("before"):
        for nm, (x0, x1) in STREETS.items():
            ax.add_patch(Rectangle((x0, 0), x1 - x0, H, fc="#7fd17f", alpha=.18, lw=0))
            ax.text((x0 + x1) / 2, H / 2, f"street {nm}\n{x1 - x0:.0f} um", rotation=90, ha="center", va="center", fontsize=8, color="darkgreen")
        def arr(a, b, txt, lw):
            ca = ((box[a][0] + box[a][2]) / 2, (box[a][1] + box[a][3]) / 2); cb = ((box[b][0] + box[b][2]) / 2, (box[b][1] + box[b][3]) / 2)
            ax.add_patch(FancyArrowPatch(ca, cb, arrowstyle="-|>", mutation_scale=12, lw=lw, color="purple", alpha=.7))
            ax.text((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2, txt, fontsize=7, color="purple")
        arr("u_lf.u_vs", "u_lf.u_ve.u_m", "1484b", 3); arr("u_lf.u_ve.u_m", "u_lf.u_ve.u_s", "772b", 2.4)
        arr("u_lf.u_vs", "u_lf.u_vsw", "642b", 2.2); arr("u_lf.u_vs", "u_lf.u_vq", "542b", 2.1)
        arr("u_lf.u_ve.u_s", "u_lf.u_vs", "200b", 1.4); arr("u_lf.u_rxsf", "u_lf.u_rxsb", "192b", 1.4)
        arr("u_lf.u_vn.u_b", "u_lf.u_vp.g_ln[7].u_l", "vn->16 g_ln 256b stations", 1.4)
    ax.set_xlim(-20, W + 20); ax.set_ylim(-40, H + 40); ax.set_aspect("equal"); ax.set_title(f"{T} {tag}")
fig.suptitle("t73 ST4 intent: S buses leafdn_i0/leafup_o0 (E) -> vn/vq/vs -> ve_m/ve_s/vsw; 3.9 kb N-S ft in two straight streets A/B (+W for ft7)", fontsize=10)
fig.tight_layout(); fig.savefig(f"{out}/t73_intent.svg"); fig.savefig(f"{out}/t73_intent.png", dpi=90)
