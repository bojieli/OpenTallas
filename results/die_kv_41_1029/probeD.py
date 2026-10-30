import sys, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
for i in blk.getInsts():
    m = i.getMaster()
    if m.isBlock() or m.getWidth()/u > 50:
        b = i.getBBox()
        if 8200 < b.xMax()/u < 8320 and b.yMin()/u < 24700 < b.yMax()/u + 300:
            layers = sorted({o.getTechLayer().getName() for o in m.getObstructions() if o.getTechLayer()})
            print(i.getName(), m.getName(), b.xMin()/u, b.yMin()/u, b.xMax()/u, b.yMax()/u, layers)
