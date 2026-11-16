#!/usr/bin/env python3
"""S81 strap-form CA region table (DIE-S81-92, COORD 11-15 04:0x; FABLE-PD-S81-0335 B(c)).

count_align_bind --parts table / --strap-form / --straps-out needs a regions table (regions + inter-region ports).  The
HEAD builder fallback_land.table() derives each partition's region from box containment and refuses overlapping region
boxes; the S81 landed regions (part_region map of the die sidecar) are not disjoint boxes, so it stops with "region box
overlap/miss".  This builder resolves every partition by its DECLARED region (the map), never by box containment:
  - regions[]: tag, box_um (bounding box of its partitions; boxes MAY overlap, informational only), parts, members
  - part_region: {partition: region tag} (the declaration; clock_landings uses it instead of centre-in-box when present)
  - ports[]: every plan port whose src/dst partitions sit in different declared regions (same rows as fallback_land)
Fails closed when the map misses a partition, names an unknown partition, or a region has no partition.

usage: ca_region_table.py PLAN.json --regions MAP.json --out TABLE.json
"""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "s81_head"))
import fallback_land as F  # noqa: E402

SCHEMA = "opentallas.fallback_head_regions.v1"


def declared_table(plan, part_region):
    names = [p["name"] for p in plan["partitions"]]
    miss = [n for n in names if n not in part_region]
    if miss:
        raise ValueError(f"region map misses {len(miss)} partitions: {miss[:5]}")
    extra = sorted(set(part_region) - set(names))
    if extra:
        raise ValueError(f"region map names {len(extra)} partitions not in the plan: {extra[:5]}")
    reg = {n: part_region[n] for n in names}
    B = F.part_boxes(plan)
    members = collections.defaultdict(list)
    for n, tag in reg.items():
        members[tag].append(n)
    rows = []
    for tag, parts in sorted(members.items()):
        bs = [B[p] for p in parts]
        rows.append(dict(tag=tag, box_um=[min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs),
                                          max(b[3] for b in bs)], parts=len(parts), members=sorted(parts)))
    lane_of = {pid: ln["id"] for ln in plan["lanes"] for pid in ln["ports"]}
    ports = []
    for pr in plan["ports"]:
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if "@" in (a[:1] + b[:1]) or reg[a] == reg[b]:
            continue
        ports.append(dict(port=pr["id"], lane=lane_of.get(pr["id"]), src=a, dst=b, src_region=reg[a],
                          dst_region=reg[b], width=int(pr["width"]), kind=pr.get("kind", "data"), added_cycles=F.CYC))
    return dict(schema=SCHEMA, granularity="declared", region_resolution="declared (part_region), boxes may overlap",
                added_cycles_per_crossing=F.CYC, regions=rows, part_region=reg, ports=ports)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--regions", required=True, help="{part_region: {partition: region}} (or a bare map)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    m = json.loads(Path(a.regions).read_text())
    t = declared_table(plan, m.get("part_region", m))
    Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
    print(f"TABLE regions {len(t['regions'])} ports {len(t['ports'])} partitions {len(t['part_region'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
