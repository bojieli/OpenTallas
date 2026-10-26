import json, os, odb
db = odb.dbDatabase.create(); db = odb.read_db(db, os.environ["ODB"])
blk = db.getChip().getBlock()
cells = 0; area = 0.0; macros = {}; ffs = 0
for i in blk.getInsts():
    m = i.getMaster(); a = m.getWidth() * m.getHeight() / (blk.getDbUnitsPerMicron() ** 2)
    if m.getType() == "BLOCK":
        macros[m.getName()] = macros.get(m.getName(), 0) + 1; macros.setdefault("_area", 0); macros["_area"] += a
    else:
        cells += 1; area += a
        if "DFF" in m.getName() or "DHL" in m.getName() or "DLL" in m.getName(): ffs += 1
bits = sum(1 for b in blk.getBTerms() if b.getSigType() not in ("POWER", "GROUND") and b.getName() not in ("VDD", "VSS"))
json.dump(dict(top=blk.getName(), cells=cells, std_area_um2=round(area, 2), ffs=ffs, macros=macros, port_bits=bits),
          open(os.environ["OUT"], "w"), indent=1)
print("ODB_STATS", blk.getName(), cells, round(area, 1), bits)
