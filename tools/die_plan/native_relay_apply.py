#!/usr/bin/env python3
"""Allocate legal sites for an explicit native_relay_plan on its actual ODB.

Default is a dry run. --out-odb writes a separate candidate only after every
move fits its declared radius, existing rows, occupancy and placement blockages.
No instance/net/port is created, removed or reconnected. Run in pinned OpenROAD
Python, then review the proposal before standard GPL/DPL and actual measurement.
"""
import argparse
from bisect import bisect_left, bisect_right
import hashlib
import json
import math
from pathlib import Path
import re


def main():
    import odb
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--odb", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--out-odb")
    a = p.parse_args()
    plan = json.loads(Path(a.plan).read_text())
    assert plan["schema"] == "opentallas.native_relay_placement.v1"
    db = odb.dbDatabase.create()
    odb.read_db(db, a.odb)
    b = db.getChip().getBlock()
    u = b.getDbUnitsPerMicron()
    insts = list(b.getInsts())
    counts = (len(insts), len(b.getNets()), len(b.getBTerms()))
    names = [r["name"] for r in plan["moves"]]
    assert len(names) == len(set(names)), "duplicate placement targets"
    selected = set(names)
    rows = {}
    for row in b.getRows():
        box, site = row.getBBox(), row.getSite()
        assert site.getHeight() > 0 and site.getWidth() > 0
        y = box.yMin()
        # Multiple row segments can share a y; never fill a cut-out gap.
        rows.setdefault(y, []).append((box.xMin(), box.xMax(), site.getWidth(),
                                       site.getHeight(), row.getOrient()))
    ys = sorted(rows)
    occupied = {y: [] for y in ys}

    def reserve(box):
        x0, y0, x1, y1 = box
        lo = max(0, bisect_left(ys, y0) - 1)
        hi = bisect_left(ys, y1)
        for y in ys[lo:hi]:
            if any(y + r[3] > y0 for r in rows[y]):
                occupied[y].append((x0, x1))

    for i in insts:
        if i.getName() in selected:
            continue
        box = i.getBBox()
        reserve((box.xMin(), box.yMin(), box.xMax(), box.yMax()))
    for bl in b.getBlockages():
        box = bl.getBBox()
        reserve((box.xMin(), box.yMin(), box.xMax(), box.yMax()))

    def merged(intervals):
        out = []
        for x0, x1 in sorted(intervals):
            if out and x0 <= out[-1][1]:
                out[-1] = (out[-1][0], max(x1, out[-1][1]))
            else:
                out.append((x0, x1))
        return out

    for y in ys:
        occupied[y] = merged(occupied[y])

    def connections(i):
        return sorted((t.getMTerm().getName(),
                       t.getNet().getName() if t.getNet() else None)
                      for t in i.getITerms())

    actual, failures = [], []
    for r in plan["moves"]:
        i = b.findInst(r["name"])
        assert i and i.getMaster().getName() == r["master"], r["name"]
        assert re.search(r"(?:^|_)S?DFF", r["master"]), "not a sequential transport cell"
        assert r["role"] in ("post_ring_native_capture", "existing_pure_native_relay")
        if r["role"] == "post_ring_native_capture":
            assert re.search(r"(?:^|[./])u_bin_[^/]+/", r["name"])
        else:
            assert not re.search(r"(?:^|[./])u_(?:cland_|bin_|bout_|ft_)", r["name"])
            assert str(i.getPlacementStatus()) not in ("FIRM", "LOCKED"), "protected physical stage"
        box = i.getBBox()
        original = ((box.xMin() + box.xMax()) / (2 * u),
                    (box.yMin() + box.yMax()) / (2 * u))
        assert sum(abs(x - y) for x, y in zip(original, r["original_center_um"])) < .002, \
            "stale checkpoint geometry: " + r["name"]
        w, h = i.getMaster().getWidth(), i.getMaster().getHeight()
        tx, ty = [v * u for v in r["target_center_um"]]
        radius = r["max_site_offset_um"] * u
        best = None
        for y in ys[max(0, bisect_left(ys, ty - radius - h)):bisect_right(ys, ty + radius)]:
            for x0, x1, sw, sh, orient in rows[y]:
                if h > sh:
                    continue
                lo, hi = x0, x1
                for left, right in occupied[y] + [(hi, hi)]:
                    # One native site on each side is retained for legalization.
                    gap_end = min(left, hi)
                    low = math.ceil((lo + sw - x0) / sw)
                    high = math.floor((gap_end - w - sw - x0) / sw)
                    if high >= low:
                        k = min(high, max(low, round((tx - w / 2 - x0) / sw)))
                        x = x0 + k * sw
                        delta = abs(x + w / 2 - tx) + abs(y + h / 2 - ty)
                        candidate = (delta, y, x, orient, sw)
                        if delta <= radius and (best is None or candidate[:3] < best[:3]):
                            best = candidate
                    lo = max(lo, right)
                    if lo >= hi:
                        break
        if best is None:
            failures.append(dict(name=r["name"], reason="no legal free row/site within target radius"))
            continue
        delta, y, x, orient, sw = best
        before = connections(i)
        i.setPlacementStatus("PLACED")
        i.setOrient(orient)
        i.setLocation(x, y)
        i.setPlacementStatus("FIRM")
        assert connections(i) == before, "coordinate application changed connections"
        occupied[y] = merged(occupied[y] + [(x - sw, x + w + sw)])
        actual.append(dict(name=r["name"], role=r["role"], master=r["master"],
                           original_center_um=list(original),
                           allocated_center_um=[(x + w / 2) / u, (y + h / 2) / u],
                           target_offset_um=delta / u, connections=before))
    assert counts == (len(b.getInsts()), len(b.getNets()), len(b.getBTerms()))
    result = dict(status="FAIL_NO_CHECKPOINT" if failures else "LEGAL_SITE_PROPOSAL_REQUIRES_LOOK_DPL",
                  input_odb=a.odb, input_odb_sha256=hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),
                  input_plan=a.plan, moves=actual, failures=failures,
                  instance_net_port_counts=list(counts),
                  scope="Existing coordinates/status only. Connectivity and cell inventory preserved. No STA/GRT/route claim.")
    if not failures and a.out_odb:
        odb.write_db(db, a.out_odb)
        result["candidate_odb"] = a.out_odb
    Path(a.receipt).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status=result["status"], moves=len(actual), failures=len(failures))))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
