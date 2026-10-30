#!/usr/bin/env python3
"""HBM n4 lane-map assertion (HBM-MU-QUAD-3; COORD RULING HBM-MU-QUAD-2 2026-10-27 00:44: n4 is ADOPTED only if the
binder ASSERTS the lane map NW hub = global FUSED lanes 0..15, NE hub = 16..31, and fails the bind otherwise).

Why: with n4 the root receives ONE input per die hub (t5 = (NW n4, NE n4)); the fused sum equals the golden 5-level
pairwise tree (level k pairs (2c, 2c+1), left = even chunk; chunk c = global lane c at ph 0) ONLY if every hub-local lane
u_mu_fused_L is global lane 16*side + L (side NW = 0, NE = 1) and the NW n4 feeds the root's a side.  A different map
(e.g. NE = 0..15, or lanes permuted inside a hub) still times correctly but changes the rounding order.

Opt-in: the check is active only when the plan declares the n4 topology (a partition type with a hard core / content
`u_mu_fused_n4` of module ot_hnx_fused_tnode), or with --force.  Plans without it pass untouched (exit 0, active=false).

Checks (any failure -> exit 1):
  1. exactly two hub partitions carry the n4 topology, named NW_* and NE_*, and NW lies west of NE (die x);
  2. each hub type has exactly the 16 lanes u_mu_fused_0..15 (module hnx_fused_lane);
  3. the hub-local reduction tree, rebuilt from the type's mu_tree internal_stations (child .uo -> parent .ua/.ub),
     equals the golden pairwise tree over local lanes 0..15 (structure incl. a/b sides) with u_mu_fused_n4 its root;
  4. a declared lane identity (parent_id_straps lane_lane_id / lid, params lid / LID) equals 16*side + L;
  5. a declared root side (internal_station capture 'face root.up' with a trailing ':a'/':b' or 'ua'/'ub' slot, or a
     die port from the hub to the root naming slot a/b) puts NW on a and NE on b.
Undeclared lane ids / root side are not errors: they are reported as the DERIVED values the binder must tie
(`required_lid` table); --strict makes undeclared values errors.

Usage: hbm_n4_lanemap.py PLAN.json [--out report.json] [--force] [--strict]
"""
import argparse
import json
import re
import sys

LANE_MODULE = "hnx_fused_lane"
NODE_MODULE = "ot_hnx_fused_tnode"
N4 = "u_mu_fused_n4"
LANES = 16


def golden(lo=0, n=LANES):
    return ("L", lo) if n == 1 else (golden(lo, n // 2), golden(lo + n // 2, n // 2))


def _leaves(t):
    return list(t.get("hard_cores", [])) + list(t.get("contents", []))


def has_n4(t):
    return any(h.get("inst") == N4 and h.get("module", NODE_MODULE) == NODE_MODULE for h in _leaves(t))


def hub_tree(t):
    """local expression tree rooted at u_mu_fused_n4 from the mu_tree up edges; raises ValueError on a malformed tree."""
    par = {}
    for s in t.get("internal_stations", []):
        c = str(s.get("conn", ""))
        if not c.startswith("mu_tree:"):
            continue
        L, C = str(s.get("launch", "")), str(s.get("capture", ""))
        if not L.endswith(".uo"):
            continue
        child = L[:-3]
        parent, _, slot = C.rpartition(".")
        if slot not in ("ua", "ub"):
            raise ValueError(f"mu_tree edge {c}: capture slot {slot!r} is not ua/ub")
        if child in par and par[child] != (parent, slot):
            raise ValueError(f"mu_tree node {child} has two parents")
        par[child] = (parent, slot)
    kids = {}
    for ch, (p, sl) in par.items():
        if sl in kids.setdefault(p, {}):
            raise ValueError(f"mu_tree node {p}: slot {sl} driven twice")
        kids[p][sl] = ch

    def expr(n, depth=0):
        if depth > 64:
            raise ValueError("mu_tree cycle")
        m = re.fullmatch(r"u_mu_fused_(\d+)", n)
        if m:
            return ("L", int(m.group(1)))
        k = kids.get(n, {})
        if set(k) != {"ua", "ub"}:
            raise ValueError(f"mu_tree node {n}: children {sorted(k)} (need ua and ub)")
        return (expr(k["ua"], depth + 1), expr(k["ub"], depth + 1))
    if N4 not in kids:
        raise ValueError(f"{N4} has no mu_tree children")
    return expr(N4)


def declared_lid(h):
    ids = h.get("parent_id_straps") or {}
    alias = h.get("physical_id_alias") or {}
    if alias:
        # OWNER 10-30 (3)(B): a physical strap_* alias carries the native lane identity (lane_lane_id)
        try:
            from parent_id_straps import logical_id_straps
        except ImportError:
            from tools.die_plan.parent_id_straps import logical_id_straps
        ids = logical_id_straps(h)
    for src in (ids, h.get("params") or {}):
        for k in ("lane_lane_id", "lid", "LID"):
            if k in src:
                v = src[k]
                return int(v["value"] if isinstance(v, dict) else v)
    return None


def declared_root_side(P, part, t):
    """'a' / 'b' if the plan states which root input this hub's n4 drives, else None."""
    for s in t.get("internal_stations", []):
        if str(s.get("conn", "")).startswith("mu_tree_root:") and str(s.get("launch", "")).endswith(".uo"):
            m = re.search(r"(?:[:.]u?)([ab])$", str(s.get("capture", "")))
            if m and "root" in str(s.get("capture", "")):
                return m.group(1)
    for pt in P.get("ports", []):
        if pt.get("src", {}).get("part") == part and pt.get("dst", {}).get("part") == "root":
            m = re.search(r"(?:mu|n4|fused)\w*?_u?([ab])(?:_i)?$", str(pt["dst"].get("bus", "")))
            if m:
                return m.group(1)
    return None


def check(P, force=False, strict=False):
    T = P.get("partition_types", {})
    hubs = [p for p in P.get("partitions", []) if has_n4(T.get(p["type"], {}))]
    rep = dict(active=bool(hubs) or force, errors=[], notes=[], required_lid={}, hubs={})
    if not rep["active"]:
        rep["notes"].append("no n4 topology declared (no u_mu_fused_n4): check not applicable")
        return rep
    err = rep["errors"].append
    side_of = {}
    for p in hubs:
        nm = p["name"]
        side = 0 if nm.startswith("NW_") else 1 if nm.startswith("NE_") else None
        if side is None:
            err(f"partition {nm}: n4 hub must be named NW_* or NE_*")
        else:
            side_of[nm] = side
    if sorted(side_of.values()) != [0, 1]:
        err(f"need exactly one NW and one NE n4 hub, got {sorted(side_of)}")
    else:
        nw = next(p for p in hubs if side_of.get(p["name"]) == 0)
        ne = next(p for p in hubs if side_of.get(p["name"]) == 1)
        if not nw["origin_um"][0] < ne["origin_um"][0]:
            err(f"NW hub {nw['name']} x {nw['origin_um'][0]} is not west of NE hub {ne['name']} x {ne['origin_um'][0]}")
    G = golden()
    for p in hubs:
        nm = p["name"]
        if nm not in side_of:
            continue
        side = side_of[nm]
        base = LANES * side
        t = T[p["type"]]
        lanes = {}
        for h in _leaves(t):
            m = re.fullmatch(r"u_mu_fused_(\d+)", h.get("inst", ""))
            if m:
                if h.get("module", LANE_MODULE) != LANE_MODULE:
                    err(f"{nm}: {h['inst']} module {h.get('module')} != {LANE_MODULE}")
                lanes[int(m.group(1))] = h
        if sorted(lanes) != list(range(LANES)):
            err(f"{nm} ({p['type']}): lanes {sorted(lanes)} != u_mu_fused_0..{LANES - 1}")
        try:
            e = hub_tree(t)
            if e != G:
                err(f"{nm}: hub-local mu_tree is not the golden pairwise tree over lanes 0..15 (left = even)")
        except ValueError as x:
            err(f"{nm}: {x}")
        for L, h in sorted(lanes.items()):
            want = base + L
            rep["required_lid"][f"{nm}.{h['inst']}"] = want
            got = declared_lid(h)
            if got is None:
                if strict:
                    err(f"{nm}.{h['inst']}: lane id undeclared (binder must tie lid = {want})")
            elif got != want:
                err(f"{nm}.{h['inst']}: declared lane id {got} != {want} (NW = 0..15, NE = 16..31)")
        rs = declared_root_side(P, nm, t)
        want_side = "a" if side == 0 else "b"
        if rs is None:
            rep["notes"].append(f"{nm}: root side undeclared -> binder must connect {N4}.uo to root t5.u{want_side}")
            if strict:
                err(f"{nm}: root side undeclared (need u{want_side})")
        elif rs != want_side:
            err(f"{nm}: n4 drives root side {rs}, must be {want_side} (NW -> a, NE -> b)")
        rep["hubs"][nm] = dict(type=p["type"], side=("NW", "NE")[side], global_lanes=[base, base + LANES - 1],
                               root_side=rs or f"derived u{want_side}")
    rep["verdict"] = "FAIL" if rep["errors"] else "PASS"
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true", help="check even without a declared n4 topology")
    ap.add_argument("--strict", action="store_true", help="undeclared lane ids / root side are errors")
    a = ap.parse_args(argv)
    rep = check(json.load(open(a.plan)), force=a.force, strict=a.strict)
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(dict(active=rep["active"], verdict=rep.get("verdict", "N/A"), errors=rep["errors"][:10],
                          notes=rep["notes"][:4], hubs=rep["hubs"])))
    return 1 if rep["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
