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
  An empty candidate list: the nearest node of `fallback` (the reset tree taps) with how 'fallback-nearest' (callers warn, never error);
  without a fallback (None, 'none') and the caller keeps its own rst_n_t0 / delivered-reset fallback."""
import re

KEY = "landing_origin_raw"


def _nat(name):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", str(name))]


def pick_origin_raw(cands, origin_xy=None, plan_raw=None, legacy_first=False, fallback=None):
    nets = []
    sites = {}
    for net, xy in cands:
        if net not in sites or (sites[net] is None and xy is not None):
            sites[net] = xy
        if net not in nets:
            nets.append(net)
    if not nets:
        # no input ring node: the nearest node of the reset tree (fallback = [(net, (x, y))]); the caller prints the warning
        if fallback and origin_xy is not None:
            fb = [(n, xy) for n, xy in fallback if xy is not None]
            if fb:
                return min(fb, key=lambda c: (abs(c[1][0] - origin_xy[0]) + abs(c[1][1] - origin_xy[1]), _nat(c[0])))[0], "fallback-nearest"
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


def band_face_xy(t, b, geom_fallback=None):
    """receiver face centre of input ring band b of type dict t -> [x, y], or None when the band has no face geometry.
    Extracted unchanged from clock_landings (bus face/window_um, else the bound collector's bus_geometry, else the ft_slot in-window)."""
    geom = next((x for x in t.get("buses", []) if x["name"] == b and "face" in x and "window_um" in x), None)
    if geom is None and geom_fallback:
        geom = geom_fallback.get(b)
    if geom is None:
        slot = next((x for x in t.get("ft_slots", []) if x["name"] + "_i" == b), None)
        if slot:
            geom = dict(face=slot["in_face"], window_um=slot["in_window_um"])
    if geom is None:
        return None
    face = geom["face"]
    at = sum(geom["window_um"]) / 2
    tw, th = t["outline_um"]
    return list((0 if face == "W" else tw, at) if face in "EW" else (at, 0 if face == "S" else th))


def nearest_tap(t, taps, x, y):
    """(tap index, [x, y]) of the ring tap nearest (Manhattan) to (x, y); no taps -> tap 0 at clock.tap_um / the outline centre (unchanged)"""
    if taps:
        tap = min(range(len(taps)), key=lambda i: abs(taps[i][0] - x) + abs(taps[i][1] - y))
        return tap, list(taps[tap])
    tw, th = t["outline_um"]
    return 0, t.get("clock", {}).get("tap_um", [tw / 2, th / 2])


def band_reset_site(t, b, taps, geom_fallback=None):
    """-> (tap_index, [x, y]) of the reset tap serving input band b, or None without face geometry"""
    f = band_face_xy(t, b, geom_fallback)
    return None if f is None else nearest_tap(t, taps, f[0], f[1])


def plan_candidates(t, taps):
    """plan-level stand-in for ca_raw: [(rst_n_t<tap>, xy)] of the input ring bands of type dict t (landing_contract bands named like a
    receiver bus).  landing_remap records the pick as clock.landing_origin_raw; the bind uses it only when it is one of its own ring
    nodes, so an approximate band list can never produce a wrong bind, only a warning and the legacy node."""
    out = []
    for b in sorted((t.get("clock", {}).get("landing_contract") or {}).get("bands") or {}):
        r = band_reset_site(t, b, taps)
        if r is not None:
            out.append((f"rst_n_t{r[0]}", tuple(r[1])))
    return out
