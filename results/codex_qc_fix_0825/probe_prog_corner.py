"""Native read-only geometry of the persistent current-aspect PROG DRT hotspot."""
import json
import os
from pathlib import Path
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ['ODB'])
block = db.getChip().getBlock()
scale = db.getTech().getDbUnitsPerMicron()
roi = (245, 105, 292, 148)

def rect(obj):
    return [getattr(obj, k)() / scale for k in ('xMin', 'yMin', 'xMax', 'yMax')]

def hits(r):
    return r[0] < roi[2] and r[2] > roi[0] and r[1] < roi[3] and r[3] > roi[1]

cells = []
for inst in block.getInsts():
    box = rect(inst.getBBox())
    if hits(box):
        cells.append(dict(name=inst.getName(), master=inst.getMaster().getName(),
                          rect=box, macro=inst.getMaster().isBlock(),
                          status=str(inst.getPlacementStatus()), protected=inst.isDoNotTouch()))
pg = []
for net in block.getNets():
    if str(net.getSigType()) not in ('POWER', 'GROUND'):
        continue
    for wire in net.getSWires():
        for box in wire.getWires():
            r = rect(box)
            if hits(r):
                layer = box.getTechLayer()
                pg.append(dict(net=net.getName(), layer=layer.getName() if layer else 'VIA', rect=r))
obs = []
for obj in block.getObstructions():
    box = obj.getBBox()
    r = rect(box)
    if hits(r):
        layer = box.getTechLayer()
        obs.append(dict(layer=layer.getName() if layer else 'NONE', rect=r))
record = dict(odb=os.environ['ODB'], roi=roi, cells=cells, pg=pg, obstructions=obs)
Path(os.environ['OUT']).write_text(json.dumps(record, indent=1) + '\n')
print('PROG_CORNER', len(cells), 'cells', len(pg), 'PG shapes', len(obs), 'route obstructions')
