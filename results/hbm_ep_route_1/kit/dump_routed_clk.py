"""HBM-EP-ROUTE-1: ODB=<6_final.odb> OUT=<txt> openroad -python -exit dump_routed_clk.py
Rows: W layer x0 y0 x1 y1 net (routed clock wire segments, um) | B name master x y | M name x0 y0 x1 y1 | P layer x0 y0 x1 y1 (PG stripes M5+)."""
import os, odb
db = odb.read_db(odb.dbDatabase.create(), os.environ["ODB"]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
fh = open(os.environ["OUT"], "w")
for n in blk.getNets():
    if n.getSigType() != "CLOCK" or n.getWire() is None: continue
    dec = odb.dbWireDecoder(); dec.begin(n.getWire()); prev = None; lay = None
    while True:
        op = dec.next()
        if op == odb.dbWireDecoder.END_DECODE: break
        if op in (odb.dbWireDecoder.PATH, odb.dbWireDecoder.JUNCTION, odb.dbWireDecoder.SHORT, odb.dbWireDecoder.VWIRE):
            lay = dec.getLayer().getName(); prev = None
        elif op in (odb.dbWireDecoder.POINT, odb.dbWireDecoder.POINT_EXT):
            p = dec.getPoint()[:2] if op == odb.dbWireDecoder.POINT else dec.getPoint_ext()[:2]
            if prev is not None and p != prev:
                fh.write("W %s %.3f %.3f %.3f %.3f %s\n" % (lay, prev[0]/u, prev[1]/u, p[0]/u, p[1]/u, n.getName()))
            prev = p
        elif op == odb.dbWireDecoder.VIA:
            lay = dec.getVia().getBottomLayer().getName() if False else lay
for i in blk.getInsts():
    m = i.getMaster(); x, y = i.getLocation()
    if m.isBlock():
        b = i.getBBox(); fh.write("M %s %.3f %.3f %.3f %.3f\n" % (i.getName(), b.xMin()/u, b.yMin()/u, b.xMax()/u, b.yMax()/u))
    elif i.getName().startswith("ot_ms_"):
        fh.write("B %s %s %.3f %.3f\n" % (i.getName(), m.getName(), (x + m.getWidth()/2)/u, (y + m.getHeight()/2)/u))
fh.close()
