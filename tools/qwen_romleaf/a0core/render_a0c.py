#!/usr/bin/env python3
"""QC-A0 render: (left) the A0 core kit floorplan -- outline, hard children, soft-root fences, pin buses per face,
the single core clock pin and the clock-sink masses that used to be separate entries; (right) the CB quad partition of
the variant-B plan with its four cores, the partition tap and the per-core taps (one spine tap per planned core).
    render_a0c.py <kit> <out.png> <stats.json>
"""
import json, pathlib, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = pathlib.Path(__file__).resolve().parents[3]
COL = {"ot_qwen_tile_romleaf": "#8fb3d9", "ot_qwen_tile_lsl_fp1": "#e6b07a", "ot_qwen_tile_node": "#a8d5a2"}


def main(kit, out, stats_out):
    fp = json.load(open(ROOT / f"physical/ref_tile/{kit}/floorplan.json"))
    spec = json.load(open(ROOT / f"physical/ref_tile/{kit}/spec.json"))
    x0, y0, W, H = fp["die"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(15, 14), gridspec_kw={"width_ratios": [1, 1.25]})
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    hard = 0.0
    for b in fp["blocks"]:
        if b.get("kind") != "child":
            continue
        w, h = b.get("w"), b.get("h")
        ax.add_patch(Rectangle((b["x"], b["y"]), w, h, fc=COL.get(b["master"], "#ccc"), ec="k", lw=0.6))
        ax.text(b["x"] + w / 2, b["y"] + h / 2, f"{b['master'].split('_')[-1]}\n{b.get('orient', '')}", ha="center",
                va="center", fontsize=6)
        hard += w * h
    rt = (ROOT / spec["pin_hook_before_flops"][0]).read_text()
    for m in re.finditer(r"name (\w+) type (\w+) .*? boxes \{((?:\{[\d. ]+\} ?)+)\}", rt):
        for bx_ in re.findall(r"\{([\d. ]+)\}", m.group(3)):
            a, b_, c, d = map(float, bx_.split())
            ax.add_patch(Rectangle((a, b_), c - a, d - b_, fc="#c050c0", alpha=0.25, ec="#802080", lw=0.3))
        ax.text(a, d, m.group(1), fontsize=4.5, color="#601060", va="bottom")
    pins = {}
    for l in (ROOT / spec["io_tcl"]).read_text().splitlines():
        m = re.match(r"place_pin -pin_name \{(\w+)(?:\[\d+\])?\} -layer (\w+) -location \{([\d.]+) ([\d.]+)\}", l)
        if m:
            pins.setdefault(m[1], []).append((float(m[3]), float(m[4]), m[2]))
    face = {"W": 0, "E": 0}
    for n, ps in pins.items():
        xs = [p[0] for p in ps]; ys = [p[1] for p in ps]
        f = "W" if xs[0] < 1 else "E"; face[f] += len(ps)
        x = 0 if f == "W" else W
        if n == "ck":
            ax.plot([x], [ys[0]], marker="*", ms=18, color="red", zorder=5)
            ax.annotate("ck (ONLY clock entry)", (x, ys[0]), (x - 190, ys[0] + 25), color="red", fontsize=9,
                        arrowprops=dict(arrowstyle="->", color="red"))
            continue
        ax.plot([x, x], [min(ys), max(ys)], lw=5, color="green" if f == "W" else "teal", alpha=0.7)
        ax.text(x + (5 if f == "W" else -5), (min(ys) + max(ys)) / 2, f"{n}[{len(ps)}]", fontsize=7,
                ha="left" if f == "W" else "right", color="darkgreen")
    ax.set_xlim(-30, W + 30); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
    ax.set_title(f"{kit} core {W} x {H} um ({W * H / 1e6:.4f} mm2), hard fill {hard / (W * H):.2f}\n"
                 f"1 clock port (was {'38' if '_nk_' in kit else '34'} entries); pins W {face['W']} / E {face['E']}",
                 fontsize=9)
    # quad context from the plan
    d = json.load(open(ROOT / "physical/die_plan/qwen_compute/die_plan.json"))
    t = d["partition_types"]["cbf_q00"]
    PW, PH = t["outline_um"]
    bx.add_patch(Rectangle((0, 0), PW, PH, fill=False, lw=1.5))
    ck = pins["ck"][0]
    taps = []
    for c in t["contents"]:
        if "romleaf" in c["module"]:
            ox, oy = c["origin_um"]
            bx.add_patch(Rectangle((ox, oy), W, H, fc="#dde8f5", ec="navy", lw=1))
            bx.text(ox + W / 2, oy + H / 2, f"{c['inst']}\nA0 core ({c['module'][9:11].upper()})", ha="center", fontsize=8)
            tx, ty = ox + ck[0], oy + ck[1]; taps.append((tx, ty))
            bx.plot([tx], [ty], marker="*", ms=14, color="red")
    tp = t["clock"]["tap_um"]
    bx.plot([tp[0]], [tp[1]], marker="P", ms=14, color="purple")
    bx.text(tp[0] + 10, tp[1] + 10, "plan partition tap", color="purple", fontsize=8)
    for tx, ty in taps:
        bx.plot([tp[0], tx], [tp[1], ty], ls=":", color="purple", lw=0.8)
    bx.set_xlim(-30, PW + 30); bx.set_ylim(-20, PH + 20); bx.set_aspect("equal")
    bx.set_title("CB quad cbf_q00 (variant B plan @6587487a5): 4 A0 cores, red * = per-core spine tap at the core ck pin",
                 fontsize=9)
    fig.tight_layout(); fig.savefig(out, dpi=110)
    st = {"kit": kit, "outline_um": [W, H], "area_mm2": round(W * H / 1e6, 4), "hard_fill": round(hard / (W * H), 3),
          "clock_ports": ["ck"], "ck_pin_um": [ck[0], ck[1]], "pins_per_face": face,
          "core_taps_in_quad_um": taps, "partition_tap_um": tp,
          "unchanged_vs": "qfd_tile_" + ("nk" if "_nk_" in kit else "nl") + "_romleaf_rpf@fce5d5cb2 (GEOM PASS-CONDITIONAL 02:15): "
                          "children, fences, request decoders, data pins, RTL body",
          "changed": "clock interface: 1 entry; " + ("CTS: clock_split_km 48 local roots + TritonCTS (FALLBACK)" if kit.endswith("k") else "clock spine with child-insertion targets (MAIN)")}
    json.dump(st, open(stats_out, "w"), indent=1)
    print("WROTE", out, stats_out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
