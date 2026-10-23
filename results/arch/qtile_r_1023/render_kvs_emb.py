#!/usr/bin/env python3
"""QTILE-R: pre-P&R plan render + stats of qkd_kvs_emb nc32a/b (from floorplan.json) for GEOM-REVIEW."""
import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
FB = {"S": 674, "E": 758, "W": 598, "N": 0}; CH = 216.0 * 151.2; STD = 2600.0
fig, axs = plt.subplots(1, 3, figsize=(20, 6)); out = {}
for ax, k in zip(axs, ["qkd_kvs_emb", "qkd_kvs_emb_nc32a", "qkd_kvs_emb_nc32b"]):
    f = json.load(open(f"{ROOT}/physical/ref_tile/{k}/floorplan.json")); W, H = f["die"][2], f["die"][3]
    ax.add_patch(Rectangle((0, 0), W, H, fc="#cfe8c8", ec="k", lw=2))
    for b in f["blocks"]:
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="#4a90d9", ec="w"))
        ax.plot([b["x"]] * 2, [b["y"], b["y"] + b["h"]], "r-", lw=3); ax.plot([b["x"] + b["w"]] * 2, [b["y"], b["y"] + b["h"]], "r-", lw=3)
        ax.text(b["x"] + 5, b["y"] + b["h"] / 2, "u_rowtx (MY)\nW edge: 554 word pins (join)\nE edge: 550 payload pins", fontsize=7, color="w")
        ax.text(b["x"] / 2 - 12, H / 2, "join\nband", fontsize=7)
    fl = {"W": H, "E": H, "S": W, "N": W}
    for fc, (x, y, r) in {"W": (-22, H / 3, 90), "E": (W + 3, H / 3, 90), "S": (W / 3, -14, 0), "N": (W / 3, H + 3, 0)}.items():
        ax.text(x, y, f"{fc}: {FB[fc]} ({FB[fc] / fl[fc]:.2f}/um)", fontsize=8, rotation=r)
    st = {"outline": [W, H], "area_um2": round(W * H), "child_um2": CH, "std_est_um2": STD, "fill_of_free": round(STD / (W * H - CH), 3),
          "total_fill": round((CH + STD) / (W * H), 3), "pins_per_um": {fc: round(FB[fc] / fl[fc], 2) for fc in FB},
          "pin_regs": "recipe 3 every pin incl. rst_n (as e1): +1 per input / output, px_tok/px_tep +2", "layer_cap": "M5"}
    out[k] = st
    ax.set_title(f"{k}{' (OLD e1/i2 frame slot)' if k == 'qkd_kvs_emb' else ''}: {W} x {H} = {W * H / 1e3:.1f}k um2\nfill {st['total_fill']:.0%}, std fill of free {st['fill_of_free']:.0%}", fontsize=9)
    ax.set_xlim(-30, 400); ax.set_ylim(-20, 315); ax.set_aspect("equal")
plt.savefig(f"{ROOT}/results/arch/qtile_r_1023/kvs_emb_nc32_geom.png", dpi=100, bbox_inches="tight")
json.dump(out, open(f"{ROOT}/results/arch/qtile_r_1023/kvs_emb_nc32_geom_stats.json", "w"), indent=1)
print(json.dumps(out)[:900])
