"""ADV-GCELL-SLIVER (FP-CONVERGE-HEAD 11-25; an estimator, report only, never a gate; proposal to PRECHECK).

Class: GRT obstruction / gcell capacity (hd_host_w GRT-0116 139 on W6p; hd_host_e net21446 M6; hd_serdes sdr2c M4).  A reserved die-clock-site
obstruction (M1-M7) ends inside a GRT gcell row / column; the part of the gcell it leaves free holds fewer than OT_OBS_GCELL_MIN_TRACKS (3)
DRT-legal tracks, GRT still counts them, routes a net there and DRT cannot (obs_gcell_cap.tcl owns the run-time cure: capacity 0 on the
sliver, with the tap-pin exemption of 0d7deda5143).  Reference case (obs_gcell_cap.tcl header): rect (337.338, 345.06)-(339.498, 346.41), gcell 0.57 um
-> the row y 345.99-346.56 keeps 150 nm of 570 nm.

Static form (plan only, no placement): each clock tap of a type (clock.taps[].xy, else clock.tap_um) is a reserved site of RECT_UM (2.16 x 1.35 um,
centred on the tap) in the type frame; gcell origin (0, 0), tile GC_UM (0.57).  Per rect edge the residual free strip of the gcell it ends in is
 (0 = the edge sits on a boundary); the edge is a SLIVER when
0 < residual < SLIVER_UM (0.20 um: three tracks at the M6/M7 0.064 pitch plus clearance) (a tap pin inside its
rect is exempt on every layer by 0d7deda5143, the plan cannot see block pins, so this is the exposure BEFORE that cure).  Calibrated only on the case above
(top edge residual 0.15 um -> sliver): treat the count as a risk estimate, not a prediction of the GRT number.
Fix: shift the tap by a multiple of the 0.07 um clock-site pitch so both rect edges leave residual 0 or >= 0.20 um (sliver_fix below), or keep the
tap-pin exemption (0d7deda5143) in the kit tool list.
findings(raw, plan_path, tree=None, **kw) -> WARN lines.
"""
import math
import sys
from pathlib import Path

CHECK = "ADV-GCELL-SLIVER"
GC_UM = 0.57
RECT_UM = (2.16, 1.35)
SLIVER_UM = 0.20
EPS = 1e-6
MAX_EX = 4


def residuals(lo, hi, gc=GC_UM):
    """-> (below, above): free strip of the gcell the low edge / the high edge ends in, on the side away from the rect"""
    a = lo - math.floor(lo / gc + EPS) * gc
    b = math.ceil(hi / gc - EPS) * gc - hi
    return (0.0 if a < EPS or gc - a < EPS else a), (0.0 if b < EPS or gc - b < EPS else b)


def slivers(xy, rect=RECT_UM):
    """-> [(side, residual_um)] for the sliver edges of the rect centred on xy"""
    out = []
    for ax, c, d in (("x", xy[0], rect[0]), ("y", xy[1], rect[1])):
        lo, hi = residuals(c - d / 2, c + d / 2)
        for side, r in ((ax + "-", lo), (ax + "+", hi)):
            if EPS < r < SLIVER_UM:
                out.append((side, round(r, 3)))
    return out


def tap_points(t):
    ck = t.get("clock") or {}
    pts = []
    for tp in ck.get("taps") or []:
        xy = tp.get("xy") if isinstance(tp, dict) else None
        if xy and len(xy) == 2:
            pts.append((tp.get("name") or "tap", float(xy[0]), float(xy[1])))
    if not pts and ck.get("tap_um"):
        pts.append(("tap_um", float(ck["tap_um"][0]), float(ck["tap_um"][1])))
    return pts


def sliver_fix(xy, pitch=0.07, rng=8):
    """smallest shift (dx, dy) in multiples of pitch (|k| <= rng) that leaves no sliver edge; None when none"""
    best = None
    for kx in range(-rng, rng + 1):
        for ky in range(-rng, rng + 1):
            if not slivers((xy[0] + kx * pitch, xy[1] + ky * pitch)):
                c = abs(kx) + abs(ky)
                if best is None or c < best[0]:
                    best = (c, round(kx * pitch, 3), round(ky * pitch, 3))
    return None if best is None else best[1:]


def findings(raw, plan_path=None, tree=None, **_kw):
    """one summary WARN (a random site is a sliver ~70 % of the time: per-type lines would be noise) + the worst types by tap count"""
    rows = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict):
            continue
        pts = tap_points(t)
        bad = [(nm, x, y) for nm, x, y in pts if slivers((x, y))]
        if bad:
            rows.append((tn, len(bad), len(pts), bad[0]))
    if not rows:
        return []
    tot = sum(r[2] for r in rows)
    n = sum(r[1] for r in rows)
    rows.sort(key=lambda r: -r[1])
    top = "; ".join(f"{tn} {b}/{p}" for tn, b, p, _ in rows[:MAX_EX + 2])
    return [f"WARN {CHECK} summary: {n} of {tot} tap site rects ({len(rows)} types) leave a gcell sliver strip < {SLIVER_UM:g} um; worst {top}; "
            f"exposure BEFORE the run-time cure (obs_gcell_cap.tcl + tap-pin exemption 0d7deda5143, kit tool list); fix for a type that still fails GRT: sliver_fix() shift"]


if __name__ == "__main__":
    import json
    for line in findings(json.loads(Path(sys.argv[1]).read_text()), sys.argv[1]):
        print(line)
