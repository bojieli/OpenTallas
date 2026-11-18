#!/usr/bin/env python3
"""TAIL-REPL (lane TAIL-REPL 11-17): per-consumer-cluster copies of a landing-pad chain's last stage.

Plan key (bind only, absent = nothing runs):
    asbuilt.tail_repl = {"types": [plan type, ...], "min_spread_um": 400, "cluster_um": 200}
A landing pad (bind land_align, ot_dp_dly u_pd<D>_<bus>_<j>) ends in ONE flop that drives the same pin of every hard
core reading that in-bus bit.  When the hard-core consumers of one pad are spread over more than min_spread_um
(bounding-box half perimeter of the core centres, plan hard_cores origin_um + outline_um / 2), the pad's last stage
is replicated: stages 1..D-1 stay shared (pad D-1, which is the in-lane flop for D = 1), and each cluster of cores
(greedy, a core joins the first cluster whose seed centre is within cluster_um L1) gets its own ONE-stage ot_dp_dly
u_pd<D>_<bus>_c<n>_<j>.  Total latency is unchanged (D stages in every path), no stage is added to any lane, so
LATCHECK and as-built latency stay as they are.  Non-core sinks keep the original shared tail.  The copy is a normal
relay chain: type_relay_sites.py sites it at the L1 minimax of the pins it drives, i.e. at its own cluster.
"""
DEFAULT_MIN_SPREAD_UM = 400.0
DEFAULT_CLUSTER_UM = 200.0


def config(ab):
    """-> {type: (min_spread_um, cluster_um)} (empty when the key is absent)"""
    c = (ab or {}).get("tail_repl")
    if not c:
        return {}
    ms = float(c.get("min_spread_um", DEFAULT_MIN_SPREAD_UM))
    cl = float(c.get("cluster_um", DEFAULT_CLUSTER_UM))
    if ms < 0 or cl <= 0:
        raise ValueError("asbuilt.tail_repl: min_spread_um >= 0 and cluster_um > 0 required")
    types = c.get("types")
    if not types:
        raise ValueError("asbuilt.tail_repl.types must list the plan types it applies to")
    return {t: (ms, cl) for t in types}


def centers(hard_cores):
    """{core inst: (cx, cy)} from plan hard_cores rows"""
    out = {}
    for h in hard_cores or []:
        o, w = h["origin_um"], h["outline_um"]
        out[h["inst"]] = (o[0] + w[0] / 2.0, o[1] + w[1] / 2.0)
    return out


def spread(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (max(xs) - min(xs)) + (max(ys) - min(ys)) if pts else 0.0


def decide(cons, min_spread_um, cluster_um):
    """cons {core key: (x, y)} -> {core key: cluster index} when the tail must be replicated, else None"""
    if len(cons) < 2 or spread(list(cons.values())) <= min_spread_um:
        return None
    seeds, out = [], {}
    for k in sorted(cons, key=lambda k: (cons[k][0], cons[k][1], str(k))):
        x, y = cons[k]
        for n, (sx, sy) in enumerate(seeds):
            if abs(x - sx) + abs(y - sy) <= cluster_um:
                out[k] = n
                break
        else:
            out[k] = len(seeds)
            seeds.append((x, y))
    return out if len(seeds) > 1 else None
