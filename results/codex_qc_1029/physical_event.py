#!/usr/bin/env python3
"""QC post-compose physical delta: align existing same-region START relay pins.

No ports, cells, registers, clocks, latency or CA settings are changed. Pin
placement remains subject to the eventual kit's internal reach/geometry review.
Native predecessor cell estimates and IO sidecars are carried to the composed
types, with landing-ring accounting left to the normal cells.py estimator.
"""
import argparse
import copy
import json
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def align(plan, tools):
    sys.path.insert(0, str(tools))
    import schema as S
    import gen_phys as GP
    result = copy.deepcopy(plan)
    physical = S.Plan(result)
    requests = defaultdict(set)
    edges = [edge for edge in physical.clock["landing_network"]["edges"]
             if edge["id"].startswith("cland_relay__")]
    before = []
    for edge in edges:
        src, dst = edge["src"]["part"], edge["dst"]["part"]
        a, b = physical.rect(src), physical.rect(dst)
        y0, y1 = max(a[1], b[1]), min(a[3], b[3])
        x0, x1 = max(a[0], b[0]), min(a[2], b[2])
        if abs(a[2]-b[0]) < 1e-6 and y1 > y0:
            points = [(a[2]-2.16, (y0+y1)/2), (b[0]+2.16, (y0+y1)/2)]
        elif abs(b[2]-a[0]) < 1e-6 and y1 > y0:
            points = [(a[0]+2.16, (y0+y1)/2), (b[2]-2.16, (y0+y1)/2)]
        elif abs(a[3]-b[1]) < 1e-6 and x1 > x0:
            points = [((x0+x1)/2, a[3]-2.16), ((x0+x1)/2, b[1]+2.16)]
        elif abs(b[3]-a[1]) < 1e-6 and x1 > x0:
            points = [((x0+x1)/2, a[1]+2.16), ((x0+x1)/2, b[3]-2.16)]
        else:
            raise ValueError(f"relay {edge['id']} does not connect abutting partitions")
        old = []
        for side, point in zip(("src", "dst"), points):
            part, name = edge[side]["part"], edge[side]["bus"]
            tn = physical.parts[part]["type"]
            pins = physical.types[tn]["clock"]["landing_contract"]["pins"]
            pin = next(pin for pin in pins if pin["name"] == name)
            old.append(physical.to_die(part, pin["xy_um"]))
            local = physical.to_type(part, point)
            snapped = tuple(round(value, 6) for value in GP._snap_tap(physical, *local))
            requests[(tn, name)].add(snapped)
        before.append(dict(edge=edge["id"], hop_um=sum(abs(x-y) for x,y in zip(*old))))
    changes = []
    for (tn, name), points in sorted(requests.items()):
        w, h = physical.types[tn]["outline_um"]
        def face(point):
            x,y = point
            return min((x,"W"),(w-x,"E"),(y,"S"),(h-y,"N"))[1]
        if len({face(point) for point in points}) != 1:
            raise ValueError(f"type pin needs different faces: {tn}.{name}: {points}")
        # Different neighbour widths can shift an overlap midpoint slightly.
        # Pick one type-uniform point, then require every resulting real hop
        # to pass reach. Never manufacture per-instance master pin locations.
        point = list(GP._snap_tap(physical,
            statistics.median(point[0] for point in points),
            statistics.median(point[1] for point in points)))
        pins = physical.types[tn]["clock"]["landing_contract"]["pins"]
        pin = next(pin for pin in pins if pin["name"] == name)
        collisions = [other["name"] for other in pins
                      if other["name"] != name and other.get("layer") == pin.get("layer")
                      and abs(other["xy_um"][0]-point[0]) < .08
                      and abs(other["xy_um"][1]-point[1]) < .432]
        if collisions:
            raise ValueError(f"new relay pin overlaps infrastructure pins: {tn}.{name} {collisions}")
        changes.append(dict(type=tn, pin=name, old_xy_um=pin["xy_um"], new_xy_um=point))
        pin["xy_um"] = point
    after = []
    for edge in edges:
        points = []
        for side in ("src", "dst"):
            part, name = edge[side]["part"], edge[side]["bus"]
            pins = physical.ptype(part)["clock"]["landing_contract"]["pins"]
            points.append(physical.to_die(part, next(pin["xy_um"] for pin in pins if pin["name"] == name)))
        hop = sum(abs(x-y) for x,y in zip(*points))
        if hop > 405:
            raise ValueError(f"relay still exceeds reach: {edge['id']} {hop}")
        after.append(dict(edge=edge["id"], hop_um=round(hop,6)))
    assert result["ports"] == plan["ports"] and result["lanes"] == plan["lanes"]
    assert result["latency"] == plan["latency"]
    return result, dict(changes=changes, before=before, after=after,
                        data_cycles_added=0, boot_cycles_added=0,
                        internal_pin_register_reach="NOT RUN; requires actual kit placement")


def carry_evidence(base_path, plan, out, tools):
    sys.path.insert(0, str(tools))
    import cells
    base = json.loads(base_path.read_text())
    estimates, sources = cells.estimate(base, base_path.parent)
    old_parts = {part["name"]: part["type"] for part in base["partitions"]}
    by_type = defaultdict(set)
    for part in plan["partitions"]:
        by_type[part["type"]].add(old_parts[part["name"]])
    rows = {}
    for tn, originals in sorted(by_type.items()):
        values = []
        for original in originals:
            value, basis = estimates[original]
            if basis != "plan":
                value -= cells.landing_rings(base["partition_types"][original])
            values.append(value)
        if len(set(values)) != 1:
            raise ValueError(f"merged cohort has unequal native cell estimates: {tn} {values}")
        rows[tn] = dict(cells=values[0], base_types=sorted(originals),
                        basis="native predecessor estimate excluding predecessor landing rings; cells.py adds current rings")
    (out/"cells_est.json").write_text(json.dumps(dict(cells_per_type=rows, sources=sources), indent=1)+"\n")
    shutil.copyfile(base_path.parent/"die_io.json", out/"die_io.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result, receipt = align(json.loads(args.plan.read_text()), args.tools)
    carry_evidence(args.base, result, args.out, args.tools)
    (args.out/"plan.json").write_text(json.dumps(result, indent=1)+"\n")
    (args.out/"relay_pins.json").write_text(json.dumps(receipt, indent=1)+"\n")
    print("QC_PHYSICAL_EVENT", len(receipt["changes"]), "uniform type pins;",
          len(receipt["after"]), "relay edges; max hop",
          max(row["hop_um"] for row in receipt["after"]), "um; 0 added cycles")
