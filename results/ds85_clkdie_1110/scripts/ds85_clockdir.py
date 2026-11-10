#!/usr/bin/env python3
"""DS85 CLKDIE-S81 (DO_NOT_COUNT): adapt a die_trial kit clock dir (ctree.v + ctree.tcl placement + tree.json) to the
clock_grt_probe.build input layout (tree.json with meta.root_um, place.json {cell: x, y, orient, kind, level},
nets.json {ports, nets: [{name, drv, loads}]}, ctree.v).  Reads KIT/clock read-only, writes OUT.

kind/level (used only for the probe's NDR width choice, 8W for levels <= 6, else 4W): b<id> = die tree node cell
(kind node, level = tree node level), b<id>_r = the root's input inverter (node, level 0), r<id>_<k> = repeater of the
leg into node <id> (kind rep, level of node <id>), p* = tap trim pad (kind pad, level 99).

  ds85_clockdir.py KIT/clock OUT
"""
import json
import re
import shutil
import sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
tree = json.loads((src / "tree.json").read_text())
tcl = (src / "ctree.tcl").read_text()
m = re.search(r"place_pin -pin_name root -layer \S+ -location \{(\S+) (\S+)\}", tcl)
tree["meta"]["root_um"] = [float(m.group(1)), float(m.group(2))]
lvl = {str(k): v["level"] for k, v in tree["nodes"].items()}
cells = {}
for mm in re.finditer(r"^place_inst -name (\S+) -location \{(\S+) (\S+)\}(?: -orient (\S+))?", tcl, flags=re.M):
    nm = mm.group(1)
    c = dict(x=float(mm.group(2)), y=float(mm.group(3)), orient=mm.group(4) or "R0")
    if (q := re.fullmatch(r"b(\d+)(_r)?", nm)):
        c.update(kind="node", level=0 if q.group(2) else lvl[q.group(1)])
    elif (q := re.fullmatch(r"r(\d+)_\d+", nm)):
        c.update(kind="rep", level=lvl[q.group(1)])
    else:
        c.update(kind="pad", level=99)
    cells[nm] = c
v = (src / "ctree.v").read_text()
hm = re.search(r"module\s+\w+\s*\(([^)]*)\);", v)
ports = [p.strip() for p in hm.group(1).split(",")]
pset = set(ports)
drv, loads = {}, {}
for im in re.finditer(r"^\s*(\S+_ASAP7_75t_R)\s+(\S+)\s*\(\.A\((\S+?)\),\s*\.Y\((\S+?)\)\);", v, flags=re.M):
    _, inst, a, y = im.groups()
    drv[y] = inst
    loads.setdefault(a, []).append(inst)
nets = []
for n in set(drv) | set(loads):
    d = drv.get(n, "port:" + n if n in pset else None)
    ld = list(loads.get(n, []))
    if n in pset and n in drv:
        ld.append("port:" + n)
    nets.append(dict(name=n, drv=d, loads=ld))
miss = set(cells) ^ (set(drv.values()) | {i for l in loads.values() for i in l})
if miss:
    raise SystemExit(f"place/netlist cell mismatch {len(miss)} e.g. {sorted(miss)[:5]}")
(out / "tree.json").write_text(json.dumps(tree) + "\n")
(out / "place.json").write_text(json.dumps(cells) + "\n")
(out / "nets.json").write_text(json.dumps(dict(ports=ports, nets=nets)) + "\n")
shutil.copyfile(src / "ctree.v", out / "ctree.v")
print(json.dumps(dict(cells=len(cells), nets=len(nets), ports=len(ports), root_um=tree["meta"]["root_um"],
                      undriven=[n["name"] for n in nets if n["drv"] is None][:5])))
