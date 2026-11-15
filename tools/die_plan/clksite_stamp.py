#!/usr/bin/env python3
"""CLKSITE-RESERVE-1115 stamp mode (FABLE-PD-HEAD-0945 fixes 1+2): geometry for 'one region tree per type, stamped on every
instance'.  Pure functions, type frame in / die frame out, so the clock generator and the reservation tool use the same rules.

  cell_box(xy)                    2.70 x 0.81 um site rectangle (cell 1.62 x 0.27 + 0.54 / 0.27 halo) centred at xy
  slide_off_pg(rect, ...)         move a rect in x by <= 1.3 um so it lies between two M7 PG pairs (no PG cut needed)
  orient_rect(rect, (W, H), o)    type-frame rect -> instance frame for R0 / MY / MX / R180: the RECT is mirrored (cell box
                                  mirrored with the instance), never only its node point
  stamp(template, (W, H), orients)  {instance: [rect]} die-relative rects of one template for each instance orientation
  start_stage_rows(stages, cap=7) <= cap row sites (5.40 x 0.81 um) per tile from type-frame start-stage positions
Exact stamp property: stage lengths are preserved by an orientation (isometry), so a tree with max leg 402.4 um stays <= 405.
"""
import math

CELL_BOX = (2.70, 0.81)
ROW_BOX = (5.40, 0.81)
PG_PITCH, PG_LO, PG_HI = 8.64, 3.984, 4.656        # kit M7 VDD/VSS pair: centre 4.128 / 4.512, width 0.288 -> [3.984, 4.656]


def cell_box(xy, box=CELL_BOX):
    return (xy[0] - box[0] / 2, xy[1] - box[1] / 2, xy[0] + box[0] / 2, xy[1] + box[1] / 2)


def _pg_overlap(x0, x1, pitch=PG_PITCH, lo=PG_LO, hi=PG_HI):
    k0 = math.floor((x0 - hi) / pitch)
    for k in range(k0, k0 + 3):
        if x0 < hi + k * pitch and x1 > lo + k * pitch:
            return k
    return None


def slide_off_pg(rect, max_slide=1.3, pitch=PG_PITCH, lo=PG_LO, hi=PG_HI):
    """-> (rect, slid_um) clear of every PG pair, or (None, None) when the 1.3 um slide does not clear it"""
    x0, y0, x1, y1 = rect
    if _pg_overlap(x0, x1, pitch, lo, hi) is None:
        return rect, 0.0
    best = None
    for d in sorted([i * 0.054 for i in range(-int(max_slide / 0.054), int(max_slide / 0.054) + 1)], key=abs):
        if _pg_overlap(x0 + d, x1 + d, pitch, lo, hi) is None:
            best = d
            break
    if best is None:
        return None, None
    return (round(x0 + best, 4), y0, round(x1 + best, 4), y1), round(abs(best), 4)


def orient_rect(rect, size, o):
    W, H = size
    x0, y0, x1, y1 = rect
    if o == "R0":
        return (x0, y0, x1, y1)
    if o == "MY":
        return (W - x1, y0, W - x0, y1)
    if o == "MX":
        return (x0, H - y1, x1, H - y0)
    if o == "R180":
        return (W - x1, H - y1, W - x0, H - y0)
    raise ValueError(f"orientation {o}")


def stamp(template, size, orients):
    """template [rect] type frame; orients {instance: orient} -> {instance: [rect]} (same sites, mirrored boxes)"""
    return {n: [orient_rect(r, size, o) for r in template] for n, o in orients.items()}


def start_stage_rows(stages, cap=7, box=ROW_BOX, size=None):
    """stages: [(x, y)] type-frame positions (or union over instances).  -> at most cap row rects (merged when more)."""
    rects = [cell_box(p, box) for p in sorted(set(map(tuple, stages)))]
    if len(rects) > cap:
        import clksite_reserve as C
        rects, _ = C.merge_rects(rects, cap)
    if size:
        rects = [(max(0, a), max(0, b), min(size[0], c), min(size[1], d)) for a, b, c, d in rects]
    return rects
