#!/usr/bin/env python3
"""CLAND-GEOM-1 (FAIL-QCKV-1 pass 4, 11-14): keep START-relay stages off the type outline edge, spread, never on corners.

Why: clock.landing_writer_start / landing_reader_start stage windows are sited by the route toward the cland_fstart_out_*
face pin, so the last stages of every branch land on the outline-minus-4.32-um line (CORE_MARGIN), the tails of a shared
trunk 0.4..1.7 um apart (KV hgi ft13_o..ft19_o), and the corner when two pins meet (QC sle_su_l1 x_sc_o).  Each stage
group needs a strip of rows (landing_placement.tcl cland_put_start grows x2..x32 about the centre, but the grow is cut
by the core boundary and by the neighbouring stations at the edge), so OT_CLAND says "no legal nonoverlapping row/site in
reserved band".  The window tolerance (KV-CLAND-EDGE2) cannot help: the area is not there.

Form: every stage xy within EDGE_TOL of the core boundary (4.32 um from the outline) is re-sited INSIDE it by one row
(INSET_Y 8.64 um from a top/bottom edge) / one column step (INSET_X 25.92 um from a left/right edge), and a cluster of such
stages is spread on a PITCH_X x PITCH_Y (25.92 x 8.64 um) lattice, nearest free lattice point first, in a fixed order.
Never a corner: both coordinates stay >= CORE_MARGIN + one inset from the outline when an edge stage is moved.  Stages
with an identical xy (a shared trunk stage, or stage k and k+1 of one branch sharing a window) move together.

Unchanged by construction: stage count (cycles, stations, RTL, LEC, lane latency rows), branch names, pins and the
landing_contract.  Only stage xy_um moves.  A stage is left alone (and reported) when no lattice point within MAX_MOVE_UM
is clear of the hard cores, the other stages and the macros, or when the move would stretch a branch hop above
max(its old hop, HOP_LIMIT_UM).

    cland_stage_inset.py PLAN OUT [--types REGEX] [--report REPORT.json]
"""
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

CORE_MARGIN = 4.32
EDGE_TOL = 0.05
INSET_X = 25.92
INSET_Y = 8.64
PITCH_X = 25.92
PITCH_Y = 8.64
MAX_MOVE_UM = 120.0
import os as _os_cbc, sys as _sys_cbc
_sys_cbc.path.insert(0, _os_cbc.path.dirname(_os_cbc.path.abspath(__file__)))
import cbc_rules as _CBC  # noqa: E402  OWNER 11-20 #6: generator hop default (300 um), one knob for every die
HOP_LIMIT_UM = _CBC.REACH_UM_PER_HOP - _CBC.SITE_MARGIN_UM
KEYS = ("landing_writer_start", "landing_reader_start")


def _hard_rects(t):
    out = []
    for h in (t.get("hard_cores") or []):
        r = h.get("rect_um") if isinstance(h, dict) else None
        if r and len(r) == 4:
            out.append(tuple(r))
    for h in (t.get("macros") or []) if isinstance(t.get("macros"), list) else []:
        r = h.get("rect_um") if isinstance(h, dict) else None
        if r and len(r) == 4:
            out.append(tuple(r))
    return out


def _core_rects(t):
    """Hard-core rects exactly as landing_place sees them (single source of truth when importable)."""
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    if os.environ.get('CLAND_TOOLS'):
        sys.path.insert(0, os.environ['CLAND_TOOLS'])
    try:
        import landing_place as LP
        return [tuple(r) for r in LP._hard_core_rects(t)]
    except Exception:  # noqa: BLE001 - standalone use / unit tests without the whole tool tree
        return _hard_rects(t)


def edge_sides(xy, w, h):
    """Set of outline sides ('W','E','S','N') whose core boundary the point sits on."""
    x, y = xy
    s = set()
    if abs(x - CORE_MARGIN) <= EDGE_TOL:
        s.add("W")
    if abs(x - (w - CORE_MARGIN)) <= EDGE_TOL:
        s.add("E")
    if abs(y - CORE_MARGIN) <= EDGE_TOL:
        s.add("S")
    if abs(y - (h - CORE_MARGIN)) <= EDGE_TOL:
        s.add("N")
    return s


def _inbox(p, rects, margin):
    x, y = p
    return any(a - margin <= x <= c + margin and b - margin <= y <= d + margin for a, b, c, d in rects)


def _conflict(p, q):
    return abs(p[0] - q[0]) < PITCH_X - 1e-6 and abs(p[1] - q[1]) < PITCH_Y - 1e-6


def respot(t, only_types=None):
    """Return (moves {old_xy_tuple: new_xy_tuple}, notes) for one partition type dict."""
    w, h = t["outline_um"]
    ck = t.get("clock") or {}
    branches = []
    for k in KEYS:
        for bus, br in sorted(((ck.get(k) or {}).get("branches") or {}).items()):
            branches.append((k, bus, br))
    pts = {}
    for k, bus, br in branches:
        for st in br.get("stages", []):
            pts.setdefault(tuple(round(v, 3) for v in st["xy_um"]), []).append((k, bus))
    edge = {p: edge_sides(p, w, h) for p in pts}
    edge = {p: s for p, s in edge.items() if s}
    if not edge:
        return {}, []
    cores = _core_rects(t)
    lo_x, hi_x = CORE_MARGIN + INSET_X, w - CORE_MARGIN - INSET_X
    lo_y, hi_y = CORE_MARGIN + INSET_Y, h - CORE_MARGIN - INSET_Y
    fixed = [p for p in pts if p not in edge]
    taken = list(fixed)
    moves, notes = {}, []
    # deterministic: along-edge position, then coordinates
    for p in sorted(edge, key=lambda q: (q[1] if edge[q] & {"W", "E"} else q[0], q)):
        sides = edge[p]
        bx = p[0] + (INSET_X if "W" in sides else -INSET_X if "E" in sides else 0.0)
        by = p[1] + (INSET_Y if "S" in sides else -INSET_Y if "N" in sides else 0.0)
        # a stage on a left/right edge is moved in x by INSET_X, on a top/bottom edge in y by INSET_Y; corners both
        best = None
        for i in range(0, 12):
            for j in range(0, 40):
                for si in ((1, -1) if i else (1,)):
                    for sj in ((1, -1) if j else (1,)):
                        c = (round(bx + si * i * PITCH_X, 3), round(by + sj * j * PITCH_Y, 3))
                        if not (lo_x - 1e-6 <= c[0] <= hi_x + 1e-6 and lo_y - 1e-6 <= c[1] <= hi_y + 1e-6):
                            # the edge axis may keep its own coordinate (mid-edge stage): only the inset axis is bound
                            pass
                        if "W" in sides or "E" in sides:
                            ok_x = lo_x - 1e-6 <= c[0] <= hi_x + 1e-6
                        else:
                            ok_x = CORE_MARGIN + 1e-6 <= c[0] <= w - CORE_MARGIN - 1e-6
                        if "S" in sides or "N" in sides:
                            ok_y = lo_y - 1e-6 <= c[1] <= hi_y + 1e-6
                        else:
                            ok_y = CORE_MARGIN + 1e-6 <= c[1] <= h - CORE_MARGIN - 1e-6
                        if not (ok_x and ok_y):
                            continue
                        d = math.hypot(c[0] - p[0], c[1] - p[1])
                        if d > MAX_MOVE_UM:
                            continue
                        if any(_conflict(c, q) for q in taken) or _inbox(c, cores, CORE_MARGIN):
                            continue
                        if best is None or d < best[0] - 1e-9:
                            best = (d, c)
        if best is None:
            notes.append(("kept", p, "no free lattice point"))
            taken.append(p)
            continue
        moves[p] = best[1]
        taken.append(best[1])
    # hop guard: a move may not stretch a branch hop above max(old hop, HOP_LIMIT_UM)
    changed = True
    while changed:
        changed = False
        for k, bus, br in branches:
            xs = [tuple(round(v, 3) for v in st["xy_um"]) for st in br["stages"]]
            for a, b in zip(xs, xs[1:]):
                na, nb = moves.get(a, a), moves.get(b, b)
                old = abs(a[0] - b[0]) + abs(a[1] - b[1])
                new = abs(na[0] - nb[0]) + abs(na[1] - nb[1])
                if new > max(old, HOP_LIMIT_UM) + 1e-6:
                    for q in (a, b):
                        if q in moves:
                            notes.append(("kept", q, "hop %.1f > %.1f on %s.%s" % (new, max(old, HOP_LIMIT_UM), k, bus)))
                            del moves[q]
                            changed = True
                    break
            if changed:
                break
    return moves, notes


def apply(plan, types_re=None):
    rep = {}
    for tn, t in sorted(plan["partition_types"].items()):
        if types_re is not None and not types_re.search(tn):
            continue
        if not t.get("outline_um"):
            continue
        moves, notes = respot(t)
        if not moves and not notes:
            continue
        n = 0
        for k in KEYS:
            for bus, br in ((t.get("clock") or {}).get(k) or {}).get("branches", {}).items():
                for st in br.get("stages", []):
                    p = tuple(round(v, 3) for v in st["xy_um"])
                    if p in moves:
                        st["xy_um"] = [moves[p][0], moves[p][1]]
                        n += 1
        rep[tn] = dict(moved_points=len(moves), moved_stages=n, kept=[[list(a), b, c] for a, b, c in notes],
                       moves=[[list(a), list(b)] for a, b in sorted(moves.items())])
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--types", default=None, help="regex over partition type names (default: every type)")
    ap.add_argument("--report", default=None)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    rep = apply(plan, re.compile(a.types) if a.types else None)
    Path(a.out).write_text(json.dumps(plan, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep.items():
        print("%s: moved %d points (%d stages), kept %d" % (tn, r["moved_points"], r["moved_stages"], len(r["kept"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
