#!/usr/bin/env python3
"""DIE-KV-14a: render the core_tx plan delta in its hub_Wi neighbourhood (old slot, new outline, pins by partner)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "physical/die_plan/qwen_kvsys/cores"))
import core_tx_plan as C
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, delta, conns, out = C.load(sys.argv[1]), json.load(open(sys.argv[2])), C.load(sys.argv[3]), sys.argv[4]
d = Path(sys.argv[2]).parent
new = json.load(open(d / delta["new"]["pins_file"]))
cc = conns[delta["type"]][delta["inst"]]
fig, ax = plt.subplots(1, 2, figsize=(16, 8))
cols = {}
pal = ["tab:red", "tab:blue", "tab:green", "tab:orange", "tab:purple", "tab:brown", "tab:pink", "tab:olive", "tab:cyan"]
def col(b):
    k = ",".join(sorted(cc.get(b, []))) if all(x.startswith("core:") for x in cc.get(b, ["bus:"])) else "logic-face"
    if k not in cols:
        cols[k] = pal[len(cols) % len(pal)]
    return cols[k], k
for h in plan["partition_types"][delta["type"]]["hard_cores"]:
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]
    me = h["inst"] == delta["inst"]
    ax[0].add_patch(Rectangle((x, y), w, hh, fill=False, ec="k", ls="--" if me else "-", lw=1))
    ax[0].text(x + 3, y + hh - 20, h["inst"].replace("host__qkd_hr_", "") + (" (old slot)" if me else ""), fontsize=7)
ox, oy = delta["new"]["origin_um"]; w, hh = delta["new"]["outline_um"]
ax[0].add_patch(Rectangle((ox, oy), w, hh, fill=False, ec="r", lw=2))
for p in new["pins"]:
    c, _ = col(C.bus_of(p["name"]))
    ax[0].plot(ox + p["x"], oy + p["y"], ".", ms=1, color=c)
    ax[1].plot(p["x"], p["y"], ".", ms=2, color=c)
ex, ey = delta["new"]["clock_entry_um"]
ax[1].plot(ex, ey, "*", ms=14, color="gold", mec="k")
ax[1].add_patch(Rectangle((0, 0), w, hh, fill=False, ec="r", lw=1))
ax[1].add_patch(Rectangle((4.32, 4.32), w - 8.64, hh - 8.64, fill=False, ec="0.5", lw=0.5, ls=":"))
for k, c in cols.items():
    ax[1].plot([], [], "s", color=c, label=k.replace("core:host__qkd_hr_", "")[:60])
ax[1].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.01, 1.0))
ax[0].set_xlim(0, 1278.72); ax[0].set_ylim(0, 1676.16); ax[0].set_aspect("equal")
ax[0].set_title("hub_Wi: old core_tx slot (dashed) vs new outline (red)", fontsize=9)
ax[1].set_xlim(-5, w + 5); ax[1].set_ylim(-5, hh + 5); ax[1].set_aspect("equal")
ax[1].set_title(f"core_tx {w:g}x{hh:g}: pins by partner, ck entry star; faces {delta['face_pins']}", fontsize=9)
fig.tight_layout(); fig.savefig(out, dpi=110)
