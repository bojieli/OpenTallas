"""Re-seat anchored local FSTART reset copies without editing their raw authority."""

import argparse
import copy
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clock_landings import ring_reset_fan_um, ring_reset_load_xy
from hub_repack import G, Raster, chain_metrics
from landing_place import _origin_home_groups, _reader_start_groups, _status_reset_groups, _writer_start_groups
from placement_obstacles import placement_boxes
from reach_rules import HALF_CYCLE_CELLS, HALF_REACH_UM, REACH_UM
import reset_anchor
import reset_tree
import schema

CLEARANCE = G / 2


def _distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _choose_site(raster, old, source, targets, blocked, incoming_cap, outgoing_cap):
    """Find the nearest legal site to the old copy within both routed reach limits."""
    def span(coord, limit):
        return range(math.ceil(max(G, coord - incoming_cap) / G),
                     math.floor(min(limit - G, coord + incoming_cap) / G) + 1)

    def hits_site(site):
        x, y = site
        return any(a - CLEARANCE <= x <= c + CLEARANCE
                   and b - CLEARANCE <= y <= d + CLEARANCE for a, b, c, d in blocked)

    choices = []
    for i in span(source[0], raster.W):
        for j in span(source[1], raster.H):
            xy = (round(i * G, 3), round(j * G, 3))
            if not raster.free(*xy) or hits_site(xy) or _distance(source, xy) > incoming_cap:
                continue
            longest = max(_distance(xy, target) for target in targets)
            if longest <= outgoing_cap:
                choices.append((_distance(xy, old), longest, xy))
    for _, _, xy in sorted(choices):
        incoming, _ = chain_metrics(raster, [source, xy])
        if incoming > incoming_cap:
            continue
        outgoing = max(chain_metrics(raster, [xy, target])[0] for target in targets)
        if outgoing <= outgoing_cap:
            return xy, round(incoming, 3), round(outgoing, 3)
    return None


def reseat(P, tn, root):
    """Return the per-copy result for bounded geometry changes on one type."""
    t = P.types[tn]
    clock = t.get("clock") or {}
    rows = [row for row in clock.get("landing_local_resets", [])
            if row.get("name", "").startswith("fstart_")]
    if not rows:
        return []
    tree = reset_tree.for_type(P, tn)
    anchor = clock.get(reset_anchor.KEY)
    if not anchor:
        return [{"status": "missing reset-tree anchor"}]
    resolved = reset_anchor.resolve(tn, copy.deepcopy(t), tree, root)
    if resolved["remaps"]:
        return [{"status": "reset-tree anchor must be resolved before reseating"}]

    relays = {row["q"]: row for row in tree["relays"]}
    ported = reset_anchor.ported(tree)
    sites = {row["q"]: tuple(tree.get("relay_seats", {}).get(row["name"], row["xy"]))
             for row in tree["relays"]}
    phase_rows = anchor["relays"]
    macros = list(placement_boxes(t).values())
    width, height = t["outline_um"]
    raster = Raster(width, height, macros, halo=CLEARANCE)
    bands = (clock.get("landing_contract") or {}).get("bands", {})
    blocked = [rect for band in bands.values()
               for rect in (band.get("rects_um") or [band.get("rect_um")]) if rect]
    blocked.extend(rect for groups in (_origin_home_groups(t), _reader_start_groups(t), _writer_start_groups(t),
                                        _status_reset_groups(t))
                   for _, rect, kind in groups if kind != "local-reset")
    reserved = list(sites.values()) + [(x, y) for _, x, y in schema.tap_grid(P, tn)]
    blocked.extend((x, y, x, y) for x, y in reserved)
    out_cap = ring_reset_fan_um()
    results = []
    for row in rows:
        name, raw, old = row["name"], row.get("raw"), row["xy_um"]
        result = dict(name=name, raw=raw, old_xy=old)
        results.append(result)
        if raw not in relays or raw not in phase_rows or raw in ported:
            result["status"] = "no anchored non-ported relay"
            continue
        targets = [ring_reset_load_xy(t, consumer) for consumer in row.get("consumers", [])]
        if not targets or any(point is None for point in targets):
            result["status"] = "consumer location unavailable"
            continue
        source = sites[raw]
        in_cap = min(REACH_UM, out_cap)
        if not t.get("reset_relay_full") and reset_tree.relay_cell(tree, relays[raw]) in HALF_CYCLE_CELLS:
            in_cap = HALF_REACH_UM
        result.update(depth=phase_rows[raw]["depth"], incoming_cap=in_cap, outgoing_cap=out_cap)
        previous_in, _ = chain_metrics(raster, [source, old])
        previous_out = max(chain_metrics(raster, [old, target])[0] for target in targets)
        result.update(old_incoming_um=round(previous_in, 3), old_outgoing_um=round(previous_out, 3))
        if previous_in <= in_cap and previous_out <= out_cap:
            result["status"] = "within reach"
            continue
        other_resets = [(x - CLEARANCE, y - CLEARANCE, x + CLEARANCE, y + CLEARANCE)
                        for other in clock["landing_local_resets"] if other is not row
                        for x, y in [other["xy_um"]]]
        found = _choose_site(raster, old, source, targets, blocked + other_resets, in_cap, out_cap)
        if found is None:
            result["status"] = "no legal site for existing raw relay and consumer reach"
            continue
        xy, incoming, outgoing = found
        row["xy_um"] = list(xy)
        result.update(status="reseated", new_xy=row["xy_um"], incoming_um=incoming, outgoing_um=outgoing)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--types", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.plan.resolve() == args.out.resolve():
        parser.error("output must be a separate plan")
    raw = json.loads(args.plan.read_bytes())
    P = schema.Plan(raw, str(args.plan))
    reports = {tn: reseat(P, tn, args.root) for tn in args.types.split(",")}
    args.report.write_text(json.dumps(reports, indent=2) + "\n")
    args.out.write_text(json.dumps(raw, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
