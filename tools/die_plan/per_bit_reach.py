"""per_bit_reach.py -- ONE model of where the kit seats a bit_route "per_bit" internal station chain, for the static reach checks.
(HEAD-INT-R2 11-26, C-LEG405 / P-FALSE-GREEN; independent review F1 of hd_spn SPN r2.)

kit_istations.is_bits (istations.tcl) seats bit b of station k at L_b*(k+1)/(n+1) along its own L from its face pin to leaf_um
(taps.per_bit_station_sites is the plan-side mirror).  It never reads regs_um except for the station COUNT n, so a plan edit that
only re-seats regs_um moves nothing in the placed design, while a check that measures from_um -> regs_um -> to_um reports a
number the flow ignores (hd_spn be_i / bw_i: lean 598.5 / 756 false red; the reseat turned it green with identical placed
centroids; placed be_i max 332.1 um).  Chosen source of truth = the KIT (placed results of every existing plan stay unchanged):
the checks replace regs_um by the kit rule via per_bit_hops().

per_bit_hops(e, bus, w, h) -> [hop um] (n+1 equal path hops of the worst pin window end <-> leaf_um), or None when the
entry is not a FIRM per_bit chain (the caller keeps its regs_um chain).

DEFAULT OFF (COORD ruling 11-26, FABLE-INDEP review): the model is not yet the kit model.  (1) packed_input_delay per_bit
entries are seated at regs_um by kit_istations.py (QC sle_ctl istations.tcl matches the plan regs_um), but applies() has no packed
exclusion -> QC C9 431.9 read as 299.4 (false green); (2) the kit is_knee_site splits the n+1 edges over the normal and along legs,
while L/(n+1) is the stale taps.per_bit_station_sites rule (same row: kit 419.2, check 299.4).  OT_PERBIT_REACH=1 opts in.
Re-enable only with a packed exclusion, a knee rule shared with the kit code, tests on a real istations.tcl, a flip census with
every placed hop < 405 um and a GOOD independent review."""
import os


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def applies(e, bus):
    """True when the kit places this entry per bit (mirrors taps.per_bit_station_sites / kit_istations.is_bits)."""
    if os.environ.get("OT_PERBIT_REACH", "0") != "1":
        return False
    return bool(e.get("bit_route") == "per_bit" and str(e.get("conn", "")).startswith("bus:") and e.get("leaf_um")
                and e.get("regs_um") and not e.get("bit_sites_um") and not e.get("start_core")
                and e.get("leg_order") != "channel" and bus and bus.get("face") in ("N", "S", "E", "W") and bus.get("window_um"))


def per_bit_hops(e, bus, w, h):
    if not applies(e, bus):
        return None
    lo, hi = sorted((float(bus["window_um"][0]), float(bus["window_um"][1])))
    face = bus["face"]
    ends = [{"N": (c, h), "S": (c, 0.0), "E": (w, c), "W": (0.0, c)}[face] for c in (lo, hi)]
    leaf = (float(e["leaf_um"][0]), float(e["leaf_um"][1]))
    L = max(_man(p, leaf) for p in ends)          # the kit path pin -> knee -> leaf is monotone: its length is the Manhattan distance
    n = len(e["regs_um"])
    return [L / (n + 1)] * (n + 1)
