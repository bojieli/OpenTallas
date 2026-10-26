#!/usr/bin/env python3
"""KVG3-CORES review: partition-level picture of the planned hard cores of one KV partition type.

    python3 render_part_cores.py PLAN.json TYPE OUT.png [--conns core_conns.json]

Draws the partition outline, clock tap, every hard core (orient applied) with its pins from the plan pins file
(red dots), and for every core the share of its pins that leave on a face blocked by another core closer than
BLOCK_UM ('blocked' faces: the pins must route sideways through the gap).  Prints a JSON summary per core.
"""
import json
import sys
from pathlib import Path

BLOCK_UM = 60.0


def xform(x, y, w, h, o):
    if o == "R0":
        return x, y
    if o == "MX":
        return x, h - y
    if o == "MY":
        return w - x, y
    if o == "R180":
        return w - x, h - y
    raise SystemExit(f"orient {o}")


def main(plan, typ, outp, conns=None):
    root = Path(plan).resolve().parent
    CC = json.load(open(conns or root / "core_conns.json")).get(typ, {})
    P = json.load(open(plan))
    T = P["partition_types"][typ]
    W, H = T["outline_um"]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 11 * H / W), dpi=120)
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.2))
    tx, ty = T["clock"]["tap_um"]
    ax.plot([tx], [ty], marker="*", ms=14, color="tab:orange")
    rects = []
    for c in T["hard_cores"]:
        (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
        rects.append((c["inst"], x0, y0, x0 + w, y0 + h))
    summ = {}
    for c in T["hard_cores"]:
        (x0, y0), (w, h) = c["origin_um"], c["outline_um"]
        o = c.get("orient", "R0")
        ax.add_patch(plt.Rectangle((x0, y0), w, h, fc="tab:blue", alpha=0.15, ec="tab:blue"))
        ax.text(x0 + 3, y0 + h / 2, f"{c['inst']}\n{c['module']} {o}", fontsize=6)
        pf = c.get("pins_file")
        if not pf or not (root / pf).is_file():
            continue
        pins = json.load(open(root / pf))["pins"]
        xs, ys, face = [], [], {"N": 0, "S": 0, "E": 0, "W": 0}
        pface = {}
        for p in pins:
            px, py = xform(p["x"], p["y"], w, h, o)
            xs.append(x0 + px)
            ys.append(y0 + py)
            f = "W" if px < 1 else "E" if px > w - 1 else "S" if py < 1 else "N"
            face[f] += 1
            pface[p["name"]] = (f, x0 + px, y0 + py)
        ax.scatter(xs, ys, s=0.4, color="tab:red")
        gap = {}
        for f in face:
            best = None
            for n, a0, b0, a1, b1 in rects:
                if n == c["inst"]:
                    continue
                if f == "N" and a0 < x0 + w and a1 > x0 and b0 >= y0 + h:
                    d = b0 - (y0 + h)
                elif f == "S" and a0 < x0 + w and a1 > x0 and b1 <= y0:
                    d = y0 - b1
                elif f == "E" and b0 < y0 + h and b1 > y0 and a0 >= x0 + w:
                    d = a0 - (x0 + w)
                elif f == "W" and b0 < y0 + h and b1 > y0 and a1 <= x0:
                    d = x0 - a1
                else:
                    continue
                if best is None or d < best[0]:
                    best = (round(d, 2), n)
            if f == "N" and best is None:
                best = (round(H - (y0 + h), 2), "edge")
            gap[f] = best
        # pins on a face whose nearest core (< BLOCK_UM) is NOT among the pin's connection targets: they must
        # detour through the gap around that core
        cc = CC.get(c["inst"], {})
        detour, dxy = {}, []
        for pn, (f, ax_, ay_) in pface.items():
            hit = None
            for n, a0, b0, a1, b1 in rects:
                if n == c["inst"]:
                    continue
                if f == "N" and a0 <= ax_ <= a1 and 0 <= b0 - ay_ < BLOCK_UM:
                    hit = n
                elif f == "S" and a0 <= ax_ <= a1 and 0 <= ay_ - b1 < BLOCK_UM:
                    hit = n
                elif f == "E" and b0 <= ay_ <= b1 and 0 <= a0 - ax_ < BLOCK_UM:
                    hit = n
                elif f == "W" and b0 <= ay_ <= b1 and 0 <= ax_ - a1 < BLOCK_UM:
                    hit = n
            if hit and f"core:{hit}" not in cc.get(pn.split("[")[0], []):
                detour[f"{f}->{hit}"] = detour.get(f"{f}->{hit}", 0) + 1
                dxy.append((ax_, ay_))
        if dxy:
            ax.scatter([q[0] for q in dxy], [q[1] for q in dxy], s=2.5, color="black", marker="x")
        blocked = sum(n for f, n in face.items() if n and gap.get(f) and gap[f][1] != "edge" and gap[f][0] < BLOCK_UM)
        summ[c["inst"]] = dict(module=c["module"], orient=o, pins_by_face=face, nearest_on_face=gap,
                               pins_on_blocked_faces=blocked, detour_pins=detour)
    ax.set_xlim(-10, W + 10)
    ax.set_ylim(-10, H + 10)
    ax.set_aspect("equal")
    ax.set_title(f"{typ}: hard cores + plan pins (red; black x = pin faces a core < {BLOCK_UM:g} um away it does not connect to), clock tap (star)", fontsize=9)
    fig.tight_layout()
    fig.savefig(outp)
    Path(outp + ".json").write_text(json.dumps(summ, indent=1) + "\n")
    for k, v in summ.items():
        print(k, v["module"], v["orient"], v["pins_by_face"], v["nearest_on_face"], "near-core faces", v["pins_on_blocked_faces"], "DETOUR", v["detour_pins"])


if __name__ == "__main__":
    main(*sys.argv[1:5])
