# QC-CORES-2 F4I probe: signal pins under/near PG M2-M5 via-stack M3 pads (stripe-pair columns)
import os, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["ODB"]); b = db.getChip().getBlock()
dbu = b.getDbUnitsPerMicron(); M = float(os.environ.get("MARGIN", "0.1")) * dbu
pads = collections.defaultdict(list)   # layer -> boxes
for n in b.getNets():
    if n.getSigType() not in ("POWER", "GROUND"): continue
    for sw in n.getSWires():
        for s in sw.getWires():
            if not s.isVia(): continue
            v = s.getTechVia() or s.getBlockVia(); x0, y0 = s.getViaXY()
            for vb in v.getBoxes():
                tl = vb.getTechLayer()
                if tl is None: continue
                L = tl.getName()
                if L in ("M2", "M3", "M4"): pads[L].append((x0 + vb.xMin(), y0 + vb.yMin(), x0 + vb.xMax(), y0 + vb.yMax()))
print("PADS", {k: len(v) for k, v in pads.items()})
# bucket M3 pads by row y
m3 = pads["M3"]; xs = sorted(set((p[0] + p[2]) // 2 for p in m3))
cols = sorted(set(round(x / dbu, 3) for x in xs)); print("PAD_COLS_UM", len(cols), cols[:6], "...")
grid = collections.defaultdict(list); G = 2000
for p in m3: grid[(p[1] // G)].append(p)
hot = set(); hotpins = 0; inst_n = 0; tot_area = 0
for i in b.getInsts():
    m = i.getMaster()
    if m.isBlock(): continue
    inst_n += 1; tot_area += m.getWidth() * m.getHeight()
    for it in i.getITerms():
        if it.getSigType() in ("POWER", "GROUND"): continue
        if it.getNet() is None: continue
        r = it.getBBox()
        for k in (r.yMin() // G - 1, r.yMin() // G, r.yMin() // G + 1):
            hit = False
            for p in grid.get(k, []):
                if r.xMax() + M > p[0] and r.xMin() - M < p[2] and r.yMax() + M > p[1] and r.yMin() - M < p[3]:
                    hot.add(i.getName()); hotpins += 1; hit = True; break
            if hit: break
mk = os.environ.get("MARK", "_10830_")
print("PA_HOT margin_um", M / dbu, "insts", inst_n, "hot_insts", len(hot), "hot_pins", hotpins, "marker_in_hot", mk in hot)
