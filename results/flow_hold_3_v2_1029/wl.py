import sys, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron()
out = open(sys.argv[2], "w")
for net in blk.getNets():
    if net.getSigType() != "CLOCK": continue
    acc = {}
    g = list(net.getGuides())
    for gd in g:
        b = gd.getBox(); dx, dy = b.dx(), b.dy()
        k = "G" + gd.getLayer().getName(); acc[k] = acc.get(k, 0.0) + (max(dx, dy) - min(dx, dy)) / dbu
    w = net.getWire()
    if w is not None:
        itr = odb.dbWirePathItr(); itr.begin(w); path = odb.dbWirePath(); ps = odb.dbWirePathShape()
        while itr.getNextPath(path):
            while itr.getNextShape(ps):
                s = ps.shape
                if s.isVia():
                    v = s.getTechVia() or s.getVia(); k = "V@" + (v.getBottomLayer().getName() if v else "?"); acc[k] = acc.get(k, 0) + 1
                else:
                    dx, dy = s.getDX(), s.getDY(); k = s.getTechLayer().getName(); acc[k] = acc.get(k, 0.0) + (max(dx, dy) - min(dx, dy)) / dbu
    ndr = net.getNonDefaultRule()
    out.write(net.getName() + "\t" + (ndr.getName() if ndr else "-") + "\t" + " ".join("%s=%.2f" % kv for kv in sorted(acc.items())) + "\n")
out.close(); print("WL_DONE")
