# rc_calib_wire_dump.py (openroad -python): per-net routed length per layer (um) and via counts from a routed ODB.
import sys, odb
db = odb.dbDatabase.create()
odb.read_db(db, sys.argv[1])
blk = db.getChip().getBlock()
dbu = blk.getDbUnitsPerMicron()
out = open(sys.argv[2], "w")
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
n = 0
for net in blk.getNets():
    st = net.getSigType()
    if st in ("POWER", "GROUND"):
        continue
    w = net.getWire()
    if w is None:
        continue
    acc = {}
    itr = odb.dbWirePathItr(); itr.begin(w); path = odb.dbWirePath(); ps = odb.dbWirePathShape()
    while itr.getNextPath(path):
      while itr.getNextShape(ps):
        s = ps.shape
        if s.isVia():
            v = s.getTechVia() or s.getVia()
            bl = v.getBottomLayer().getName() if v else "?"
            k = "V@" + bl
            acc[k] = acc.get(k, 0) + 1
        else:
            dx, dy = s.getDX(), s.getDY()
            L = (max(dx, dy) - min(dx, dy)) / dbu
            k = s.getTechLayer().getName()
            acc[k] = acc.get(k, 0.0) + L
    out.write(net.getName() + "\t" + st + "\t" + " ".join("%s=%.3f" % kv for kv in sorted(acc.items())) + "\n")
    n += 1
    if n >= lim:
        break
out.close()
print("WIRE_DUMP_DONE", n)
