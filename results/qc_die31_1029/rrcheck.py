# DIE-QC-31: geometric check of re-routed nets in the spliced c1 odb: overlap (short) / spacing vs every other net shape on
# the same routing layer; M8/M9 checked at the CK2W2S NDR spacing 0.32, lower layers at 0 (overlap only; DRT owns min rules).
import odb, sys
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); blk = db.getChip().getBlock()
rr = sys.argv[2].split(",")
def boxes(net):
    out = []
    w = net.getWire()
    if not w: return out
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath()
    while it.getNextPath(p):
        ps = odb.dbWirePathShape()
        while it.getNextShape(ps):
            s = ps.shape
            if s.isVia():
                bs = list(s.getTechVia().getBoxes()); ox = s.xMin() - min(b.xMin() for b in bs); oy = s.yMin() - min(b.yMin() for b in bs)
                out += [(b.getTechLayer().getName(), ox + b.xMin(), oy + b.yMin(), ox + b.xMax(), oy + b.yMax()) for b in bs]
            else:
                out.append((s.getTechLayer().getName(), s.xMin(), s.yMin(), s.xMax(), s.yMax()))
    return out
allb = {n.getName(): boxes(n) for n in blk.getNets()}
for sn in blk.getNets():
    if sn.isSpecial():
        for sw in sn.getSWires():
            for b in sw.getWires():
                if not b.isVia(): allb.setdefault(sn.getName(), []).append((b.getTechLayer().getName(), b.xMin(), b.yMin(), b.xMax(), b.yMax()))
bad = 0
for r in rr:
    for (L, x0, y0, x1, y1) in allb[r]:
        sp = 320 if L in ("M8", "M9") else 0
        for on, bl in allb.items():
            if on == r: continue
            for (L2, a0, b0, a1, b1) in bl:
                if L2 != L: continue
                dx = max(a0 - x1, x0 - a1); dy = max(b0 - y1, y0 - b1)
                d = max(dx, dy)   # >0: separated (Chebyshev-ish), <=0 both: overlap
                if (dx < 0 and dy < 0) or (d < sp and min(dx, dy) < 0):
                    if on in ("VDD", "VSS") and d >= 40 and dx < 0 and dy < 0 is False: pass
                    # PG: only true overlaps count (NDR spacing to PG is the tech table, not the clock NDR)
                    if on in ("VDD", "VSS") and not (dx < 0 and dy < 0) and d >= 40: continue
                    bad += 1
                    if bad <= 30: print("VIOL", r, on, L, "gap_um=%.3f" % (d / 1000), "at", x0 / 1000, y0 / 1000, x1 / 1000, y1 / 1000)
print("RRCHECK", sys.argv[1], "violations", bad)
