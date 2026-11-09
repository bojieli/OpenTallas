"""Dump every native shape (signal wires+vias, special nets incl PG, fill, instance pins/OBS,
block obstructions) on V4..M8 inside an ROI of the NK routed DB. Read-only on the DB.
Usage (openroad -python -exit): native_roi.py <odb> <out.json> x0 y0 x1 y1 (um, child frame)"""
import json, sys
import odb

odb_path, out, *roi = sys.argv[1:]
x0, y0, x1, y1 = [int(round(float(v) * 1000)) for v in roi]
db = odb.dbDatabase.create()
odb.read_db(db, odb_path)
blk = db.getChip().getBlock()
assert blk.getDbUnitsPerMicron() == 1000
LAYERS = {"V4", "M5", "V5", "M6", "V6", "M7", "V7", "M8", "V8", "M9"}
shapes = []
NOLAYER = []


def hit(a, b, c, d):
    return min(c, x1) >= max(a, x0) and min(d, y1) >= max(b, y0)


def add(layer, a, b, c, d, **kw):
    if layer in LAYERS and hit(a, b, c, d):
        shapes.append(dict(layer=layer, bbox=[a, b, c, d], **kw))


def via_boxes(vm, ox, oy, **kw):
    for bx in vm.getBoxes():
        l = bx.getTechLayer()
        if l is None:
            continue
        add(l.getName(), ox + bx.xMin(), oy + bx.yMin(), ox + bx.xMax(), oy + bx.yMax(), **kw)


for net in blk.getNets():
    name = net.getName(); sig = net.getSigType()
    w = net.getWire()
    if w is not None:
        pit = odb.dbWirePathItr(); pit.begin(w); path = odb.dbWirePath(); ps = odb.dbWirePathShape()
        while pit.getNextPath(path):
            while pit.getNextShape(ps):
                s = ps.shape
                if s.isVia():
                    v = s.getTechVia() or s.getVia()
                    if v is None:
                        raise SystemExit('via without master')
                    rb = v.getBBox()
                    ox, oy = s.xMin() - rb.xMin(), s.yMin() - rb.yMin()
                    via_boxes(v, ox, oy, net=name, signal=sig, kind="wire-via", via=v.getName(), origin=[ox, oy])
                else:
                    l = s.getTechLayer()
                    if l is None:
                        NOLAYER.append(name); continue
                    add(l.getName(), s.xMin(), s.yMin(), s.xMax(), s.yMax(), net=name, signal=sig, kind="wire-RECT")
    for sw in net.getSWires():
        for sb in sw.getWires():
            if sb.isVia():
                v = sb.getTechVia() or sb.getBlockVia()
                ox, oy = sb.getViaXY()
                # dbSBox via: geometry from via boxes relative to origin
                via_boxes(v, ox, oy, net=name, signal=sig, kind="swire-via", via=v.getName(),
                          origin=[ox, oy])
            else:
                l = sb.getTechLayer()
                add(l.getName(), sb.xMin(), sb.yMin(), sb.xMax(), sb.yMax(), net=name, signal=sig,
                    kind="swire", shape=sb.getWireShapeType())
def xf(t, b):
    pts = []
    for x, y in ((b.xMin(), b.yMin()), (b.xMax(), b.yMax())):
        p = odb.Point(x, y); t.apply(p); pts.append((p.x(), p.y()))
    return [min(pts[0][0], pts[1][0]), min(pts[0][1], pts[1][1]), max(pts[0][0], pts[1][0]), max(pts[0][1], pts[1][1])]


for f in blk.getFills():
    r = f.getRect(); add(f.getTechLayer().getName(), r.xMin(), r.yMin(), r.xMax(), r.yMax(), net=None, kind="fill")
for o in blk.getObstructions():
    b = o.getBBox(); l = b.getTechLayer()
    if l is not None:
        add(l.getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax(), net=None, kind="block-obs")
for inst in blk.getInsts():
    bb = inst.getBBox()
    if not hit(bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax()):
        continue
    t = inst.getTransform()
    for ob in inst.getMaster().getObstructions():
        l = ob.getTechLayer()
        if l is None:
            continue
        r = xf(t, ob)
        add(l.getName(), *r, net=None, kind="inst-obs",
            inst=inst.getName(), master=inst.getMaster().getName())
    for it in inst.getITerms():
        n = it.getNet()
        for mp in it.getMTerm().getMPins():
            for g in mp.getGeometry():
                l = g.getTechLayer()
                if l is None:
                    continue
                r = xf(t, g)
                add(l.getName(), *r, net=n.getName() if n else None,
                    kind="inst-pin", inst=inst.getName(), pin=it.getMTerm().getName())
for bt in blk.getBTerms():
    for bp in bt.getBPins():
        for b in bp.getBoxes():
            l = b.getTechLayer()
            add(l.getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax(), net=bt.getNet().getName(), kind="bterm",
                bterm=bt.getName())
tracks = {}
for tg in blk.getTrackGrids():
    l = tg.getTechLayer().getName()
    if l in LAYERS:
        tracks[l] = dict(x=[list(tg.getGridPatternX(i)) for i in range(tg.getNumGridPatternsX())],
                         y=[list(tg.getGridPatternY(i)) for i in range(tg.getNumGridPatternsY())])
rules = {}
for l in db.getTech().getLayers():
    if l.getName() in LAYERS:
        rules[l.getName()] = dict(width=l.getWidth(), spacing=l.getSpacing(), dir=l.getDirection(),
                                  pitch=l.getPitch() if hasattr(l, "getPitch") else None)
json.dump(dict(schema="opentallas.native_roi.v1", odb=odb_path, dbu=1000, roi_dbu=[x0, y0, x1, y1],
               die=[blk.getDieArea().xMin(), blk.getDieArea().yMin(), blk.getDieArea().xMax(), blk.getDieArea().yMax()],
               tracks=tracks, rules=rules, nolayer_wire_shapes=len(NOLAYER), shapes=shapes), open(out, "w"), indent=1)
print("shapes", len(shapes))
