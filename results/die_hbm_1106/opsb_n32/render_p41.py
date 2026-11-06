#!/usr/bin/env python3
"""part 41 plan-time GEOM render: ot_hgi_sfu_opsb_output core (local frame) = new core_macros rects + halo, plan pins by
bus, clock entry; right: the q_b113 slot of u_sfucore_Q_opstore_b__o with its neighbours.   render_p41.py PLAN_DIR OUT.png"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = Path(sys.argv[1]); P = json.loads((d / "die_plan.json").read_text()); T = P["partition_types"]["q_b113"]
cm = json.loads((d / "core_macros.json").read_text())["cores"]["ot_hgi_sfu_opsb_output"]
h = next(c for c in T["hard_cores"] if c.get("inst") == "u_sfucore_Q_opstore_b__o")
pins = json.loads((d / h["pins_file"]).read_text())
fig, axs = plt.subplots(1, 2, figsize=(24, 9), dpi=110)
ax = axs[0]; W, H = cm["outline_um"]
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5)); ax.add_patch(Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=0.5, ls="--"))
for q in cm["macros"]:
    x0, y0, x1, y1 = q["rect_um"]
    ax.add_patch(Rectangle((x0 - 4.32, y0 - 4.32), x1 - x0 + 8.64, y1 - y0 + 8.64, fill=False, lw=0.4, ls=":", color="gray"))
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, alpha=0.3, color="tab:blue"))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, q["name"].split(".")[2].replace("g_bank", "b") + f"\n{x1-x0:.1f}x{y1-y0:.1f}", ha="center", va="center", fontsize=7)
    ax.plot([x0, x0], [y0, y1], color="tab:green", lw=2); ax.plot([x1, x1], [y0, y1], color="tab:red", lw=2)
col = {"sr_d": "tab:green", "lwd": "tab:red", "lwa": "tab:orange", "lw": "tab:purple", "sr_addr": "olive", "sr_v": "olive", "sr_rv": "olive", "flt": "k", "rst_n": "k", "clk": "k"}
for p in pins:
    b = p["name"].split("[")[0]; ax.plot(p["x"], p["y"], "s" if b in ("clk", "rst_n", "flt") else ".", ms=5 if b in ("clk", "rst_n", "flt") else 1.5, color=col.get(b, "gray"))
ax.set_aspect("equal"); ax.set_xlim(-15, W + 15); ax.set_ylim(-15, H + 15)
ax.set_title("ot_hgi_sfu_opsb_output part 41 (local, R0): 16 x 2048x32_g32 4x4, halo dotted; macro W face (read) green, E (write) red; pins sr_d green, lwd red, lwa orange")
ax = axs[1]; ox, oy = h["origin_um"]; w, hh = h["outline_um"]
for c in T["hard_cores"]:
    (x, y), (cw, ch) = c["origin_um"], c["outline_um"]
    if x < ox + w + 400 and x + cw > ox - 400 and y < oy + hh + 300 and y + ch > oy - 300:
        me = c.get("inst") == "u_sfucore_Q_opstore_b__o"
        ax.add_patch(Rectangle((x, y), cw, ch, alpha=0.25 if me else 0.1, color="tab:red" if me else "tab:blue"))
        ax.add_patch(Rectangle((x, y), cw, ch, fill=False, lw=0.6))
        ax.text(x + cw / 2, y + ch / 2, f"{c.get('inst')}\n{c['module'][-30:]} {c.get('orient', 'R0')}", ha="center", va="center", fontsize=6)
mir = h.get("orient") == "MX"
for q in cm["macros"]:
    x0, y0, x1, y1 = q["rect_um"]; ya, yb = (hh - y1, hh - y0) if mir else (y0, y1)
    ax.add_patch(Rectangle((ox + x0, oy + ya), x1 - x0, yb - ya, alpha=0.5, color="tab:blue"))
ax.set_aspect("equal"); ax.set_xlim(ox - 400, ox + w + 400); ax.set_ylim(oy - 300, oy + hh + 300)
ax.set_title(f"q_b113 slot {h['inst']} {h.get('orient')} at {h['origin_um']} (macros mirrored into the slot)")
fig.tight_layout(); fig.savefig(sys.argv[2]); print("render", sys.argv[2])
