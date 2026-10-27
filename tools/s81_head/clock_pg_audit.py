"""OpenROAD -python; read-only PG connectivity audit for a planned core tree."""
import json
import os
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ODB"])
b = db.getChip().getBlock()
selected, pins, bad = 0, 0, []
for inst in b.getInsts():
    if not inst.getName().startswith(("ot_ms_", "u_isl_")):
        continue
    selected += 1
    for p in inst.getITerms():
        sig = p.getMTerm().getSigType()
        if sig not in ("POWER", "GROUND"):
            continue
        pins += 1
        net = p.getNet()
        if net is None or net.getSigType() != sig:
            bad.append(inst.getName()+"/"+p.getMTerm().getName())
result = dict(scope="Clock/island PG logical connectivity; not IR or physical PG continuity",
              cells=selected, supply_pins=pins, unconnected_or_wrong_type=bad,
              pg_special_wires={n.getName(): len(n.getSWires()) for n in b.getNets()
                                if n.getSigType() in ("POWER", "GROUND")})
with open(os.environ["OUT"], "w") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
