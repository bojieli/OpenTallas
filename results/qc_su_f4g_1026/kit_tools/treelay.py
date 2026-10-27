# F4G: per tree net (ot_ms_*_n) wire length by layer (um) and horizontal length on M5 (= trunk dropped off M6). env ODB, NETS (regex)
import os, odb, re, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
rx = re.compile(os.environ.get("NETS", r"^ot_ms_.*_n$")); tot = collections.Counter(); hm5 = 0.0
for n in sorted(b.getNets(), key=lambda n: n.getName()):
    if not rx.search(n.getName()): continue
    w = n.getWire()
    if w is None: print("TL", n.getName(), "UNROUTED"); continue
    L = collections.Counter(); h5 = 0.0
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(s):
            sh = s.shape
            if sh.isVia(): L["via"] += 1; continue
            ln = sh.getTechLayer().getName(); l = max(sh.getDX(), sh.getDY()) / u; L[ln] += l
            if ln == "M5" and sh.getDX() > sh.getDY() and sh.getDX() / u > 0.5: h5 += sh.getDX() / u
    tot.update(L); hm5 += h5
    if os.environ.get("V"): print("TL", n.getName(), {k: round(v, 1) for k, v in sorted(L.items())}, "M5_horiz>0.5um", round(h5, 2))
print("TL_TOTAL", {k: round(v, 1) for k, v in sorted(tot.items())}, "M5_horiz_total", round(hm5, 2))
