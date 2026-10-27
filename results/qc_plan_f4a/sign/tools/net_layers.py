# routed length by layer + via count + bbox for the named nets (env NETS space-separated, or all ot_ms_* when NETS=ALL)
import os, odb, collections
from openroad import Design, Tech
t = Tech(); d = Design(t); d.readDb(os.environ["ODB"]); b = d.getBlock(); u = b.getDbUnitsPerMicron()
names = os.environ["NETS"].split()
nets = [n for n in b.getNets() if n.getName().startswith("ot_ms_")] if names == ["ALL"] else [b.findNet(x) for x in names]
for n in nets:
    w = n.getWire(); L = collections.Counter(); nv = 0
    if w is None: print(n.getName(), "NO WIRE"); continue
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(s):
            sh = s.shape
            if sh.isVia(): nv += 1; continue
            L[sh.getTechLayer().getName()] += max(sh.getDX(), sh.getDY()) / u
    tot = sum(L.values())
    hp = n.getTermBBox() if hasattr(n, "getTermBBox") else None
    print("%-22s fanout %3d len %7.1f %s vias %d" % (n.getName(), len(n.getITerms()) - 1, tot, " ".join("%s:%.1f" % kv for kv in sorted(L.items())), nv))
