# F4G: routed-wire fingerprint per class. env ODB. clock = sigType CLOCK or ot_ms_* or clknet*
import os, odb, hashlib
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock()
def isclk(n):
    nm = n.getName(); return n.getSigType() == "CLOCK" or nm.startswith("ot_ms_") or nm.startswith("clknet")
h = hashlib.sha256(); nclk = nsig = nsig_r = 0; m6 = {"clk": 0, "sig": 0}; m5clk = 0
for n in sorted(b.getNets(), key=lambda n: n.getName()):
    if n.isSpecial(): continue
    c = isclk(n); w = n.getWire()
    if c: nclk += 1
    else:
        nsig += 1
    if w is None: continue
    if not c: nsig_r += 1
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(s):
            sh = s.shape
            ln = "V" if sh.isVia() else sh.getTechLayer().getName()
            if c: h.update(("%s %s %d %d %d %d;" % (n.getName(), ln, sh.xMin(), sh.yMin(), sh.xMax(), sh.yMax())).encode())
            if ln == "M6": m6["clk" if c else "sig"] += 1
print("WFP clk_nets %d clk_sha %s sig_nets %d sig_routed %d M6_shapes %s" % (nclk, h.hexdigest()[:16], nsig, nsig_r, m6))
