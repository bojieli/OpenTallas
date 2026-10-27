# QC-SU-F4A-SIGN: routed (5_2_route) escape of every SRAM signal pin: routed dbWire shapes of the pin's net that overlap the
# pin box (layers) and vias within 1 um of it; plus M5 PG straps.  ODB=... OUT=... openroad -python -exit escape_drt.py
import os, odb
from openroad import Design, Tech
tech = Tech(); d = Design(tech); d.readDb(os.environ["ODB"])
b = d.getBlock(); u = b.getDbUnitsPerMicron(); e = u
f = open(os.environ["OUT"], "w")
for i in b.getInsts():
    if not i.getMaster().isBlock(): continue
    for it in i.getITerms():
        if it.getSigType() != "SIGNAL": continue
        n = it.getNet()
        if n is None: continue
        r = it.getBBox(); x0, y0, x1, y1 = r.xMin(), r.yMin(), r.xMax(), r.yMax()
        lay = ""
        for mp in it.getMTerm().getMPins():
            for bx in mp.getGeometry(): lay = bx.getTechLayer().getName()
        touch, vias = set(), set()
        w = n.getWire()
        if w is not None:
            itr = odb.dbWirePathItr(); itr.begin(w); p = odb.dbWirePath(); ps = odb.dbWirePathShape(); shapes = []
            while itr.getNextPath(p):
                while itr.getNextShape(ps):
                    s = ps.shape; sx0, sy0, sx1, sy1 = s.xMin(), s.yMin(), s.xMax(), s.yMax()
                    if s.isVia():
                        if sx0 <= x1 + e and x0 - e <= sx1 and sy0 <= y1 + e and y0 - e <= sy1:
                            v = s.getTechVia(); vias.add(v.getName() if v else "via")
                        continue
                    t = u // 20
                    if sx0 <= x1 + t and x0 - t <= sx1 and sy0 <= y1 + t and y0 - t <= sy1: touch.add(s.getTechLayer().getName())
        f.write("%s %s %s %s %.4f %.4f %.4f %.4f T=%s V=%s\n" % (i.getName(), it.getMTerm().getName(), n.getName(), lay,
                x0 / u, y0 / u, x1 / u, y1 / u, ",".join(sorted(touch)), ",".join(sorted(vias))))
for n in b.getNets():
    if n.getSigType() not in ("POWER", "GROUND"): continue
    for sw in n.getSWires():
        for w in sw.getWires():
            if w.isVia() or w.getTechLayer().getName() != "M5": continue
            f.write("STRAP %s M5 %.4f %.4f %.4f %.4f\n" % (n.getName(), w.xMin() / u, w.yMin() / u, w.xMax() / u, w.yMax() / u))
f.close(); print("ESC_DRT done")
