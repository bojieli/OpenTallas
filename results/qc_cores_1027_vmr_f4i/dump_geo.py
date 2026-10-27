# QC-CORES-2 F4I render dump: cells (x0,y0,x1,y1,kind), blockages, macros, PG M3 pads in window
import os, odb
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
W = [float(v) for v in os.environ.get("WIN", "112,10,126,22").split(",")]
with open(os.environ["OUT"], "w") as f:
    c = b.getCoreArea(); f.write("core %f %f %f %f\n" % (c.xMin()/u, c.yMin()/u, c.xMax()/u, c.yMax()/u))
    for k in b.getBlockages():
        bb = k.getBBox(); f.write("blk %f %f %f %f\n" % (bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u))
    for i in b.getInsts():
        bb = i.getBBox(); m = i.getMaster(); n = m.getName()
        kind = "macro" if m.isBlock() else "tap" if n.startswith("TAP") else "clk" if i.getName().startswith("ot_ms_") or "clkbuf" in i.getName() else "cell"
        f.write("%s %f %f %f %f %s\n" % (kind, bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, i.getName()))
    for n in b.getNets():
        if n.getSigType() not in ("POWER", "GROUND"): continue
        for sw in n.getSWires():
            for s in sw.getWires():
                if not s.isVia(): continue
                x0, y0 = s.getViaXY()
                if not (W[0]*u < x0 < W[2]*u and W[1]*u < y0 < W[3]*u): continue
                v = s.getTechVia() or s.getBlockVia()
                for vb in v.getBoxes():
                    tl = vb.getTechLayer()
                    if tl is not None and tl.getName() == "M3":
                        f.write("pad %f %f %f %f %s\n" % ((x0+vb.xMin())/u, (y0+vb.yMin())/u, (x0+vb.xMax())/u, (y0+vb.yMax())/u, n.getName()))
