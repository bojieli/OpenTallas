"""OpenROAD -python: exact r2r geometric reach through every combinational cone.

env ODB / OUT. Keeps extrema of x+y and x-y rather than enumerating all source
registers, so reconvergent cones remain linear in netlist size. Clock inputs are
excluded; data, enable and reset inputs are included. No timing claim.
"""
import json
import os
import re
import sys
import odb

sys.setrecursionlimit(20000)
db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ODB"])
block = db.getChip().getBlock()
scale = db.getTech().getDbUnitsPerMicron()
roots, drivers, captures = {}, {}, []


def point(obj):
    r = obj.getBBox()
    return ((r.xMin()+r.xMax())/(2*scale), (r.yMin()+r.yMax())/(2*scale))


def root(obj):
    x, y = point(obj)
    return (x+y, x+y, x-y, x-y)


for inst in block.getInsts():
    master = inst.getMaster()
    sequential = bool(re.search(r"(?:DFF|SDF)", master.getName()))
    inputs, outputs = [], []
    for pin in inst.getITerms():
        mt, net = pin.getMTerm(), pin.getNet()
        if net is None or mt.getSigType() in ("POWER", "GROUND"):
            continue
        name = net.getName()
        if mt.getIoType() == "OUTPUT":
            outputs.append((name, pin))
        elif mt.getIoType() == "INPUT" and mt.getSigType() != "CLOCK" and mt.getName() not in ("CLK", "CK"):
            inputs.append((name, pin))
    if sequential or master.isBlock():
        for name, pin in outputs:
            roots.setdefault(name, []).append(root(pin))
        for name, pin in inputs:
            captures.append((inst.getName()+"/"+pin.getMTerm().getName(), name, point(pin)))
    else:
        for name, _ in outputs:
            drivers.setdefault(name, []).append([n for n, _ in inputs])

cache, active, cycles = {}, set(), set()


def bounds(net):
    if net in cache:
        return cache[net]
    if net in active:
        cycles.add(net)
        return None
    active.add(net)
    terms = list(roots.get(net, []))
    for gate in drivers.get(net, []):
        terms.extend(b for n in gate if (b := bounds(n)) is not None)
    active.remove(net)
    value = ((min(b[0] for b in terms), max(b[1] for b in terms),
              min(b[2] for b in terms), max(b[3] for b in terms)) if terms else None)
    cache[net] = value
    return value


distances, no_source = [], 0
for pin, net, (x, y) in captures:
    b = bounds(net)
    if b is None:
        no_source += 1
        continue
    reach = max(x+y-b[0], b[1]-x-y, x-y-b[2], b[3]-x+y)
    distances.append((round(reach, 4), pin))
distances.sort(reverse=True)
result = dict(scope="Placed register/macro data-cone endpoint Manhattan reach; no STA",
              captures=len(captures), captures_with_register_or_macro_sources=len(distances),
              primary_or_constant_only=no_source, combinational_cycle_nets=sorted(cycles),
              over_405=sum(d > 405 for d, _ in distances), max_um=distances[0][0] if distances else None,
              worst=distances[:20], nets_visited=len(cache))
with open(os.environ["OUT"], "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps({k: v for k, v in result.items() if k != "worst"}))
