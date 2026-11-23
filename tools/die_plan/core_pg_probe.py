# PG-CORECONN-1 diagnostic (not a gate): per hard-macro (BLOCK master) PG pin shape -> is it physically touched by its net's special wiring
# (a via with that pin layer as bottom/top inside the pin rect, or a same-layer special wire overlapping it)?
# usage: openroad -python -exit core_pg_probe.py (env ODB=..., optional OT_PG_PROBE_MASTER=<exact macro master>)
import os, sys, json, odb
db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ODB"])
blk = db.getChip().getBlock()
def ov(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def supply_boxes(net):
    # Convert the SWIG objects once per supply net, not once per macro PG term.
    for sw in net.getSWires():
        for sb in sw.getWires():
            rect = (sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax())
            if sb.isVia():
                via = sb.getTechVia() or sb.getBlockVia()
                if via is None:
                    continue
                layers = (via.getBottomLayer().getName(), via.getTopLayer().getName())
            else:
                layer = sb.getTechLayer()
                if layer is None:
                    continue
                layers = (layer.getName(),)
            yield rect, layers


rows = []
wires = {}
master = os.environ.get("OT_PG_PROBE_MASTER")
for inst in blk.getInsts():
    m = inst.getMaster()
    if not m.isBlock() or (master and m.getName() != master):
        continue
    ox, oy = inst.getOrigin()
    tr = odb.dbTransform(inst.getOrient(), odb.Point(ox, oy))
    for mt in m.getMTerms():
        if mt.getSigType() not in ("POWER", "GROUND"):
            continue
        it = inst.findITerm(mt.getName())
        net = it.getNet() if it else None
        shapes = []
        for mp in mt.getMPins():
            for g in mp.getGeometry():
                if g.getTechLayer() is None:
                    continue
                p0 = odb.Point(g.xMin(), g.yMin()); p1 = odb.Point(g.xMax(), g.yMax())
                tr.apply(p0); tr.apply(p1)
                xs = sorted((p0.getX(), p1.getX())); ys = sorted((p0.getY(), p1.getY()))
                shapes.append([g.getTechLayer().getName(), (xs[0], ys[0], xs[1], ys[1]), 0])
        if net is not None:
            net_name = net.getName()
            if net_name not in wires:
                wires[net_name] = list(supply_boxes(net))
            bb = inst.getBBox()
            ib = (bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax())
            for box, layers in wires[net_name]:
                if not ov(box, ib):
                    continue
                for shape in shapes:
                    if shape[0] in layers and ov(shape[1], box):
                        shape[2] += 1
        n = len(shapes); c = sum(1 for s in shapes if s[2])
        rows.append(dict(inst=inst.getName(), master=m.getName(), pin=mt.getName(), net=net.getName() if net else None,
                         layers=sorted({s[0] for s in shapes}), shapes=n, touched=c))
if master and not rows:
    raise ValueError(f"No PG terms found for the requested macro master {master}")
bad = [r for r in rows if r["net"] is None or r["touched"] == 0]
print("OT_CORE_PG_PROBE", json.dumps(dict(odb=os.environ["ODB"], macro_pg_terms=len(rows), unconnected_terms=len(bad),
      shapes=sum(r["shapes"] for r in rows), touched_shapes=sum(r["touched"] for r in rows))))
for r in rows:
    print("OT_CORE_PG_ROW", json.dumps(r))
sys.exit(0)
