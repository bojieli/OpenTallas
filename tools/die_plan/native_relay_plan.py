#!/usr/bin/env python3
"""Plan physical movement of existing post-landing captures and pure relay flops.

Opt-in prototype tool: never changes a plan, RTL, clocks, or a checkpoint.  The
input is an actual placed geom_dump; targets need legal-site allocation, DPL,
actual reach measurements and LOOK before adoption.  Branches, opaque logic,
ports, clock consumers and already fixed stages are anchors, never transport.
"""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def geometry_module():
    p = Path(__file__).resolve().parents[1] / "autopilot" / "geom_rules.py"
    s = importlib.util.spec_from_file_location("native_relay_geom", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def source_flop(d, cid, depth=64):
    """Unique upstream flop through only BUF/INV; refuse ambiguous/opaque nets."""
    ins = [n for n, clock in d.cell_in.get(cid, ()) if not clock]
    if len(ins) != 1:
        return None
    n = ins[0]
    seen = set()
    for _ in range(depth):
        if n in seen or n in d.multi_drv:
            return None
        seen.add(n)
        _, driver, _ = d.nets[n]
        if not driver or driver[0] != "i":
            return None
        c = driver[1]
        if d.kind(c) == "S":
            return c
        if d.kind(c) != "B":
            return None
        ins = [n for n, clock in d.cell_in.get(c, ()) if not clock]
        if len(ins) != 1:
            return None
        n = ins[0]
    return None


def data_consumers(d, cid):
    """All first flop consumers, plus whether any other observable use exists."""
    todo = list(d.drives.get(cid, ()))
    seen, flops, opaque = set(), set(), False
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in d.multi_drv:
            opaque = True
        for target in d.nets[n][2]:
            if target[0] != "i" or target[2]:
                opaque = True
            elif d.kind(target[1]) == "S":
                flops.add(target[1])
            elif d.kind(target[1]) == "B":
                todo.extend(d.drives.get(target[1], ()))
            else:
                opaque = True
    return flops, opaque


def build(d, landed_buses, include_relays=True, site_radius=25.0):
    xy = {c: ((v[2] + v[4]) / 2, (v[3] + v[5]) / 2) for c, v in d.cells.items()}
    src = {c: p for c, v in d.cells.items() if v[0] == "S"
           if (p := source_flop(d, c)) is not None and p != c}
    moves, anchors, rejected, chains = {}, [], [], []
    statuses = d.extra.get("status", {})
    protected = re.compile(r"(?:^|[./])u_(?:cland_|bin_|bout_|ft_)")

    def record(c, target, role):
        if c in moves:
            raise ValueError("conflicting movement for " + d.cells[c][6])
        v = d.cells[c]
        clocks = sorted(n for n, ck in d.cell_in.get(c, ()) if ck)
        moves[c] = dict(name=v[6], master=v[1], cell_id=c,
                        original_center_um=list(xy[c]), target_center_um=list(target),
                        max_site_offset_um=site_radius, role=role, clock_net_ids=clocks)

    for c, v in sorted(d.cells.items()):
        m = re.search(r"(?:^|[./])u_bin_([^/]+)/", v[6])
        if v[0] != "S" or not m or m[1] not in landed_buses:
            continue
        p = src.get(c)
        if p is None or not re.search(r"(?:^|[./])u_cland_" + re.escape(m[1]) + r"/", d.cells[p][6]):
            rejected.append(dict(name=v[6], reason="no exact same-bus landing output through pure buffers"))
            continue
        # A boundary capture keeps its exact data/clock connections.  Its target
        # is the actual output register, not a ring centroid or guessed pin.
        record(c, xy[p], "post_ring_native_capture")
        anchors.append(dict(capture=v[6], ring_output=d.cells[p][6],
                            original_reach_um=distance(xy[c], xy[p])))

    if include_relays:
        eligible = set()
        for c in src:
            if c in moves or protected.search(d.cells[c][6]) or statuses.get(c) in ("FIRM", "LOCKED"):
                continue
            targets, opaque = data_consumers(d, c)
            if not opaque and len(targets) == 1 and src.get(next(iter(targets))) == c:
                eligible.add(c)
        used = set()
        # Split at every branch or observable consumer.  Only disjoint, purely
        # transporting interior stages move; endpoints remain actual anchors.
        for end in sorted(src):
            if end in eligible:
                continue
            chain, seen = [end], {end}
            cur = src[end]
            while cur in eligible and cur not in seen:
                chain.append(cur)
                seen.add(cur)
                cur = src[cur]
            if cur in seen or len(chain) < 2:
                continue
            chain.append(cur)
            chain.reverse()
            middle = chain[1:-1]
            if any(c in used for c in middle):
                raise ValueError("shared interior relay stage")
            old = [xy[c] for c in chain]
            longest = max(distance(a, b) for a, b in zip(old, old[1:]))
            if longest <= 405:
                continue
            start = moves.get(chain[0], {}).get("target_center_um", xy[chain[0]])
            finish = moves.get(chain[-1], {}).get("target_center_um", xy[chain[-1]])
            nominal = distance(start, finish) / (len(chain) - 1)
            if nominal + 2 * site_radius > 405:
                rejected.append(dict(chain=[d.cells[c][6] for c in chain],
                                     reason="existing stages insufficient at unchanged 405um reach",
                                     nominal_hop_um=nominal))
                continue
            targets = [list(start)]
            for i, c in enumerate(middle, 1):
                f = i / (len(chain) - 1)
                target = [start[0] + f * (finish[0] - start[0]),
                          start[1] + f * (finish[1] - start[1])]
                record(c, target, "existing_pure_native_relay")
                used.add(c)
                targets.append(target)
            targets.append(list(finish))
            chains.append(dict(stage_names=[d.cells[c][6] for c in chain],
                               original_max_hop_um=longest, target_centers_um=targets,
                               nominal_hop_um=nominal,
                               bounded_site_hop_um=nominal + 2 * site_radius))
    return dict(schema="opentallas.native_relay_placement.v1", status="PLAN_ONLY_REQUIRES_LOOK_AND_DPL",
                source_cells=len(d.cells), source_nets=len(d.nets),
                scope="Coordinates of existing flops only; no RTL/net/clock/cycle/outline changes",
                moves=list(moves.values()), post_ring_captures=anchors, relay_chains=chains,
                rejected=rejected,
                separate_holds=["sparse outline", "clock-load capacity", "START pin placement", "unfixed logic paths", "congestion/GRT"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("geom_dump")
    p.add_argument("land_slots")
    p.add_argument("out")
    p.add_argument("--anchors-only", action="store_true")
    a = p.parse_args()
    m = geometry_module()
    d = m.Design(a.geom_dump)
    slots = json.loads(Path(a.land_slots).read_text())["buses"]
    buses = {name for name, v in slots.items() if v.get("form") == "hold_mux"}
    r = build(d, buses, not a.anchors_only)
    r["geom_dump_sha256"] = hashlib.sha256(Path(a.geom_dump).read_bytes()).hexdigest()
    Path(a.out).write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({k: len(r[k]) for k in ("moves", "post_ring_captures", "relay_chains", "rejected")}))


if __name__ == "__main__":
    main()
