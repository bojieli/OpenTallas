#!/usr/bin/env python3
"""CB-CROSS preflight (FABLE-QC-CB 11-14, from the what-if conn6.py): count signal nets whose pins lie on both sides of a
hard core and level with it (the net must cross the tile or detour round it; M1-M5 are blocked over the tile).

Run on a placed database in OpenROAD's python:
    ODB=3_place.odb [OT_CROSS_MAX=20] openroad -python -exit tools/die_plan/cross_nets_check.py
Prints  OT_CROSS_NETS total T port_nets P other_nets O limit L PASS|FAIL  and the per-tile split; exit 1 on FAIL
(OT_CROSS_ADVISORY=1 keeps the exit 0).  `port_nets` = nets driven by a port or a clock-landing cell (they are allowed:
13 on cbn_q00); the limit applies to every other net (default 20).  Today (as built): cbn_q00 421, cbn_q11 414,
cbn_q01 635 crossing nets; the CB-HEADHOP / CB-XSTN hooks target <= 20.

The geometry is plain Python (straddles, classify) so it is unit-tested without OpenROAD."""
import os
import re
import sys

MARGIN_UM = 2.0
MAX_PINS = 50


def straddles(tile, xs, ys, margin=MARGIN_UM):
    """True when the pins span the tile left to right (beyond both faces by margin) and sit between its top and bottom."""
    x0, y0, x1, y1 = tile
    return min(xs) < x0 + margin and max(xs) > x1 - margin and min(ys) > y0 and max(ys) < y1


def is_port_net(driver_name):
    """Driven by a port ('PORT') or a clock-landing / ring cell."""
    return driver_name == "PORT" or "cland" in driver_name or "u_ring" in driver_name


def count(tiles, nets):
    """tiles {name: (x0, y0, x1, y1)}; nets iterable of (driver_name, xs, ys).  -> {tile: [port_nets, other_nets]}"""
    out = {}
    for drv, xs, ys in nets:
        if len(xs) < 2:
            continue
        for k, t in tiles.items():
            if straddles(t, xs, ys):
                out.setdefault(k, [0, 0])[0 if is_port_net(drv) else 1] += 1
    return out


def main():
    import odb
    db = odb.dbDatabase.create()
    odb.read_db(db, os.environ["ODB"])
    blk = db.getChip().getBlock()
    U = float(blk.getDbUnitsPerMicron())
    tiles = {}
    for i in blk.getInsts():
        if i.getMaster().isBlock():
            b = i.getBBox()
            tiles[i.getName().split(".")[-1]] = (b.xMin() / U, b.yMin() / U, b.xMax() / U, b.yMax() / U)
    nets = []
    for n in blk.getNets():
        if n.getSigType() != "SIGNAL" or n.getITermCount() > MAX_PINS:
            continue
        xs, ys, drv = [], [], "PORT"
        for it in n.getITerms():
            ok, x, y = it.getAvgXY()
            if not ok:
                b = it.getInst().getBBox()
                x, y = (b.xMin() + b.xMax()) // 2, (b.yMin() + b.yMax()) // 2
            xs.append(x / U)
            ys.append(y / U)
            if it.isOutputSignal():
                drv = re.sub(r"\\", "", it.getInst().getName())
        for bt in n.getBTerms():
            b = bt.getBBox()
            xs.append((b.xMin() + b.xMax()) / 2 / U)
            ys.append((b.yMin() + b.yMax()) / 2 / U)
        nets.append((drv, xs, ys))
    per = count(tiles, nets)
    port = sum(v[0] for v in per.values())
    other = sum(v[1] for v in per.values())
    limit = int(os.environ.get("OT_CROSS_MAX", "20"))
    ok = other <= limit
    print("OT_CROSS_NETS total %d port_nets %d other_nets %d limit %d %s per_tile %s"
          % (port + other, port, other, limit, "PASS" if ok else "FAIL", {k: tuple(v) for k, v in sorted(per.items())}))
    if not ok and os.environ.get("OT_CROSS_ADVISORY") != "1":
        sys.exit(1)


if __name__ == "__main__":
    main()
