#!/usr/bin/env python3
"""Die clock mesh plan item (D-<DIE>-CLKMESH, e.g. D-QC-CLKMESH / D-KV-CLKMESH): reserve the die clock cell sites (mesh
drivers, H-tree nodes/repeaters, tap stubs) built by die_clock_mesh.py build.
usage: apply_clkmesh_sites.py PLAN MESH_DIR [--write --delta-id D-<DIE>-CLKMESH]

* die level: plan.clock.mesh = the mesh profile + a pointer (repo-relative) to clock_mesh_sites.json (every die clock
  cell: name, kind, die xy, owning partition or "die" for a channel).
* per partition type: partition_types[t].clock.die_islands_um = the UNION over all instances of that type of the
  local rect of every die clock cell placed inside an instance (cell footprint + halo).  One list per type, so every
  replica stays identical (FT-station style); an island unused by a given replica is filled like any free row.
Checks: no island overlaps a type hard core / clock keep-out; cell+halo portions crossing an abutted
partition boundary are reserved in every touched partition type. Site rows retain their original format.

CLOCK-KV-R24 (METHODOLOGY 12.2a1 declared exception): a clock cell whose body lies WHOLLY inside a hard core AND
inside a window the mesh build declared for that very core (mesh.json island_windows [x0,y0,x1,y1,'part/inst'],
die_clock_mesh.py pushdown records) is a 12.2a1 PUSHDOWN cell: it is built in the core netlist, so it is NOT a
partition placement hole.  Its core-frame body rect goes to plan.clock.mesh.core_islands[module]; the part of its
halo outside the core is still reserved in the touched partition types.  Accepted only when every instance of that
module in the plan carries the IDENTICAL core-frame island set (1 nm); otherwise, or for any undeclared cell on a
hard core, the overlap FAILs as before.
"""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/die_plan"))
import schema as S  # noqa: E402
import die_clock_mesh as CLK  # noqa: E402

CELL_H = 0.27                     # Current ASAP7 RVT row height; widths are per master.
HALO_X, HALO_Y = 0.54, 0.27          # one site / one row each side


def minus(r, k):
    """rect r minus rect k -> list of disjoint rects (0..4)."""
    if not (r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]):
        return [r]
    out = []
    if r[1] < k[1]:
        out.append((r[0], r[1], r[2], k[1]))
    if k[3] < r[3]:
        out.append((r[0], k[3], r[2], r[3]))
    y0, y1 = max(r[1], k[1]), min(r[3], k[3])
    if r[0] < k[0]:
        out.append((r[0], y0, k[0], y1))
    if k[2] < r[2]:
        out.append((k[2], y0, r[2], y1))
    return [q for q in out if q[0] < q[2] and q[1] < q[3]]


def core_rect(c):
    """hard-core keep-out rect in the partition type frame (as the overlap check uses it)."""
    return (c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
            c["origin_um"][1] + c["outline_um"][1])


def pushdown_core(P, windows, x0, y0, x1, y1):
    """(part, core) when the die-frame body is wholly inside a declared island window of a hard core AND wholly
    inside that core outline (12.2a1 pushdown cell), else None."""
    for w in windows:
        if not (w[0] <= x0 and x1 <= w[2] and w[1] <= y0 and y1 <= w[3]) or "/" not in str(w[4]):
            continue
        part, inst = w[4].split("/", 1)
        if part not in P.parts:
            continue
        core = next((c for c in P.ptype(part).get("hard_cores", []) or [] if c["inst"] == inst), None)
        if core is None:
            continue
        a, b = P.to_type(part, (x0, y0)), P.to_type(part, (x1, y1))
        k = core_rect(core)
        if k[0] - 1e-6 <= min(a[0], b[0]) and max(a[0], b[0]) <= k[2] + 1e-6 and \
                k[1] - 1e-6 <= min(a[1], b[1]) and max(a[1], b[1]) <= k[3] + 1e-6:
            return part, core
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("mesh_dir")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--sites-out")
    ap.add_argument("--delta-id", help="plan delta tag written to plan.clock.mesh.delta (required with --write), "
                    "e.g. D-QC-CLKMESH, D-KV-CLKMESH")
    a = ap.parse_args()
    if a.write and not a.delta_id:
        ap.error("--write needs --delta-id (the die's plan delta tag, e.g. D-KV-CLKMESH)")
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(S.load(a.plan))
    d = Path(a.mesh_dir)
    M = json.loads((d / "mesh.json").read_text())
    cells = json.loads((d / "place.json").read_text())
    overlaps = CLK.placement_overlaps(cells)
    if overlaps:
        print(json.dumps({"cell_body_overlaps": len(overlaps), "examples": overlaps[:10]}))
        return 1
    rects = {n: P.rect(n) for n in P.parts}
    # bucket partitions for lookup
    B = 500.0
    grid = defaultdict(list)
    for n, r in rects.items():
        for i in range(int(r[0] // B), int(r[2] // B) + 1):
            for j in range(int(r[1] // B), int(r[3] // B) + 1):
                grid[(i, j)].append(n)
    sites, isl = [], defaultdict(set)
    partial_owners = {}
    per_kind = defaultdict(int)
    windows = [w for w in M.get("island_windows", []) or [] if len(w) >= 5]
    pd_inst = defaultdict(lambda: defaultdict(set))     # module -> (part, inst) -> core-frame body rects
    pd_cells = {}
    for name, c in sorted(cells.items()):
        x, y = c["x"], c["y"]
        cell_w = CLK.cell_width(c)
        pdc = pushdown_core(P, windows, x, y, x + cell_w, y + CELL_H) if windows else None
        if pdc:
            part, core = pdc
            q = [CLK.core_frame(P, part, core, pt) for pt in ((x, y), (x + cell_w, y + CELL_H))]
            pd_inst[core["module"]][(part, core["inst"])].add(
                (round(min(q[0][0], q[1][0]), 3), round(min(q[0][1], q[1][1]), 3),
                 round(max(q[0][0], q[1][0]), 3), round(max(q[0][1], q[1][1]), 3)))
            pd_cells[name] = f"{part}/{core['inst']}"
            sites.append([name, c["kind"], x, y, part])
            per_kind[(c["kind"] + "_pushdown", True)] += 1
            # the halo outside the core is a placement hole of every touched partition type
            halo = (x-HALO_X, y-HALO_Y, x+cell_w+HALO_X, y+CELL_H+HALO_Y)
            for touched in sorted({n for i in range(int(halo[0]//B),int(halo[2]//B)+1)
                                   for j in range(int(halo[1]//B),int(halo[3]//B)+1) for n in grid[(i,j)]}):
                pr = rects[touched]
                clipped = (max(halo[0],pr[0]),max(halo[1],pr[1]),min(halo[2],pr[2]),min(halo[3],pr[3]))
                if clipped[0] >= clipped[2] or clipped[1] >= clipped[3]:
                    continue
                tn = P.parts[touched]["type"]
                corners = [P.to_type(touched,(xx,yy)) for xx in (clipped[0],clipped[2]) for yy in (clipped[1],clipped[3])]
                r = (round(min(p[0] for p in corners),3),round(min(p[1] for p in corners),3),
                     round(max(p[0] for p in corners),3),round(max(p[1] for p in corners),3))
                pieces = [r]
                for hc in P.types[tn].get("hard_cores", []) or []:
                    pieces = [u for v in pieces for u in minus(v, core_rect(hc))]
                for u in pieces:
                    u = tuple(round(v_, 3) for v_ in u)
                    if u[0] < u[2] and u[1] < u[3]:
                        isl[tn].add(u)
            continue
        own = [n for n in grid[(int(x // B), int(y // B))]
               if rects[n][0] <= x and x + cell_w <= rects[n][2] and rects[n][1] <= y and y + CELL_H <= rects[n][3]]
        if len(own) > 1:
            raise SystemExit(f"{name} inside {own}")
        part = own[0] if own else "die"
        sites.append([name, c["kind"], x, y, part])
        per_kind[(c["kind"], part != "die")] += 1
        # A die-level clock body can span abutted tile outlines. Reserve every
        # touched portion; labelling such a body "die" must not leave either
        # adjacent hardened tile free to fill its occupied physical area.
        halo = (x-HALO_X, y-HALO_Y, x+cell_w+HALO_X, y+CELL_H+HALO_Y)
        candidates = {n for i in range(int(halo[0]//B),int(halo[2]//B)+1)
                      for j in range(int(halo[1]//B),int(halo[3]//B)+1) for n in grid[(i,j)]}
        body_parts = []
        reserved_parts = set()
        for touched in sorted(candidates):
            pr = rects[touched]
            if min(x+cell_w,pr[2])-max(x,pr[0]) > 1e-6 and min(y+CELL_H,pr[3])-max(y,pr[1]) > 1e-6:
                body_parts.append(touched)
            clipped = (max(halo[0],pr[0]),max(halo[1],pr[1]),min(halo[2],pr[2]),min(halo[3],pr[3]))
            if clipped[0] >= clipped[2] or clipped[1] >= clipped[3]:
                continue
            tn = P.parts[touched]["type"]
            corners = [P.to_type(touched,(xx,yy)) for xx in (clipped[0],clipped[2]) for yy in (clipped[1],clipped[3])]
            r = (round(min(p[0] for p in corners),3),round(min(p[1] for p in corners),3),
                 round(max(p[0] for p in corners),3),round(max(p[1] for p in corners),3))
            if r[0] < r[2] and r[1] < r[3]:
                isl[tn].add(r)
                reserved_parts.add(touched)
        missing = set(body_parts) - reserved_parts
        if missing:
            raise SystemExit(f"{name} has unreserved physical body in {sorted(missing)}")
        if body_parts and not own:
            partial_owners[name] = body_parts
    # 12.2a1 identity: every instance of a module with pushdown cells carries the same core-frame island set
    bad = []
    core_islands = {}
    for mod, per in sorted(pd_inst.items()):
        insts = [(pn, hc["inst"]) for pn, p in P.parts.items()
                 for hc in P.types[p["type"]].get("hard_cores", []) or [] if hc["module"] == mod]
        pats = defaultdict(list)
        for k in insts:
            pats[tuple(sorted(per.get(k, set())))].append(k)
        if len(pats) != 1:
            top = sorted(pats.items(), key=lambda kv: -len(kv[1]))
            bad.append(("core_islands", mod, f"{len(pats)} patterns over {len(insts)} instances "
                        f"(12.2a1 needs one): " + "; ".join(f"{len(k)} rects x {len(v)} inst e.g. {'/'.join(v[0])}"
                                                          for k, v in top[:3]),
                        {"/".join(v[0]): list(k) for k, v in top[:4]}))
            continue
        rs = next(iter(pats))
        core_islands[mod] = dict(rule="12.2a1 pushdown (in the core netlist, fixed, dont_touch; die-owned ft ports)",
                                 instances=len(insts), rects_um=[list(r) for r in rs], frame="core R0 master")
    # merge identical / overlapping islands per type and check against hard cores + keep-outs
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
        # CLOCK-KV-R22: clip to the type outline on the site/row lattice (a halo outside the outline belongs to the
        # abutted neighbour, reserved there); KV pc-family rects at x = -0.54 blocked gen_phys
        merged = [(max(r[0], 0.0), max(r[1], 0.0), min(r[2], w), min(r[3], h)) for r in merged]
        merged = [r for r in merged if r[0] < r[2] and r[1] < r[3]]
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in merged)
        out_types[tn] = dict(islands=len(merged), area_um2=round(area, 1), frac=round(area / (w * h), 6),
                             rects=[list(r) for r in merged])
    summary = dict(plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(), cells=len(sites),
                   in_partitions={f"{k}{'_part' if p else '_die'}": v for (k, p), v in sorted(per_kind.items())},
                   cell_body_overlaps=0, unreserved_body_parts=0, boundary_spanning_cells=len(partial_owners), types_with_islands=len(out_types), island_overlaps_hard_core=len(bad),
                   max_type_frac=max((v["frac"] for v in out_types.values()), default=0),
                   islands_per_type={k: v["islands"] for k, v in sorted(out_types.items())},
                   pushdown_cells=len(pd_cells),
                   core_islands={k: dict(instances=v["instances"], rects=len(v["rects_um"])) for k, v in core_islands.items()})
    print(json.dumps(summary, indent=1))
    if bad:
        print("OVERLAPS", bad[:10])
        return 1
    if a.write:
        sp = Path(a.sites_out or Path(a.plan).parent / "clock_mesh_sites.json")
        sp.write_text(json.dumps(dict(meta=M["meta"], sites=sites, partial_owners=partial_owners,
                                      **(dict(pushdown_cells=pd_cells) if pd_cells else {}))) + "\n")
        mm = {k: M["meta"][k] for k in ("nx", "ny", "m", "rep_um", "ndr", "pitch_um")}
        if M["meta"].get("regions_depth"):
            mm.update(regions_depth=M["meta"]["regions_depth"], regions=M["meta"]["regions"])
        raw["clock"]["mesh"] = dict(mm, delta=a.delta_id, layers={"straps_h": "M8", "straps_v": "M9"},
                                    tool="tools/die_plan/die_clock_mesh.py build", sites_file=sp.name,
                                    sites_sha256=hashlib.sha256(sp.read_bytes()).hexdigest(), cells=len(sites),
                                    **(dict(core_islands=core_islands) if core_islands else {}))
        if M["meta"].get("root_plan_um") is not None:
            spine = raw["clock"].setdefault("spine", {})
            spine["root_um"] = M["meta"]["root_um"]
            if "die_root_um" in spine:
                spine["die_root_um"] = M["meta"]["root_um"]
        types = raw["partition_types"]
        # A new profile replaces the old profile completely, including types with no sites in the new mesh.
        for t in types.values():
            t.get("clock", {}).pop("die_islands_um", None)
        for tn, v in out_types.items():
            types[tn].setdefault("clock", {})["die_islands_um"] = v["rects"]
        Path(a.plan).write_text(json.dumps(raw, indent=1) + "\n")
        print("written", a.plan, sp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
