# openroad -python dump.py ODB OUT.csv
import sys, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
die = blk.getDieArea()
with open(sys.argv[2], "w") as f:
    f.write(f"#die,{die.xMin()/u},{die.yMin()/u},{die.xMax()/u},{die.yMax()/u}\n")
    for i in blk.getInsts():
        m = i.getMaster()
        if m.getName().startswith(("TAPCELL", "FILLER", "DECAP")): continue
        b = i.getBBox()
        f.write(f"{m.getName()},{(b.xMin()+b.xMax())/2/u:.2f},{(b.yMin()+b.yMax())/2/u:.2f},{m.getWidth()*m.getHeight()/u/u:.4f}\n")
    for t in blk.getBTerms():
        for p in t.getBPins():
            bb = p.getBBox(); f.write(f"PIN:{t.getName()},{(bb.xMin()+bb.xMax())/2/u:.2f},{(bb.yMin()+bb.yMax())/2/u:.2f},0\n")
