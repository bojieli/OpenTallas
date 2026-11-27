"""KIT-OVERLAY-1: per-type positions-only overlay on a bound die plan.

A placement-only change inside ONE type (hard cores / placed contents / internal station sites move or re-orient inside
the same outline; ports, buses, lanes, latency, RTL unchanged) does not need a die plan event, a die-wide strict bind and
a regenerated kit for every type.  The bound RTL (bind root, sidecars) of the die's last strict-bound plan stays valid; only
the type's physical kit is regenerated from the bound plan + this overlay and launched through the full flow.

    python3 -I tools/die_plan/type_overlay.py diff  BASE_PLAN NEW_PLAN --type T --out OVERLAY.json
    python3 -I tools/die_plan/type_overlay.py check BASE_PLAN OVERLAY.json [--g0-full]
    python3 -I tools/die_plan/type_overlay.py apply BASE_PLAN OVERLAY.json --out OVERLAID_PLAN.json
    python3 -I tools/die_plan/gen.py phys BASE_PLAN --types T --type-overlay OVERLAY.json --kit-rtl T=... --out DIR

Overlay file (format type-overlay-1), every key but "format"/"type" optional:
    {"format": "type-overlay-1", "type": "T", "base_plan_sha256": "<canonical sha of the bound plan>",
     "hard_cores": {"<inst>": {"origin_um": [x, y], "orient": "MX", "track_offset_um": [dx, dy]}},
     "contents":   {"<inst>": {"origin_um": [x, y], "orient": "R0"}},
     "internal_stations": {"<index>": {"conn": "<guard, optional>", "regs_um": [[x, y], ...],
                                       "bit_sites_um": [[[x, y], ...], ...], "leaf_um": [x, y]}}}

The optional "ft_polarity_sites" key takes {"group": "<existing native group>", "sites": [[bit, x, y], ...]}.
It requires the base plan digest and preserves every bound bit selector and its order.

What a positions-only delta may touch (and nothing else; every other key is REJECTED):
    partition_types[T].hard_cores[*].{origin_um, orient, track_offset_um}
    partition_types[T].contents[*].{origin_um, orient}
    partition_types[T].internal_stations[i].{regs_um, bit_sites_um, leaf_um}   (same number of stations and banks)
    partition_types[T] clock.tap_um, reset.tap_um, clock.taps[i].xy, clock.edge_clocks[i].tap_um, collector relay xy,
      count_straps[i].sites_um, ft_slots[i].regs_um / bit_sites_um (key "type_positions": {dotted path: value}; same shape, inside the outline)
    budgets.ft_polarity_local_sites_by_type[T] coordinate columns of existing bits
These feed only physical code (gen_phys placement/pins/clock taps, kit_istations FIRM sites, G0 geometry, the reset
relay SITES).  bind.py / gen_rtl.py read hard_cores[].origin_um in one place (the CORE_SPLIT reset gate picks the
wavefront tap nearest the core centre) and reset_tree.for_type reads core boxes as obstacles; `rtl_projection` therefore
re-derives the type's reset tree (structure with coordinates stripped, plus every gate-tap choice), clock tap names and
core tap names for the base and the overlaid plan and REJECTS the overlay unless they are identical: EQ by construction.
CORE-SHAPE FREEZE (COORD 11-11): cores move/rotate only, no outline changes.  Outline, buses/ports, partitions, die ports, lanes, latency, clock/reset declarations, other types: always REJECTED.
"""
import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import schema as S  # noqa: E402

FORMAT = "type-overlay-1"
TOP_KEYS = {"format", "type", "base_plan_sha256", "hard_cores", "contents", "internal_stations", "type_positions", "note", "place_regions",
            "ft_polarity_sites"}
# Type-local site coordinates (dotted path inside partition_types[T]); every one is physical only, and the rtl_projection
# check proves the bind inputs derived from them (reset tree incl. relay names, tap names, gate taps) did not move.
import re  # noqa: E402
POS_PATHS = re.compile(r"^(clock\.tap_um|reset\.tap_um|clock\.edge_clocks\.\d+\.tap_um|clock\.taps\.\d+\.xy"
                       r"|clock\.landing_contract\.collector_tree\.relays\.\d+\.xy|count_straps\.\d+\.sites_um|ft_slots\.\d+\.regs_um"
                       r"|ft_slots\.\d+\.bit_sites_um)$")      # S81-GEOM-OPUS 11-18: ft bit sites ride with their regs
POS_LEAF = ("tap_um", "xy", "sites_um", "regs_um", "bit_sites_um")
HC_KEYS = ("origin_um", "orient", "track_offset_um")
CONTENT_KEYS = ("origin_um", "orient")
STATION_KEYS = ("regs_um", "bit_sites_um", "leaf_um")
EPS = 1e-6
FT_SITE_TABLE = "ft_polarity_local_sites_by_type"
FT_GROUP_TABLE = "ft_polarity_local_group_by_type"


class OverlayError(Exception):
    """The overlay is not a positions-only intra-type delta (or breaks the type's validation)."""

    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("type overlay rejected:\n  " + "\n  ".join(self.errors[:30]))


def load_json(path):
    p = Path(path)
    return json.loads((gzip.open(p, "rt") if p.suffix == ".gz" else open(p)).read())


def plan_sha(raw):
    return hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---------------------------------------------------------------- overlay -> plan
def _xy(v, what, errs):
    ok = isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(c, (int, float)) and not isinstance(c, bool)
                                                              and math.isfinite(c) for c in v)
    if not ok:
        errs.append(f"{what}: expected [x, y] numbers, got {v!r}")
    return ok


def _shape_of(v):
    if isinstance(v, list):
        return [len(v)] + ([_shape_of(x) for x in v] if v and isinstance(v[0], list) else [])
    return None


def _scalars(v):
    return sum(_scalars(x) for x in v) if isinstance(v, list) else 1


def _points(v):
    if isinstance(v, list) and len(v) == 2 and all(isinstance(c, (int, float)) for c in v):
        yield v
    elif isinstance(v, list):
        for x in v:
            yield from _points(x)


def _rows(t, key, inst_key="inst"):
    rows = {}
    for i, r in enumerate(t.get(key) or []):
        rows.setdefault(r.get(inst_key), []).append(i)
    return rows


def _ft_sites(rows, outline):
    if not isinstance(rows, list) or not rows:
        raise OverlayError("ft_polarity_sites: expected a nonempty list of [bit, x, y] rows")
    indexed = {}
    width, height = outline
    for row in rows:
        if not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int or row[0] < 0:
            raise OverlayError(f"ft_polarity_sites: invalid [bit, x, y] row {row!r}")
        bit, x, y = row
        if bit in indexed:
            raise OverlayError(f"ft_polarity_sites: duplicate bit {bit}")
        errors = []
        if not _xy([x, y], f"ft_polarity_sites bit {bit}", errors):
            raise OverlayError(errors)
        if not (0 <= x <= width and 0 <= y <= height):
            raise OverlayError(f"ft_polarity_sites: bit {bit} outside the type outline")
        indexed[bit] = row
    return indexed


def _ft_source(raw, tn):
    budgets = raw.get("budgets", {})
    groups, sites = budgets.get(FT_GROUP_TABLE), budgets.get(FT_SITE_TABLE)
    if not isinstance(groups, dict) or not isinstance(sites, dict):
        raise OverlayError("ft_polarity_sites: existing group and site tables are required")
    group = groups.get(tn)
    if not isinstance(group, str) or re.fullmatch(S.FT_POLARITY_GROUP_PATTERN, group) is None:
        raise OverlayError("ft_polarity_sites: an existing exact native group is required")
    return group, _ft_sites(sites.get(tn), raw["partition_types"][tn]["outline_um"])


def _apply_ft_sites(new, tn, edits):
    if not isinstance(edits, dict) or set(edits) != {"group", "sites"}:
        raise OverlayError("ft_polarity_sites: expected only group and sites")
    group, rows = _ft_source(new, tn)
    if edits["group"] != group:
        raise OverlayError("ft_polarity_sites: group does not match the bound plan selector")
    replacement = _ft_sites(edits["sites"], new["partition_types"][tn]["outline_um"])
    if replacement.keys() - rows.keys():
        raise OverlayError("ft_polarity_sites: edit names a bit absent from the bound plan")
    for bit, row in replacement.items():
        rows[bit][1:] = row[1:]


def apply_overlay(raw, ov):
    """Deep copy of `raw` with the overlay applied.  Raises OverlayError on any key outside the positions-only allowlist,
    an unknown instance, a changed station count, a point outside the outline or an invalid orient."""
    errs = []
    if not isinstance(ov, dict):
        raise OverlayError("overlay is not an object")
    if ov.get("format") != FORMAT:
        errs.append(f"format must be {FORMAT!r}")
    for k in sorted(set(ov) - TOP_KEYS):
        why = {"ports": "ports", "lanes": "lanes", "latency": "latency", "outline_um": "outline", "die": "die",
               "buses": "ports", "partitions": "partitions"}.get(k, "not a positions-only key")
        errs.append(f"overlay key {k!r} rejected: {why} (positions-only intra-type deltas only)")
    tn = ov.get("type")
    types = raw.get("partition_types", {})
    if tn not in types:
        errs.append(f"type {tn!r} is not a partition type of the plan")
    if errs:
        raise OverlayError(errs)
    base_sha = ov.get("base_plan_sha256")
    if "ft_polarity_sites" in ov and base_sha is None:
        raise OverlayError("ft_polarity_sites: exact base_plan_sha256 is required")
    if base_sha is not None and base_sha != plan_sha(raw):
        raise OverlayError(f"base_plan_sha256 {str(base_sha)[:12]} != the loaded plan {plan_sha(raw)[:12]} "
                           "(overlay was made against another bound plan)")
    new = copy.deepcopy(raw)
    t = new["partition_types"][tn]
    W, H = t["outline_um"]

    def place(kind, key, allowed, edits):
        rows = _rows(t, key)
        if not isinstance(edits, dict):
            errs.append(f"{kind}: expected an object {{inst: {{...}}}}")
            return
        for inst, e in sorted(edits.items()):
            if inst not in rows:
                errs.append(f"{kind} {inst!r}: not a {key} instance of type {tn}")
                continue
            if not isinstance(e, dict) or not e:
                errs.append(f"{kind} {inst!r}: empty or not an object")
                continue
            for k in sorted(set(e) - set(allowed)):
                errs.append(f"{kind} {inst!r}: key {k!r} rejected" + (" (CORE-SHAPE FREEZE: an overlay moves or rotates cores only, never changes an outline)" if k == "outline_um" else "") + f" (allowed: {', '.join(allowed)}; "
                            "outline_um, ports, module, params, pins, bind are never overlay keys)")
            for i in rows[inst]:
                row = t[key][i]
                for k in allowed:
                    if k not in e:
                        continue
                    v = e[k]
                    if k == "orient":
                        if v not in S.ORIENTS:
                            errs.append(f"{kind} {inst!r}: orient {v!r} not in {list(S.ORIENTS)}")
                            continue
                    elif not _xy(v, f"{kind} {inst!r}.{k}", errs):
                        continue
                    row[k] = list(v) if k != "orient" else v
                ow = row.get("outline_um")
                org = row.get("origin_um")
                if ow and org and "origin_um" in e:
                    off = row.get("track_offset_um") or [0.0, 0.0]
                    x0, y0 = org[0] + off[0], org[1] + off[1]
                    if x0 < -EPS or y0 < -EPS or x0 + ow[0] > W + EPS or y0 + ow[1] > H + EPS:
                        errs.append(f"{kind} {inst!r}: placed box [{x0:g},{y0:g},{x0 + ow[0]:g},{y0 + ow[1]:g}] "
                                    f"leaves the type outline {W:g}x{H:g}")

    place("hard_core", "hard_cores", HC_KEYS, ov.get("hard_cores") or {})
    place("content", "contents", CONTENT_KEYS, ov.get("contents") or {})
    for dotted, val in sorted((ov.get("type_positions") or {}).items()):
        if not POS_PATHS.match(dotted):
            errs.append(f"type_positions {dotted!r} rejected (allowed: tap_um / taps[].xy / edge_clocks[].tap_um / collector "
                        "relay xy / count_straps[].sites_um / reset.tap_um / ft_slots[].regs_um|bit_sites_um)")
            continue
        node, ok = t, True
        parts = [int(x) if x.isdigit() else x for x in dotted.split(".")]
        for k in parts[:-1]:
            try:
                node = node[k]
            except (KeyError, IndexError, TypeError):
                ok = False
                break
        if not ok or not isinstance(node, dict) or parts[-1] not in node:
            errs.append(f"type_positions {dotted!r}: the plan has no such site (adding one is a plan event)")
            continue
        if _shape_of(val) != _shape_of(node[parts[-1]]):
            errs.append(f"type_positions {dotted!r}: shape {_shape_of(val)} != plan {_shape_of(node[parts[-1]])}")
            continue
        pts = list(_points(val))
        if _scalars(val) != 2 * len(pts):
            errs.append(f"type_positions {dotted!r}: expected [x, y] numbers, got {val!r}")
            continue
        if not all(_xy(p, f"type_positions {dotted!r}", errs) for p in pts):
            continue
        if any(not (-EPS <= p[0] <= W + EPS and -EPS <= p[1] <= H + EPS) for p in pts):
            errs.append(f"type_positions {dotted!r}: point outside the type outline {W:g}x{H:g}")
            continue
        node[parts[-1]] = copy.deepcopy(val)
    # PLACE-GROUP (FABLE-FIX-CONE-SCATTER 11-22): "place_regions": [rows] REPLACES partition_types[T].place_regions ([] removes it).
    # The key is read by gen_phys install_place_regions only (place_regions.tcl at global place): no bind / RTL / G0 input, so it rides
    # on the bound plan like a position; its rows are schema-checked with the type (validate_overlay step 1).
    if "place_regions" in ov:
        pr = ov["place_regions"]
        if not isinstance(pr, list) or not all(isinstance(r, dict) for r in pr):
            errs.append("place_regions: expected a list of rows (partition_types.<type>.place_regions form)")
        elif pr:
            t["place_regions"] = copy.deepcopy(pr)
        else:
            t.pop("place_regions", None)
    sts = ov.get("internal_stations") or {}
    if not isinstance(sts, dict):
        errs.append("internal_stations: expected {index: {...}}")
        sts = {}
    for idx, e in sorted(sts.items()):
        try:
            i = int(idx)
            row = t["internal_stations"][i]
        except (ValueError, IndexError, KeyError):
            errs.append(f"internal_stations[{idx}]: no such station row on type {tn}")
            continue
        if not isinstance(e, dict) or not e:
            errs.append(f"internal_stations[{idx}]: empty or not an object")
            continue
        if "conn" in e and e["conn"] != row.get("conn"):
            errs.append(f"internal_stations[{idx}]: conn {e['conn']!r} != plan {row.get('conn')!r}")
        for k in sorted(set(e) - set(STATION_KEYS) - {"conn"}):
            errs.append(f"internal_stations[{idx}]: key {k!r} rejected (allowed: {', '.join(STATION_KEYS)}; the "
                        "endpoints, bits, launch/capture and face_bit_sites_um sit on ports and are not positions-only)")
        for k in STATION_KEYS:
            if k not in e:
                continue
            if k not in row:
                errs.append(f"internal_stations[{idx}].{k}: the plan row has none (adding a station site is a plan event)")
                continue
            if _shape_of(e[k]) != _shape_of(row[k]):
                errs.append(f"internal_stations[{idx}].{k}: shape {_shape_of(e[k])} != plan {_shape_of(row[k])} "
                            "(station count / bank layout is latency and RTL: plan event)")
                continue
            pts = list(_points(e[k]))
            if not all(_xy(p, f"internal_stations[{idx}].{k}", errs) for p in pts):
                continue
            for p in pts:
                if not (-EPS <= p[0] <= W + EPS and -EPS <= p[1] <= H + EPS):
                    errs.append(f"internal_stations[{idx}].{k}: point {p} outside the type outline {W:g}x{H:g}")
                    break
            row[k] = copy.deepcopy(e[k])
    if errs:
        raise OverlayError(errs)
    if "ft_polarity_sites" in ov:
        _apply_ft_sites(new, tn, ov["ft_polarity_sites"])
    return new


# ---------------------------------------------------------------- plan -> overlay (reject anything else)
def _diff(a, b, path=()):
    if type(a) is not type(b):
        yield path
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                yield path + (k,)
            else:
                yield from _diff(a[k], b[k], path + (k,))
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                yield from _diff(x, y, path + (i,))
    elif a != b:
        yield path


def _is_note(path, tn):
    """free-text `note` keys (plan level, type level, rows of this type): documentation, no kit input"""
    return bool(path) and path[-1] == "note" and (len(path) == 1 or path[:2] == ("partition_types", tn))


def _is_place_regions(path, tn):
    """PLACE-GROUP: partition_types[tn].place_regions (any depth): a kit-only key (gen_phys install_place_regions)"""
    return len(path) >= 3 and path[0] == "partition_types" and path[1] == tn and path[2] == "place_regions"


def pk_parts(dotted):
    return [int(x) if x.isdigit() else x for x in dotted.split(".")]


def _get(raw, path):
    for k in path:
        raw = raw[k]
    return raw


def pos_key(path, tn):
    """dotted type_positions key covering a changed-leaf `path`, or None"""
    if len(path) < 4 or path[0] != "partition_types" or path[1] != tn:
        return None
    tail = path[2:]
    for i, k in enumerate(tail):
        if k in POS_LEAF:
            d = ".".join(str(x) for x in tail[:i + 1])
            return d if POS_PATHS.match(d) else None
    return None


def _is_ft_site_position(path, tn):
    return (len(path) == 5 and path[:3] == ("budgets", FT_SITE_TABLE, tn)
            and isinstance(path[3], int) and path[4] in (1, 2))


def _ft_site_delta(base, new, tn, indices):
    old_group, old_rows = _ft_source(base, tn)
    group, rows = _ft_source(new, tn)
    if old_group != group or list(old_rows) != list(rows):
        raise OverlayError("ft_polarity_sites: group and ordered bit selectors must match the bound plan")
    ordered = list(rows.values())
    return {"group": group, "sites": [ordered[i] for i in sorted(indices)]}


def _category(path):
    if not path:
        return "plan"
    if path[0] in ("ports", "lanes", "latency", "die", "partitions", "clock", "reset", "budgets"):
        return {"ports": "ports", "lanes": "lanes", "latency": "latency", "die": "die/outline"}.get(path[0], path[0])
    if path[0] == "partition_types" and len(path) > 2:
        return {"outline_um": "outline (CORE-SHAPE FREEZE)", "buses": "ports", "module": "RTL"}.get(path[2], path[2])
    return str(path[0])


def overlay_from_plans(base, new, tn):
    """The overlay equivalent to `new` against `base`; OverlayError listing every changed path outside the allowlist."""
    errs, hc, ct, st, tp = [], {}, {}, {}, {}
    prx = None
    ft_indices = set()
    for path in _diff(base, new):
        ok = False
        if _is_note(path, tn):           # the plan's free-text note: documentation, no kit input
            continue
        if _is_place_regions(path, tn):  # PLACE-GROUP: the whole row list rides in the overlay
            prx = copy.deepcopy(new["partition_types"][tn].get("place_regions") or [])
            continue
        if _is_ft_site_position(path, tn):
            ft_indices.add(path[3])
            continue
        pk = pos_key(path, tn)
        if pk:
            tp[pk] = _get(new, ("partition_types", tn) + tuple(pk_parts(pk)))
            continue
        if len(path) >= 5 and path[0] == "partition_types" and path[1] == tn and isinstance(path[3], int):
            t = base["partition_types"][tn]
            kind, i, k = path[2], path[3], path[4]
            if kind == "hard_cores" and k in HC_KEYS:
                hc.setdefault(t["hard_cores"][i]["inst"], {})[k] = new["partition_types"][tn]["hard_cores"][i][k]
                ok = True
            elif kind == "contents" and k in CONTENT_KEYS:
                ct.setdefault(t["contents"][i]["inst"], {})[k] = new["partition_types"][tn]["contents"][i][k]
                ok = True
            elif kind == "internal_stations" and k in STATION_KEYS:
                st.setdefault(str(i), {})[k] = new["partition_types"][tn]["internal_stations"][i][k]
                ok = True
        if not ok:
            errs.append(f"{_category(path)}: {'.'.join(str(p) for p in path)} changed (not a positions-only intra-type key)")
    if errs:
        raise OverlayError(errs)
    ov = {"format": FORMAT, "type": tn, "base_plan_sha256": plan_sha(base)}
    for k, v in (("hard_cores", hc), ("contents", ct), ("internal_stations", st), ("type_positions", tp)):
        if v:
            ov[k] = v
    if prx is not None:
        ov["place_regions"] = prx
    if ft_indices:
        ov["ft_polarity_sites"] = _ft_site_delta(base, new, tn, ft_indices)
    return ov


# ---------------------------------------------------------------- EQ by construction: derived RTL inputs
def _strip_xy(o):
    if isinstance(o, dict):
        return {k: _strip_xy(v) for k, v in o.items() if k not in ("xy", "xy_um", "sites", "site_um")}
    if isinstance(o, list):
        return [_strip_xy(v) for v in o]
    return o


def rtl_projection(raw, tn, plan_path=None):
    """What bind / gen_rtl derive from the type's placement: clock tap and core tap names, the reset tree structure
    (coordinates stripped) and the reset-gate tap each hard core binds to.  Overlay must leave it identical."""
    P = S.Plan(raw, plan_path)
    out = {"taps": [n for n, _x, _y in S.tap_grid(P, tn)],
           "core_taps": [(n, tp.get("name")) for n, _x, _y, tp in S.core_taps(P, tn)]}
    import reset_tree as RT
    if RT.delivered(P):
        tree = RT.for_type(P, tn)
        out["reset_tree"] = _strip_xy(tree)
        gates = {}
        if tree:
            import bind_core_split as BCS
            for h in P.types[tn].get("hard_cores") or []:
                (w, hh), o = h["outline_um"], h["origin_um"]
                try:
                    gates[h["inst"]] = BCS.gate_tap(tree["relays"], (o[0] + w / 2, o[1] + hh / 2), RT.consumer_count(tree))
                except Exception as exc:        # no consumer tap etc.: same error for base and overlay is equal
                    gates[h["inst"]] = f"ERR {type(exc).__name__}"
        out["reset_gate_taps"] = gates
    return json.loads(json.dumps(out, sort_keys=True, default=str))


# ---------------------------------------------------------------- type-scoped validation
def type_lanes(P, tn):
    parts = {n for n, p in P.parts.items() if p["type"] == tn}
    return sorted(lid for lid, ln in P.lanes.items()
                  if any({P.ports[x]["src"]["part"], P.ports[x]["dst"]["part"]} & parts for x in ln["ports"]))


def seam_rows(raw, tn, plan_path=None):
    import check as C
    import seam_hop as SH
    P = S.Plan(raw, plan_path)
    geo = {lid: C.lane_geometry(P, lid) for lid in type_lanes(P, tn)}
    return {(r["lane"], r["port"]): r for r in SH.seam_hops(P, geo)}


G0_SUBSET = ("check_types", "check_core_pg", "check_taps_cores", "check_core_faces", "check_geometry")


def g0_errors(raw, tn, full=False, plan_path=None):
    """{(check, msg)} ERROR items of the type-scoped G0 subset (or the whole check.run with full=True) that name the type
    or one of its lanes."""
    import check as C
    if full:
        R, _ = C.run(raw, seam_hop="off", plan_dir=str(Path(plan_path).parent) if plan_path else None)
    else:
        R = C.Report(True)
        P = S.Plan(raw, plan_path)
        pd = str(Path(plan_path).parent) if plan_path else None
        for name in G0_SUBSET:
            try:
                fn = getattr(C, name)
                if name == "check_taps_cores":
                    fn(P, R, pd, None)
                elif name == "check_core_faces":
                    fn(P, R, pd, None)
                elif name == "check_core_pg":
                    fn(P, R, pd)
                else:
                    fn(P, R)
            except Exception as exc:
                R.err(name, f"type {tn}: {name} raised {type(exc).__name__}: {exc}")
    P = S.Plan(raw, plan_path)
    lanes = set(type_lanes(P, tn))
    return {(i["check"], i["msg"]) for i in R.items
            if i["level"] == "ERROR" and (tn in i["msg"] or i.get("type") == tn or i.get("lane") in lanes)}


# G0-DRIFT-1125 (COORD; KV-OWN-PV V1NSITE): G0 findings are matched on (check, key), not on exact text.  The key is the
# message with its directional metrics masked: 'cos <x>' (lower is worse, core_faces mean cos) and '<x> um' (larger is
# worse: hops, overlaps).  Every other number (pin counts, coordinates, indices) stays in the key, as before.  A finding is
# new when its key is new, its key occurs more often, or a metric gets worse by more than the tolerance; a metric that only
# drifts (better, or worse within the tolerance) is reported in the receipt (g0_metric_drift), never an overlay error.
# Real case: kv3_pv_v1n V1NSITE moved stations 12 um and 5 pre-existing core_faces ERRORs re-printed with cos -0.34 -> -0.33
# (-0.20 -> -0.19, -0.66 -> -0.64): exact text called them new and blocked the overlay.
_G0_METRIC = re.compile(r"(?P<cos>(?<=cos )[-+]?\d+(?:\.\d+)?)|(?P<um>(?<![\w.\[])[-+]?\d+(?:\.\d+)?(?=\s?um\b))")
G0_COS_TOL = 0.05
G0_UM_TOL = 1.0
G0_UM_REL = 0.02


def g0_key(msg):
    """(masked message, [(kind, value)]) -- kind 'cos' (lower is worse) or 'um' (larger is worse)"""
    metrics = []

    def sub(m):
        kind = "cos" if m.group("cos") is not None else "um"
        metrics.append((kind, float(m.group(0))))
        return "<" + kind + ">"
    return _G0_METRIC.sub(sub, msg), metrics


def _worse(old, new):
    """how much new is worse than old beyond the tolerance (0 = not worse past it); same kinds by position"""
    w = 0.0
    for (k, a), (_, b) in zip(old, new):
        d = (a - b) if k == "cos" else (b - a)
        tol = G0_COS_TOL if k == "cos" else max(G0_UM_TOL, G0_UM_REL * abs(a))
        if d > tol + 1e-9:
            w = max(w, d)
    return w


def g0_new(old_e, new_e):
    """(new findings [(check, msg, base msg or None)], drift [(check, base msg, msg)]) of G0 ERROR sets {(check, msg)}"""
    def group(E):
        g = {}
        for c, m in E:
            k, mt = g0_key(m)
            g.setdefault((c, k), []).append((mt, m))
        return {k: sorted(v) for k, v in g.items()}
    go, gn = group(old_e), group(new_e)
    new, drift = [], []
    for key, rows in sorted(gn.items()):
        base = go.get(key, [])
        for i, (mt, m) in enumerate(rows):
            if i >= len(base):
                new.append((key[0], m, None))
                continue
            bmt, bm = base[i]
            if bm == m:
                continue
            if _worse(bmt, mt):
                new.append((key[0], m, bm))
            else:
                drift.append((key[0], bm, m))
    return new, drift


def _skip(skipped, check, why):
    """a check that cannot run is never silent: WARN line on stderr and an entry in the result record"""
    print(f"TYPE_OVERLAY WARN skipped check {check}: {why}", file=sys.stderr)
    if skipped is not None:
        skipped.append({"check": check, "why": why})


def validate_overlay(base, new, tn, g0_full=False, plan_path=None, skipped=None, drift=None):
    """All type-scoped checks of the overlaid plan `new` against the bound plan `base`; list of error strings."""
    errs, ft_indices = [], set()
    for path in _diff(base, new):
        if _is_ft_site_position(path, tn):
            ft_indices.add(path[3])
        elif not (_is_note(path, tn) or pos_key(path, tn) or _is_place_regions(path, tn)
                  or (len(path) >= 5 and path[:2] == ("partition_types", tn) and isinstance(path[3], int)
                      and path[4] in HC_KEYS + CONTENT_KEYS + STATION_KEYS)):
            errs.append(f"changed outside the allowlist: {'.'.join(map(str, path))}")
    if ft_indices and not errs:
        try:
            _ft_site_delta(base, new, tn, ft_indices)
        except OverlayError as exc:
            errs.extend(exc.errors)
    if errs:
        return errs
    # CORE-SHAPE FREEZE: no outline of the type or of any core/content may differ (rotation keeps the footprint)
    for key in ("hard_cores", "contents"):
        for r0, r1 in zip(base["partition_types"][tn].get(key) or [], new["partition_types"][tn].get(key) or []):
            if r0.get("outline_um") != r1.get("outline_um"):
                errs.append(f"CORE-SHAPE FREEZE: {key} {r0.get('inst')} outline_um changed")
    if base["partition_types"][tn]["outline_um"] != new["partition_types"][tn]["outline_um"]:
        errs.append("CORE-SHAPE FREEZE: type outline_um changed")
    # 1. schema + local consistency, only this type (and the ports/lanes touching it)
    e_new = S.scope_errors_typed(S.validate(new), [tn], new)
    if e_new:
        e_old = set(S.scope_errors_typed(S.validate(base), [tn], base))
        errs += [f"schema: {e}" + ("" if e in e_old else " [new]") for e in e_new]
    # 2. EQ by construction
    try:
        a, b = rtl_projection(base, tn, plan_path), rtl_projection(new, tn, plan_path)
    except Exception as exc:
        return errs + [f"rtl_projection failed ({type(exc).__name__}: {exc}): cannot prove the RTL unchanged"]
    if a != b:
        keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        errs.append(f"RTL inputs change with the placement ({', '.join(keys)}): reset tree / tap names / reset-gate taps "
                    "must be identical to the bound plan's; this is a plan event, not an overlay")
    # 3. collector_reach (G0 ERROR) on the type itself
    try:
        import collector_reach as CR
    except ImportError:         # a wave source older than SEAM-HOP-1 has no collector_reach rule (bind enforces it)
        CR = None
        _skip(skipped, "collector_reach", "module collector_reach.py is not in this source")
    for r in (CR.type_findings(tn, new["partition_types"][tn]) if CR else []):
        errs.append(f"collector_reach: {r['kind']} {r['src']}->{r['dst']} {r['hop_um']:.3f}um exceeds {CR.REACH_UM:g}")
    # 4. seam_hop on this type's lanes: no hop may get worse, none may become over the limit
    try:
        import seam_hop  # noqa: F401  (absent in a source older than SEAM-HOP-1: advisory check skipped)
        sb, sn = seam_rows(base, tn, plan_path), seam_rows(new, tn, plan_path)
        for k, r in sorted(sn.items()):
            b0 = sb.get(k)
            if r["over"] and (b0 is None or not b0["over"] or r["hop_um"] > b0["hop_um"] + 0.05):
                errs.append(f"seam_hop lane {r['lane']} {r['src']}->{r['dst']}: {r['hop_um']:.1f}um > {r['limit_um']:g} um"
                            + ("" if b0 is None else f" (bound plan {b0['hop_um']:.1f})"))
    except ImportError:
        _skip(skipped, "seam_hop", "module seam_hop.py is not in this source")
    except Exception as exc:
        errs.append(f"seam_hop check failed ({type(exc).__name__}: {exc})")
    # 5. G0 subset: no new ERROR naming the type or its lanes (matched by (check, key); G0-DRIFT-1125 above)
    nw, dr = g0_new(g0_errors(base, tn, g0_full, plan_path), g0_errors(new, tn, g0_full, plan_path))
    for c, m, bm in nw:
        errs.append(f"G0 {c}: {m}" + ("" if bm is None else f" (worse than the bound plan's: {bm})"))
    for c, bm, m in dr:
        print(f"TYPE_OVERLAY NOTE G0 {c} metric drift within tolerance or better (report only): {bm} -> {m}", file=sys.stderr)
        if drift is not None:
            drift.append({"check": c, "base": bm, "overlay": m})
    return errs


def apply_validated(raw, ov, g0_full=False, plan_path=None):
    """(overlaid plan, receipt).  The single entry point of gen_phys --type-overlay and the CLI."""
    new = apply_overlay(raw, ov)
    tn = ov["type"]
    skipped, drift = [], []
    errs = validate_overlay(raw, new, tn, g0_full, plan_path, skipped, drift)
    if errs:
        raise OverlayError(errs)
    changed = {k: sorted(ov[k]) for k in ("hard_cores", "contents", "internal_stations", "type_positions") if ov.get(k)}
    if "ft_polarity_sites" in ov:
        changed["ft_polarity_sites"] = sorted(row[0] for row in ov["ft_polarity_sites"]["sites"])
    if "place_regions" in ov:
        changed["place_regions"] = sorted(r.get("name", "?") for r in ov["place_regions"])
    return new, {"format": FORMAT, "type": tn, "base_plan_sha256": plan_sha(raw), "overlaid_plan_sha256": plan_sha(new),
                 "changed": changed, "checks": [c for c in ("allowlist", "schema(type-scoped)", "rtl_projection", "collector_reach",
                                                        "seam_hop", "g0_full" if g0_full else "g0_subset")
                           if c not in {x["check"] for x in skipped}],
                 "skipped_checks": skipped, "g0_metric_drift": drift}


# The controller's prepare-stations and generator consume the same validated
# overlay on one pinned launch tree. Keep this receipt beside their work so
# individual gen invocations still validate their own overlay by default.
_PREPARED_TYPE_OVERLAY = "kit-wave-prepared-type-overlay.v1"
_PREPARED_TOOLS = ("type_overlay.py", "gen.py", "gen_phys.py", "schema.py",
                   "reset_tree.py", "check.py", "cbc_rules.py")
_PREPARED_ENV = ("OT_REPO_ROOT", "OT_PLAN_ROOT", "OT_CBC_REACH_UM",
                 "OT_RESET_HOP_CAP_UM", "OT_FT_IN_BUDGET", "OT_RESETPUB_SOLVE")


def _file_stamp(path):
    p = Path(path).resolve(strict=True)
    st = p.stat()
    return [str(p), st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def _prepared_context(plan, overlay):
    return {"plan": _file_stamp(plan), "overlay": _file_stamp(overlay),
            "tools": [_file_stamp(HERE / name) for name in _PREPARED_TOOLS],
            "launch_tree": str(Path.cwd().resolve()),
            "env": {k: os.environ.get(k) for k in _PREPARED_ENV}}


def _write_preparation(path, before, plan, overlay, prepared, receipt):
    after = _prepared_context(plan, overlay)
    if before != after:
        return False
    doc = {"format": _PREPARED_TYPE_OVERLAY, "inputs": after,
           "prepared": _file_stamp(prepared), "receipt": receipt}
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(doc, sort_keys=True) + "\n")
    tmp.replace(path)
    return True


def read_prepared(raw, ov, plan, overlay, path, work):
    """Reuse one exact authenticated kit-wave preparation, or validate normally."""
    if os.environ.get("OT_KIT_WAVE") != "1" or not plan or not isinstance(overlay, (str, Path)):
        return None
    try:
        proof = Path(path).resolve(strict=True)
        if proof.parent != Path(work).resolve():
            return None
        prepared = proof.with_name("plan_overlaid.json")
        context = _prepared_context(plan, overlay)
        stamp = _file_stamp(prepared)
        value = load_json(proof)
        receipt = value["receipt"]
        required = {"allowlist", "schema(type-scoped)", "rtl_projection", "g0_subset"}
        if (value["format"] != _PREPARED_TYPE_OVERLAY or value["inputs"] != context
                or value["prepared"] != stamp or receipt["format"] != FORMAT
                or receipt["type"] != ov["type"] or not required.issubset(receipt["checks"])):
            return None
        new = load_json(prepared)
        # The cheap semantic application also binds the prepared result to the
        # precise raw input already loaded by gen. No additional file hashing.
        if new != apply_overlay(raw, ov):
            return None
        if _file_stamp(prepared) != stamp or _prepared_context(plan, overlay) != context:
            return None
        return new, receipt
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverlayError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diff")
    d.add_argument("base")
    d.add_argument("new")
    d.add_argument("--type", required=True)
    d.add_argument("--out", required=True)
    for n in ("check", "apply"):
        c = sub.add_parser(n)
        c.add_argument("base")
        c.add_argument("overlay")
        c.add_argument("--g0-full", action="store_true")
        if n == "apply":
            c.add_argument("--out", required=True)
            c.add_argument("--prepared-receipt", help="record kit-wave reuse of this validated application")
    a = ap.parse_args(argv)
    try:
        prepare = getattr(a, "prepared_receipt", None)
        before = _prepared_context(a.base, a.overlay) if prepare else None
        base = load_json(a.base)
        if a.cmd == "diff":
            ov = overlay_from_plans(base, load_json(a.new), a.type)
            new, rec = apply_validated(base, ov, plan_path=a.base)
            Path(a.out).write_text(json.dumps(ov, indent=1, sort_keys=True) + "\n")
            print("TYPE_OVERLAY OK", json.dumps(rec["changed"]))
            return 0
        ov = load_json(a.overlay)
        if prepare:
            # Match gen's plan-addressed reset cap during the checked preparation.
            import cbc_rules
            with cbc_rules.bound_reset_hop_cap(cbc_rules.plan_reset_hop_cap(a.base)):
                new, rec = apply_validated(base, ov, a.g0_full, plan_path=a.base)
        else:
            new, rec = apply_validated(base, ov, a.g0_full, plan_path=a.base)
        if a.cmd == "apply":
            Path(a.out).write_text(json.dumps(new, indent=1) + "\n")
            if prepare and _write_preparation(prepare, before, a.base, a.overlay, a.out, rec):
                print("TYPE_OVERLAY PREPARED")
        print("TYPE_OVERLAY OK", json.dumps(rec))
        return 0
    except OverlayError as e:
        print(e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
