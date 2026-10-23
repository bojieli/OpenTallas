#!/usr/bin/env python3
"""QTILE-R: pre-P&R geometry render + stats of the ctlm rp kits for GEOM-REVIEW (from the kit floorplan.json; no ODB yet).
Green = placeable logic (core minus macros + 5.4-um halo); lime band = io_flop_at_pins face-register band (4 cols);
red = macro signal-pin edges (W/E, M4); face labels = data bits per face and bits/um."""
import json, os, sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
FACE_BITS = {"W": 1779, "S": 766, "E": 424, "N": 192}      # from the synthesized port widths (spec pins dict)
STD = 43100.0; PR_BITS = 1144
out = {}
kits = sys.argv[1:] or ["qfd_hp13_cpub39_rp_main", "qfd_hp13_cpub39_rp_alt"]
fig, axs = plt.subplots(1, len(kits), figsize=(8 * len(kits), 8.5))
for ax, k in zip(axs, kits):
    f = json.load(open(f"{ROOT}/physical/ref_tile/{k}/floorplan.json"))
    W, H = f["die"][2], f["die"][3]
    ax.add_patch(Rectangle((0, 0), W, H, fc="#cfe8c8", ec="k", lw=2))
    for face, (x, y, w, h) in {"W": (0, 0, 8, H), "E": (W - 8, 0, 8, H), "S": (0, 0, W, 8), "N": (0, H - 8, W, 8)}.items():
        ax.add_patch(Rectangle((x, y), w, h, fc="#9be35a", ec="none", alpha=.9))
    mac = 0.0; halo = 0.0
    for b in f["blocks"]:
        ax.add_patch(Rectangle((b["x"] - 5.4, b["y"] - 5.4), b["w"] + 10.8, b["h"] + 10.8, fc="#e8e8e8", ec="none"))
    for b in f["blocks"]:
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="#4a90d9", ec="white", lw=.6))
        ax.plot([b["x"]] * 2, [b["y"], b["y"] + b["h"]], "r-", lw=2); ax.plot([b["x"] + b["w"]] * 2, [b["y"], b["y"] + b["h"]], "r-", lw=2)
        nm = b["inst"].split(".")[-1] if "u_hr" in b["inst"] else ".".join(b["inst"].split(".")[-2:])
        ax.text(b["x"] + 2, b["y"] + b["h"] / 2, nm[-16:], fontsize=5.5, color="white", va="center")
        mac += b["w"] * b["h"]
    face_len = {"W": H, "E": H, "S": W, "N": W}
    for face, (x, y, r) in {"W": (-30, H / 2, 90), "E": (W + 4, H / 2, 90), "S": (W / 2 - 40, -22, 0), "N": (W / 2 - 40, H + 6, 0)}.items():
        ax.text(x, y, f"{face}: {FACE_BITS[face]} b ({FACE_BITS[face] / face_len[face]:.2f}/um)", fontsize=8, rotation=r)
    xs = sorted({round(b["x"], 2) for b in f["blocks"]}); ys = min(b["y"] for b in f["blocks"]); ytop = max(b["y"] + b["h"] for b in f["blocks"])
    colA = min(b["x"] for b in f["blocks"]); colA_end = colA + 171.288
    colB = min(b["x"] for b in f["blocks"] if b["x"] > colA + 1); colB_end = max(b["x"] + b["w"] for b in f["blocks"])
    ax.text(colA / 2 - 10, H / 2, "W core\n(logic)", fontsize=8); ax.text(W / 2 - 30, ys / 2 - 3, "S core (logic)", fontsize=8)
    ax.text((colA_end + colB) / 2 - 6, ys + 40, "mid\nch.", fontsize=7)
    sys.path.insert(0, f"{ROOT}/tools/ref_tile"); import ref_tile as rt
    um = rt.util_metrics(STD, [dict(b) for b in f["blocks"]], (W - 4.32) * (H - 4.32), 5.4, 5.4)
    st = {"kit": k, "outline_um": [W, H], "area_um2": round(W * H), "macros": len(f["blocks"]), "macro_um2": round(mac),
          "std_um2_synth_est": STD, "std_density_of_placeable": round(um["density"], 3), "placeable_um2": round(um["placeable_um2"]),
          "fill_of_free": round(STD / (W * H - mac), 3), "outline_vs_content": round(W * H / (mac + STD / 0.6), 3),
          "aspect": round(max(W, H) / min(W, H), 3),
          "W_core_um": round(colA, 2), "S_core_um": round(ys, 2), "mid_channel_um": round(colB - colA_end, 2),
          "E_strip_um": round(W - colB_end, 2), "N_band_um": round(H - ytop, 2),
          "pins_per_um": {fc: round(FACE_BITS[fc] / face_len[fc], 2) for fc in FACE_BITS},
          "pin_regs": {"rtl_added_bits": PR_BITS, "rtl_added_ports": 15, "already_flop_direct_bits": 3159 - 2 - 698 - 69 - 2,
                       "unregistered_after": "0 data bits (69 bits have no load at all: dh_user, parts of native_ret/ss5/ag5/dh)",
                       "placement": "io_flop_at_pins cols 4 (FIRM at the pin before GPL)"},
          "clock_roots": {"ck_core[0]": "16.8k sinks (wtnbal24 synth)", "ck_hr[0]": "13.5k sinks"},
          "layer_cap": "M5 (signals M2-M5)"}
    out[k] = st
    ax.set_title(f"{k}  {W} x {H} um = {W * H / 1e3:.1f}k um2 (was 864 x 561.6)\nstd density {um['density']:.0%} of placeable, fill of free {st['fill_of_free']:.0%}, "
                 f"outline/content {st['outline_vs_content']}x", fontsize=9)
    ax.set_xlim(-40, W + 30); ax.set_ylim(-30, H + 20); ax.set_aspect("equal")
plt.savefig(f"{ROOT}/results/arch/qtile_r_1023/ctlm_rp_geom.png", dpi=100, bbox_inches="tight")
json.dump(out, open(f"{ROOT}/results/arch/qtile_r_1023/ctlm_rp_geom_stats.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:1500])
