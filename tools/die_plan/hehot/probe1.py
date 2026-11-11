# DS85-HEHOT probe 1 (DO_NOT_COUNT): what blocks M6 over he in the parent h9 4_cts.odb
import os, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron(); tech = db.getTech()
he = [i for i in b.getInsts() if i.getMaster().getName().endswith("_gb_he")]
print("he insts", [(i.getName(), [x/u for x in (i.getBBox().xMin(), i.getBBox().yMin(), i.getBBox().xMax(), i.getBBox().yMax())], i.getOrient()) for i in he])
def ov(a, bb): return a.xMin() < bb.xMax() and a.xMax() > bb.xMin() and a.yMin() < bb.yMax() and a.yMax() > bb.yMin()
print("die", b.getDieArea().xMax()/u, b.getDieArea().yMax()/u, "core", b.getCoreArea().xMax()/u, b.getCoreArea().yMax()/u)
for ln in ("M4","M5","M6","M7","M8","M9"):
    l = tech.findLayer(ln); tg = b.findTrackGrid(l)
    print(ln, l.getDirection(), "pitch", l.getPitch()/u, "width", l.getWidth()/u, "tg", tg is not None)
# block obstructions / blockages
c = collections.Counter()
for o in b.getObstructions():
    bb = o.getBBox(); l = bb.getTechLayer()
    hit = sum(ov(bb, i.getBBox()) for i in he)
    c[(l.getName() if l else None, hit>0)] += 1
print("block obstructions (layer, over he):", dict(c))
for o in b.getObstructions():
    bb = o.getBBox(); l = bb.getTechLayer()
    if l and l.getName() in ("M6","M7") :
        print("  OBS", l.getName(), [x/u for x in (bb.xMin(), bb.yMin(), bb.xMax(), bb.yMax())], "slot" if o.isSlotObstruction() else "", "fill" if o.isFillObstruction() else "")
print("placement blockages", len(list(b.getBlockages())))
# special wires on M6/M7 over he
for net in b.getNets():
    if not net.isSpecial(): continue
    cnt = collections.Counter(); area = collections.Counter()
    for sw in net.getSWires():
        for w in sw.getWires():
            if w.isVia(): continue
            ln = w.getTechLayer().getName()
            for i in he[:1]:
                ib = i.getBBox()
                if ov(w, ib):
                    cnt[ln] += 1
                    x0=max(w.xMin(),ib.xMin()); x1=min(w.xMax(),ib.xMax()); y0=max(w.yMin(),ib.yMin()); y1=min(w.yMax(),ib.yMax())
                    area[ln] += (x1-x0)*(y1-y0)/u/u
    if cnt: print("swire", net.getName(), net.getSigType(), dict(cnt), {k: round(v,1) for k,v in area.items()})
m = he[0].getMaster()
print("master", m.getName(), "obs layers", collections.Counter(o.getTechLayer().getName() for o in m.getObstructions() if o.getTechLayer()))
pl = collections.Counter()
for mt in m.getMTerms():
    for mp in mt.getMPins():
        for g in mp.getGeometry():
            pl[g.getTechLayer().getName()] += 1
print("pin layers", dict(pl), "nterms", len(list(m.getMTerms())))
