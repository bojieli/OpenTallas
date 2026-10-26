#!/usr/bin/env python3
"""HEAD-CORE-LAT render for GEOM-REVIEW: core outline, ROM macros, std-cell density, clock cells/branches, the infra
island hole (placement blockages + route obstructions), clk/rst_n pins, plus a zoom panel on the hole.
  dump (inside ORFS docker):  ODB=... OUT=dump.json openroad -python -exit infra_island_render.py dump
  plot (host python3):        python3 infra_island_render.py plot dump.json out.png "title"
"""
import json, os, sys


def dump():
    import odb
    b = odb.read_db(odb.dbDatabase.create(), os.environ["ODB"]).getChip().getBlock()
    u = b.getDbUnitsPerMicron()
    R = lambda z: [z.xMin() / u, z.yMin() / u, z.xMax() / u, z.yMax() / u]
    die = R(b.getDieArea())
    cells, edges = [], []
    ctr = lambda i: [(i.getBBox().xMin() + i.getBBox().xMax()) / 2 / u, (i.getBBox().yMin() + i.getBBox().yMax()) / 2 / u]
    for i in b.getInsts():
        m = i.getMaster()
        mn = m.getName()
        if m.isBlock():
            k = "macro"
        elif mn.startswith(("TAPCELL", "FILL", "DECAP")):
            continue
        elif any(t.getNet() and t.getNet().getSigType() == "CLOCK" and t.getIoType() == "OUTPUT" for t in i.getITerms()):
            k = "clock"
        elif "DFF" in mn:
            k = "ff"
        else:
            k = "std"
        cells.append({"n": i.getName(), "k": k, "xy": ctr(i), "bb": R(i.getBBox())})
    for n in b.getNets():
        if n.getSigType() != "CLOCK":
            continue
        ds = [t for t in n.getITerms() if t.getIoType() == "OUTPUT"]
        src = ctr(ds[0].getInst()) if len(ds) == 1 else None
        if src is None:
            for bt in n.getBTerms():
                for bp in bt.getBPins():
                    src = [(bp.getBBox().xMin() + bp.getBBox().xMax()) / 2 / u, (bp.getBBox().yMin() + bp.getBBox().yMax()) / 2 / u]
        if src is None:
            continue
        for t in n.getITerms():
            if t.getIoType() == "INPUT" and "DFF" not in t.getInst().getMaster().getName():
                edges.append([src, ctr(t.getInst())])
    blk = [R(x.getBBox()) for x in b.getBlockages()]
    obs = [[x.getBBox().getTechLayer().getName()] + R(x.getBBox()) for x in b.getObstructions()]
    pins = {}
    for bt in b.getBTerms():
        if bt.getName() in ("clk", "rst_n"):
            for bp in bt.getBPins():
                pins[bt.getName()] = R(bp.getBBox())
    inhole = []
    for x in blk:
        for c in cells:
            if c["k"] != "macro" and c["bb"][0] < x[2] and c["bb"][2] > x[0] and c["bb"][1] < x[3] and c["bb"][3] > x[1]:
                inhole.append(c["n"])
    json.dump({"die": die, "cells": cells, "edges": edges, "blockages": blk, "obstructions": obs, "pins": pins,
               "cells_in_keepout": inhole}, open(os.environ["OUT"], "w"))
    print("RENDER_DUMP cells", len(cells), "clock", sum(c["k"] == "clock" for c in cells), "blk", blk, "obs", len(obs),
          "pins", pins, "cells_in_keepout", len(inhole))


def plot(js, png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    q = json.load(open(js))
    f, (a, z) = plt.subplots(1, 2, figsize=(18, 9))
    for ax in (a, z):
        l, bm, r, t = q["die"]
        ax.add_patch(Rectangle((l, bm), r - l, t - bm, fill=False, color="black", lw=1))
        for c in q["cells"]:
            x, y = c["xy"]
            if c["k"] == "macro":
                L, B, Rr, T = c["bb"]
                ax.add_patch(Rectangle((L, B), Rr - L, T - B, fill=True, alpha=.15, color="black"))
                ax.text(L, T, c["n"], fontsize=7)
            elif c["k"] == "ff":
                ax.plot(x, y, ".", c="grey", ms=.6, alpha=.25)
            elif c["k"] == "std" and ax is z:
                ax.plot(x, y, ".", c="lightgrey", ms=1, alpha=.4)
            elif c["k"] == "clock":
                ax.plot(x, y, "o", c="royalblue", ms=2 if ax is a else 4)
        for p, s in q["edges"]:
            ax.plot([p[0], s[0]], [p[1], s[1]], c="cyan", lw=.3, alpha=.6)
        for L, B, Rr, T in q["blockages"]:
            ax.add_patch(Rectangle((L, B), Rr - L, T - B, fill=False, color="orange", lw=1.5))
        for o in q["obstructions"]:
            L, B, Rr, T = o[1:]
            ax.add_patch(Rectangle((L, B), Rr - L, T - B, fill=True, alpha=.25, color="red"))
        for n, (L, B, Rr, T) in q["pins"].items():
            ax.plot((L + Rr) / 2, (B + T) / 2, "*", c="magenta", ms=10)
            ax.text(Rr, T, n, color="magenta", fontsize=9)
    if q["blockages"]:
        L, B, Rr, T = q["blockages"][0]
        z.set_xlim(L - 30, Rr + 30)
        z.set_ylim(B - 30, T + 30)
    a.set(aspect="equal", title=title)
    z.set(aspect="equal", title="infra island zoom (orange = core keep-out, red = M2-M5 OBS = top-owned hole, * = clk/rst_n)  cells in keep-out: %d" % len(q["cells_in_keepout"]))
    f.savefig(png, bbox_inches="tight", dpi=110)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "plot":
        plot(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    else:
        dump()
