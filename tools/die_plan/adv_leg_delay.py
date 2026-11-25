#!/usr/bin/env python3
"""adv_leg_delay.py -- PRECHECK ADV-LEG-DELAY (FP-CONVERGE-KV 11-25; VIS-CAUSES C4 / C6).

HOP-GAP and G0-HOPS judge station chains and RTL-traced hops; both were silent on KV although two classes missed setup by 757-870 ps in
the placed kit: C4 kv3_pc face register (i_phy_Q__*) -> kvpc core pin across the spine (-757..-824 ps), C6 kv3_hgi core-to-core legs
(-870 ps).  This rule needs only the plan and core_conns.json: every bus -> hard-core-port connection without an internal_stations chain
is one cycle from the bus face window (the face register sits there) to the core box, and every core -> core connection without a
station is one cycle between the two boxes.  Length = Manhattan gap, estimated setup slack
    slack = CLOCK_PS - OVERHEAD_PS - WIRE_PS_PER_UM * length
(CLOCK_PS 833, OVERHEAD_PS 130 = 60 uncertainty + clk->q + setup, WIRE_PS_PER_UM 1.2 calibrated on C4: 1,218 um -> -773 ps).
A leg is reported when its estimated slack is worse than SLACK_FLOOR_PS (-400: the misses a kit cannot repair, VIS-CAUSES 500-900 ps; the -150 visual-gate floor flagged 60 of 67 types), i.e. longer than ~920 um;
the summary also counts legs over the 405 um reach.  Fix: pull the block adjacent, re-seat the face window, or add stations
(1-2 cycles, RTL stage + LEC).  Report only (plan_advisory forces WARN); OT_FP_BLOCK=1 -> FAIL lines.
findings(raw, plan_path, tree=None, **kw) -> lines, never raises.
"""
import json
import os
from pathlib import Path

CHECK = "LEG-DELAY"
CLOCK_PS = 833.0
OVERHEAD_PS = 130.0
WIRE_PS_PER_UM = 1.2
SLACK_FLOOR_PS = -400.0
REACH_UM = 405.0
MAX_LINES = 20


def est_slack(length_um):
    return CLOCK_PS - OVERHEAD_PS - WIRE_PS_PER_UM * length_um


def _gap(box, pt):
    x0, y0, x1, y1 = box
    return max(x0 - pt[0], 0.0, pt[0] - x1) + max(y0 - pt[1], 0.0, pt[1] - y1)


def _box_gap(a, b):
    dx = max(a[0] - b[2], 0.0, b[0] - a[2])
    dy = max(a[1] - b[3], 0.0, b[1] - a[3])
    return dx + dy


def legs(t, bus_pts, conns):
    """[(length um, kind, src, dst)] of the station-free legs of type dict t.
    bus_pts {bus: (x, y)} face-window centres; conns {core inst: {port: ["bus:<n>" | "core:<inst>[.port]", ...]}}."""
    boxes = {}
    for h in t.get("hard_cores", []) or []:
        if h.get("origin_um") and h.get("outline_um"):
            x, y = h["origin_um"]
            w, hh = h["outline_um"]
            boxes[h["inst"]] = (x, y, x + w, y + hh)
    staged_bus, staged_core, staged_pair = set(), set(), set()
    for e in t.get("internal_stations", []) or []:
        if not e.get("regs_um"):
            continue
        c = str(e.get("conn", ""))
        if c.startswith("bus:"):
            staged_bus.add(c[4:])
        ends = []
        for end in [x for x in c.split("|")] + [str(e.get("launch", "")), str(e.get("capture", ""))]:
            if end.startswith("core:"):
                n = end[5:].split(".")[0]
                ends.append(n[2:] if n.startswith("u_") else n)
        if len(ends) >= 2 and ends[0] != ends[1]:
            staged_pair.add(frozenset(ends[:2]))      # a station chain between these two cores
        staged_core.update(ends[:0])
    out, seen = [], set()
    for ci, ports in (conns or {}).items():
        a = boxes.get(ci)
        if not a:
            continue
        for lp, lst in ports.items():
            for v in lst:
                k, _, nm = v.partition(":")
                if k == "bus" and nm in bus_pts and nm not in staged_bus:
                    key = ("bus", nm, ci)
                    if key not in seen:
                        seen.add(key)
                        out.append((_gap(a, bus_pts[nm]), "face", nm, ci))
                elif k == "core":
                    other = nm.split(".")[0]
                    b = boxes.get(other)
                    if b and other != ci and frozenset((ci, other)) not in staged_pair:
                        key = ("core",) + tuple(sorted((ci, other)))
                        if key not in seen:
                            seen.add(key)
                            out.append((_box_gap(a, b), "core", ci, other))
    return sorted(out, reverse=True)


def type_line(name, lv, lvl="WARN"):
    over = [x for x in lv if x[0] > REACH_UM]
    bad = [x for x in lv if est_slack(x[0]) < SLACK_FLOOR_PS]
    if not bad:
        return None
    w = bad[0]
    top = "; ".join(f"{k} {a}->{b} {L:.0f} um" for L, k, a, b in bad[:3])
    return (f"{lvl} ADV-LEG-DELAY {name}: {len(bad)} leg(s) with estimated setup slack < {SLACK_FLOOR_PS:.0f} ps ({len(over)} over {REACH_UM:.0f} um "
            f"of {len(lv)} station-free legs); worst {w[1]} {w[2]}->{w[3]} {w[0]:.0f} um = {est_slack(w[0]):.0f} ps; {top}; "
            "fix: move the block adjacent / re-seat the face window / add 1-2 stations (RTL stage + LEC)")


def _conns_for(plan_path, tn, cache={}):
    """core_conns of type tn from the first core_conns.json beside the plan (plan dir, its parent, grandparent) that names the type
    (or its base type before the first '__'); None when no core_conns.json exists at all, {} when none names the type."""
    p = Path(plan_path or ".").resolve()
    found = False
    for d in (p.parent, p.parent.parent, p.parent.parent.parent):
        f = d / "core_conns.json"
        if f.is_file():
            found = True
            if str(f) not in cache:
                cache[str(f)] = json.loads(f.read_text())
            c = cache[str(f)]
            hit = c.get(tn) or c.get(tn.split("__")[0])
            if hit:
                return hit
    return {} if found else None


def findings(raw, plan_path=None, tree=None, **kw):
    lvl = "FAIL" if os.environ.get("OT_FP_BLOCK") == "1" else "WARN"
    try:
        import check as C
        import schema as S
        P = S.Plan(raw, plan_path)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [f"WARN ADV-LEG-DELAY not checked: {type(e).__name__}: {str(e)[:160]}"]
    out, nbad, nchk = [], 0, 0
    for tn, t in sorted(P.types.items()):
        try:
            if not t.get("hard_cores"):
                continue
            conns = _conns_for(plan_path, tn)
            if conns is None:
                out.append(f"WARN ADV-LEG-DELAY {tn}: not checked (no core_conns.json beside the plan)")
                break
            if not conns:
                continue
            bt = C._bus_targets(P, tn)
            lv = legs(t, {k: v[1] for k, v in bt.items()}, conns)
            nchk += 1
            ln = type_line(tn, lv, lvl)
            if ln:
                nbad += 1
                out.append(ln)
        except Exception as e:  # noqa: BLE001
            out.append(f"WARN ADV-LEG-DELAY {tn}: not checked ({type(e).__name__}: {str(e)[:80]})")
    out.append(f"WARN ADV-LEG-DELAY summary {nbad} of {nchk} types with a station-free leg whose estimated slack is worse than "
               f"{SLACK_FLOOR_PS:.0f} ps (wire {WIRE_PS_PER_UM} ps/um calibrated on C4)")
    return out[:MAX_LINES] + out[MAX_LINES:][-1:]
