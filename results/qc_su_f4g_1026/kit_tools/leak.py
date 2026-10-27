import os, odb
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock()
T, O = [], []
for n in b.getNets():
    w = n.getWire()
    if w is None: continue
    tree = n.getName().startswith("ot_ms_") and n.getName().endswith("_n")
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); s = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(s):
            x = s.shape
            if x.isVia() or x.getTechLayer().getName() != "M6": continue
            (T if tree else O).append((n.getName(), x.xMin(), x.yMin(), x.xMax(), x.yMax()))
def d(a, b):
    dx = max(0, max(a[1], b[1]) - min(a[3], b[3])); dy = max(0, max(a[2], b[2]) - min(a[4], b[4])); return dx, dy
for o in O:
    best = min(T, key=lambda t: sum(d(o, t)))
    print("LEAK", o, "nearest_tree", best, "gap", d(o, best))
