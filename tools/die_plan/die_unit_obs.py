#!/usr/bin/env python3
"""DIE-ROUTE-ABS-1: delete the GRT-only die obstructions from a unit / die route database before detail route.

grt/obs.tcl (written by `die_trial kit`) holds `create_obstruction -region {x0 y0 x1 y1} -layer Mn` lines for global route:
the PG stripes as obstructions and `reserve_rects`, the 0.4 um tracks reserved FOR the clock legs.  Detail route sees them as
fixed shapes: the clock wire put on its own reserved track shorts against its reservation (u201: 297 of 475 M8 markers).
The real PG stripes are special wires in the database and stay.  Only obstructions that match an obs.tcl line EXACTLY
(layer + rectangle) are deleted, so a macro or user obstruction is never touched.

Library (no odb import):  parse_obs_tcl(text, dbu) -> {(layer, x0, y0, x1, y1)};  drop_grt_obstructions(block, rects) -> stats
CLI (inside openroad -python):  die_unit_obs.py IN.odb OBS_TCL OUT.odb
"""
import re
import sys

_LINE = re.compile(r"^\s*create_obstruction\s+-region\s+\{\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\}\s+-layer\s+(\S+)\s*$")


def parse_obs_tcl(text, dbu=1000):
    """{(layer, x0, y0, x1, y1)} in database units; unknown lines are ignored"""
    out = set()
    for ln in text.splitlines():
        m = _LINE.match(ln)
        if m:
            x0, y0, x1, y1 = (int(round(float(m.group(i)) * dbu)) for i in range(1, 5))
            out.add((m.group(5), min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    return out


def drop_grt_obstructions(block, rects, destroy):
    """destroy every block obstruction whose (layer, bbox) is in rects.  `destroy` is odb.dbObstruction.destroy.
    -> dict(total, dropped, kept)"""
    drop, keep = [], 0
    for o in block.getObstructions():
        b = o.getBBox()
        if (b.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax()) in rects:
            drop.append(o)
        else:
            keep += 1
    for o in drop:
        destroy(o)
    return dict(total=len(drop) + keep, dropped=len(drop), kept=keep)


def main(argv):
    import odb
    src, obs, dst = argv
    db = odb.dbDatabase.create()
    odb.read_db(db, src)
    blk = db.getChip().getBlock()
    rects = parse_obs_tcl(open(obs).read(), blk.getDbUnitsPerMicron())
    st = drop_grt_obstructions(blk, rects, odb.dbObstruction.destroy)
    st["obs_tcl_rects"] = len(rects)
    print("GRT_OBS_DROP", st, flush=True)
    odb.write_db(db, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
