import sys, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
for bl in b.getBlockages():
    bb = bl.getBBox(); 
    if bb.xMax()/u > 1860: print("BLK", bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, bl.isSoft(), bl.getMaxDensity())
for o in b.getObstructions():
    bb = o.getBBox()
    if bb.xMax()/u > 1860: print("OBS", bb.getTechLayer().getName(), bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u)
for i in b.getInsts():
    if i.getMaster().isBlock():
        bb = i.getBBox(); print("MAC", i.getName(), bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, i.getHalo() and (i.getHalo().xMin()/u, i.getHalo().xMax()/u))
st = collections.Counter(); ys = []
fail = set(l.strip().replace("\\","") for l in open(sys.argv[2]) if l.startswith(" u_bound"))
for i in b.getInsts():
    n = i.getName().replace("\\","")
    if n in fail:
        bb = i.getBBox(); st[(str(i.getPlacementStatus()), i.getMaster().getName()[:8])] += 1; ys.append((bb.xMin()/u, bb.yMin()/u))
print(len(fail), st.most_common(6)); print("x range", min(x for x,y in ys), max(x for x,y in ys), "y range", min(y for x,y in ys), max(y for x,y in ys))
ok = set(i.getName().replace("\\","") for i in b.getInsts() if "u_cland_i_host" in i.getName()) - fail
print("cland not failing", len(ok), list(ok)[:3])
for n in list(ok)[:3]:
    i = b.findInst(n) 
