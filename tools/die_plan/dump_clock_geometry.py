"""Read-only OpenDB geometry for a row-legal planned clock trunk; all coordinates DBU integers.

Run with OpenROAD -python -exit SCRIPT; GEOM_ODB/GEOM_OUT/GEOM_ROOT_PORTS are explicit inputs.
No timing, placement or netlist changes are performed.
"""
import json
import os
import re
import odb

path = os.environ['GEOM_ODB']
out = os.environ['GEOM_OUT']
roots = os.environ['GEOM_ROOT_PORTS'].split(',')
db = odb.dbDatabase.create()
odb.read_db(db, path)
b = db.getChip().getBlock()
dbu = db.getTech().getDbUnitsPerMicron()
root_terms = [b.findBTerm(n) for n in roots if b.findBTerm(n)]
if len(root_terms) != 1:
    raise RuntimeError('expected one actual root among '+repr(roots)+': '+repr([x.getName() for x in root_terms]))
root = root_terms[0]
r = root.getBBox()
root_xy = [(r.xMin()+r.xMax())//2, (r.yMin()+r.yMax())//2]
master = None
for lib in db.getLibs():
    m = lib.findMaster('BUFx24_ASAP7_75t_R')
    if m:
        master = m
        break
if master is None:
    raise RuntimeError('actual BUFx24_ASAP7_75t_R master missing')
rows = cells = taps = 0
with open(out, 'w') as f:
    def emit(*fields):
        f.write('\t'.join(str(v) for v in fields)+'\n')
    emit('DBU', dbu)
    r = b.getCoreArea()
    emit('CORE', r.xMin(), r.yMin(), r.xMax(), r.yMax())
    emit('ROOT', *root_xy)
    emit('ROOT_NAME', root.getName())
    emit('MASTER', master.getName(), master.getWidth(), master.getHeight())
    for row in b.getRows():
        x,y = row.getOrigin()
        site = row.getSite()
        emit('ROW', x, y, site.getWidth(), site.getHeight(), row.getSiteCount())
        emit('ROW_ORIENT', row.getName(), x, y, row.getOrient(), row.getSpacing(), row.getDirection())
        rows += 1
    for i in b.getInsts():
        status = str(i.getPlacementStatus()).upper()
        if status not in {'PLACED','FIRM','LOCKED','COVER'}:
            continue
        r = i.getBBox()
        m = i.getMaster()
        emit('CELL', i.getName(), r.xMin(), r.yMin(), r.xMax(), r.yMax(), int(m.isBlock()))
        cells += 1
        if re.fullmatch(r'ot_dtap_[0-9]+',i.getName()):
            ins = [t for t in i.getITerms() if t.isInputSignal()]
            outs = [t for t in i.getITerms() if t.isOutputSignal()]
            if len(ins)!=1 or len(outs)!=1 or ins[0].getNet() is None or outs[0].getNet() is None:
                raise RuntimeError('ambiguous/disconnected tap '+i.getName())
            emit('TAP', i.getName(), (r.xMin()+r.xMax())//2, (r.yMin()+r.yMax())//2,
                 ins[0].getNet().getName(), outs[0].getNet().getName())
            taps += 1
    emit('COUNTS', rows, cells, taps)
print(json.dumps(dict(source=path,output=out,dbu=dbu,root_port=root.getName(),root_xy=root_xy,
                      rows=rows,placed_cells=cells,taps=taps)))
if not rows or not cells or not taps:
    raise RuntimeError('missing actual geometry inventory')
