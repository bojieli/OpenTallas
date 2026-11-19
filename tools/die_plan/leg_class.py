"""leg_class.py -- CBC rule 2 by wire class, not distance alone (COORD 11-19 from FABLE-CLOSURE-STRATEGY 03:30, lever 3).

A buffered register-to-pin leg with no logic closes to about 550 um (col_h9_r2 passes 30 / 30 with ~3,400 legs at 491-550 um);
a leg over a hard core cannot be buffered and fails near 400.  So a leg over cbc_rules.REACH_UM_PER_HOP takes +cycle
stations only if its path spans more than REACH_CORE_SPAN_UM of hard core or it carries logic; a pure buffered leg is
priced at REACH_BUFFERED_UM per hop; static strap / tie legs never count.
"""
import math
import re

import cbc_rules as RULES

STATIC = re.compile(RULES.STATIC_LEG_RE)


def _overlap(lo, hi, a, b):
    return max(0.0, min(hi, b) - max(lo, a))


def seg_core_um(p, q, rects):
    """length of the axis-aligned segment p -> q inside the rectangles [(x0, y0, x1, y1)]"""
    if p[1] == q[1]:
        lo, hi = sorted((p[0], q[0]))
        return sum(_overlap(lo, hi, x0, x1) for x0, y0, x1, y1 in rects if y0 < p[1] < y1)
    lo, hi = sorted((p[1], q[1]))
    return sum(_overlap(lo, hi, y0, y1) for x0, y0, x1, y1 in rects if x0 < p[0] < x1)


def core_span_um(a, b, rects):
    """hard-core length along the better of the two L paths a -> b (the router takes the cheaper bend)"""
    xy = (b[0], a[1])
    yx = (a[0], b[1])
    return min(seg_core_um(a, xy, rects) + seg_core_um(xy, b, rects), seg_core_um(a, yx, rects) + seg_core_um(yx, b, rects))


def core_rects(t):
    out = []
    for h in t.get("hard_cores") or []:
        if "origin_um" in h and "outline_um" in h:
            dx, dy = h.get("track_offset_um", [0.0, 0.0])
            x0, y0 = h["origin_um"][0] + dx, h["origin_um"][1] + dy
            out.append((x0, y0, x0 + h["outline_um"][0], y0 + h["outline_um"][1]))
    return out


def classify(length_um, core_um=0.0, logic=False, name=""):
    """-> (class, hops): class 'static' (strap / tie: never a cycle), 'core' (over REACH_CORE_SPAN_UM of hard core),
    'logic' (carries logic), 'buffered' (pure wire, repair buffers it); hops = register-to-register hops the leg needs
    (1 = closes as is; stations = hops - 1 on a leg with none)"""
    if STATIC.search(name or ""):
        return "static", 1
    if core_um > RULES.REACH_CORE_SPAN_UM:
        return "core", max(1, math.ceil(length_um / RULES.REACH_UM_PER_HOP - 1e-9))
    if logic:
        return "logic", max(1, math.ceil(length_um / RULES.REACH_UM_PER_HOP - 1e-9))
    return "buffered", max(1, math.ceil(length_um / RULES.REACH_BUFFERED_UM - 1e-9))
