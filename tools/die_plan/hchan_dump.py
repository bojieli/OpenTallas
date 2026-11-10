"""DIE-S81-85 HCHAN 11-10 (DO_NOT_COUNT): dump what hchan.py needs from a placed ODB, read-only.

HCHAN_IN=IN.odb HCHAN_OUT=OUT.json openroad -python -exit hchan_dump.py
-> {dbu, die, core, macros: [{name, master, box, orient, loc, obs}], tracks: {layer: {dir, pitch}},
    nets: [[xmin, ymin, xmax, ymax, n_cell_pins, [[macro_idx, x, y], ...]]]}  (um; cell box covers std-cell pins and bterms)
Power/ground nets are skipped as nets; their horizontal stripes go to pg [layer, box].  Nothing is written to the ODB.
"""
import json
import os
import sys

import odb


def main(src, dst):
    db = odb.dbDatabase.create()
    odb.read_db(db, src)
    blk = db.getChip().getBlock()
    u = float(blk.getDbUnitsPerMicron())
    die = blk.getDieArea()
    core = blk.getCoreArea()
    macros, midx = [], {}
    for i in blk.getInsts():
        m = i.getMaster()
        if not m.isBlock():
            continue
        b = i.getBBox()
        obs = sorted({o.getTechLayer().getName() for o in m.getObstructions() if o.getTechLayer()})
        lx, ly = i.getLocation()
        midx[i.getName()] = len(macros)
        macros.append({"name": i.getName(), "master": m.getName(), "orient": i.getOrient(),
                       "box": [b.xMin() / u, b.yMin() / u, b.xMax() / u, b.yMax() / u], "loc": [lx / u, ly / u],
                       "obs": obs})
    tracks = {}
    for tl in db.getTech().getLayers():
        if tl.getType() != "ROUTING":
            continue
        tracks[tl.getName()] = {"dir": tl.getDirection(), "pitch": tl.getPitch() / u}
    for g in blk.getTrackGrids():
        tl = g.getTechLayer()
        if tl.getName() in tracks:
            ps = []
            for k in range(g.getNumGridPatternsY()):
                ps.append(g.getGridPatternY(k)[2] / u)
            for k in range(g.getNumGridPatternsX()):
                ps.append(g.getGridPatternX(k)[2] / u)
            if ps:
                tracks[tl.getName()]["grid_pitch"] = min(ps)
    nets = []
    for n in blk.getNets():
        if n.getSigType() in ("POWER", "GROUND"):
            continue
        xs, ys, mp = [], [], []
        for it in n.getITerms():
            ok, x, y = it.getAvgXY()
            if not ok:
                b = it.getInst().getBBox()
                x, y = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
            k = midx.get(it.getInst().getName())
            if k is None:
                xs.append(x); ys.append(y)
            else:
                mp.append([k, round(x / u, 4), round(y / u, 4)])
        for bt in n.getBTerms():
            ok, x, y = bt.getFirstPinLocation()
            if ok:
                xs.append(x); ys.append(y)
        if len(xs) + len(mp) < 2:
            continue
        box = [min(xs) / u, min(ys) / u, max(xs) / u, max(ys) / u] if xs else None
        nets.append([*(round(v, 4) for v in box)] + [len(xs), mp] if box else [None, None, None, None, 0, mp])
    # power-grid stripes on horizontal routing layers (GRT takes them as blockage: S81 macro M6 straps halve the
    # over-macro M6 capacity, t15 attempt_8 congestion.rpt capacity 3 per 0.57-um gcell against 6.2 nominal)
    hl = {n for n, t in tracks.items() if t["dir"] == "HORIZONTAL" and n not in ("M1", "Pad")}
    pg = []
    for n in blk.getNets():
        if not n.isSpecial():
            continue
        for sw in n.getSWires():
            for w in sw.getWires():
                if w.isVia():
                    continue
                tl = w.getTechLayer()
                if tl is None or tl.getName() not in hl:
                    continue
                pg.append([tl.getName(), w.xMin() / u, w.yMin() / u, w.xMax() / u, w.yMax() / u])
    out = {"src": src, "pg": pg, "dbu": u, "die": [die.xMin() / u, die.yMin() / u, die.xMax() / u, die.yMax() / u],
           "core": [core.xMin() / u, core.yMin() / u, core.xMax() / u, core.yMax() / u],
           "macros": macros, "tracks": tracks, "nets": nets}
    with open(dst, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"HCHAN_DUMP macros={len(macros)} nets={len(nets)} -> {dst}")


main(os.environ.get("HCHAN_IN") or sys.argv[1], os.environ.get("HCHAN_OUT") or sys.argv[2])
