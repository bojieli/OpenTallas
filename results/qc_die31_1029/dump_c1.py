# DIE-QC-31: dump c1 M8/M9 shapes (openroad -python) -> JSON for render_c1.py
import odb, sys, json
out = sys.argv[1]; res = {}
keep = ("ck_mesh","n_P1u","n_B1","n_P1d","n_C1u","n_D1ud")
for f in sys.argv[2:]:
    db = odb.dbDatabase.create(); odb.read_db(db, f); blk = db.getChip().getBlock(); L_ = []
    for n in blk.getNets():
        nn = n.getName(); w = n.getWire()
        if nn not in keep or not w: continue
        it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath()
        while it.getNextPath(p):
            ps = odb.dbWirePathShape()
            while it.getNextShape(ps):
                s = ps.shape
                if s.isVia(): continue
                L = s.getTechLayer().getName()
                if L in ("M8", "M9"): L_.append([nn, L, s.xMin()/1e3, s.yMin()/1e3, s.xMax()/1e3, s.yMax()/1e3])
    res[f] = L_
json.dump(res, open(out, "w"))
