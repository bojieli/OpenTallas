#!/usr/bin/env python3
"""adv_channel_pile.py -- report-only advisory ADV-CHANNEL-PILE (FP-CONVERGE-QC C5, from VIS-CAUSES cbn_q00 / cbn_q11).

Why: cbn_q00 (cl622f65d2, GRT overflow 3160) and cbn_q11 (cl5cc92dfe, overflow 1449) placed a tap/flop pile in the
central channel with no CB tap grid; the plan carried 5 glue taps for ~10k relay sinks and 3.6k-5.7k bus wires through
strips only 60-100 um wide.  Per channel between the two hard-core columns of a CB quad type (W strip, central channel,
E strip; the 60 um row street is not rated) this checks
  WIDTH   vertical through-wires / (width x tracks/um of M3/M5/M7 x SUPPLY_FRAC) >= WARN_UTIL: the channel is too narrow
          for the buses planned through it (same supply model as ADV-ROUTE-DEMAND).  Through-wires = the largest sum, over
          any horizontal cut, of the widths of the distinct buses (one station chain / ft slot = one bus) that have a
          vertical leg inside the channel spanning that cut.  (11-25 fix: the first version summed every leg, so a bus with
          4 stations counted 4x and WIDTH was overstated 3-5x on the C1o v13 cb types.)
  TAPGRID (central channel only: the strips are fed by the core taps) relay sinks inside the channel need >= ceil(sinks / TAP_SINKS) non-core clock taps inside it, and no gap along
          the channel longer than MAX_GAP_UM between taps (a missing grid piles the tap/flop clusters at the few taps there are).
          Sinks are the plan relay_sites only: the plan carries no netlist flop count (the kit counts behind ADV-TAP-LOAD are
          2.6-8.6x higher on the C1o v13 cb types), so TAPGRID is a lower bound, NOT sized on the netlist flops.
Plan only; never a gate.

    findings(raw, plan_path=None, tree=None, types=None, **kw) -> ["WARN ADV-CHANNEL-PILE ..."]
    channels(t) -> [(label, x0, x1)]   stats(t, x0, x1) -> dict
"""
import math
import re

import adv_route_demand as R

CHECK = "CHANNEL-PILE"
DEFAULT_TYPES = r"^cb"
WARN_UTIL = 0.6
TRACKS_PER_UM = R._sup(0)[1] * R.SUPPLY_FRAC     # V tracks/um (M3, M5, M7) x 0.5
TAP_SINKS = 900.0                                # plan clock.tap_target_sinks
MAX_GAP_UM = 400.0                               # 2 x plan clock.tap_radius_um (200)
BIG_UM2 = 1e5                                    # a quad core, not a landing band
MAX_LINES = 60


def _big(t):
    return [h for h in t.get("hard_cores") or [] if h["outline_um"][0] * h["outline_um"][1] > BIG_UM2]


def channels(t):
    """W strip, central channel, E strip as (label, x0, x1) when the type has two core columns."""
    big = _big(t)
    if len(big) < 4 or not t.get("outline_um"):
        return []
    W = float(t["outline_um"][0])
    xs = [h["origin_um"][0] for h in big]
    mid = (min(xs) + max(xs)) / 2          # two core columns: split at the middle of their origins (strips may be wide)
    left = [h for h in big if h["origin_um"][0] < mid]
    right = [h for h in big if h["origin_um"][0] >= mid]
    if not left or not right:
        return []
    lo = min(h["origin_um"][0] for h in left)
    lr = max(h["origin_um"][0] + h["outline_um"][0] for h in left)
    rl = min(h["origin_um"][0] for h in right)
    rr = max(h["origin_um"][0] + h["outline_um"][0] for h in right)
    return [("W strip", 0.0, lo), ("central", lr, rl), ("E strip", rr, W)]


def buses(t):
    """[(bits, [points])] one entry per planned bus: internal station chain (from -> regs -> to) or ft slot (regs)."""
    out = []
    for s in t.get("internal_stations") or []:
        try:
            out.append((int(s.get("bits") or 0), [s["from_um"]] + list(s.get("regs_um") or []) + [s["to_um"]]))
        except (KeyError, TypeError):
            continue
    for f in t.get("ft_slots") or []:
        out.append((int(f.get("width") or 0), list(f.get("regs_um") or [])))
    return out


def through_wires(t, x0, x1):
    """max over horizontal cuts of the summed widths of distinct buses with a vertical leg in [x0, x1] spanning the cut."""
    ev = []
    for n, pts in buses(t):
        iv = sorted((min(a[1], b[1]), max(a[1], b[1])) for a, b in zip(pts, pts[1:])
                    if x0 - 1 <= a[0] <= x1 + 1 and x0 - 1 <= b[0] <= x1 + 1 and abs(b[1] - a[1]) > abs(b[0] - a[0]))
        merged = []
        for lo, hi in iv:                          # a bus counts once where its own legs overlap or touch
            if merged and lo <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        for lo, hi in merged:
            ev += [(lo, 1, n), (hi, 0, -n)]
    cur = best = 0
    for _y, _o, d in sorted(ev):                   # at equal y a closing interval goes before an opening one
        cur += d
        best = max(best, cur)
    return best


def stats(t, x0, x1):
    wires = through_wires(t, x0, x1)
    width = x1 - x0
    util = wires / max(width * TRACKS_PER_UM, 1e-9) if width > 0 else (9.9 if wires else 0.0)
    sinks = sum(1 for v in (t.get("relay_sites") or {}).values() if x0 <= v[0] <= x1)
    H = float(t["outline_um"][1])
    ys = sorted(q["xy"][1] for q in (t.get("clock") or {}).get("taps") or []
                if q.get("kind") != "core" and x0 <= q["xy"][0] <= x1)
    gap = max([b - a for a, b in zip([0.0] + ys, ys + [H])])
    return dict(width=width, wires=wires, util=util, sinks=sinks, taps=len(ys), gap=gap,
                need=int(math.ceil(sinks / TAP_SINKS)))


def type_lines(tn, t):
    out = []
    for lab, x0, x1 in channels(t):
        s = stats(t, x0, x1)
        why = []
        if s["util"] >= WARN_UTIL:
            why.append("WIDTH %.0f through-wires in %.1f um = util %.2f (>= %.1f)" % (s["wires"], s["width"], s["util"], WARN_UTIL))
        if lab == "central" and s["sinks"] and (s["taps"] < s["need"] or s["gap"] > MAX_GAP_UM):
            why.append("TAPGRID %d sinks, %d tap(s) (need %d), max tap gap %.0f um (limit %.0f): no tap grid" % (
                s["sinks"], s["taps"], s["need"], s["gap"], MAX_GAP_UM))
        if why:
            out.append("WARN ADV-%s %s: %s x%.1f-%.1f: %s; fix: add a tap grid in the channel and/or widen / split the channel "
                       "(pre-approved growth)" % (CHECK, tn, lab, x0, x1, "; ".join(why)))
    return out


def findings(raw, plan_path=None, tree=None, types=None, **_kw):
    P = raw.get("partition_types") or {}
    if not P:
        return [f"WARN ADV-{CHECK} not checked: plan has no partition_types"]
    rx = re.compile(types or DEFAULT_TYPES)
    out = []
    for tn in sorted(P):
        t = P[tn]
        if not rx.search(tn) or not isinstance(t, dict):
            continue
        try:
            out += type_lines(tn, t)
        except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
            out.append(f"WARN ADV-{CHECK} {tn}: not checked: {type(e).__name__}: {str(e)[:120]}")
    return out[:MAX_LINES]
