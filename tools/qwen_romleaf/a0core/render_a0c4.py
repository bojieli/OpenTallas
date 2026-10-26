#!/usr/bin/env python3
"""QC-P5 10-23 A0 v4 render: (left) the core kit -- outline, hard children, soft-root fences, pin buses per face, the
interior clock tap pins (ck + ck_t<i>) and the nearest-tap regions (what a0_clock_taps.tcl builds pre-CTS), with an
optional sampled placed-sink overlay (a v2 4_1_cts clock probe: OT_SINK lines) coloured by tap, per-tap sink share and
max Manhattan pin->sink reach; (right) the CB quad cbf_q00 of the current plan with its 4 cores (hard_cores, orient)
and the 32 core tap points the quad tap grid must deliver.
    render_a0c4.py <kit> <out.png> <stats.json> [plan die_plan.json] [probe.out]
"""
import json, pathlib, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = pathlib.Path(__file__).resolve().parents[3]
COL = {"ot_qwen_tile_romleaf": "#8fb3d9", "ot_qwen_tile_lsl_fp1": "#e6b07a", "ot_qwen_tile_node": "#a8d5a2"}
TC = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b", "#e377c2", "#bcbd22", "#7f7f7f"]


def main(kit, out, stats_out, plan=None, probe=None):
    fp = json.load(open(ROOT / f"physical/ref_tile/{kit}/floorplan.json"))
    spec = json.load(open(ROOT / f"physical/ref_tile/{kit}/spec.json"))
    x0, y0, W, H = fp["die"]
    pins = {}
    for l in (ROOT / spec["io_tcl"]).read_text().splitlines():
        m = re.match(r"place_pin -pin_name \{(\w+)(?:\[\d+\])?\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\}", l)
        if m:
            pins.setdefault(m[1], []).append((float(m[3]), float(m[4]), m[2]))
    taps = sorted([(n, ps[0][0], ps[0][1]) for n, ps in pins.items() if re.fullmatch(r"ck(_t\d+)?", n)],
                  key=lambda t: (t[0] != "ck", t[0]))
    near = lambda x, y: min(range(len(taps)), key=lambda i: abs(x - taps[i][1]) + abs(y - taps[i][2]))
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(16, 14), gridspec_kw={"width_ratios": [1, 1.25]})
    # nearest-tap regions (pre-CTS sink assignment)
    st = 4.0
    for i in range(int(W / st) + 1):
        for j in range(int(H / st) + 1):
            k = near(i * st, j * st)
            ax.add_patch(Rectangle((i * st, j * st), st, st, fc=TC[k % len(TC)], alpha=0.10, lw=0))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    hard = 0.0
    for b in fp["blocks"]:
        if b.get("kind") != "child":
            continue
        w, h = b.get("w"), b.get("h")
        ax.add_patch(Rectangle((b["x"], b["y"]), w, h, fc=COL.get(b["master"], "#ccc"), ec="k", lw=0.6, alpha=0.8))
        ax.text(b["x"] + w / 2, b["y"] + h / 2, b["master"].split("_")[-1], ha="center", va="center", fontsize=6)
        hard += w * h
    rt = (ROOT / spec["pin_hook_before_flops"][0]).read_text()
    for m in re.finditer(r"name (\w+) type (\w+) .*? boxes \{((?:\{[\d. ]+\} ?)+)\}", rt):
        for bx_ in re.findall(r"\{([\d. ]+)\}", m.group(3)):
            a, b_, c, d = map(float, bx_.split())
            ax.add_patch(Rectangle((a, b_), c - a, d - b_, fill=False, ec="#802080", lw=0.4))
    face = {"W": 0, "E": 0}
    for n, ps in pins.items():
        xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
        if re.fullmatch(r"ck(_t\d+)?", n):
            continue
        f = "W" if xs[0] < 1 else "E"; face[f] += len(ps)
        x = 0 if f == "W" else W
        ax.plot([x, x], [min(ys), max(ys)], lw=4, color="green" if f == "W" else "teal", alpha=0.5)
        ax.text(x + (5 if f == "W" else -5), (min(ys) + max(ys)) / 2, f"{n}[{len(ps)}]", fontsize=7,
                ha="left" if f == "W" else "right", color="darkgreen")
    reach = {t[0]: 0.0 for t in taps}; cnt = {t[0]: 0 for t in taps}; mac = {t[0]: 0 for t in taps}
    if probe:
        for l in open(probe):
            if l.startswith("OT_SINK"):
                f_ = l.split(); x, y = int(f_[2]) / 1000, int(f_[3]) / 1000
                k = near(x, y); n = taps[k][0]
                cnt[n] += 1; reach[n] = max(reach[n], abs(x - taps[k][1]) + abs(y - taps[k][2]))
                ax.plot([x], [y], ".", ms=2.5, color=TC[k % len(TC)])
    for b in fp["blocks"]:
        if b.get("kind") == "child":
            k = near(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2); mac[taps[k][0]] += 1
    for k, (n, x, y) in enumerate(taps):
        ax.plot([x], [y], marker="*", ms=18, color=TC[k % len(TC)], mec="k", zorder=6)
        ax.text(x + 4, y + 4, f"{n}" + (f"\n{cnt[n]} smp, reach {reach[n]:.0f}" if probe else ""),
                fontsize=6.5, ha="left", color="k", fontweight="bold")
    ax.set_xlim(-30, W + 30); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
    ax.set_title(f"{kit} core {W} x {H} um, hard fill {hard / (W * H):.2f}\n{len(taps)} interior M7 clock taps (sink-count sized, "
                 f"shading = nearest-tap sink regions; dots = sampled v2 placed sinks); pins W {face['W']} / E {face['E']}",
                 fontsize=9)
    qt = []
    if plan:
        d = json.load(open(plan))
        t = d["partition_types"]["cbf_q00"]
        PW, PH = t["outline_um"]
        bx.add_patch(Rectangle((0, 0), PW, PH, fill=False, lw=1.5))
        for c in t.get("hard_cores", []):
            ox, oy = c["origin_um"]; my = c.get("orient", "R0") in ("MY", "R180")
            bx.add_patch(Rectangle((ox, oy), W, H, fc="#eef3fa", ec="navy", lw=1))
            bx.text(ox + W / 2, oy + H / 2, f"{c['inst']} {c['orient']}", ha="center", fontsize=8)
            for k, (n, x, y) in enumerate(taps):
                tx, ty = ox + (W - x if my else x), oy + y
                qt.append([c["inst"] + "." + n, round(tx, 3), round(ty, 3)])
                bx.plot([tx], [ty], marker="*", ms=11, color=TC[k % len(TC)], mec="k")
        tp = t["clock"]["tap_um"]
        bx.plot([tp[0]], [tp[1]], marker="P", ms=14, color="purple")
        bx.text(tp[0] + 10, tp[1] + 10, "plan partition tap (spine)", color="purple", fontsize=8)
        bx.set_xlim(-30, PW + 30); bx.set_ylim(-20, PH + 20); bx.set_aspect("equal")
        bx.set_title(f"CB quad cbf_q00: 4 A0 cores x {len(taps)} taps = {len(qt)} core tap points the quad tap grid "
                     "delivers (equal arrival, neighbour <= 80 ps)", fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=110)
    s = {"kit": kit, "outline_um": [W, H], "hard_fill": round(hard / (W * H), 3), "taps": taps,
         "pins_per_face": face, "macros_per_tap": mac,
         "sampled_sinks_per_tap": cnt if probe else None, "max_reach_um_per_tap": reach if probe else None,
         "quad_core_taps_um": qt}
    json.dump(s, open(stats_out, "w"), indent=1)
    print("WROTE", out, stats_out)


if __name__ == "__main__":
    main(*sys.argv[1:6])
