#!/usr/bin/env python3
"""UNIFY-TOOLS (FABLE-SUPERSET-0415 section 10, U1/U4/U6/U7): merge a class of partition types into ONE type.

Every instance of a member type is re-typed to the representative, so bind emits one bound module for the class and one
kit / one synthesis serves every instance (U7).  The class row is the representative's whole row (floorplan, taps, reset
tree, reader / writer start, bands: U2/U4/U6).  What may differ between members, and how it is made per instance:

  - collector (monitor) children (U1): the representative must carry every child site (xy, seam, occurrence) any member
    uses; all of them become clock.landing_contract.tieable_children, seam children get a strap_cland_use_<k> pin
    (landing_tie_children.with_use_pins).  An instance ties the children it does not use (ready 1, fault 0, clock 0)
    and its use strap is derived from its real landing edges (landing_tie_children.instance_use).  Die landing edges
    (plan clock.landing_network.edges dst.bus, sidecar collector.edges dst_index) are re-indexed by child site.
  - reset outs (U4): the representative's outs; an instance leaves the outs it does not drive open.
  - pad strap (U3): r8_strap_pad_max = the class maximum (the pad is a strap tied at the parent, OWNER 10-25 B).
  - landing role origin / relay: must be equal, or with --role-strap the class row takes every origin / relay start
    pin a member has, the count-strap union, strap_ca_relay and landing_role_strap (clock_landings ROLE-STRAP).

Refused (exit 2, nothing written): a member child site the representative lacks, a different outline or bus / ft pin
table, a member with data landing pins the representative lacks.  Per-type die tables keyed by a member type name
(clock.tap_window / tap_offset, reset.in_sites, sidecar collector.types) are dropped; the representative's stay.

    class_merge.py PLAN SIDECAR OUT_PLAN OUT_SIDECAR --rep TYPE (--members T1,T2,.. | --stem STEM) [--report R.json]
"""
import argparse, collections, copy, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import landing_tie_children as LTC  # noqa: E402

DN = re.compile(r"^(cland_dn_ready|cland_dn_fault|fclk_in_cland_dn)_(\d+)$")
UP = ("cland_up_ready", "cland_up_fault", "fclk_out_cland_up")
# type-row fields that are the class row (representative) by definition; a member's own value is replaced
CLASS_ROW = {"clock", "reset", "hard_cores", "internal_stations", "cells", "relay_sites", "note", "landing_base_type",
             "contents", "count_straps", "r8_strap_pad_max", "module", "ft_track_frac"}
# fields that must be equal: a difference means the member is not a copy of the class row
MUST_EQUAL = ("outline_um", "buses", "ft_slots")


class MergeError(Exception):
    pass


def _lc(t):
    return ((t.get("clock") or {}).get("landing_contract")) or {}


def child_keys(lc):
    """{old index: (xy, seam, occurrence)} of a landing contract's collector children."""
    occ = collections.Counter(); out = {}
    for ch in sorted(lc.get("collector_children") or [], key=lambda r: int(r["index"])):
        k0 = (tuple(round(float(v), 3) for v in ch["xy_um"]), bool(ch["seam"]))
        out[int(ch["index"])] = (k0[0], k0[1], occ[k0]); occ[k0] += 1
    return out


def data_landing_pins(lc):
    return {p["name"] for p in lc.get("pins", []) if p["name"] not in UP and not DN.match(p["name"])
            and not p["name"].startswith(LTC.MONITOR_USE_PREFIX)}


def landing_role(sidecar, part):
    """Count-aligned origin / relay role of a partition (None when it is not a count-aligned part)."""
    ca = (sidecar.get("count_aligned") or {}).get("parts") or {}
    row = ca.get(part)
    if not isinstance(row, dict):
        return None
    return row.get("role")


def free_site_on_line(pins, pin, outline, tries=16, clear_um=1.0):
    """Nearest free site for `pin` on its own layer: moved across its routing direction by whole track pairs (a V layer
    moves in x, an H layer in y; die_plan.schema layer pitch), so it stays on a track; a site is free when no same-layer
    landing pin is within clear_um.  None when no free site lies within `tries` steps inside the outline."""
    import schema as S
    lay = next((L for L in S.ASAP7_LAYERS if L["name"] == pin.get("layer")), None)
    if lay is None:
        return None
    step = 2 * lay["pitch_um"]
    x0, y0 = (float(v) for v in pin["xy_um"])
    same = [tuple(float(v) for v in q["xy_um"]) for q in pins if q.get("layer") == pin.get("layer") and "xy_um" in q]
    for k in range(1, tries + 1):
        for sgn in (1, -1):
            d = sgn * k * step
            c = (x0 + d, y0) if lay["dir"] == "V" else (x0, y0 + d)
            if not all(0 <= v <= lim for v, lim in zip(c, outline)):
                continue
            if all(abs(c[0] - a) + abs(c[1] - b) >= clear_um for a, b in same):
                return [round(c[0], 6), round(c[1], 6)]
    return None


def role_pins_union(P, rep, members, rep_out):
    """ROLE-STRAP class row: the representative takes every origin / relay start pin a member has (same name, site and
    layer as on that member), the union of the count straps (max width) plus strap_ca_relay, and landing_role_strap."""
    R = P[rep]; rlc = _lc(R)
    have = {p["name"]: p for p in rlc.get("pins", [])}
    sites = {(p["layer"], tuple(round(float(v), 3) for v in p["xy_um"])): p["name"] for p in rlc.get("pins", [])
             if "xy_um" in p and "layer" in p}
    added, src_site = [], {}      # src_site: the member site of a pin the class row moved
    for m in members:
        for pin in _lc(P[m]).get("pins", []):
            n = pin["name"]
            if n not in ROLE_PINS:
                continue
            if n in have:
                if (have[n].get("layer"), src_site.get(n, have[n].get("xy_um"))) != (pin.get("layer"), pin.get("xy_um")):
                    rep_out["refused"].append(f"{m}: role pin {n} at another site than the class row's")
                continue
            key = (pin.get("layer"), tuple(round(float(v), 3) for v in pin.get("xy_um", [])))
            q = copy.deepcopy(pin)
            if key in sites:
                # the relay rx of one copy sits where the origin tx of another copy is (the two ends of one seam
                # edge): the class row takes the next free site on the same pin line (the pitch of that line)
                xy = free_site_on_line(rlc.get("pins", []), pin, R["outline_um"])
                if xy is None:
                    rep_out["refused"].append(f"{m}: role pin {n} site is {sites[key]} on the class row, no free site")
                    continue
                rep_out.setdefault("role_pins_moved", {})[n] = [pin["xy_um"], xy]
                src_site[n] = pin["xy_um"]
                q["xy_um"] = xy; key = (pin.get("layer"), tuple(round(float(v), 3) for v in xy))
            rlc.setdefault("pins", []).append(q); have[n] = q; sites[key] = n; added.append(n)
    widths = {}
    for t in [rep] + members:
        for c in P[t].get("count_straps", []):
            widths[c["name"]] = max(widths.get(c["name"], 0), int(c["width"]))
    widths["strap_ca_relay"] = 1
    R["count_straps"] = [dict(name=n, width=w) for n, w in sorted(widths.items())]
    R["landing_role_strap"] = True
    rep_out["role_strap"] = dict(pins_added=sorted(added), count_straps=widths)


def names_used(x, names):
    """Member type names used as a dict key or a whole string value (free text such as notes does not count)."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in names:
                yield k
            yield from names_used(v, names)
    elif isinstance(x, list):
        for v in x:
            yield from names_used(v, names)
    elif isinstance(x, str) and x in names:
        yield x


ROLE_PINS = ("cland_rstart_in", "cland_rstart_out", "cland_tstart_in", "cland_tstart_out")


def merge(plan, side, rep, members, role_strap=False):
    P = plan["partition_types"]
    if rep not in P:
        raise MergeError(f"representative {rep} is not a plan type")
    members = [m for m in members if m != rep]
    missing = [m for m in members if m not in P]
    if missing:
        raise MergeError(f"member types not in the plan: {missing}")
    R = P[rep]; rlc = _lc(R); rkeys = child_keys(rlc); rindex = {k: i for i, k in rkeys.items()}
    rep_out = dict(rep=rep, members=members, refused=[], moved={}, edges=dict(plan=0, sidecar=0), dropped=[])
    # ---- refusals first: nothing is written when any member is not a copy of the class row
    for m in members:
        t = P[m]
        for f in MUST_EQUAL:
            if json.dumps(t.get(f), sort_keys=True) != json.dumps(R.get(f), sort_keys=True):
                rep_out["refused"].append(f"{m}: {f} differs from the representative")
        mlc = _lc(t)
        extra = data_landing_pins(mlc) - data_landing_pins(rlc) - (set(ROLE_PINS) if role_strap else set())
        if extra:
            rep_out["refused"].append(f"{m}: data landing pins not on the representative: {sorted(extra)[:6]}")
        for i, key in child_keys(mlc).items():
            if key not in rindex:
                rep_out["refused"].append(f"{m}: collector child {i} at {list(key[0])} seam={key[1]} is not a "
                                          f"representative child site")
    parts = [p for p in plan["partitions"] if p["type"] in members or p["type"] == rep]
    roles = {landing_role(side, p["name"]) for p in parts}
    if len(roles) > 1 and not role_strap:
        rep_out["refused"].append(f"count-aligned landing role differs between instances: {sorted(map(str, roles))} "
                                  f"(origin / relay strap needed)")
    if role_strap and len(roles) > 1:
        role_pins_union(P, rep, members, rep_out)
    if rep_out["refused"]:
        return rep_out
    # ---- class row: every representative child is tieable; seam children get a use strap pin
    if rkeys:
        tie = [dict(index=i, seam=k[1]) for i, k in sorted(rkeys.items())]
        rlc["tieable_children"] = tie
        rlc["pins"] = LTC.with_use_pins(rlc["pins"], tie, R["outline_um"])
    pads = [P[t].get("r8_strap_pad_max") for t in [rep] + members if P[t].get("r8_strap_pad_max") is not None]
    if pads:
        R["r8_strap_pad_max"] = max(pads)
    # ---- re-type every instance, re-index its incoming monitor edges by child site
    remap = {m: {i: rindex[k] for i, k in child_keys(_lc(P[m])).items()} for m in members}
    part_type = {p["name"]: p["type"] for p in plan["partitions"]}
    for e in (plan.get("clock") or {}).get("landing_network", {}).get("edges", []):
        mt = DN.match(e["dst"]["bus"]); tn = part_type.get(e["dst"]["part"])
        if mt and tn in remap:
            e["dst"]["bus"] = f"{mt.group(1)}_{remap[tn][int(mt.group(2))]}"; rep_out["edges"]["plan"] += 1
    coll = side.get("collector") or {}
    for e in coll.get("edges", []):
        if isinstance(e, dict) and part_type.get(e.get("dst")) in remap and e.get("dst_index") is not None:
            e["dst_index"] = remap[part_type[e["dst"]]][int(e["dst_index"])]; rep_out["edges"]["sidecar"] += 1
    rdepth = (coll.get("boot_budget") or {}).get("local_registered_depths", {})
    rep_parts = [p["name"] for p in plan["partitions"] if p["type"] == rep]
    rep_depth = rdepth.get(rep_parts[0]) if rep_parts else None
    for p in plan["partitions"]:
        if p["type"] in members:
            rep_out["moved"][p["name"]] = p["type"]; p["type"] = rep
            row = (coll.get("parts") or {}).get(p["name"])
            if isinstance(row, dict) and "type" in row:
                row["type"] = rep
            if p["name"] in (coll.get("base_type_by_part") or {}):
                coll["base_type_by_part"][p["name"]] = (coll.get("types", {}).get(rep) or {}).get("base_type", rep)
            if p["name"] in rdepth and rep_depth is not None and rdepth[p["name"]] != rep_depth:
                rep_out.setdefault("boot_depth_changed", {})[p["name"]] = [rdepth[p["name"]], rep_depth]
                rdepth[p["name"]] = rep_depth
    # ---- drop per-type die tables of the member types (the representative's apply to every instance)
    def drop(d, path):
        if isinstance(d, dict):
            for k in list(d):
                if k in members:
                    d.pop(k); rep_out["dropped"].append(f"{path}/{k}")
                else:
                    drop(d[k], f"{path}/{k}")
    drop({k: v for k, v in plan.items() if k not in ("partition_types", "partitions")}, "")
    drop(coll.get("types", {}), "/sidecar/collector/types")
    for m in members:
        del P[m]
    left = sorted(set(names_used(plan, set(members))) | set(names_used(side, set(members))))
    if left:
        raise MergeError(f"member type names still referenced after the merge: {left}")
    rep_out["instances"] = len(rep_parts) + len(rep_out["moved"])
    return rep_out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("side"); ap.add_argument("oplan"); ap.add_argument("oside")
    ap.add_argument("--rep", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--members"); g.add_argument("--stem")
    ap.add_argument("--role-strap", action="store_true",
                    help="allow origin and relay copies in the class (landing_role_strap, strap_ca_relay)")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text()); side = json.loads(Path(a.side).read_text())
    members = (a.members.split(",") if a.members else
               sorted(k for k in plan["partition_types"] if k.split("__")[0] == a.stem))
    try:
        rep = merge(plan, side, a.rep, members, role_strap=a.role_strap)
    except MergeError as exc:
        print(f"CLASS-MERGE ERROR {exc}", file=sys.stderr); return 2
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    if rep["refused"]:
        for r in rep["refused"]:
            print("CLASS-MERGE REFUSED", r, file=sys.stderr)
        return 2
    Path(a.oplan).write_text(json.dumps(plan, indent=1) + "\n")
    Path(a.oside).write_text(json.dumps(side, separators=(",", ":")) + "\n")
    print(f"CLASS-MERGE {a.rep}: {len(rep['members'])} member types -> 1, {rep['instances']} instances, "
          f"edges plan {rep['edges']['plan']} sidecar {rep['edges']['sidecar']}, dropped {len(rep['dropped'])} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
