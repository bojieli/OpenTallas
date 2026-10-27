# openroad -python: std cells (non-fixed-tree) whose bbox overlaps a sram_pincol_halo strip
import odb, json, os
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
S = json.load(open("/work/sram_pincol_halo.json"))["strips"]
n = 0; hit = []
for i in b.getInsts():
    m = i.getMaster()
    if m.isBlock() or m.getName().startswith(("TAPCELL", "FILL", "DECAP")): continue
    bb = i.getBBox(); x0, y0, x1, y1 = bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u
    for s in S:
        a, c, d, e = s["rect"]
        if x1 > a + 1e-3 and x0 < d - 1e-3 and y1 > c + 1e-3 and y0 < e - 1e-3: hit.append(i.getName()); break
print("STRIP_CHECK blockages", len(list(b.getBlockages())), "cells_in_strips", len(hit), hit[:8])
