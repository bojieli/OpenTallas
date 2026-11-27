#!/usr/bin/env python3
"""geom_corridor.py -- REPORT-ONLY fill metric `fill_corridor` for AUTO-GEOM (COORD RULING 2026-11-27 09:25 PST item 7,
class C-SPARSE-OUTLINE; related C-FILL-RULE-STRUCTURAL).

Why: AUTO-GEOM `fill` (geom_rules.area_metrics fill_of_free = std-cell area / (outline - macros), gate >= 0.15) cannot be met by
a fixed-pin sparse partition whose outline is set by its pin envelope (QC coll_ftc: pin envelope 848,781 um2, 32,437 um2 of
cells = 3.8 %).  COORD ruled YES, on the easiest-closure reading, to ALSO measure fill inside the DECLARED landing and
routing corridors, ONLY for pin-hull-bound, macro-free collector types, with the raw fill reported next to it.

This module computes that second number.  It changes no gate: the raw `fill` rule and every verdict are untouched; the
`fill_corridor` rule row is INFO (never PASS/FAIL/WARN) and appears beside the raw fill.

Definition (all geometry in the type frame, um, clipped to the type outline; plan record = partition_types[<type>]):
  declared corridors (union of rectangles, overlaps counted once):
    landing   : per outline face that carries signal pins, a strip PIN_STRIP_UM (30 um) deep along that face's pin span --
                AUTO-GEOM pin_reg already requires every pin register within 30 um (p90) of its pin, so that strip is the
                landing area the rule set itself demands (pins are fixed by the plan; measured from the dump)
    landing   : clock.landing_contract.bands[*].rect_um          (declared landing-ring bands)
    landing   : clock.landing_contract.group_rects_um[*]         (declared reset-landing group rects)
    routing   : per ft_slots[*] station j: bounding box of bit_sites_um[j] grown by bit_site_cell_um (w, h) on the
                upper-right (sites are lower-left origins)  -- the declared feed-through station site footprint
  fill_corridor = std-cell area of cells whose CENTRE lies in the corridor union / area of the corridor union
                  (std cells = geom_rules area_metrics set: dump kinds S, B, K, L; macros excluded)
  also reported: corridor_area, cell_area_in/total, share_in (= cells in corridors / all std cells; a low share means the
  design is mostly OUTSIDE the corridors and fill_corridor says little), raw_fill.

Eligibility (all three from plan / measured data, never from names; all must hold or fill_corridor is None):
  collector     : clock.landing_contract.collector_tree is a dict AND ft_slots is non-empty AND `contents` is empty
                  (the type declares no logic content of its own: it only lands, relays and feeds clock/reset/data through)
  macro_free    : no hard_cores, no `hard` block, no `macro_under_ft`, and (when measured) zero hard macros in the dump
  pin_hull_bound: the signal-pin bounding box spans >= PIN_HULL_SPAN (0.98) of the outline width AND height (pins on
                  opposite faces on both axes), so the outline cannot shrink below the pin envelope; pin_hull_frac = bbox area
                  / outline area is reported (QC coll_ftc 848,781 / 849,139 = 0.9996)
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

SCHEMA = "opentallas.fill_corridor.v1"
PIN_HULL_SPAN = 0.98
PIN_STRIP_UM = 30.0     # geom_rules PIN_REG_P90: AUTO-GEOM requires every pin register within 30 um (p90) of its pin
FACE_TOL_UM = 2.0       # geom_rules.face_of tolerance


def _rect(r, W, H):
    """[x0, y0, x1, y1] clipped to the outline; None when empty / malformed"""
    try:
        x0, y0, x1, y1 = (float(v) for v in r[:4])
    except (TypeError, ValueError):
        return None
    x0, x1 = max(0.0, min(x0, x1)), min(W, max(x0, x1))
    y0, y1 = max(0.0, min(y0, y1)), min(H, max(y0, y1))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def pin_strips(pins, W, H):
    """landing strips: per outline face carrying signal pins, PIN_STRIP_UM deep along the pin span of that face"""
    byf = {"W": [], "E": [], "S": [], "N": []}
    for x, y in pins or []:
        f = ("W" if x < FACE_TOL_UM else "E" if x > W - FACE_TOL_UM else "S" if y < FACE_TOL_UM
             else "N" if y > H - FACE_TOL_UM else None)
        if f:
            byf[f].append(y if f in "WE" else x)
    d, out = PIN_STRIP_UM, []
    for f, v in byf.items():
        if not v:
            continue
        lo, hi = min(v), max(v)
        r = {"W": [0, lo, d, hi], "E": [W - d, lo, W, hi], "S": [lo, 0, hi, d], "N": [lo, H - d, hi, H]}[f]
        r = _rect(r, W, H)
        if r:
            out.append(("pin_landing_strip",) + r)
    return out


def corridor_rects(t, pins=None):
    """[(kind, x0, y0, x1, y1)] declared corridors of one plan partition type (type frame, clipped); pins = [(x, y)]"""
    W, H = (float(v) for v in t["outline_um"][:2])
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    out = []
    for b in (lc.get("bands") or {}).values():
        r = _rect(b.get("rect_um") or [], W, H) if isinstance(b, dict) else None
        if r:
            out.append(("landing_band",) + r)
    for r in (lc.get("group_rects_um") or {}).values():
        r = _rect(r, W, H)
        if r:
            out.append(("landing_group",) + r)
    for s in t.get("ft_slots") or []:
        if not isinstance(s, dict):
            continue
        cw, ch = (list(s.get("bit_site_cell_um") or []) + [0.0, 0.0])[:2]
        for st in s.get("bit_sites_um") or []:
            pts = [p for p in st if isinstance(p, (list, tuple)) and len(p) >= 2]
            if not pts:
                continue
            xs, ys = [float(p[0]) for p in pts], [float(p[1]) for p in pts]
            r = _rect([min(xs), min(ys), max(xs) + float(cw), max(ys) + float(ch)], W, H)
            if r:
                out.append(("routing_station",) + r)
    return out + pin_strips(pins, W, H)


class Union:
    """exact union of axis-aligned rectangles: disjoint y-intervals per x-slab, O(log n) point test"""

    def __init__(self, rects):
        xs = sorted({v for r in rects for v in (r[0], r[2])})
        self.xs, self.slabs, self.area = xs, [], 0.0
        for a, b in zip(xs, xs[1:]):
            iv = sorted((r[1], r[3]) for r in rects if r[0] <= a and r[2] >= b)
            merged = []
            for lo, hi in iv:
                if merged and lo <= merged[-1][1]:
                    merged[-1][1] = max(merged[-1][1], hi)
                else:
                    merged.append([lo, hi])
            self.slabs.append(([m[0] for m in merged], [m[1] for m in merged]))
            self.area += (b - a) * sum(m[1] - m[0] for m in merged)

    def contains(self, x, y):
        i = bisect.bisect_right(self.xs, x) - 1
        if i < 0 or i >= len(self.slabs):
            return False
        los, his = self.slabs[i]
        k = bisect.bisect_right(los, y) - 1
        return k >= 0 and y <= his[k]


def eligibility(t, outline=None, pins=None, macros=None):
    """dict(eligible, collector, macro_free, pin_hull_bound, pin_hull_frac, reasons[]); pins = [(x, y)] in the type frame
    (None = not measurable -> pin_hull_bound False), macros = measured hard-macro count (None = not measured)"""
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    reasons = []
    collector = isinstance(lc.get("collector_tree"), dict) and bool(t.get("ft_slots")) and not t.get("contents")
    if not collector:
        reasons.append("not collector (needs landing_contract.collector_tree, ft_slots, empty contents)")
    macro_free = not t.get("hard_cores") and not t.get("hard") and not t.get("macro_under_ft") and not macros
    if not macro_free:
        reasons.append("not macro-free (hard_cores / hard / macro_under_ft / measured macros)")
    W, H = (float(v) for v in (outline or t["outline_um"])[:2])
    frac, hull = None, False
    if pins:
        xs, ys = [p[0] for p in pins], [p[1] for p in pins]
        sx, sy = (max(xs) - min(xs)) / W, (max(ys) - min(ys)) / H
        frac = round(sx * sy, 4)
        hull = sx >= PIN_HULL_SPAN and sy >= PIN_HULL_SPAN
    if not hull:
        reasons.append("not pin-hull-bound" if pins else "pin hull not measurable")
    return dict(eligible=collector and macro_free and hull, collector=collector, macro_free=macro_free,
                pin_hull_bound=hull, pin_hull_frac=frac, reasons=reasons)


def fill_corridor(t, cells, pins, outline=None, macros=0, raw_fill=None):
    """cells = [(x0, y0, x1, y1)] std cells in the type frame; pins = [(x, y)] signal pins in the type frame.
    Returns the report dict (fill_corridor None unless eligible); never raises on a malformed plan record."""
    el = eligibility(t, outline, pins, macros)
    res = dict(schema=SCHEMA, raw_fill=raw_fill, fill_corridor=None, **el)
    if not el["eligible"]:
        return res
    rects = corridor_rects(t, pins)
    u = Union([r[1:] for r in rects])
    tot = ins = 0.0
    for c in cells:
        a = (c[2] - c[0]) * (c[3] - c[1])
        tot += a
        if u.contains((c[0] + c[2]) / 2, (c[1] + c[3]) / 2):
            ins += a
    kinds = {}
    for r in rects:
        kinds[r[0]] = kinds.get(r[0], 0) + 1
    res.update(corridor_area=round(u.area, 3), corridor_rects=kinds, cell_area_in=round(ins, 3), cell_area_total=round(tot, 3),
               share_in=round(ins / tot, 4) if tot > 0 else None,
               fill_corridor=round(ins / u.area, 4) if u.area > 0 else None)
    return res


def load_type(plan_path=None, type_name=None, type_json=None):
    """a plan partition type from PLAN.json + name, or from a file holding the type record itself"""
    if type_json:
        return json.loads(Path(type_json).read_text())
    return json.loads(Path(plan_path).read_text())["partition_types"][type_name]


def detail(res):
    if res.get("fill_corridor") is None:
        return "raw fill %s; fill_corridor n/a: %s" % (res.get("raw_fill"), "; ".join(res.get("reasons") or ["no corridor area"]))
    return ("raw fill %s (gate unchanged); fill_corridor %s = %s um2 of cells in / %s um2 declared corridors %s; "
            "%s of all std-cell area lies in the corridors; pin_hull_frac %s; REPORT-ONLY"
            % (res["raw_fill"], res["fill_corridor"], res["cell_area_in"], res["corridor_area"], res["corridor_rects"],
               res["share_in"], res["pin_hull_frac"]))
