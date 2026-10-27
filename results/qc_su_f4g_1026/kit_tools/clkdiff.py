# per clock net shape diff between ODB A and B
import os, odb
def load(fn):
    db = odb.dbDatabase.create(); odb.read_db(db, fn); b = db.getChip().getBlock(); d = {}
    for n in b.getNets():
        nm = n.getName()
        if not (n.getSigType() == "CLOCK" or nm.startswith("ot_ms_") or nm.startswith("clknet")): continue
        s = set(); w = n.getWire()
        if w:
            it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); sh = odb.dbWirePathShape()
            while it.getNextPath(p):
                while it.getNextShape(sh):
                    x = sh.shape; s.add(("V" if x.isVia() else x.getTechLayer().getName(), x.xMin(), x.yMin(), x.xMax(), x.yMax()))
        d[nm] = s
    return d
A = load(os.environ["A"]); B = load(os.environ["B"])
ch = [k for k in A if A[k] != B.get(k)]
print("CLKDIFF changed_nets", len(ch), "of", len(A))
for k in ch[:20]:
    print("CLKDIFF", k, "removed", sorted(A[k] - B[k])[:4], "added", sorted(B[k] - A[k])[:4], len(A[k] - B[k]), len(B[k] - A[k]))
