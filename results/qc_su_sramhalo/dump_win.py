# openroad -python: dump instances / macro pins / PDN + routing-blockages in a window to JSON
import odb, json, os, sys
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
x0, y0, x1, y1 = [float(v) for v in os.environ["WIN"].split(",")]
def inwin(bb): return bb.xMax()/u >= x0 and bb.xMin()/u <= x1 and bb.yMax()/u >= y0 and bb.yMin()/u <= y1
out = dict(insts=[], mpins=[], sw=[], blk=[], rows=[], ok=[])
for i in b.getInsts():
    bb = i.getBBox()
    if not inwin(bb): continue
    m = i.getMaster()
    out["insts"].append([i.getName(), m.getName(), bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, m.isBlock()])
    if m.isBlock():
        for it in i.getITerms():
            for mp in it.getMTerm().getMPins():
                for g in mp.getGeometry():
                    pass
        # transformed pin boxes
        for it in i.getITerms():
            r = it.getBBox()
            if inwin(r) and it.getNet() is not None:
                out["mpins"].append([it.getMTerm().getName(), it.getNet().getName(), r.xMin()/u, r.yMin()/u, r.xMax()/u, r.yMax()/u])
for n in b.getNets():
    if n.getSigType() not in ("POWER", "GROUND"): continue
    for sw in n.getSWires():
        for w in sw.getWires():
            if w.isVia(): continue
            if inwin(w): out["sw"].append([n.getName(), w.getTechLayer().getName(), w.xMin()/u, w.yMin()/u, w.xMax()/u, w.yMax()/u])
for bl in b.getBlockages():
    bb = bl.getBBox(); out["blk"].append([bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u])
for ob in b.getObstructions():
    bb = ob.getBBox(); out["blk"].append([bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, bb.getTechLayer().getName()])
for r in b.getRows():
    bb = r.getBBox()
    if inwin(bb): out["rows"].append([bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u])
out["die"] = [b.getDieArea().xMax()/u, b.getDieArea().yMax()/u]
json.dump(out, open(os.environ["OUT"], "w"))
print("DUMP", len(out["insts"]), len(out["mpins"]), len(out["sw"]), len(out["blk"]), len(out["rows"]))
