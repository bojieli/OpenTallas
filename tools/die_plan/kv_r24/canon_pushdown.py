#!/usr/bin/env python3
"""CLOCK-KV-R24: put every 12.2a1 PUSHDOWN clock cell of a die_clock_mesh build on ONE core-frame body per module.

    canon_pushdown.py PLAN SRC_BUILD OUT_BUILD [--report R.json]

Why: die_clock_mesh build places a pushdown driver/node group on the DIE row/site grid around its ideal point (row
above or below the ideal y, group centred on the ideal x).  The ideal point is identical in every instance's core
frame (census_pd, 1 nm), but the cell BODY is not: in a mirrored core (core orient composed with the partition
orient) the die row above the point is the core row below it, and the die site phase differs per core track offset.
12.2a1 requires the island cells at plan-fixed coordinates IDENTICAL for every instance of the core type (the core
netlist holds them), so apply_clkmesh_sites refuses the build (KV r22u: 5 modules, 2-8 body patterns each).

Rule (plan-only geometry, no timing input): per pushdown record (mesh.json pushdown, cells NAME or NAME_k), in the
core frame (R0 master) the group sits on the core row whose bottom is the ideal v snapped DOWN to the 0.27 row
lattice, its cells abut left-to-right from u0 = snap(ideal u - group width / 2, 0.054); each die cell body is the
die image of its core-frame rect (cells keep their die x order).  Moves are <= one cell width + one row.  The
island_windows of the build are rewritten from the new bodies (+ one site, as die_clock_mesh does).  Fails on any
clock-cell body overlap after the move.  Every other file of the build is copied unchanged (nets reference names).
"""
import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schema as S  # noqa: E402
import die_clock_mesh as DCM  # noqa: E402

SITE, ROW = DCM.SITE_X, DCM.ROW_Y


def snap_down(v, g):
    return round(int(v / g + 1e-6) * g, 4)


def snap(v, g):
    return round(round(v / g) * g, 4)


def group(cells, name):
    if name in cells:
        return [name]
    return sorted((k for k in cells if k.startswith(name + "_") and k[len(name) + 1:].isdigit()),
                  key=lambda k: (cells[k]["x"], k))


def canon(P, M, cells):
    moves, windows, per_mod = [], [], defaultdict(set)
    for r in M.get("pushdown", []):
        if not r.get("core"):
            continue
        part, inst = r["core"].split("/", 1)
        core = next(c for c in P.ptype(part).get("hard_cores", []) if c["inst"] == inst)
        names = group(cells, r["name"])
        if not names:
            continue
        iu, iv = DCM.core_frame(P, part, core, tuple(r.get("ideal") or r["xy"]))
        ws = [DCM.cell_width(cells[n]) for n in names]
        u0 = snap(iu - sum(ws) / 2.0, SITE)
        v0 = snap_down(iv + 1e-6, ROW)
        # die x order of the cells = their order along the die x axis of the image; place left-to-right in die frame
        rects = []
        u = u0
        for w in ws:
            rects.append((u, v0, round(u + w, 4), round(v0 + ROW, 4)))
            u = round(u + w, 4)
        imgs = []
        for q in rects:
            a = DCM.core_frame(P, part, core, (q[0], q[1]), inverse=True)
            b = DCM.core_frame(P, part, core, (q[2], q[3]), inverse=True)
            imgs.append((round(min(a[0], b[0]), 4), round(min(a[1], b[1]), 4), q))
        imgs.sort()
        for n, (x, y, q) in zip(names, imgs):
            c = cells[n]
            moves.append(dict(cell=n, dx=round(x - c["x"], 4), dy=round(y - c["y"], 4)))
            c["x"], c["y"] = x, y
        xs = [cells[n]["x"] for n in names]
        windows.append([round(min(xs) - SITE, 4), round(min(cells[n]["y"] for n in names) - 1e-3, 4),
                        round(max(cells[n]["x"] + DCM.cell_width(cells[n]) for n in names) + SITE, 4),
                        round(max(cells[n]["y"] for n in names) + ROW + 1e-3, 4), r["core"]])
        per_mod[(core["module"], r["core"])] |= set(rects)
    return moves, windows, per_mod


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    raw.pop("plan_deltas", None)
    P = S.Plan(raw)
    src, out = Path(a.src), Path(a.out)
    M = json.loads((src / "mesh.json").read_text())
    cells = json.loads((src / "place.json").read_text())
    moves, windows, per_mod = canon(P, M, cells)
    ov = DCM.placement_overlaps(cells)
    pats = defaultdict(set)
    for (mod, _inst), rs in per_mod.items():
        pats[mod].add(tuple(sorted(rs)))
    rep = dict(tool="tools/die_plan/kv_r24/canon_pushdown.py", plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),
               src=str(src), src_place_sha256=hashlib.sha256((src / "place.json").read_bytes()).hexdigest(),
               cells_moved=sum(1 for m in moves if m["dx"] or m["dy"]), cells=len(moves),
               max_dx_um=max((abs(m["dx"]) for m in moves), default=0), max_dy_um=max((abs(m["dy"]) for m in moves), default=0),
               clock_cell_overlaps=len(ov), patterns_per_module={k: len(v) for k, v in sorted(pats.items())})
    if ov or any(len(v) != 1 for v in pats.values()):
        print(json.dumps(rep, indent=1))
        print("FAIL", ov[:5])
        return 1
    out.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.is_file() and f.name not in ("place.json", "mesh.json"):
            shutil.copy2(f, out / f.name)
    M["island_windows"] = windows
    M["meta"]["pushdown_canon"] = dict(tool=rep["tool"], cells=rep["cells"], cells_moved=rep["cells_moved"],
                                       max_dx_um=rep["max_dx_um"], max_dy_um=rep["max_dy_um"])
    M["clock_hard_keepout_violations"] = DCM.hard_keepout_violations(P, cells, [tuple(w) for w in windows])
    M["meta"]["clock_hard_keepout_violations"] = len(M["clock_hard_keepout_violations"])
    rep["clock_hard_keepout_violations"] = len(M["clock_hard_keepout_violations"])
    (out / "place.json").write_text(json.dumps(cells) + "\n")
    (out / "mesh.json").write_text(json.dumps(M) + "\n")
    rep["out_place_sha256"] = hashlib.sha256((out / "place.json").read_bytes()).hexdigest()
    print(json.dumps(rep, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(dict(rep, moves=moves), indent=1) + "\n")
    return 1 if rep["clock_hard_keepout_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
