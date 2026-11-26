"""origin_raw.py -- which reset node feeds a landing count origin (KV-SINKBINS 11-25, COORD).

clock_landings._origin_rtl took `next(iter(ca_raw.values()))`: the reset node of whichever input ring band the bind visited first, so
the origin's raw reset depended on dict order, and after a tap re-solve landing_raw_branches finals named a node the bind no longer
chose ("origin reset phase/equation differs").  One documented rule, one function (pure, no plan access):

  pick_origin_raw(cands, origin_xy=None, plan_raw=None, legacy_first=False) -> (net, how)
    cands      [(net, (x, y) | None)] reset nodes of the region's input ring bands, in the order the bind visits them
    plan_raw   clock.landing_origin_raw recorded in the plan: used when it is one of the candidates ('plan'); a name that is not a
               candidate is ignored with a warning (how 'plan-unknown')
    otherwise  the node nearest (Manhattan) to origin_xy, ties and unsited nodes by natural name order ('nearest');
               no origin site -> the lowest name ('name').  legacy_first=True keeps the old first-visited node ('legacy').
  An empty candidate list returns (None, 'none'); the caller keeps its own fallback (rst_n_t0 / delivered reset)."""
import re

KEY = "landing_origin_raw"


def _nat(name):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", str(name))]


def pick_origin_raw(cands, origin_xy=None, plan_raw=None, legacy_first=False):
    nets = []
    sites = {}
    for net, xy in cands:
        if net not in sites or (sites[net] is None and xy is not None):
            sites[net] = xy
        if net not in nets:
            nets.append(net)
    if not nets:
        return None, "none"
    how = "plan-unknown" if plan_raw else None
    if plan_raw in sites:
        return plan_raw, "plan"
    if legacy_first:
        return nets[0], "legacy" if how is None else how
    if origin_xy is not None and any(sites[n] is not None for n in nets):
        d = lambda n: (abs(sites[n][0] - origin_xy[0]) + abs(sites[n][1] - origin_xy[1])) if sites[n] is not None else float("inf")
        return min(nets, key=lambda n: (d(n), _nat(n))), "nearest" if how is None else how
    return min(nets, key=_nat), "name" if how is None else how


def check(plan_raw, cands, origin_xy=None):
    """retap-check style comparison: (ok, picked, how) -- ok when the plan's recorded node is the one the rule picks"""
    net, how = pick_origin_raw(cands, origin_xy, None)
    return plan_raw == net, net, how
