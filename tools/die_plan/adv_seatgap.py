#!/usr/bin/env python3
"""adv_seatgap.py -- FP-CONVERGE-S81 11-25 (COORD, from the S81-KVLEAF-T2 Fable review of the kv leaf t2 GRT congestion, 16.8M overflow):
two report-only plan checks (WARN ADV-<NAME>, one line per type, never a gate; geometry over the plan only).

SEAT-ORIENT  an internal_stations chain leaves its launch core (or reaches its capture core) through the face OPPOSITE the face its
             pin sits on: the launch pin (from_um) / capture pin (to_um) lies on a face F of the core rect (within PIN_FACE_UM of the
             edge) and the first hop (pin -> regs_um[0], or pin -> to_um when no register) / last hop (regs_um[-1] -> pin) runs on the
             inside of F by more than AGAINST_UM (the wire would have to cross the core).  Reported per type: hops against / hops
             with a core-face pin, and the share.  Kit evidence: kv leaf t2 ~81% of input-relay hops and 54 of 73 exit-relay hops
             against the relay pin faces (relays then block M1-M5 inline inside the bus lanes).
MACRO-GAP    two hard cores facing across 0 < gap < GAP_UM (9 um) over >= MIN_FACE_UM that BLOCK a bus lane: an internal_stations hop
             (Manhattan L, horizontal first) runs inside the gap strip along it (>= MIN_RUN_UM of wire in the strip), so the lane has
             the gap's width, or a station register sits in the strip.  Kit evidence: 202 macro pairs < 9 um apart on kv leaf t2.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import adv_fpconv as F0  # noqa: E402

PIN_FACE_UM = 2.0
AGAINST_UM = 5.0
GAP_UM = 9.0
MIN_FACE_UM = 10.0
MIN_RUN_UM = 5.0
MAX_EX = 3


def _xy(v):
    try:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return float(v[0]), float(v[1])
    except (TypeError, ValueError):
        pass
    return None


def _core_of(name, rects):
    """the hard rect whose instance path is the longest prefix of a 'core:<inst>[.<pin>]' / '<inst>' string"""
    s = str(name or "").split("core:")[-1]
    best = None
    for r in rects:
        n = r[4]
        if s == n or s.startswith(n + "."):
            if best is None or len(n) > len(best[4]):
                best = r
    return best


def _face(p, r):
    """-> unit outward normal (nx, ny) of the face of rect r that point p sits on (within PIN_FACE_UM), else None"""
    x, y = p
    if r[1] - PIN_FACE_UM <= y <= r[3] + PIN_FACE_UM:
        if abs(x - r[0]) <= PIN_FACE_UM:
            return (-1, 0)
        if abs(x - r[2]) <= PIN_FACE_UM:
            return (1, 0)
    if r[0] - PIN_FACE_UM <= x <= r[2] + PIN_FACE_UM:
        if abs(y - r[1]) <= PIN_FACE_UM:
            return (0, -1)
        if abs(y - r[3]) <= PIN_FACE_UM:
            return (0, 1)
    return None


def seat_orient(t):
    """-> (against, total, [(conn, end, bits)]) over launch / capture ends whose pin sits on a core face"""
    rects = G.hard_rects(t)
    against, total, ex = 0, 0, []
    for i, s in enumerate(t.get("internal_stations") or []):
        if not isinstance(s, dict):
            continue
        fr, to = _xy(s.get("from_um")), _xy(s.get("to_um"))
        regs = [p for p in (_xy(r) for r in s.get("regs_um") or []) if p]
        for end, core_name, pin, nxt in (("launch", s.get("launch"), fr, (regs[0] if regs else to)),
                                         ("capture", s.get("capture"), to, (regs[-1] if regs else fr))):
            if pin is None or nxt is None or not core_name:
                continue
            r = _core_of(core_name, rects)
            if r is None:
                continue
            n = _face(pin, r)
            if n is None:
                continue
            total += 1
            if (nxt[0] - pin[0]) * n[0] + (nxt[1] - pin[1]) * n[1] < -AGAINST_UM:
                against += 1
                ex.append((s.get("conn", f"#{i}"), end, s.get("bits")))
    return against, total, ex


def _facing_gaps(t):
    rs = G.hard_rects(t)
    out = []
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            for lo, hi in ((a, b), (b, a)):
                gx = hi[0] - lo[2]
                oy = min(lo[3], hi[3]) - max(lo[1], hi[1])
                if 0 < gx < GAP_UM and oy >= MIN_FACE_UM:
                    out.append((gx, lo[4], hi[4], (lo[2], max(lo[1], hi[1]), hi[0], min(lo[3], hi[3]))))
                gy = hi[1] - lo[3]
                ox = min(lo[2], hi[2]) - max(lo[0], hi[0])
                if 0 < gy < GAP_UM and ox >= MIN_FACE_UM:
                    out.append((gy, lo[4], hi[4], (max(lo[0], hi[0]), lo[3], min(lo[2], hi[2]), hi[1])))
    return out


def _legs(t):
    for s in t.get("internal_stations") or []:
        if not isinstance(s, dict):
            continue
        pts = [p for p in [_xy(s.get("from_um"))] + [_xy(r) for r in s.get("regs_um") or []] + [_xy(s.get("to_um"))] if p]
        yield s, pts


def macro_gap(t):
    """-> (pairs_lt_gap, [(gap, nameA, nameB, run_um, bits)]) gaps < GAP_UM that carry a bus lane"""
    gaps = _facing_gaps(t)
    if not gaps:
        return 0, []
    blocked = []
    for g, a, b, strip in gaps:
        run, bits = 0.0, 0
        for s, pts in _legs(t):
            r = 0.0
            for p, q in zip(pts, pts[1:]):
                mid = (q[0], p[1])
                r += F0._seg_inside_len(p, mid, strip) + F0._seg_inside_len(mid, q, strip)
            for p in pts[1:-1]:
                if strip[0] <= p[0] <= strip[2] and strip[1] <= p[1] <= strip[3]:
                    r += MIN_RUN_UM
            if r >= MIN_RUN_UM:
                run += r
                bits += int(s.get("bits") or 0)
        if bits:
            blocked.append((round(g, 2), a, b, round(run, 1), bits))
    return len(gaps), sorted(blocked, key=lambda h: -h[4])


def _run_orient(raw, plan_path, tree=None, **_k):
    out, n, ta, tt = [], 0, 0, 0
    for tn, t in F0._types(raw):
        a, tot, ex = seat_orient(t)
        ta, tt = ta + a, tt + tot
        if a:
            n += 1
            out.append(F0._w("SEAT-ORIENT", tn, f"{a} of {tot} core-face hops run against the pin face ({100.0 * a / tot:.0f}%):",
                             "; ".join(f"{c} {e}" for c, e, _b in ex[:MAX_EX]) + (" ..." if len(ex) > MAX_EX else "")))
    return out + [F0._w("SEAT-ORIENT", f"summary {n} types flagged, {ta} of {tt} core-face hops against (report only)")]


def _run_gap(raw, plan_path, tree=None, **_k):
    out, n = [], 0
    for tn, t in F0._types(raw):
        npairs, blk = macro_gap(t)
        if blk:
            n += 1
            out.append(F0._w("MACRO-GAP", tn, f"{len(blk)} of {npairs} sub-{GAP_UM:g} um macro gap(s) carry a bus lane:",
                             "; ".join(f"{a}|{b} {g} um {bits} bits" for g, a, b, _r, bits in blk[:MAX_EX]) + (" ..." if len(blk) > MAX_EX else "")))
    return out + [F0._w("MACRO-GAP", f"summary {n} types flagged (report only)")]


F = {"SEAT-ORIENT": _run_orient, "MACRO-GAP": _run_gap}
findings_by_check = {k: G._safe(k, v) for k, v in F.items()}
