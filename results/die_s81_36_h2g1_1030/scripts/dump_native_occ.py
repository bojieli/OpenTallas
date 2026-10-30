# openroad -python: every PLACED instance of the native 3_place as a converter BLOCKAGE row (DIE-S81-36/H2G1 site rule:
# no overlap with native placed std cells/taps/macros). env PLACE OUT
import os, odb
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["PLACE"]); b = db.getChip().getBlock()
U = b.getDbUnitsPerMicron(); n = 0; kinds = {}
with open(os.environ["OUT"], "w") as f:
    for i in b.getInsts():
        if not i.isPlaced(): continue
        bb = i.getBBox(); m = i.getMaster()
        f.write("BLOCKAGE native %.4f %.4f %.4f %.4f\n" % (bb.xMin()/U, bb.yMin()/U, bb.xMax()/U, bb.yMax()/U)); n += 1
        kinds[str(m.getType())] = kinds.get(str(m.getType()), 0) + 1
print("NATIVE_OCC", n, kinds)
