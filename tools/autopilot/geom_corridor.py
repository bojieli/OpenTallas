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
  collector     : (pure feed-through collector tile) plan die is in COLLECTOR_DIES (qwen_compute: the ruling is QC-only; the
                  record carries it as `_die`, set by load_type / the kit record writer), clock.landing_contract.collector_tree
                  is a non-empty dict, ft_slots is non-empty AND `contents` is empty (the type declares no logic of its own:
                  it only lands, relays and feeds clock/reset/data through).  collector_tree alone does not discriminate
                  (it is on nearly every type); on S81 the same shape is a slice station, hence the die scope (FABLE review M1)
  content_free  : the KIT declares no content instance: kit_hierarchy.json (generator) has expected 0 and required_expected 0,
                  no hard / required instance and no hierarchy problem; carried on the record as `_kit_content`, set by
                  load_type from the kit the checkpoint was built from.  The plan `contents` test alone admits a tile whose
                  logic is bound through required instances (QC slw_fw_v2: required_expected 74); a missing or invalid
                  declaration grants nothing (COORD flow review 1247 item 1, QC-R3-FTC)
  macro_free    : no hard_cores, no `hard` block, no `macro_under_ft`, and (when measured) zero hard macros in the dump
  pin_hull_bound: >= PIN_HULL_MIN_PINS (100) signal pins whose full extent (min..max: fixed pins cannot move, so the
                  outline cannot shrink below the farthest pin) spans >= PIN_HULL_SPAN (0.98) of the measured outline width
                  AND height; pin_hull_frac = span_x * span_y is reported (QC coll_ftc 848,781 / 849,139 = 0.9996).  The
                  p1..p99 trimmed extent is reported alongside as pin_hull_frac_robust (information; it is far lower for the
                  small collector siblings, whose far-end pins are few).  This is an extent test: a face may carry no pins.
  frame         : the plan record outline must equal the measured outline within OUTLINE_TOL, else ineligible (wrong type /
                  stale record); all geometry uses the measured outline.

Numerator: EXACT cell area overlapping the corridor union (a cell straddling an edge counts its overlap), so the value is
bounded by 1.  The result is reported per corridor kind, with the number of ft slots that declare no station sites
(`ft_slots_undeclared`): routing area is only counted where the plan declares it, so the value degrades to landing-only,
visibly, on a plan without bit_sites_um.  Provenance (`_plan_sha256`, `_type`, `_die`) of the record is echoed.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "opentallas.fill_corridor.v1"
PIN_HULL_SPAN = 0.98
PIN_STRIP_UM = 30.0     # == geom_rules.PINREG_P90 (asserted in the test): every pin register within 30 um (p90) of its pin
PIN_HULL_MIN_PINS = 100
OUTLINE_TOL = 0.01      # == geom_rules.OUTLINE_TOL
COLLECTOR_DIES = ("qwen_compute",)
HIER_SCHEMA = "opentallas.kit_hierarchy.v1"
FACE_TOL_UM = 2.0       # == geom_rules.face_of default tolerance


def _rect(r, W, H):
    """[x0, y0, x1, y1] clipped to the outline; None when empty / malformed"""
    try:
        x0, y0, x1, y1 = (float(v) for v in r[:4])
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (x0, y0, x1, y1)):
        return None
    x0, x1 = max(0.0, min(x0, x1)), min(W, max(x0, x1))
    y0, y1 = max(0.0, min(y0, y1)), min(H, max(y0, y1))
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def pin_strips(pins, W, H):
    """landing strips: along every face carrying signal pins, PIN_STRIP_UM deep, as the union of per-pin +-PIN_STRIP_UM
    intervals (a gap between two pin clusters is NOT corridor; a single pin still gets a strip)"""
    byf = {"W": [], "E": [], "S": [], "N": []}
    for x, y in pins or []:
        f = ("W" if x < FACE_TOL_UM else "E" if x > W - FACE_TOL_UM else "S" if y < FACE_TOL_UM
             else "N" if y > H - FACE_TOL_UM else None)
        if f:
            byf[f].append(y if f in "WE" else x)
    d, out = PIN_STRIP_UM, []
    for f, v in byf.items():
        merged = []
        for lo, hi in sorted((p - d, p + d) for p in v):
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            r = {"W": [0, lo, d, hi], "E": [W - d, lo, W, hi], "S": [lo, 0, hi, d], "N": [lo, H - d, hi, H]}[f]
            r = _rect(r, W, H)
            if r:
                out.append(("pin_landing_strip",) + r)
    return out


def corridor_rects(t, pins=None, outline=None):
    """[(kind, x0, y0, x1, y1)] declared corridors of one plan partition type (type frame, clipped); pins = [(x, y)]"""
    W, H = (float(v) for v in (outline or t["outline_um"])[:2])
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

    def overlap(self, c):
        """exact area of rect c = (x0, y0, x1, y1) inside the union"""
        if not self.slabs or c[2] <= self.xs[0] or c[0] >= self.xs[-1]:
            return 0.0
        i = max(0, bisect.bisect_right(self.xs, c[0]) - 1)
        tot = 0.0
        while i < len(self.slabs) and self.xs[i] < c[2]:
            w = min(c[2], self.xs[i + 1]) - max(c[0], self.xs[i])
            if w > 0:
                los, his = self.slabs[i]
                h = 0.0
                k = max(0, bisect.bisect_right(los, c[1]) - 1)
                while k < len(los) and los[k] < c[3]:
                    h += max(0.0, min(c[3], his[k]) - max(c[1], los[k]))
                    k += 1
                tot += w * h
            i += 1
        return tot

    def contains(self, x, y):
        i = bisect.bisect_right(self.xs, x) - 1
        if i < 0 or i >= len(self.slabs):
            return False
        los, his = self.slabs[i]
        k = bisect.bisect_right(los, y) - 1
        return k >= 0 and y <= his[k]


def _span(v, total, trim=False):
    v = sorted(v)
    if trim:
        return (v[int(math.ceil(0.99 * (len(v) - 1)))] - v[int(0.01 * (len(v) - 1))]) / total
    return (v[-1] - v[0]) / total


def kit_content(path):
    """kit_hierarchy.json -> dict(expected, required, errors): the content instances the kit must contain.  A missing,
    unreadable or invalid file is an error entry (never raised) and makes the type ineligible."""
    try:
        d = json.loads(Path(path).read_text())
        if not isinstance(d, dict) or d.get("schema") != HIER_SCHEMA:
            raise ValueError("want schema %s" % HIER_SCHEMA)
        exp, req = d.get("expected"), d.get("required_expected")
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in (exp, req)):
            raise ValueError("expected / required_expected must be integers")
        errs = ["%d hierarchy problem(s)" % len(d["problems"])] if d.get("problems") else []
        return dict(expected=max(exp, len(d.get("hard_instances") or [])),
                    required=max(req, len(d.get("required_instances") or [])), errors=errs)
    except (OSError, ValueError, TypeError) as e:
        return dict(expected=None, required=None, errors=["kit_hierarchy: %s: %s" % (type(e).__name__, e)])


def eligibility(t, outline=None, pins=None, macros=None):
    """dict(eligible, collector, content_free, macro_free, pin_hull_bound, pin_hull_frac, frame_ok, reasons[]); pins = [(x, y)] in the
    measured type frame (None = not measurable -> pin_hull_bound False), macros = measured hard-macro count (None = not measured)"""
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    reasons = []
    ct = lc.get("collector_tree")
    collector = (t.get("_die") in COLLECTOR_DIES and isinstance(ct, dict) and bool(ct)
                 and bool(t.get("ft_slots")) and not t.get("contents"))
    if not collector:
        reasons.append("not a QC pure feed-through collector (needs _die in %s, collector_tree, ft_slots, empty contents)"
                       % (COLLECTOR_DIES,))
    kc = t.get("_kit_content")
    content_free = (isinstance(kc, dict) and not kc.get("errors") and kc.get("expected") == 0 and kc.get("required") == 0
                    and not isinstance(kc.get("expected"), bool) and not isinstance(kc.get("required"), bool))
    if not content_free:
        reasons.append("kit does not declare a content-free collector (kit_hierarchy.json expected 0, required_expected 0): %s" % (kc,))
    macro_free = not t.get("hard_cores") and not t.get("hard") and not t.get("macro_under_ft") and not macros
    if not macro_free:
        reasons.append("not macro-free (hard_cores / hard / macro_under_ft / measured macros)")
    W, H = (float(v) for v in (outline or t["outline_um"])[:2])
    po = t.get("outline_um")
    frame_ok = bool(po) and abs(float(po[0]) - W) <= OUTLINE_TOL and abs(float(po[1]) - H) <= OUTLINE_TOL
    if not frame_ok:
        reasons.append("plan record outline %s != measured %sx%s (wrong or stale record)" % (po, W, H))
    frac, hull, robust = None, False, None
    if pins and len(pins) >= PIN_HULL_MIN_PINS:
        xs, ys = [p[0] for p in pins], [p[1] for p in pins]
        sx, sy = _span(xs, W), _span(ys, H)
        frac = round(sx * sy, 4)
        robust = round(_span(xs, W, True) * _span(ys, H, True), 4)
        hull = sx >= PIN_HULL_SPAN and sy >= PIN_HULL_SPAN
    if not hull:
        reasons.append("not pin-hull-bound" if pins and len(pins) >= PIN_HULL_MIN_PINS else "pin hull not measurable")
    return dict(eligible=collector and content_free and macro_free and hull and frame_ok, collector=collector,
                content_free=content_free, macro_free=macro_free,
                pin_hull_bound=hull, pin_hull_frac=frac, pin_hull_frac_robust=robust, frame_ok=frame_ok, reasons=reasons)


def fill_corridor(t, cells, pins, outline=None, macros=0, raw_fill=None):
    """cells = [(x0, y0, x1, y1)] std cells in the measured type frame; pins = [(x, y)] signal pins in that frame.
    Returns the report dict (fill_corridor None unless eligible); never raises: a malformed record is reported."""
    prov = {k: t.get(k) for k in ("_die", "_type", "_plan_sha256", "_kit_content")} if isinstance(t, dict) else {}
    try:
        return _fill_corridor(t, cells, pins, outline, macros, raw_fill, prov)
    except Exception as e:
        return dict(schema=SCHEMA, raw_fill=raw_fill, fill_corridor=None, eligible=False, provenance=prov,
                    reasons=["error: %s: %s" % (type(e).__name__, e)])


def _fill_corridor(t, cells, pins, outline, macros, raw_fill, prov):
    el = eligibility(t, outline, pins, macros)
    res = dict(schema=SCHEMA, raw_fill=raw_fill, fill_corridor=None, provenance=prov, **el)
    if not el["eligible"]:
        return res
    rects = corridor_rects(t, pins, outline)
    slots = [s for s in t.get("ft_slots") or [] if isinstance(s, dict)]
    undeclared = sum(1 for s in slots if not any(s.get("bit_sites_um") or []))
    per, allr = {}, [r[1:] for r in rects]
    for r in rects:
        per.setdefault(r[0], []).append(r[1:])
    unions = {k: Union(v) for k, v in per.items()}
    u = Union(allr)
    tot = ins = 0.0
    ink = {k: 0.0 for k in unions}
    for c in cells:
        tot += (c[2] - c[0]) * (c[3] - c[1])
        ins += u.overlap(c)
        for k, uk in unions.items():
            ink[k] += uk.overlap(c)
    by_kind = {k: dict(rects=len(per[k]), area=round(unions[k].area, 3), cell_area=round(ink[k], 3),
                       fill=round(ink[k] / unions[k].area, 4) if unions[k].area > 0 else None) for k in unions}
    res.update(corridor_area=round(u.area, 3), corridor_rects={k: len(v) for k, v in per.items()}, by_kind=by_kind,
               cell_area_in=round(ins, 3), cell_area_total=round(tot, 3),
               share_in=round(ins / tot, 4) if tot > 0 else None,
               ft_slots_total=len(slots), ft_slots_undeclared=undeclared,
               fill_corridor=round(ins / u.area, 4) if u.area > 0 else None)
    return res


def with_kit_content(t, kit_hierarchy):
    """the record with `_kit_content` taken ONLY from the given kit_hierarchy.json (a value already in the record is dropped:
    the declaration belongs to the measured kit, not to the plan record); no file given -> no declaration -> ineligible"""
    t = dict(t)
    t.pop("_kit_content", None)
    if kit_hierarchy:
        t["_kit_content"] = kit_content(kit_hierarchy)
    return t


def load_type(plan_path=None, type_name=None, type_json=None, kit_hierarchy=None):
    """a plan partition type, from PLAN.json + name or from a file holding the record; the record carries its provenance
    (_die, _type, _plan_sha256 -- sha of the plan file when read from a plan) which fill_corridor echoes, and the kit's
    content declaration (_kit_content, from kit_hierarchy)"""
    if type_json:
        return with_kit_content(json.loads(Path(type_json).read_text()), kit_hierarchy)
    raw = Path(plan_path).read_bytes()
    plan = json.loads(raw)
    t = dict(plan["partition_types"][type_name])
    t.update(_die=(plan.get("die") or {}).get("name"), _type=type_name, _plan_sha256=hashlib.sha256(raw).hexdigest())
    return with_kit_content(t, kit_hierarchy)


def detail(res):
    if res.get("fill_corridor") is None:
        return "raw fill %s; fill_corridor n/a: %s" % (res.get("raw_fill"), "; ".join(res.get("reasons") or ["no corridor area"]))
    bk = " ".join("%s=%s(%s um2)" % (k, v["fill"], v["area"]) for k, v in sorted(res["by_kind"].items()))
    p = res.get("provenance") or {}
    return ("raw fill %s (gate unchanged); fill_corridor %s = %s um2 of cells in / %s um2 declared corridors; by kind %s; "
            "%s of all std-cell area lies in the corridors; ft slots without declared sites %s/%s; pin_hull_frac %s (robust %s); "
            "record %s %s sha %s; REPORT-ONLY"
            % (res["raw_fill"], res["fill_corridor"], res["cell_area_in"], res["corridor_area"], bk, res["share_in"],
               res["ft_slots_undeclared"], res["ft_slots_total"], res["pin_hull_frac"], res["pin_hull_frac_robust"], p.get("_die"), p.get("_type"),
               (p.get("_plan_sha256") or "none")[:12]))
