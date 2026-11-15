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


_TAP = re.compile(r"^t_.+__clk(_t\d+)?$")


RAIL_M8 = (2.16, 0.24, 0.06)    # die M8 PG rails: centres every 2.16 um (VDD/VSS alternate), half width 0.24, wire clearance 0.06


def snap_pin_rect(rect, dbu=1000, pitch_um=0.08, offset_um=0.04, rails=RAIL_M8):
    """move a pin rectangle (dbu) so its centre lies on the M9 x / M8 y track grid (offset 0.04, pitch 0.08 um); size kept.
    y additionally avoids the die M8 PG rails (rails = (rail pitch, rail half width, clearance) um; None = off): the
    nearest M8 track whose centre is at least half width + clearance from every rail centre."""
    p, o = int(round(pitch_um * dbu)), int(round(offset_um * dbu))
    x0, y0, x1, y1 = rect

    def ok_y(t):
        if not rails:
            return True
        rp, rh, rc = (int(round(v * dbu)) for v in rails)
        d = abs(t - round(t / rp) * rp)
        return d >= rh + rc

    def one(lo, hi, is_y):
        c2 = lo + hi                                   # twice the centre, keeps integers
        k = int(round(((c2 / 2.0) - o) / p))
        t = k * p + o
        if is_y:
            n = 0
            while not ok_y(t) and n < 400:
                n += 1
                t = (k + ((n + 1) // 2) * (1 if n % 2 else -1)) * p + o
        d = t * 2 - c2
        return lo + d // 2, hi + d // 2
    nx0, nx1 = one(x0, x1, False)
    ny0, ny1 = one(y0, y1, True)
    return nx0, ny0, nx1, ny1


def snap_tap_pins(block, odb_mod, dbu=1000):
    """die clock tap terminals (t_<part>__clk_tN): re-create each pin box on the track grid.  -> dict(pins, moved)"""
    pins = moved = 0
    for bt in list(block.getBTerms()):
        if not _TAP.match(bt.getName()):
            continue
        boxes = [(b.getTechLayer(), (b.xMin(), b.yMin(), b.xMax(), b.yMax())) for bp in bt.getBPins() for b in bp.getBoxes()]
        if not boxes:
            continue
        pins += 1
        for bp in list(bt.getBPins()):
            odb_mod.dbBPin.destroy(bp)
        nbp = odb_mod.dbBPin.create(bt)
        for lay, r in boxes:
            n = snap_pin_rect(r, dbu)
            moved += n != r
            odb_mod.dbBox.create(nbp, lay, *n)
        nbp.setPlacementStatus("FIRM")
    return dict(pins=pins, moved=moved)


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
