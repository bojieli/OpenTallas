import json, sys, odb
from openroad import Design, Tech
db = odb.dbDatabase.create(); odb.read_db(db, sys.argv[1]); blk = db.getChip().getBlock(); u = blk.getDbUnitsPerMicron()
mv = json.load(open(sys.argv[2]))
found = {}
for k in mv:
    for nm in ("ck_"+k, k):
        i = blk.findInst(nm)
        if i:
            x, y = i.getLocation(); found[k] = (nm, x/u, y/u, i.getMaster().getName(), i.getPlacementStatus()); break
print("moved found", len(found), list(found.items())[:3])
hits = [i for i in blk.getInsts() if any(s in i.getName() for s in ("ectl_q1", "ectl_q2"))][:10]
for i in hits:
    b = i.getBBox(); print("CORE", i.getName(), i.getMaster().getName(), b.xMin()/u, b.yMin()/u, b.xMax()/u, b.yMax()/u)
obs = [o for o in blk.getObstructions()]
print("obstructions", len(obs))
print("insts", len(list(blk.getInsts())), "die", blk.getDieArea().xMax()/u, blk.getDieArea().yMax()/u)
json.dump(found, open(sys.argv[3], "w"))
