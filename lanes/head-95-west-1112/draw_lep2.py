#!/usr/bin/env python3
"""draw_lep2.py V1 V2 OUT.png : hd_lep0N re-pack v1 (rp4, GEOM-VIS-5 06:49 form) vs v2 (C1-C4 applied, lattice)."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def box(h):
    x, y = h["origin_um"]; dx, dy = h.get("track_offset_um", [0, 0]); w, hh = h["outline_um"]
    if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"): w, hh = hh, w
    return x + dx, y + dy, w, hh

def panel(ax, P, title):
    t = P["partition_types"]["hd_lep0N"]; W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="k", lw=1.2))
    for k, b in t["clock"]["landing_contract"]["bands"].items():
        x0, y0, x1, y1 = b["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#c7e9c0", ec="green", lw=0.4, alpha=0.5))
    for b in t["buses"]:
        f, (a0, a1) = b["face"], b["window_um"]
        seg = {"N": ([a0, a1], [H, H]), "S": ([a0, a1], [0, 0]), "W": ([0, 0], [a0, a1]), "E": ([W, W], [a0, a1])}[f]
        ax.plot(*seg, color="#6a3d9a", lw=3, solid_capstyle="butt")
    for h in t["hard_cores"]:
        x, y, w, hh = box(h)
        n = h["inst"]
        c = "#fbb4c4" if "g_pp" in n else ("#80b1d3" if "g_tx" in n else ("#fdb462" if "g_rx" in n else "#b3de69"))
        ax.add_patch(Rectangle((x, y), w, hh, fc=c, ec="k", lw=0.3))
        if "g_pp" in n:
            ax.text(x + w / 2, y + hh / 2, n.split(".")[2] + " " + h["orient"], ha="center", fontsize=8, clip_on=True)
            # K-face pin band (local S face, x 2..395.44) and W-face band (local W, y 2..464.56)
            o = h["orient"]; kx0, kx1 = 2, 395.44
            fx = (lambda u: x + u) if o in ("R0", "MX") else (lambda u: x + w - u)
            ky = y if o in ("R0", "MY") else y + hh
            ax.plot([fx(kx0), fx(kx1)], [ky, ky], color="red", lw=2.2)
        elif "g_tx" in n or "g_rx" in n or "g_sram" in n:
            ax.plot([x, x], [y, y + hh], color="#08306b", lw=1.2); ax.plot([x + w, x + w], [y, y + hh], color="#08306b", lw=1.2)
            if "g_tx" in n and n.endswith("g_bank[0].u_m"):
                ax.text(x + 2, y + hh + 2, n.split("u_lep.u.")[1].split(".")[0], fontsize=6, color="#08306b", clip_on=True)
    isl = t["clock"].get("die_islands_um") or []
    for x0, y0, x1, y1 in isl:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#984ea3", ec="none"))
    tx, ty = t["clock"]["tap_um"]; ax.plot(tx, ty, marker="*", color="#984ea3", ms=9)
    for tp in t["clock"].get("taps", []) or []:
        ax.plot(*tp["xy"], marker="x", color="red", ms=7, mew=1.6)
    lt = t["reset"].get("local_taps_um") or []
    ax.plot([p[0] for p in lt], [p[1] for p in lt], ".", color="#e6550d", ms=4)
    ax.add_patch(Rectangle((846.72, 0), 120.96, H, fc="none", ec="#999", ls="--", lw=0.8))
    ax.set_xlim(-30, W + 30); ax.set_ylim(-30, H + 30); ax.set_aspect("equal"); ax.set_title(title, fontsize=9)

def zoom(ax, P, title):
    panel(ax, P, title); ax.set_ylim(440, 740)

V1, V2 = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
fig, axs = plt.subplots(2, 2, figsize=(20, 13), gridspec_kw={"height_ratios": [2.2, 1]})
panel(axs[0][0], V1, "v1 = rp4 134f8353 (GEOM-VIS-5 06:49 form): 10-tx rows end to end across the street, off-lattice, 3 pair clock taps under the rows")
panel(axs[0][1], V2, "v2 = rp11 a50145295ac5 (C1-C4 applied; pins on track, origins written flat; pair clock taps moved into the street)")
zoom(axs[1][0], V1, "v1 centre band zoom"); zoom(axs[1][1], V2, "v2 centre band zoom: rows split 5+5, 81-um gap on the street")
fig.text(0.01, 0.005, "pink = lep pair cores (red edge = K-face pin band, 1114 pins on M5/M7); blue = tx SRAM, orange = rx SRAM, "
         "light green = landing SRAM (dark blue edges = W/E pin faces, M4; N/S faces have no pins); purple squares = clock die "
         "islands, purple star = type clock tap; red x = pair-core clock landings; orange dots = local reset taps; purple bars "
         "= bus windows on the outline; dashed = vertical centre street x 846.72-967.68", fontsize=8)
plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(sys.argv[3], dpi=100); print("wrote", sys.argv[3])
