# QC-SU-F4G copy of the F4E m6_strip.py: the tree keeps NDR OT_CK_M6_2S (M6 spacing 96) in the signal route, so a
# signal beside a tree wire needs 96 + 32 + 32 = 160 dbu of open strip: SIDE < 160 (default 128 >= 96 NDR to the obstruction);
# between two NDR trunks 160 apart a signal would need 96 + 32 + 96 = 224 -> no fit.  END 192.
# QC-SU-F4E (ruling QC-SU-F4D (a)): strict layer separation inside the SU core -- signals <= M5, M6 = clock tree only.
# Pass-2 helper. Reads the tree-net (ot_ms_*_n) M6 shapes (wires + via M6 enclosures) of a pass-1 routed DB (REF) and
# writes the complement of those shapes, each bloated by the M6 min spacing, as a list of M6 obstruction rectangles.
# In pass 2 these obstructions leave M6 open ONLY on the exact tracks the tree used in pass 1, so a non-tree net can
# not take M6 anywhere (no wire + spacing fits beside a tree wire inside its own bloated strip).
# usage: openroad -python m6_strip.py   env REF=<pass1 odb> OUT=<rects.txt>
import os, odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ["REF"])
b = db.getChip().getBlock(); tech = db.getTech(); m6 = tech.findLayer("M6")
sp = m6.getSpacing()
die = b.getDieArea(); X0, Y0, X1, Y1 = die.xMin(), die.yMin(), die.xMax(), die.yMax()
rects = []; nnet = 0
for n in b.getNets():
    nm = n.getName()
    if not (nm.startswith("ot_ms_") and nm.endswith("_n")):
        continue
    w = n.getWire()
    if w is None:
        continue
    it = odb.dbWirePathItr(); it.begin(w); p = odb.dbWirePath(); ps = odb.dbWirePathShape(); got = False
    while it.getNextPath(p):
        while it.getNextShape(ps):
            s = ps.shape
            if s.isVia():
                v = s.getTechVia()   # M6 enclosure of a V5/V6 via: take the via bbox (union of its layer boxes)
                if v is not None and "M6" in (v.getBottomLayer().getName(), v.getTopLayer().getName()):
                    rects.append((s.xMin(), s.yMin(), s.xMax(), s.yMax())); got = True
            elif s.getTechLayer().getName() == "M6":
                rects.append((s.xMin(), s.yMin(), s.xMax(), s.yMax())); got = True
    nnet += got
# bloat by spacing, clip to die
# side bloat < 96 dbu (= half-width 16 + one pitch 64 + spacing 32 - 16) keeps every adjacent M6 track unusable; probe3
# with side = end = spacing (32) left the strips unusable for the tree itself (6/114 tree nets on M6), so the default
# side 80 / end 160 clears the spacing-table / EOL rules with margin.
SIDE = int(os.environ.get("SIDE", 128)); END = int(os.environ.get("END", 192)); assert SIDE < 160
def bloat(a, c, e, f):
    hx, hy = (END, SIDE) if (e - a) >= (f - c) else (SIDE, END)
    return (max(X0, a - hx), max(Y0, c - hy), min(X1, e + hx), min(Y1, f + hy))
bl = [bloat(*r) for r in rects]
# complement by elementary y bands
ys = sorted({Y0, Y1} | {r[1] for r in bl} | {r[3] for r in bl})
out = []
for y0, y1 in zip(ys, ys[1:]):
    if y1 <= y0:
        continue
    iv = sorted((r[0], r[2]) for r in bl if r[1] <= y0 and r[3] >= y1)
    x = X0
    for a, e in iv:
        if a > x:
            out.append((x, y0, a, y1))
        x = max(x, e)
    if x < X1:
        out.append((x, y0, X1, y1))
# merge vertically identical x spans in consecutive bands (fewer obstructions)
out.sort(key=lambda r: (r[0], r[2], r[1])); mg = []
for r in out:
    if mg and mg[-1][0] == r[0] and mg[-1][2] == r[2] and mg[-1][3] == r[1]:
        mg[-1] = (r[0], mg[-1][1], r[2], r[3])
    else:
        mg.append(r)
with open(os.environ["OUT"], "w") as f:
    for r in mg:
        f.write("%d %d %d %d\n" % r)
print("M6_STRIP tree_nets_with_M6 %d tree_M6_shapes %d spacing_dbu %d side %d end %d obstructions %d" % (nnet, len(rects), sp, SIDE, END, len(mg)))
