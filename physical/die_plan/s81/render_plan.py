#!/usr/bin/env python3
"""Render a PLAN-S81 plan_internal.json: partitions by kind (type id label), channels hatched, lane polylines
(width ~ bits), faces over budget in red.  Usage: render_plan.py PLAN_DIR [OUT.png]"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COL = dict(frame="#8fb3d9", slice="#e8b26a", svc="#9ccf8f", link="#c9a0dc", phy="#9a9a9a", cte="#e07a7a",
           idx="#f0d060", unit="#70c0c0", lane="#f4f1e8")


def main():
    d = Path(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else str(d / "plan.png")
    pl = json.load(open(d / "plan_internal.json"))
    st = json.load(open(d / "stats.json"))
    tid = {}
    for k, names in st["types"].items():
        for n in names:
            tid[n] = k
    P = {p["name"]: p for p in pl["parts"]}
    fig, ax = plt.subplots(figsize=(26, 20.5))
    ax.add_patch(Rectangle((0, 0), 33000, 26000, fill=False, lw=2))
    for p in pl["parts"]:
        ax.add_patch(Rectangle((p["x0"], p["y0"]), p["w"], p["h"], fc=COL.get(p["kind"], "w"), ec="k", lw=0.4))
        lab = p["name"] if p["kind"] != "frame" else p["name"].split("_", 1)[1]
        fs = 3.2 if p["kind"] in ("frame", "lane", "cte") else 5
        ax.text(p["x0"] + p["w"] / 2, p["y0"] + p["h"] / 2, "%s\nT%s ft%d" % (lab, tid.get(p["name"], "?"),
                len(p["slots"])), ha="center", va="center", fontsize=fs)
    for c in pl["chans"]:
        x0, y0, x1, y1 = c["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="#c33", hatch="//", lw=0.3))
    # lanes: centre-to-centre polylines
    for ln in pl["lanes"]:
        path = pl["paths"].get(ln["id"])
        if not path or len(path) < 2:
            continue
        w = next((pt["width"] for pt in pl["ports"] if pt["lane"] == ln["id"]), 1)
        xs = [P[n]["x0"] + P[n]["w"] / 2 for n in path]
        ys = [P[n]["y0"] + P[n]["h"] / 2 for n in path]
        col = {"x": "#1f4fbf", "xo": "#1f4fbf", "ret": "#0a8a3a", "frame_int": "#888888"}.get(ln["cls"], "#7a1fa2")
        ax.plot(xs, ys, color=col, lw=0.15 + w / 1500.0, alpha=0.5)
    for f in pl["faces"]:
        if f["ratio"] > 0.6:
            a, b = P[f["a"]], P[f["b"]]
            if f["face"] in "EW":
                x = a["x0"] + a["w"] if f["face"] == "E" else a["x0"]
                ax.plot([x, x], [f["lo"], f["hi"]], color="red", lw=2.5)
            else:
                y = a["y0"] + a["h"] if f["face"] == "N" else a["y0"]
                ax.plot([f["lo"], f["hi"]], [y, y], color="red", lw=2.5)
    s = st["stats"]
    ax.set_title("S81 die plan %s: %d partitions, %d types, faces>0.6: %d, worst cut V %.3f H %.3f, stations %d"
                 % (d.name, s["partitions"], s["types"], s["faces_over_06"], s["worst_cut_V"][2],
                    s["worst_cut_H"][2], s["stations_total"]))
    ax.set_xlim(-200, 33200)
    ax.set_ylim(-200, 26200)
    ax.set_aspect("equal")
    plt.savefig(out, dpi=100, bbox_inches="tight")
    print(out)


if __name__ == "__main__":
    main()
