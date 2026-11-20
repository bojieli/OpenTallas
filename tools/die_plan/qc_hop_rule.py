#!/usr/bin/env python3
"""QC-PADLEG-1119: station-chain hop rule for QC plans (generator rule, so plans do not regress).

Measured on 9 QC kits (placed legs over 405 um): (1) the first hop was planned from the bus WINDOW CENTRE while the
bits of a bus span the whole window and the first registers spread too (nominal 435 um became 509 um placed);
(2) the last hop was aimed at the core CENTRE while the consumers/producers sit anywhere in a ~700 um deep core
(leaf 917 vs consumers y 500-1190).  Rules:
  first_hop_budget  = reach - (bit_span/2 + reg_spread/2)           (bit_span = bus bit-span along the face)
  last aim          = measured consumer/producer centroid, last reg->farthest consumer <= reach - 10
  plan_chain() places n regs on the face->aim line with hop 0 limited by the budget and the others equal;
  min_regs() is the smallest n for which every hop fits.  Stop list: no pad-site moves; only regs_um change.
"""
import math

REACH_UM = 405.0
REG_SPREAD_UM = 67.0      # measured pad/pd spread of one chain stage (x 91-158)
LAST_SLACK_UM = 10.0


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centroid(points):
    pts = list(points)
    if not pts:
        raise ValueError("no consumer/producer points")
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def spread(points, c=None):
    """largest L1 distance of any consumer/producer from the centroid"""
    pts = list(points)
    c = c or centroid(pts)
    return max(l1(c, p) for p in pts)


def _lerp(a, b, t):
    return [round(a[0] + (b[0] - a[0]) * t, 3), round(a[1] + (b[1] - a[1]) * t, 3)]


def hop_limits(n, bit_span_um, reach=REACH_UM, reg_spread=REG_SPREAD_UM, last_spread=0.0):
    """max nominal length of each of the n+1 hops (face->r1 ... rn->aim)"""
    lim = [reach - reg_spread] * (n + 1)
    lim[0] = reach - (bit_span_um / 2.0 + reg_spread / 2.0)
    lim[-1] = min(lim[-1], reach - LAST_SLACK_UM - last_spread)
    return lim


def plan_chain(face_pt, aim_pt, n, bit_span_um, reach=REACH_UM, last_spread=0.0):
    """n registers from face_pt to aim_pt.  Returns (regs_um, hops, ok).  Hop 0 gets min(budget, equal share)
    and the remainder is shared equally, so a wide window never makes the first hop the longest."""
    total = l1(face_pt, aim_pt)
    lim = hop_limits(n, bit_span_um, reach, last_spread=last_spread)
    h0 = min(lim[0], total / (n + 1))
    rest = (total - h0) / n if n else 0.0
    hops = [h0] + [rest] * n if n else [total]
    cum, regs = 0.0, []
    for h in hops[:-1]:
        cum += h
        regs.append(_lerp(face_pt, aim_pt, cum / total if total else 0.0))
    ok = all(h <= lm + 1e-6 for h, lm in zip(hops, lim))
    return regs, [round(h, 1) for h in hops], ok


def min_regs(face_pt, aim_pt, bit_span_um, reach=REACH_UM, last_spread=0.0, nmax=32):
    for n in range(0, nmax + 1):
        if plan_chain(face_pt, aim_pt, n, bit_span_um, reach, last_spread)[2]:
            return n
    raise ValueError("no chain fits")


def plan_from_consumers(face_pt, consumers, bit_span_um, n=None, reach=REACH_UM):
    """aim at the measured consumer/producer centroid; n None = fewest registers."""
    c = centroid(consumers)
    sp = spread(consumers, c)
    n = min_regs(face_pt, c, bit_span_um, reach, sp) if n is None else n
    regs, hops, ok = plan_chain(face_pt, c, n, bit_span_um, reach, sp)
    return dict(regs_um=regs, hops_um=hops, ok=ok, aim_um=[round(c[0], 3), round(c[1], 3)], consumer_spread_um=round(sp, 1), n=n)
