#!/usr/bin/env python3
"""D-QC-CLKMESH plan item: reserve the die clock cell sites (mesh drivers, H-tree nodes/repeaters, tap stubs) built by
die_clock_mesh.py build.  usage: apply_clkmesh_sites.py PLAN MESH_DIR [--write]

* die level: plan.clock.mesh = the mesh profile + a pointer (repo-relative) to clock_mesh_sites.json (every die clock
  cell: name, kind, die xy, owning partition or "die" for a channel).
* per partition type: partition_types[t].clock.die_islands_um = the UNION over all instances of that type of the
  local rect of every die clock cell placed inside an instance (cell footprint + halo).  One list per type, so every
  replica stays identical (FT-station style); an island unused by a given replica is filled like any free row.
Checks: no island overlaps a type hard core / clock keep-out; every die cell lies in at most one partition.
"""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402

CELL_W, CELL_H = 1.35, 0.27          # BUFx24_ASAP7_75t_R
HALO_X, HALO_Y = 0.54, 0.27          # one site / one row each side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("mesh_dir")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--sites-out")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(S.load(a.plan))
    d = Path(a.mesh_dir)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    rects = {n: P.rect(n) for n in P.parts}
    # bucket partitions for lookup
    B = 500.0
    grid = defaultdict(list)
    for n, r in rects.items():
        for i in range(int(r[0] // B), int(r[2] // B) + 1):
            for j in range(int(r[1] // B), int(r[3] // B) + 1):
                grid[(i, j)].append(n)
    sites, isl = [], defaultdict(set)
    per_kind = defaultdict(int)
    for name, c in sorted(cells.items()):
        x, y = c["x"], c["y"]
        own = [n for n in grid[(int(x // B), int(y // B))]
               if rects[n][0] <= x and x + CELL_W <= rects[n][2] and rects[n][1] <= y and y + CELL_H <= rects[n][3]]
        if len(own) > 1:
            raise SystemExit(f"{name} inside {own}")
        part = own[0] if own else "die"
        sites.append([name, c["kind"], x, y, part])
        per_kind[(c["kind"], part != "die")] += 1
        if own:
            tn = P.parts[part]["type"]
            corners = [P.to_type(part, (x + dx, y + dy)) for dx in (-HALO_X, CELL_W + HALO_X) for dy in (-HALO_Y, CELL_H + HALO_Y)]
            r = (round(min(p[0] for p in corners), 3), round(min(p[1] for p in corners), 3),
                 round(max(p[0] for p in corners), 3), round(max(p[1] for p in corners), 3))
            isl[tn].add(r)
    # merge identical / overlapping islands per type and check against hard cores + keep-outs
    bad = []
    out_types = {}
    for tn, rs in isl.items():
        t = P.types[tn]
        rs = sorted(rs)
        merged = []
        for r in rs:
            if merged and r[0] <= merged[-1][2] and r[1] <= merged[-1][3] and r[3] >= merged[-1][1] and r[1] == merged[-1][1]:
                m = merged[-1]
                merged[-1] = (m[0], min(m[1], r[1]), max(m[2], r[2]), max(m[3], r[3]))
            else:
                merged.append(r)
        ko = [(hc["origin_um"][0], hc["origin_um"][1], hc["origin_um"][0] + hc["outline_um"][0],
               hc["origin_um"][1] + hc["outline_um"][1]) for hc in t.get("hard_cores", []) or []]
        ko += [tuple(k) for k in t.get("clock", {}).get("keepouts_um", [])]
        for r in merged:
            for k in ko:
                if r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]:
                    bad.append((tn, r, k))
        w, h = t["outline_um"]
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in merged)
        out_types[tn] = dict(islands=len(merged), area_um2=round(area, 1), frac=round(area / (w * h), 6),
                             rects=[list(r) for r in merged])
    summary = dict(plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(), cells=len(sites),
                   in_partitions={f"{k}{'_part' if p else '_die'}": v for (k, p), v in sorted(per_kind.items())},
                   types_with_islands=len(out_types), island_overlaps_hard_core=len(bad),
                   max_type_frac=max((v["frac"] for v in out_types.values()), default=0),
                   islands_per_type={k: v["islands"] for k, v in sorted(out_types.items())})
    print(json.dumps(summary, indent=1))
    if bad:
        print("OVERLAPS", bad[:10])
        return 1
    if a.write:
        sp = Path(a.sites_out or Path(a.plan).parent / "clock_mesh_sites.json")
        sp.write_text(json.dumps(dict(meta=M["meta"], sites=sites)) + "\n")
        mm = {k: M["meta"][k] for k in ("nx", "ny", "m", "rep_um", "ndr", "pitch_um")}
        raw["clock"]["mesh"] = dict(mm, delta="D-QC-CLKMESH", layers={"straps_h": "M8", "straps_v": "M9"},
                                    tool="tools/die_plan/die_clock_mesh.py build", sites_file=sp.name,
                                    sites_sha256=hashlib.sha256(sp.read_bytes()).hexdigest(), cells=len(sites))
        types = raw["partition_types"]
        for tn, v in out_types.items():
            types[tn].setdefault("clock", {})["die_islands_um"] = v["rects"]
        Path(a.plan).write_text(json.dumps(raw, indent=1) + "\n")
        print("written", a.plan, sp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
