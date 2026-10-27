#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-4: per-type clock slot census of a head_mesh_r3 tree (tree nodes, leg repeaters, mesh drivers)
in each partition type's own frame.  A slot set is the union over the type's instances (type hardened once); it is
what the PLAN-DELTA declares as clock.slots (8.64-um islands centred on the site).
  head_slot_census.py PLAN R3_OUT_DIR OUT.json"""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_mesh_r3 as H
PL = H.Plan(sys.argv[1])
d = Path(sys.argv[2])
nodes = json.loads((d / "tree_nodes.json").read_text())
sites = H.sites_of(nodes)


def inv(p, xy):
    x, y = xy[0] - p["x0"], xy[1] - p["y0"]
    o = p["o"]
    if o in ("MY", "R180"):
        x = p["w"] - x
    if o in ("MX", "R180"):
        y = p["h"] - y
    return round(x, 2), round(y, 2)


slots = defaultdict(lambda: defaultdict(set))   # type -> (x,y) -> roles
inst = defaultdict(lambda: defaultdict(int))
nopart = []
for kind, tag, xy in sites:
    p = PL.part_at(xy)
    if p is None:
        nopart.append([kind, tag, list(xy)]); continue
    t = inv(p, xy)
    slots[p["type"]][t].add(kind)
    inst[p["type"]][p["name"]] += 1
out = dict(sites=len(sites), no_partition=nopart, types={})
for tn, s in sorted(slots.items()):
    rows = sorted({y for _, y in s}); cols = sorted({x for x, _ in s})
    out["types"][tn] = dict(slots=[dict(xy=list(k), roles=sorted(v)) for k, v in sorted(s.items())], n=len(s),
                            rows_y=rows, cols_x=cols, instances_used=len(inst[tn]),
                            max_sites_per_instance=max(inst[tn].values()))
    print(tn, "slots", len(s), "rows", rows[:8], "ncols", len(cols), "inst", len(inst[tn]))
print("sites", len(sites), "no partition", len(nopart))
Path(sys.argv[3]).write_text(json.dumps(out, indent=1))
