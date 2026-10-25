#!/usr/bin/env python3
"""S81/LEAFPLAN3 10-25: GEOM-REVIEW numbers + renders of the template leaf types (and the main plan's for comparison).

per type: max internal hop, crossings between internal bundle chains (straight centroid legs, shared end points
excluded), station bits (tree sites counted once per port and site), internal cycles (gen_plan_v4 definition: per
link the largest station count), cut (densest 50-um vertical / horizontal cut line: internal chain bits + ft slot
bits crossing it / its M4+M6 (vertical line) or M5+M7 (horizontal line) tracks), over-core ft (template.overcore).
usage: review.py PLAN_JSON OUTDIR [--types t6,t50] [--png] [--tag NAME]"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import template as TP  # noqa: E402
V = TP.V


def legs(e):
    pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
    return list(zip(pts, pts[1:]))


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def _x(s, t):
    (a, b), (c, d) = s, t
    pts = {tuple(map(lambda v: round(v, 2), p)) for p in (a, b, c, d)}
    if len(pts) < 4:
        return False
    return (_ccw(a, c, d) * _ccw(b, c, d) < 0) and (_ccw(a, b, c) * _ccw(a, b, d) < 0)


def stats(T):
    ist = T.get("internal_stations", [])
    cc = [e for e in ist if e.get("conn", "").startswith("core:")]
    bus = [e for e in ist if not e.get("conn", "").startswith("core:")]
    # station bits: a site shared by several links of the same launching port is one register bank
    seen = {}
    for e in ist:
        port = e["launch"] if e["launch"].startswith("core:u_lf.u_vn") or e["launch"].startswith("face") else e["conn"]
        if "tree gather" in e.get("note", ""):
            port = e["capture"]
        for r in e["regs_um"]:
            k = (port, round(r[0], 1), round(r[1], 1))
            seen[k] = max(seen.get(k, 0), e["bits"])
    sbits = sum(seen.values())
    sbits_cc = sum(v for k, v in seen.items() if not str(k[0]).startswith("face"))
    raw = sum(len(e["regs_um"]) * e["bits"] for e in ist)
    # unique segments (dedupe shared tree legs) and crossings among core-core chains
    segs = {}
    for e in cc:
        for s in legs(e):
            k = tuple(sorted((tuple(round(v, 1) for v in s[0]), tuple(round(v, 1) for v in s[1]))))
            segs[k] = segs.get(k, 0) + 0
    sl = list(segs)
    cross = sum(1 for i in range(len(sl)) for j in range(i + 1, len(sl)) if _x(sl[i], sl[j]))
    mh = max([max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in legs(e)) for e in ist] or [0])
    # cycles: per link pair the largest station count
    cyc = {}
    for e in cc:
        a, _, b = e["conn"].partition("|")
        a = a[5:].rsplit(".", 1)[0]
        b = b[5:]
        key = (a, e["conn"].split("|")[0].rsplit(".", 1)[1][:2]) if "u_vn" in a and "g_ln" in b else tuple(sorted((a, b)))
        cyc[key] = max(cyc.get(key, 0), len(e["regs_um"]))
    return dict(entries=len(ist), core_core=len(cc), bus=len(bus), station_bits=sbits, station_bits_core_core=sbits_cc,
                station_bits_per_link_sum=raw, core_core_cycles=sum(cyc.values()), crossings=cross,
                max_hop_um=round(mh, 2))


def cut(T):
    W, H = T["outline_um"]
    segs = []
    for e in T.get("internal_stations", []):
        for a, b in legs(e):
            segs.append((a, b, e["bits"]))
    for s in T.get("ft_slots", []):
        pts = [TP._fpt(s["in_face"], s["in_window_um"], W, H)] + [tuple(r) for r in s.get("regs_um", [])] + \
              [TP._fpt(s["out_face"], s["out_window_um"], W, H)]
        for a, b in zip(pts, pts[1:]):
            segs.append((a, b, s["width"]))
    best = (0, None)
    for vert in (True, False):
        L = H if vert else W
        tr = L * (1 / 0.048 + 1 / 0.064) if vert else L * (1 / 0.048 + 1 / 0.064)
        n = int((W if vert else H) // 50)
        for i in range(1, n):
            c = 50.0 * i
            bits = sum(b for a, q, b in segs if min(a[0 if vert else 1], q[0 if vert else 1]) < c <
                       max(a[0 if vert else 1], q[0 if vert else 1]))
            r = bits / tr
            if r > best[0]:
                best = (round(r, 4), ("x" if vert else "y") + "=%g" % c, bits)
    return dict(ratio=best[0], at=best[1], bits=best[2] if best[1] else 0)


def render(T, tn, st, oc, ct, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W, H = T["outline_um"]
    fig, ax = plt.subplots(figsize=(13, 11.5))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in T["buses"]:
        f_, m_ = b["face"], sum(b["window_um"]) / 2
        y = H if f_ == "N" else 0
        ax.plot(b["window_um"], [y, y], lw=6, color="tab:orange")
        ax.text(m_, y + (14 if f_ == "N" else -26), "%s %db" % (b["name"], b["width"]), fontsize=7, ha="center")
    # ft slots: corridor legs (centroid) in purple, width-scaled
    for s in T.get("ft_slots", []):
        pts = [TP._fpt(s["in_face"], s["in_window_um"], W, H)] + [tuple(r) for r in s.get("regs_um", [])] + \
              [TP._fpt(s["out_face"], s["out_window_um"], W, H)]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="purple", lw=0.4 + s["width"] / 600, alpha=0.35)
        ax.scatter([p[0] for p in pts[1:-1]], [p[1] for p in pts[1:-1]], s=6, color="purple", marker="s")
    bx = TP.boxes(T["hard_cores"])
    for hc in T["hard_cores"]:
        x0, y0, x1, y1 = bx[hc["inst"]]
        nm = hc["inst"].split(".")[-1] if "g_ln" not in hc["inst"] else "L" + hc["inst"].split("[")[1].split("]")[0]
        if "u_vn" in hc["inst"] or "u_ve" in hc["inst"]:
            nm = hc["inst"].split(".")[-2][2:] + "_" + hc["inst"].split(".")[-1][2:]
        fc = "#cfe0f5" if "g_ln" in hc["inst"] else ("#f5e0c8" if "u_vn" in hc["inst"] else "#e3e3e3")
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec="k", lw=0.6))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, nm + ("" if hc.get("orient", "R0") == "R0" else " " + hc["orient"]),
                ha="center", va="center", fontsize=7)
    # internal chains: tree (green), other core-core (blue), bus (grey); sites x
    drawn = set()
    for e in T.get("internal_stations", []):
        tree = "LEAFPLAN3 tree" in e.get("note", "")
        col = "green" if tree else ("tab:blue" if e.get("conn", "").startswith("core:") else "grey")
        for a, b in legs(e):
            k = (tuple(a), tuple(b))
            if k in drawn:
                continue
            drawn.add(k)
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=0.3 + min(e["bits"], 512) / 256, alpha=0.55)
        ax.scatter([r[0] for r in e["regs_um"]], [r[1] for r in e["regs_um"]], marker="x", s=30, color="k", lw=1)
    ax.set_xlim(-30, W + 30)
    ax.set_ylim(-40, H + 40)
    ax.set_aspect("equal")
    ax.set_title("%s %s\nmax hop %.0f um | crossings %d | station bits %d (core-core %d) | core-core cycles %d | "
                 "cut %.3f @%s | over-core ft worst %.3f (%d fail)" % (
                     tn, title, st["max_hop_um"], st["crossings"], st["station_bits"], st["station_bits_core_core"],
                     st["core_core_cycles"], ct["ratio"], ct["at"], oc[0], len(oc[1])), fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types")
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--tag", default="leafplan3")
    a = ap.parse_args()
    P = json.load(open(a.plan))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    want = set(a.types.split(",")) if a.types else None
    rows = {}
    for tn, T in P["partition_types"].items():
        if not tn.startswith("ot_s81sl_leaf__t"):
            continue
        short = tn.split("__")[1]
        st = stats(T)
        oc = TP.overcore(T, T["hard_cores"])
        ct = cut(T)
        rows[tn] = dict(st, overcore_worst=oc[0], overcore_fails=oc[1][:6], overcore_n_fail=len(oc[1]),
                        stations_in_core=oc[2][:6], cut=ct)
        if a.png and (want is None or short in want):
            (out / "img").mkdir(exist_ok=True)
            render(T, short, st, oc, ct, out / "img" / ("ot_s81sl_leaf__%s_%s.png" % (short, a.tag)), a.tag)
    tot = dict(types=len(rows), station_bits=sum(r["station_bits"] for r in rows.values()),
               station_bits_core_core=sum(r["station_bits_core_core"] for r in rows.values()),
               station_bits_per_link_sum=sum(r["station_bits_per_link_sum"] for r in rows.values()),
               core_core_cycles=sum(r["core_core_cycles"] for r in rows.values()),
               crossings=sum(r["crossings"] for r in rows.values()),
               max_hop_um=max(r["max_hop_um"] for r in rows.values()),
               overcore_fail_types=sorted(k.split("__")[1] for k, r in rows.items() if r["overcore_n_fail"]),
               overcore_worst=max(r["overcore_worst"] for r in rows.values()),
               cut_worst=max(r["cut"]["ratio"] for r in rows.values()))
    json.dump(dict(total=tot, types=rows), open(out / ("%s_stats.json" % a.tag), "w"), indent=1)
    print(json.dumps(tot))


if __name__ == "__main__":
    main()
