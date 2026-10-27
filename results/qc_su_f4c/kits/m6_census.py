# QC-SU-F4C post-DRT census: routed M6 shapes per net class (tree = ot_ms_*_n, other); vias per tree net
import os, odb, collections
from openroad import Design, Tech
t = Tech(); d = Design(t); d.readDb(os.environ["ODB"]); b = d.getBlock(); u = b.getDbUnitsPerMicron()
cls = collections.Counter(); m6len = collections.Counter(); bad = []
for n in b.getNets():
    w = n.getWire()
    if w is None: continue
    nm = n.getName(); tree = nm.startswith("ot_ms_") and nm.endswith("_n")
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape(); has6 = False
    while it.getNextPath(p):
        while it.getNextShape(s):
            sh = s.shape
            if not sh.isVia() and sh.getTechLayer().getName() == "M6":
                has6 = True; m6len["tree" if tree else "other"] += max(sh.getDX(), sh.getDY()) / u
    if has6:
        cls["tree" if tree else "other"] += 1
        if not tree: bad.append(nm)
print("M6_CENSUS nets_on_M6", dict(cls), "M6_um", {k: round(v, 1) for k, v in m6len.items()}, "non_tree_examples", bad[:5])
