#!/usr/bin/env python3
"""adv_rcs81.py -- FP-CONVERGE-S81 11-25 (COORD, from FABLE-RC-S81 07:06 post): three report-only plan checks, each tied to a measured c8s failure.
All WARN ADV-<NAME> lines, one per type, never a gate; geometry over the plan only (seconds per die).

STATUS-UP-REACH     landing type whose collector root (landing_contract.collector_tree.root) is > 405 um (Manhattan) from a cland_up_ready /
                    cland_up_fault pin and has no landing_contract.collector_egress_um chain (STATUS-UP stations + face register): the status
                    leg is one cycle (S81 leaf t36 c8s post-CTS u_cland_collect_rst_n_t63 -> cland_up_ready, 20 x BUFx6f, -547.7 ps).
CORE-LEG-OVERMACRO  an internal_stations leg (from_um -> regs_um[0], and reg -> reg -> to_um, Manhattan L: horizontal first) whose wire runs over a
                    hard core by > OVER_UM in total, summed over cores that are not the launch / capture core: the span is unbuffered (no repeater can
                    sit on a core) and is priced against the cycle (S81 col_h10_r0_p1 -219, col_h9_r0_p4 -150, col_h10_r0_p4 -196 ps).
RELAY-COHORT-SPAN   reset relays (landing_contract.collector_tree.relays) grouped by clock tap: the bbox Manhattan span of a cohort of >= COHORT_MIN
                    relays above SPAN_UM (a proxy of the cts.tcl sink-clustering diameter table; thresholds are module constants) (S81 serdes
                    t13 / t4 CTS abort: span 379.8 um).  Types without collector_tree.relays have no cohort data and are not flagged."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_geom_static as G  # noqa: E402
import adv_fpconv as F0  # noqa: E402

REACH_UM = 405.0
OVER_UM = 100.0
SPAN_UM = 300.0
COHORT_MIN = 16
MAX_EX = 3


def _xy(v):
    try:
        if isinstance(v, (list, tuple)) and len(v) == 2:
            return float(v[0]), float(v[1])
    except (TypeError, ValueError):
        pass
    return None


def status_up_reach(t):
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    if not lc or lc.get("collector_egress_um") is not None:
        return []
    root = _xy((lc.get("collector_tree") or {}).get("root"))
    if root is None:
        return []
    out = []
    for p in lc.get("pins") or []:
        nm, xy = p.get("name", ""), _xy(p.get("xy_um"))
        if xy is None or not (nm.startswith("cland_up_ready") or nm.startswith("cland_up_fault")):
            continue
        d = round(abs(xy[0] - root[0]) + abs(xy[1] - root[1]), 1)
        if d > REACH_UM:
            out.append((nm, d))
    return sorted(out, key=lambda h: -h[1])


def _over_len(a, b, rect):
    """length of the Manhattan L a->b (horizontal first) inside the open rect"""
    mid = (b[0], a[1])
    return F0._seg_inside_len(a, mid, rect) + F0._seg_inside_len(mid, b, rect)


def core_leg_overmacro(t):
    rects = G.hard_rects(t)
    out = []
    for i, s in enumerate(t.get("internal_stations") or []):
        if not isinstance(s, dict):
            continue
        pts = [p for p in [_xy(s.get("from_um"))] + [_xy(r) for r in s.get("regs_um") or []] + [_xy(s.get("to_um"))] if p]
        own = {n for n in (str(s.get("launch", "")).split("core:")[-1], str(s.get("capture", "")))}
        tot, worst = 0.0, None
        for a, b in zip(pts, pts[1:]):
            for r in rects:
                if any(r[4] == o or (o and r[4].startswith(o + ".")) or (o and o.startswith(r[4] + ".")) for o in own):
                    continue
                L = _over_len(a, b, r)
                if L > 0:
                    tot += L
                    if worst is None or L > worst[0]:
                        worst = (L, r[4])
        if tot >= OVER_UM:
            out.append((s.get("conn", f"#{i}"), round(tot), worst[1]))
    return sorted(out, key=lambda h: -h[1])


def relay_cohort_span(t):
    rl = (((t.get("clock") or {}).get("landing_contract") or {}).get("collector_tree") or {}).get("relays") or []
    by = {}
    for r in rl:
        xy = _xy(r.get("xy")) if isinstance(r, dict) else None
        if xy:
            by.setdefault(r.get("tap"), set()).add(xy)
    out = []
    for tap, pts in by.items():
        if len(pts) < 1:
            continue
        n = sum(1 for r in rl if r.get("tap") == tap)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        span = round((max(xs) - min(xs)) + (max(ys) - min(ys)), 1)
        if n >= COHORT_MIN and span > SPAN_UM:
            out.append((tap, n, span))
    return sorted(out, key=lambda h: -h[2])


def _f_status(raw, plan_path, tree=None, **_k):
    return F0._run("STATUS-UP-REACH", lambda t, tn, r: status_up_reach(t), lambda h: f"collector root -> {h[0]} {h[1]} um, no egress chain", raw)


def _f_over(raw, plan_path, tree=None, **_k):
    return F0._run("CORE-LEG-OVERMACRO", lambda t, tn, r: core_leg_overmacro(t),
                   lambda h: f"{h[0]} {h[1]} um over cores (worst {h[2]})", raw)


def _f_cohort(raw, plan_path, tree=None, **_k):
    return F0._run("RELAY-COHORT-SPAN", lambda t, tn, r: relay_cohort_span(t), lambda h: f"tap {h[0]} {h[1]} relays span {h[2]} um", raw)


F = {"STATUS-UP-REACH": _f_status, "CORE-LEG-OVERMACRO": _f_over, "RELAY-COHORT-SPAN": _f_cohort}
findings_by_check = {k: G._safe(k, v) for k, v in F.items()}
