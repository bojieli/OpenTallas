import odb
db = odb.dbDatabase.create(); odb.read_db(db, "/in/6_final.odb")
b = db.getChip().getBlock()
clk = set(l.strip() for l in open("/p/clk_freeze_nets.txt") if l.strip())
rects = [(252964,17280,254592,58344),(252964,90720,254592,131784)]
hits = {}
for n in b.getNets():
    w = n.getWire()
    if w is None: continue
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); ps = odb.dbWirePathShape()
    while it.getNextPath(p):
        while it.getNextShape(ps):
            s = ps.shape; ln = ps.layer.getName() if ps.layer else "?"
            if ln not in ("M5","V4"): continue
            for r in rects:
                if s.xMax() > r[0] and s.xMin() < r[2] and s.yMax() > r[1] and s.yMin() < r[3]:
                    hits.setdefault(n.getName(), set()).add(ln)
c = [k for k in hits if k in clk]
print("M5/V4 shapes in B strips: nets", len(hits), "clock(frozen) nets", len(c), c[:10])
print(sorted((k,sorted(v)) for k,v in hits.items())[:40])
