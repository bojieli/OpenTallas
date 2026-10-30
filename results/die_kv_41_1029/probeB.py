import json, sys, odb
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
s = json.load(open(sys.argv[2]))["sites"]
d = []; miss = 0
for k, (x, y) in s.items():
    i = blk.findInst("ck_" + k)
    if not i: miss += 1; continue
    b = i.getBBox(); cx = (b.xMin()+b.xMax())/2/u; cy = (b.yMin()+b.yMax())/2/u; lx, ly = [v/u for v in i.getLocation()]
    d.append((min(max(abs(lx-x), abs(ly-y)), max(abs(cx-x), abs(cy-y))), k))
d.sort(); print("tree cells", len(s), "missing", miss, "max dev", d[-5:], "n>1um", sum(v > 1 for v, _ in d))
# obstructions/blockages near the 32 repeaters x ~8250-8300
xs = []
for o in blk.getObstructions():
    b = o.getBBox(); 
    if b.xMax()/u > 8200 and b.xMax()/u < 8300 and b.yMin()/u < 24690 and b.yMax()/u > 24600: xs.append((b.getTechLayer().getName(), b.xMin()/u, b.yMin()/u, b.xMax()/u, b.yMax()/u))
print("obs near r447", xs[:10])
for bl in blk.getBlockages():
    b = bl.getBBox()
    if b.xMax()/u > 8200 and b.xMax()/u < 8300 and b.yMin()/u < 24690 and b.yMax()/u > 24600: print("blk", b.xMin()/u, b.yMin()/u, b.xMax()/u, b.yMax()/u)
