#!/usr/bin/env python3
"""Export actual routing obstructions; read-only OpenROAD helper."""
import argparse
import json
from pathlib import Path
import odb
from pg_census import transformed_rect

p = argparse.ArgumentParser()
p.add_argument("--odb", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
d = odb.dbDatabase.create()
odb.read_db(d, a.odb)
b = d.getChip().getBlock()
rows = []
for i in b.getInsts():
    if i.getMaster().getName().startswith("CKINVDCx16_"):
        continue
    for box in i.getMaster().getObstructions():
        layer = box.getTechLayer()
        if layer and 1 <= layer.getRoutingLevel() <= 8:
            rows.append([i.getName(), layer.getName(), *transformed_rect(i, box)])
for o in b.getObstructions():
    box = o.getBBox()
    layer = box.getTechLayer()
    if layer and 1 <= layer.getRoutingLevel() <= 8:
        rows.append(["BLOCK", layer.getName(), box.xMin(), box.yMin(), box.xMax(), box.yMax()])
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
(out / "obstructions.json").write_text(json.dumps(dict(dbu=b.getDbUnitsPerMicron(), obstructions=rows)))
print(json.dumps(dict(obstructions=len(rows), by_layer={
    l:sum(r[1] == l for r in rows) for l in sorted({r[1] for r in rows})})))
