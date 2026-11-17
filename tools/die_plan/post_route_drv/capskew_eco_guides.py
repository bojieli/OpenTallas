# CAPSKEW-ECO (from FABLE-FIX-HEAD-SD9F us_guides.py): for every ripped net, a local M2-M4 guide stack (+ M1 pin access) at each pin
# of a moved / new cell and at every pin of a net without guides, plus one M2-M4 box that joins the old and the new position of a
# moved pin and all pins of a new net.  Existing guides are kept; nets that are not ripped are untouched.
# usage: openroad -python capskew_eco_guides.py IN.odb OUT.odb moved.txt ripped.txt
import odb, sys
IN, OUT, MOVED, RIPPED = sys.argv[1:5]
db = odb.dbDatabase.create(); odb.read_db(db, IN)
blk = db.getChip().getBlock(); tech = db.getTech(); u = blk.getDbUnitsPerMicron()
G = int(round(0.57 * u)); E = 2 * G
lays = [tech.findLayer(n) for n in ("M2", "M3", "M4")]
m1 = tech.findLayer("M1"); m2 = lays[0]
moved = {}
for l in open(MOVED):
    f = l.rstrip("\n").split("\t")
    if len(f) == 5: moved[f[0]] = tuple(int(v) for v in f[1:])
ripped = [l.strip() for l in open(RIPPED) if l.strip()]
def snap(x0, y0, x1, y1):
    return ((x0 - E) // G * G, (y0 - E) // G * G, -(-(x1 + E) // G) * G, -(-(y1 + E) // G) * G)
nadd = 0; nnets = 0
for nm in ripped:
    n = blk.findNet(nm)
    if n is None: print("CAPSKEW_GUIDE missing net", nm); continue
    if n.getITermCount() + n.getBTermCount() < 2: continue
    fresh = len(n.getGuides()) == 0
    boxes = []; allb = []
    for it in n.getITerms():
        b = it.getBBox(); allb.append(b)
        iname = it.getInst().getName()
        if not (fresh or iname in moved): continue
        boxes.append(snap(b.xMin(), b.yMin(), b.xMax(), b.yMax()))
        if iname in moved:
            ox, oy, nx, ny = moved[iname]; dx, dy = ox - nx, oy - ny
            if dx or dy: boxes.append(snap(min(b.xMin(), b.xMin() + dx), min(b.yMin(), b.yMin() + dy), max(b.xMax(), b.xMax() + dx), max(b.yMax(), b.yMax() + dy)))
        for gx in range(b.xMin() // G * G, b.xMax(), G):
            for gy in range(b.yMin() // G * G, b.yMax(), G):
                g1 = odb.dbGuide_create(n, m1, m2, odb.Rect(gx, gy, gx + G, gy + G), False); g1.setIsConnectedToTerm(True)
                odb.dbGuide_create(n, m2, m1, odb.Rect(gx, gy, gx + G, gy + G), False); nadd += 2
    if fresh and allb:
        boxes.append(snap(min(b.xMin() for b in allb), min(b.yMin() for b in allb), max(b.xMax() for b in allb), max(b.yMax() for b in allb)))
    if boxes: nnets += 1
    for (x0, y0, x1, y1) in boxes:
        r = odb.Rect(x0, y0, x1, y1)
        for k, l in enumerate(lays):
            vl = lays[k + 1] if k + 1 < len(lays) else None
            odb.dbGuide_create(n, l, vl if vl else l, r, False); nadd += 1
print("CAPSKEW_GUIDE nets", nnets, "of", len(ripped), "guides added", nadd)
odb.write_db(db, OUT)
