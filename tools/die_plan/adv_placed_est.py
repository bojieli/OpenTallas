#!/usr/bin/env python3
"""adv_placed_est.py -- C-TAP-REACH / C-LEG405 / P-FALSE-GREEN recall calibration (R3-RECALL 11-27), report-only.

Three PRE advisories (WARN, never a gate) that estimate what the placed AUTO-GEOM / CTS checks will read, from the plan alone.  Thresholds are
the placed checks' own: geom_rules.ASPECT_MAX / R2R_MAX, OT_TAP_SPAN (clock_taps.tcl, default 300 um).

TAP-SPAN-EST   OT_TAP_SPAN reads W+H of the as-built register sink box of every tap.  The old static models read seat-to-tap reach of the FIRM
               seats only (ADV TAP-REACH worst 292 um where CTS placed 916 on hd_spn_wshim_tx: the data flops that taps.assign hands to a tap
               are not plan seats).  Estimate: the bounding box (W+H) of the type's nearest-tap (Manhattan) Voronoi cell inside the outline,
               i.e. the region the tap's sinks may occupy in a sparse tile.  HEAD W12f, 9 CTS views, estimate max / placed max = 0.7 .. 1.7x
               (est > 300 um on 9 of 9 types that placed over 300; the seat-reach model flagged 1 of 9).  An upper-leaning estimator:
               it says WHICH types can exceed the span, not by how much.
ASPECT-EST     outline aspect max(W, H) / min(W, H) > geom_rules.ASPECT_MAX.  The placed metric is computed from the same outline, so this is
               exact (QC 77f2 9 of 9, HEAD W12f 10 of 10 placed aspect FAILs).
LEG405-EST     the cland origin -> reader START pin leg of a landing type with NO landing_reader_start and NO raw-branch origin, where the origin
               is the cland_tstart_in pin (the placed u_cland_origin sits on it): planned Manhattan + DRIFT_UM > 405.  hd_spn_wshim_rx planned
               365 um, placed u_cland_origin -> u_cland_reader_start_link_i_0 469 um (+104).  Only that type has the shape on HEAD W12f and QC 77f2.
"""
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "autopilot"))
import adv_fpconv as F0  # noqa: E402
import adv_geom_static as G  # noqa: E402

try:
    import geom_rules as GR
    ASPECT_MAX, R2R_MAX = GR.ASPECT_MAX, GR.R2R_MAX
except Exception:  # noqa: BLE001 - an older tree without geom_rules: the documented constants
    ASPECT_MAX, R2R_MAX = 2.0, 405.0
TAP_SPAN_UM = float(os.environ.get("OT_TAP_SPAN", "300"))
DRIFT_UM = 100.0          # placed - planned, hd_spn_wshim_rx origin -> reader START (469 vs 365)
MAX_EX = 3
MAX_CELLS = 40000


def tap_span_est(outline, taps):
    """-> {tap name: W+H of its nearest-tap Voronoi cell inside [0,W]x[0,H]} (Manhattan, sampled on a ~sqrt(area/MAX_CELLS) grid)"""
    W, H = float(outline[0]), float(outline[1])
    if not taps or W <= 0 or H <= 0:
        return {}
    step = max(1.0, math.sqrt(W * H / MAX_CELLS))
    nx, ny = max(1, int(W / step)), max(1, int(H / step))
    box = {}
    for j in range(ny):
        y = (j + 0.5) * H / ny
        for i in range(nx):
            x = (i + 0.5) * W / nx
            best, name = None, None
            for k, (n, tx, ty) in enumerate(taps):
                d = abs(x - tx) + abs(y - ty)
                if best is None or d < best:
                    best, name = d, (k, n)
            b = box.get(name)
            if b is None:
                box[name] = [x, x, y, y]
            else:
                b[0], b[1], b[2], b[3] = min(b[0], x), max(b[1], x), min(b[2], y), max(b[3], y)
    return {n[1]: round((b[1] - b[0]) + (b[3] - b[2]) + W / nx + H / ny, 1) for n, b in box.items()}


def _taps(raw, plan_path, tn, t):
    """local flop taps [(name, x, y)] of a type: the PRE tap solver (tap_reach.solve_tap_sites), else adv_tap_load.cheap_taps; None = unsolvable"""
    try:
        import tap_reach as TR
        s = TR.solve_tap_sites(raw, plan_path, [tn])[tn]
        sites, why = s[0], s[2]
        if isinstance(sites, dict):
            sites = [(n, x, y) for n, (x, y) in sites.items()]
        sites = [s_ for s_ in sites if not str(s_[0]).startswith("clk_c")]
        if not why and sites:
            return sites
    except Exception:  # noqa: BLE001
        pass
    try:
        import adv_tap_load as TL
        return TL.cheap_taps(raw, t)
    except Exception:  # noqa: BLE001
        return None


def _run_span(raw, plan_path, tree=None, taps_of=None, **_k):
    out, flagged, judged, unchecked = [], 0, 0, 0
    for tn, t in F0._types(raw):
        if t.get("hard") or not t.get("outline_um"):
            continue
        taps = (taps_of or (lambda n, tt: _taps(raw, plan_path, n, tt)))(tn, t)
        if not taps:
            if (t.get("clock") or {}).get("tap_mode"):
                unchecked += 1
            continue
        judged += 1
        sp = tap_span_est(t["outline_um"], taps)
        over = sorted(((v, n) for n, v in sp.items() if v > TAP_SPAN_UM), reverse=True)
        if over:
            flagged += 1
            out.append(F0._w("TAP-SPAN-EST", tn, f"{len(over)} of {len(sp)} tap(s) can own a sink box over {TAP_SPAN_UM:g} um (W+H of the Voronoi cell), worst {over[0][0]:g} um:",
                             "; ".join(f"{n} {v:g}" for v, n in over[:MAX_EX]) + (" ..." if len(over) > MAX_EX else "")
                             + " (estimate of OT_TAP_SPAN; fix: a tap per sink cluster, C-TAP-REACH)"))
    return out + [F0._w("TAP-SPAN-EST", f"summary {flagged} of {judged} types flagged, {unchecked} unchecked (report only)")]


def aspect_est(t):
    o = t.get("outline_um")
    if not o or min(o) <= 0:
        return None
    return round(max(o) / min(o), 3)


def _run_aspect(raw, plan_path, tree=None, **_k):
    out, n, judged = [], 0, 0
    for tn, t in F0._types(raw):
        a = aspect_est(t)
        if a is None:
            continue
        judged += 1
        if a > ASPECT_MAX:
            n += 1
            out.append(F0._w("ASPECT-EST", tn, f"outline {t['outline_um'][0]:g} x {t['outline_um'][1]:g} um aspect {a} > {ASPECT_MAX:g} (AUTO-GEOM aspect rule reads the same outline)"))
    return out + [F0._w("ASPECT-EST", f"summary {n} of {judged} types flagged (report only)")]


def origin_pin_legs(t):
    """[(pin, planned um)] origin (cland_tstart_in pin) -> cland_fstart_in_* pin, for a landing type the staged check cannot start (no reader
    START chain, no raw-branch origin).  Empty when LEG405-ZERO / STAGED already measure the origin."""
    ck = t.get("clock") or {}
    if not ck.get("landing_contract") or ck.get("landing_reader_start") is not None or F0.cland_origin_xy(t) is not None:
        return []
    pins = F0._pin_xy(t)
    o = pins.get("cland_tstart_in")
    if o is None:
        return []
    return sorted(((n, round(F0._md(o, xy), 1)) for n, xy in pins.items() if n.startswith("cland_fstart_in_")), key=lambda h: -h[1])


def _run_leg(raw, plan_path, tree=None, **_k):
    out, n = [], 0
    for tn, t in F0._types(raw):
        hits = [h for h in origin_pin_legs(t) if h[1] + DRIFT_UM > R2R_MAX]
        if hits:
            n += 1
            out.append(F0._w("LEG405-EST", tn, f"{len(hits)} cland origin -> START pin leg(s) planned + {DRIFT_UM:g} um placed drift over {R2R_MAX:g} um:",
                             "; ".join(f"{p} {d:g} um" for p, d in hits[:MAX_EX]) + " (origin = cland_tstart_in pin; no reader START chain to stage it)"))
    return out + [F0._w("LEG405-EST", f"summary {n} types flagged (report only)")]


F = {"TAP-SPAN-EST": _run_span, "ASPECT-EST": _run_aspect, "LEG405-EST": _run_leg}
findings_by_check = {k: G._safe(k, v) for k, v in F.items()}
