# dump routed clock wires (ot_ms_* nets + ck) segments with layer, vias, clock cells, macros, M4/M5 PG straps
import os, odb
from openroad import Design, Tech
t = Tech(); d = Design(t); d.readDb(os.environ["ODB"]); b = d.getBlock(); u = b.getDbUnitsPerMicron()
f = open(os.environ["OUT"], "w")
for n in b.getNets():
    nm = n.getName()
    if not (nm.startswith("ot_ms_") or nm == "ck"): continue
    w = n.getWire()
    if w is None: continue
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(s):
            sh = s.shape
            if sh.isVia(): f.write("VIA %s %.3f %.3f\n" % (nm, (sh.xMin() + sh.xMax()) / 2 / u, (sh.yMin() + sh.yMax()) / 2 / u)); continue
            f.write("W %s %s %.3f %.3f %.3f %.3f\n" % (nm, sh.getTechLayer().getName(), sh.xMin() / u, sh.yMin() / u, sh.xMax() / u, sh.yMax() / u))
for i in b.getInsts():
    bb = i.getBBox()
    if i.getMaster().isBlock(): f.write("MACRO %s %.3f %.3f %.3f %.3f\n" % (i.getName(), bb.xMin() / u, bb.yMin() / u, bb.xMax() / u, bb.yMax() / u))
    elif i.getName().startswith("ot_ms_"): f.write("CK %s %s %.3f %.3f\n" % (i.getName(), i.getMaster().getName(), (bb.xMin() + bb.xMax()) / 2 / u, (bb.yMin() + bb.yMax()) / 2 / u))
for n in b.getNets():
    if n.getSigType() not in ("POWER", "GROUND"): continue
    for sw in n.getSWires():
        for w in sw.getWires():
            if w.isVia(): continue
            L = w.getTechLayer().getName()
            if L in ("M4", "M5"): f.write("PG %s %.3f %.3f %.3f %.3f\n" % (L, w.xMin() / u, w.yMin() / u, w.xMax() / u, w.yMax() / u))
f.close(); print("CKW done")
