#!/usr/bin/env python3
"""CLOCK-KV-R25 analysis: per module with plan.clock.mesh.core_islands, the pushdown GROUPS (one mesh driver = 2 parallel
BUFx24, one tree node = 1 cell) in the core frame, their nets (in/out) from ctree.v, the pins_file of every instance."""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, sys.argv[4])
import schema as S
import die_clock_mesh as DCM

plan, mesh_dir, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
raw = json.loads(Path(plan).read_text()); raw.pop("plan_deltas", None)
P = S.Plan(raw)
ci = raw["clock"]["mesh"]["core_islands"]
M = json.loads((mesh_dir / "mesh.json").read_text())
C = json.loads((mesh_dir / "place.json").read_text())
V = (mesh_dir / "ctree.v").read_text()
inst_re = re.compile(r"^\s*(\w+)\s+(\w+)\s*\(\.A\((\w+)\),\s*\.Y\((\w+)\)\);", re.M)
cellnet = {m.group(2): (m.group(1), m.group(3), m.group(4)) for m in inst_re.finditer(V)}

def group(name):
    if name in C:
        return [name]
    return sorted((k for k in C if k.startswith(name + "_") and k[len(name) + 1:].isdigit()), key=lambda k: (C[k]["x"], k))

res = collections.defaultdict(lambda: collections.defaultdict(list))
for r in M["pushdown"]:
    part, inst = r["core"].split("/", 1)
    core = next(c for c in P.ptype(part)["hard_cores"] if c["inst"] == inst)
    mod = core["module"]
    if mod not in ci:
        continue
    names = group(r["name"])
    rects = []
    for n in names:
        c = C[n]; w = DCM.cell_width(c)
        a = DCM.core_frame(P, part, core, (c["x"], c["y"])); b = DCM.core_frame(P, part, core, (c["x"] + w, c["y"] + 0.27))
        rects.append((round(min(a[0], b[0]), 3), round(min(a[1], b[1]), 3), round(max(a[0], b[0]), 3), round(max(a[1], b[1]), 3)))
    nets = sorted({cellnet[n][1:] for n in names})
    masters = sorted({cellnet[n][0] for n in names})
    bb = (min(q[0] for q in rects), min(q[1] for q in rects), max(q[2] for q in rects), max(q[3] for q in rects))
    res[mod][r["core"]].append(dict(role=r["role"], name=r["name"], cells=names, masters=masters, nets=nets, bbox=bb,
                                    pins_file=core.get("pins_file"), orient=core.get("orient")))
summary = {}
for mod, per in sorted(res.items()):
    pats = collections.Counter(tuple(sorted((g["role"], g["bbox"], len(g["cells"]), tuple(g["masters"])) for g in gs)) for gs in per.values())
    pf = collections.Counter((gs[0]["pins_file"], gs[0]["orient"]) for gs in per.values())
    one = next(iter(per.values()))
    nets_in = collections.Counter(g["nets"][0][0] for gs in per.values() for g in gs)
    summary[mod] = dict(instances_with_pushdown=len(per), plan_instances=ci[mod]["instances"], patterns=len(pats),
                        groups=sorted([dict(role=g["role"], bbox=g["bbox"], cells=len(g["cells"]), masters=g["masters"]) for g in one], key=lambda d: d["bbox"]),
                        pins_files={f"{a}|{b}": n for (a, b), n in pf.items()},
                        distinct_nets_per_group=len(set(n for gs in per.values() for g in gs for n in g["nets"])) )
Path(out).write_text(json.dumps(summary, indent=1) + "\n")
print(json.dumps(summary, indent=1))
