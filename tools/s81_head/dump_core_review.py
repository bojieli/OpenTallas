"""OpenROAD -python diagnostic: actual placed clock/core/PG geometry."""
import json
import os
import re
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock()
u = db.getTech().getDbUnitsPerMicron()


def box(z):
    return [z.xMin()/u, z.yMin()/u, z.xMax()/u, z.yMax()/u]


def centre(z):
    q = box(z)
    return [(q[0]+q[2])/2, (q[1]+q[3])/2]


out = dict(die=box(b.getDieArea()), macros=[], flops=[], clock={}, pg=[], ports={}, edges=[])
for i in b.getInsts():
    name, m = i.getName(), i.getMaster()
    if m.isBlock():
        out["macros"].append([name, box(i.getBBox())])
    elif re.search("DFF|SDF", m.getName()):
        out["flops"].append(centre(i.getBBox()))
    if name.startswith(("ot_ms_", "u_isl_")):
        out["clock"][name] = centre(i.getBBox())
for bt in b.getBTerms():
    out["ports"][bt.getName()] = dict(xy=centre(bt.getBBox()), net=bt.getNet().getName(),
                                      direction=bt.getIoType())
for net in b.getNets():
    if net.getSigType() in ("POWER", "GROUND"):
        for wire in net.getSWires():
            for s in wire.getWires():
                layer = s.getTechLayer()
                if layer is not None and layer.getName() in ("M4", "M5"):
                    out["pg"].append([net.getName(), layer.getName(), box(s)])
        continue
    terms = [p for p in net.getITerms() if p.getInst().getName() in out["clock"]]
    d = [p for p in terms if p.getMTerm().getIoType() == "OUTPUT"]
    if len(d) == 1:
        for p in terms:
            if p.getMTerm().getIoType() == "INPUT":
                out["edges"].append([d[0].getInst().getName(), p.getInst().getName()])
with open(os.environ["OUT"], "w") as f:
    json.dump(out, f)
print("REVIEW_GEOMETRY", len(out["flops"]), len(out["clock"]), len(out["pg"]),
      "clock_port", out["ports"].get("clk"), "meshstrap", out["ports"].get("ft_mstrap_i"))
