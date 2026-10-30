import sys, odb, collections
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
rows = []
for r in b.getRows():
    bb = r.getBBox()
    if bb.xMax()/u > 1866 and bb.yMin()/u < 530: rows.append((bb.xMin()/u, bb.yMin()/u, bb.xMax()/u, bb.yMax()/u, r.getOrient()))
print("rows touching E strip y<530:", len(rows), rows[:4], rows[-2:])
xs = collections.Counter(); bad = []
for i in b.getInsts():
    if "u_cland_i_host" in i.getName() and "/" in i.getName():
        bb = i.getBBox(); x0, y0 = bb.xMin()/u, bb.yMin()/u
        hit = [r for r in rows if r[0] <= x0 and bb.xMax()/u <= r[2] and abs(r[1]-y0) < 1e-3]
        if hit and str(hit[0][4]) != str(i.getOrient()) and str(i.getOrient()) not in ('MY' if str(hit[0][4])=='R0' else 'R180',): bad.append((i.getName(), x0, y0, 'orient', str(i.getOrient()), str(hit[0][4]))); continue
        if hit and (round((x0-hit[0][0])/0.054,6) % 1): bad.append((i.getName(), x0, y0, 'offsite')); continue
        if not hit: bad.append((i.getName(), x0, y0, bb.xMax()/u, i.getPlacementStatus(), i.getMaster().getName()))
print("cland cells not in rows", len(bad)); print(bad[:6])
xb = collections.Counter(x[3] if isinstance(x[3],str) else "norow" for x in bad); print("x hist", xb.most_common(8))
