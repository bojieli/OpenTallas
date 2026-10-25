import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d, root_png, die_png = sys.argv[1:4]
p = json.load(open(d + "/die_plan.json")); t = p["partition_types"]["root"]
rep = json.load(open(d + "/b2p_r1_report.json"))
fig, ax = plt.subplots(figsize=(7, 18)); W, H = t["outline_um"]
ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=2))
for c in t["contents"]:
    if c["inst"] == "u_tkm_SW" or "origin_um" not in c: continue
    x, y = c["origin_um"]; w, h = c["outline_um"]
    ax.add_patch(plt.Rectangle((x, y), w, h, fc="#ddd", ec="#999", lw=.5, ls="--"))
R = []
for c in t["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]; R.append((x, y, w, h))
    fc = "#9cf" if "tile" in c["inst"] else ("#f96" if "tkm" in c["inst"] else ("#fc9" if "hc_eng" in c["inst"] else "#cfc"))
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="k", lw=.6))
    lab = c["inst"].replace("u_tkm_SW_", "").replace("u_hc_eng_", "hc:").replace("u_", "") + ("/" + c["orient"] if c.get("orient") else "")
    ax.text(x + w / 2, y + h / 2, lab, fontsize=4.5, ha="center", va="center", rotation=90 if "hc:" in lab else 0)
nb = 0
for s in t["internal_stations"]:
    pts = [s["from_um"]] + s["regs_um"] + [s["to_um"]]; tk = "tkm" in s["conn"]
    ax.plot([q[0] for q in pts], [q[1] for q in pts], "-", lw=.9 if tk else .3, color="r" if tk else "#7a7", alpha=.9 if tk else .4)
    for q in s["regs_um"]:
        if any(r[0] < q[0] < r[0] + r[2] and r[1] < q[1] < r[1] + r[3] for r in R):
            ax.plot(q[0], q[1], "x", ms=5, color="k"); nb += 1
for f in t["ft_slots"]:
    r = f["regs_um"]; ax.plot([q[0] for q in r], [q[1] for q in r], "-o", ms=1.5, lw=.6, color="darkorange", alpha=.8)
cor = rep["r1"]["corridors"]
for k, v in cor.items():
    if isinstance(v, dict) and "y" in v:
        y0, y1 = v["y"]; ax.add_patch(plt.Rectangle((0, y0), W, y1 - y0, fc="yellow", alpha=.12, lw=0))
        ax.text(W + 8, (y0 + y1) / 2, f"{k}\n{v['um']:g} um cap {v['capacity_b']}\nneed {v['need_measured_b']} meas / {v['need_plan_b']} plan",
                fontsize=4.5, va="center", color="g" if v["ok"] else "r")
for tp in t["clock"]["taps"]: ax.plot(*tp["xy"], "^", ms=3, color="purple")
ax.plot(*t["clock"]["tap_um"], "*", ms=10, color="purple")
ax.set_title(f"root B2p_r1 (R1-302.4: {W:g} x {H:g}, 4x8 snake): {nb} station sites in hard cores", fontsize=7)
ax.set_aspect("equal"); ax.set_xlim(-40, W + 260); ax.set_ylim(-20, H + 20); fig.savefig(root_png, dpi=130, bbox_inches="tight")
# die
fig, ax = plt.subplots(figsize=(22, 13)); DW, DH = p["die"]["outline_um"]
ax.add_patch(plt.Rectangle((0, 0), DW, DH, fill=False, lw=2))
mv = set(rep["r1"]["die"]["moved"]); gr = set(rep["r1"]["die"]["grown"])
for q in p["partitions"]:
    tt = p["partition_types"][q["type"]]; x, y = q["origin_um"]; w, h = tt["outline_um"]
    fc = "#fdd" if q["name"] in gr else ("#ddf" if q["name"] in mv else "#eee")
    if q["name"] == "root": fc = "#f96"
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec="k", lw=.5)); ax.text(x + w / 2, y + h / 2, q["name"], fontsize=5, ha="center", va="center")
    if q["name"] == "root":
        for c in tt["hard_cores"]:
            cx, cy = c["origin_um"]; cw, ch = c["outline_um"]
            ax.add_patch(plt.Rectangle((x + cx, y + cy), cw, ch, fc="#9cf" if "tkm" in c["inst"] else "#cfc", ec="k", lw=.2))
for e in p["die"]["io"]:
    r = e["rect_um"]; ax.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ec="m", lw=1, ls=":"))
sx = rep["r1"]["die"]["seam_x"]; ax.axvline(sx, color="r", lw=.6, ls="--"); ax.axvline(sx + 302.4, color="r", lw=.6, ls="--")
ax.set_title(f"HBM die B2p_r1: {rep['r1']['die']['die_w'][0]:g} -> {DW:g} x {DH:g} um ({rep['r1']['die']['die_area_mm2'][0]} -> {rep['r1']['die']['die_area_mm2'][1]} mm2); blue = moved +302.4, pink = grown +302.4 E", fontsize=9)
ax.set_aspect("equal"); ax.set_xlim(-200, DW + 200); ax.set_ylim(-200, DH + 200); fig.savefig(die_png, dpi=110, bbox_inches="tight")
