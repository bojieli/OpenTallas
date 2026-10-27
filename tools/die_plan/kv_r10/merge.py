# CLOCK-KV-R10 probe: union coincident/overlapping VSS shield shapes per (layer, track), then re-extract
import odb, sys, collections, json
from openroad import Design, Tech
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock(); dbu = blk.getDbUnitsPerMicron()
vss = blk.findNet('VSS')
groups = collections.defaultdict(list)
for sw in vss.getSWires():
    for b in sw.getWires():
        if b.isVia(): continue
        ly = b.getTechLayer().getName()
        if ly not in ('M8', 'M9'): continue
        w = min(b.getDX(), b.getDY())
        if w != int(round(0.16 * dbu)): continue
        vert = b.getDY() > b.getDX()
        key = (ly, vert, b.xMin(), b.xMax()) if vert else (ly, vert, b.yMin(), b.yMax())
        groups[key].append((sw, b))
dup = 0; merged = 0; rec = collections.Counter()
for key, items in groups.items():
    if len(items) < 2: continue
    ly, vert = key[0], key[1]
    iv = sorted(((b.yMin(), b.yMax()) if vert else (b.xMin(), b.xMax()), sw, b) for sw, b in items)
    runs = []
    for (lo, hi), sw, b in iv:
        if runs and lo <= runs[-1][1]:
            runs[-1][1] = max(runs[-1][1], hi); runs[-1][2].append((sw, b))
        else:
            runs.append([lo, hi, [(sw, b)]])
    for lo, hi, mem in runs:
        if len(mem) < 2: continue
        dup += len(mem); merged += 1
        sw0, b0 = mem[0]; wt = b0.getWireShapeType(); layer = b0.getTechLayer()
        for sw, b in mem: odb.dbSBox.destroy(b)
        if vert: odb.dbSBox_create(sw0, layer, key[2], lo, key[3], hi, wt)
        else: odb.dbSBox_create(sw0, layer, lo, key[2], hi, key[3], wt)
        rec[ly] += 1
print('OT_MERGE shapes', dup, 'runs', merged, dict(rec))
odb.write_db(db, sys.argv[2])
