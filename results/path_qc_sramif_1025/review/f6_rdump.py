# PATH-QC-SRAMIF render dump (openroad -python): insts (kind, bbox) + per macro signal pin the nearest connected register
# through <= 4 levels (same walk as GEOM-REVIEW dumpif.py / dumpif_in.py) with its location.  env ODB, OUT.
import odb, os
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron()
def isff(m):
    n = m.getName(); return ("DFF" in n) or ("DHL" in n) or ("SDF" in n)
out = open(os.environ["OUT"], "w")
b = blk.getDieArea(); out.write("DIE\t%.3f\t%.3f\t%.3f\t%.3f\n" % (b.xMin()/dbu, b.yMin()/dbu, b.xMax()/dbu, b.yMax()/dbu))
for i in blk.getInsts():
    m = i.getMaster(); bb = i.getBBox()
    k = "M" if m.isBlock() else ("F" if isff(m) else ("B" if ("BUF" in m.getName() or "INV" in m.getName()) else "C"))
    if m.getName().startswith(("TAPCELL", "FILLER", "DECAP")): continue
    out.write("I\t%s\t%s\t%.3f\t%.3f\t%.3f\t%.3f\n" % (k, i.getName(), bb.xMin()/dbu, bb.yMin()/dbu, bb.xMax()/dbu, bb.yMax()/dbu))
for i in blk.getInsts():
    if not i.getMaster().isBlock(): continue
    for it in i.getITerms():
        if it.getMTerm().getSigType() != "SIGNAL": continue
        n = it.getNet()
        if n is None: continue
        ok, x, y = it.getAvgXY()
        isout = it.isOutputSignal()
        best = None; frontier = [n]; seen = set(); depth = 0
        while frontier and depth < 4 and best is None:
            nxt = []
            for nn in frontier:
                for o in nn.getITerms():
                    oi = o.getInst()
                    if oi.getName() in seen or oi.getMaster().isBlock(): continue
                    if isout and not o.isInputSignal(): continue
                    if not isout and not o.isOutputSignal(): continue
                    seen.add(oi.getName())
                    if isff(oi.getMaster()):
                        cx, cy = oi.getLocation(); dd = abs(cx - x)/dbu + abs(cy - y)/dbu
                        if best is None or dd < best[0]: best = (dd, oi.getName(), cx/dbu, cy/dbu)
                    else:
                        for o2 in oi.getITerms():
                            if o2.getNet() is None or o2.getMTerm().getSigType() != "SIGNAL": continue
                            if (isout and o2.isOutputSignal()) or ((not isout) and o2.isInputSignal()): nxt.append(o2.getNet())
            frontier = nxt; depth += 1
        if best: out.write("P\t%s\t%s\t%d\t%.2f\t%.2f\t%.2f\t%s\t%.2f\t%.2f\t%d\n" % (i.getName(), it.getMTerm().getName(), isout, x/dbu, y/dbu, best[0], best[1], best[2], best[3], depth))
out.close(); print("RDUMP done")
