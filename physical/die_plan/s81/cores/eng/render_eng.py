#!/usr/bin/env python3
"""CORE-S81-ENG (10-23): renders of the eng__t1 split plan (cores_eng.json + S81 die_plan.json).
  renders/core_<name>.png   core frame: outline, macro column(s) + 4.32 halo, pins coloured by bus, face pin density
  renders/eng_t1.png        eng__t1 type frame: bus windows, ft slots (in->out lines + station sites j/k), cores,
                            core->window flylines (bus centroid), the LK<->XQ crossing
  renders/stats.json        per face pins/um (avg, worst 10-um window), fill of free, ft stations added (plan rule)
usage (repo root): python3 physical/die_plan/s81/cores/eng/render_eng.py"""
import collections
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
S81 = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, S81)
MAC = {"ot_rom_4096x72_m8": (38.016, 62.91), "ot_sram_1r1w_512x128_m4_r2c2": (174.096, 29.7),
       "ot_sram_1r1w_64x512_m1_r2c2": (171.288, 77.76), "ot_sram_1r1w_128x256_m1_r2c2": (94.824, 41.064)}
COL = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#17becf", "#bcbd22", "#7f7f7f"]


def face_density(pins, W, H):
    out = {}
    by = collections.defaultdict(list)
    for p in pins:
        f = "N" if p["y"] > H - 1 else "S" if p["y"] < 1 else "E" if p["x"] > W - 1 else "W"
        by[f].append(p["x"] if f in "NS" else p["y"])
    for f, v in by.items():
        v.sort()
        L = W if f in "NS" else H
        win = max(sum(1 for c in v if a <= c < a + 10) for a in v)
        out[f] = dict(pins=len(v), per_um_face=round(len(v) / L, 2), worst_10um=win,
                      span_um=[round(v[0], 2), round(v[-1], 2)])
    return out


def core_png(c, pins, path):
    W, H = c["outline_um"]
    fig, ax = plt.subplots(figsize=(7, 7 * H / W + 0.6))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    ax.add_patch(Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=0.5, ec="grey", ls=":"))
    for m in c["macros"]:
        w, h = MAC[m["master"]]
        x, y = m["at"]
        ax.add_patch(Rectangle((x - 4.32, y - 4.32), w + 8.64, h + 8.64, fc="#eeeeee", ec="none"))
        ax.add_patch(Rectangle((x, y), w, h, fc="#9ecae1", ec="#08519c", lw=0.8))
        ax.plot([x, x], [y + 2, y + h - 2], c="#08519c", lw=2.5)          # pin edges W / E
        ax.plot([x + w, x + w], [y + 2, y + h - 2], c="#08519c", lw=2.5)
        ax.text(x + w / 2, y + h / 2, m["inst"].split(".")[-1].replace(".rom", ""), ha="center", va="center", fontsize=5)
    groups = []
    for p in pins:
        b = p["name"].split("[")[0]
        if b not in groups:
            groups.append(b)
    for i, b in enumerate(groups):
        xs = [p["x"] for p in pins if p["name"].split("[")[0] == b]
        ys = [p["y"] for p in pins if p["name"].split("[")[0] == b]
        ax.scatter(xs, ys, s=4, c=COL[i % len(COL)], label="%s (%d)" % (b, len(xs)), zorder=3)
    ax.set_xlim(-10, W + 10)
    ax.set_ylim(-10, H + 10)
    ax.set_aspect("equal")
    st = c.get("stats", {})
    ax.set_title("%s %gx%g  cells %s  std %s um2  fill of free %s\nmacros %d (abutted columns, pins W/E)  pins %d" % (
        c["module"], W, H, f"{c['cells']:,}", f"{c['std_area_um2']:,.0f}", c["fill_of_free"], len(c["macros"]),
        len(pins)), fontsize=8)
    ax.legend(fontsize=5, loc="center left", bbox_to_anchor=(1.0, 0.5), markerscale=3)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    cj = json.load(open(os.path.join(HERE, "cores_eng.json")))
    plan = json.load(open(os.path.join(S81, "die_plan.json")))
    t = plan["partition_types"]["eng__t1"]
    PW, PH = t["outline_um"]
    os.makedirs(os.path.join(HERE, "renders"), exist_ok=True)
    stats = {}
    for c in cj["cores"]:
        pins = json.load(open(os.path.join(S81, c["pins_file"])))["pins"]
        core_png(c, pins, os.path.join(HERE, "renders", "core_%s.png" % c["name"]))
        stats[c["name"]] = dict(faces=face_density(pins, *c["outline_um"]), fill_of_free=c["fill_of_free"],
                                cells=c["cells"])
    # ---- type frame
    fig, ax = plt.subplots(figsize=(10, 10 * PH / PW))
    ax.add_patch(Rectangle((0, 0), PW, PH, fill=False, lw=1.5, ec="k"))
    ax.add_patch(Rectangle((34.56, 34.56), PW - 69.12, PH - 69.12, fill=False, lw=0.5, ec="grey", ls=":"))

    def face_pt(face, win, tt):
        p = win[0] + tt * (win[1] - win[0])
        return {"E": (PW, p), "W": (0.0, p), "N": (p, PH), "S": (p, 0.0)}[face]
    import gen_plan_v4 as GP
    cores_pl = [dict(origin_um=c["placement"]["origin_um"], outline_um=c["outline_um"]) for c in cj["cores"]]
    ft = []
    for s in t.get("ft_slots", []):
        for i in range(64):
            tt = (i + 0.5) / 64
            a = face_pt(s["in_face"], s["in_window_um"], tt)
            b = face_pt(s["out_face"], s["out_window_um"], tt)
            ax.plot([a[0], b[0]], [a[1], b[1]], c="#fdae6b", lw=0.4, zorder=1)
            for j in range(1, s["stations"]):
                ax.scatter([a[0] + (b[0] - a[0]) * j / s["stations"]], [a[1] + (b[1] - a[1]) * j / s["stations"]],
                           s=6, c="#e6550d", zorder=2)
        k2 = GP.ft_stations_macro(s, cores_pl, PW, PH)
        ft.append(dict(slot=s["name"], width=s["width"], stations=s["stations"], stations_with_cores=k2))
        ax.text(*face_pt(s["in_face"], s["in_window_um"], 0.5), "%s %db k%d" % (s["name"], s["width"], s["stations"]),
                fontsize=6, color="#a63603")
    wc = {}
    for b in t["buses"]:
        lo, hi = b["window_um"]
        p0, p1 = face_pt(b["face"], b["window_um"], 0), face_pt(b["face"], b["window_um"], 1)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], lw=5, c="#31a354", solid_capstyle="butt", zorder=4)
        m = face_pt(b["face"], b["window_um"], 0.5)
        wc[b["name"]] = m
        ax.text(m[0], m[1] + 12, "%s %d" % (b["name"], b["width"]), fontsize=5, rotation=60, color="#006d2c")
    tap = t["clock"]["tap_um"]
    ax.scatter([tap[0]], [tap[1]], marker="x", c="k", s=40, zorder=6)
    ax.text(tap[0] + 6, tap[1] - 14, "clk tap", fontsize=6)
    # bus -> core port map (die plan lanes, see cores_eng.json bus_map)
    ccol = {"e": "#c6dbef", "h0": "#fdd0a2", "h1": "#fdd0a2"}
    cen = {}
    for c in cj["cores"]:
        (x, y), (w, h) = c["placement"]["origin_um"], c["outline_um"]
        dx, dy = c["placement"]["track_offset_um"]
        ax.add_patch(Rectangle((x + dx, y + dy), w, h, fc=ccol[c["name"]], ec="k", lw=1, zorder=3))
        for m in c["macros"]:
            mw, mh = MAC[m["master"]]
            ax.add_patch(Rectangle((x + dx + m["at"][0], y + dy + m["at"][1]), mw, mh, fc="#6baed6", ec="none", zorder=3))
        ax.text(x + w / 2, y + h / 2, "%s\n%s\n%gx%g\n%s cells" % (c["name"].upper(), c["module"], w, h,
                f"{c['cells']:,}"), ha="center", va="center", fontsize=7, zorder=5)
        cen[c["name"]] = (x, y, w, h)
        pins = json.load(open(os.path.join(S81, c["pins_file"])))["pins"]
        for bn, (core, port) in cj["bus_map"].items():
            if core != c["name"]:
                continue
            pp = [p for p in pins if p["name"].split("[")[0] == port]
            px = x + dx + sum(p["x"] for p in pp) / len(pp)
            py = y + dy + sum(p["y"] for p in pp) / len(pp)
            ax.annotate("", xy=wc[bn], xytext=(px, py), arrowprops=dict(arrowstyle="-", color="#238b45", lw=0.8,
                                                                         ls="--"), zorder=5)
    # crossing E S face <-> H0 / H1 N faces (1,220 b, half-cycle, straight drops)
    e = cen["e"]
    ax.text(e[0] + e[2] + 6, e[1] - 10, "E<->H crossing 1,220 b\n(68 E->H, 2x576 H->E), 17-um drops", fontsize=6,
            color="r", zorder=6)
    ax.set_xlim(-30, PW + 30)
    ax.set_ylim(-30, PH + 60)
    ax.set_aspect("equal")
    ax.set_title("eng__t1 %gx%g (S81 v4.7b): dsdv_eng_rr -> 3 hard cores E + H0 + H1; ft station sites (orange dots) "
                 "kept clear" % (PW, PH), fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "renders", "eng_t1.png"), dpi=160)
    plt.close(fig)
    stats["ft"] = ft
    json.dump(stats, open(os.path.join(HERE, "renders", "stats.json"), "w"), indent=1)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
