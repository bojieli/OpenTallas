"""Relocate reviewed existing KV control flops on legal rows; no connectivity changes.
ODB=... MOVES=<reviewed model JSON> OUT=... RECEIPT=... openroad -python -exit THIS.py
The caller legalizes neighboring movable cells and runs the ordinary geometry/timing gates.
"""
import json
import os
from pathlib import Path
import odb


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main():
    db = odb.dbDatabase.create()
    odb.read_db(db, os.environ['ODB'])
    block = db.getChip().getBlock()
    unit = block.getDbUnitsPerMicron()
    model = json.loads(Path(os.environ['MOVES']).read_text())
    assert model['r2r_captures_gt405'] == 0, 'reviewed proposal has excessive reach'
    assert model['pin_reg']['pin_reg_max'] <= 150, 'reviewed proposal exceeds pin reach'
    moves = model['proposal']
    names = {m['name'] for m in moves}
    assert len(names) == len(moves)
    insts = {i.getName(): i for i in block.getInsts()}
    assert names <= set(insts), 'reviewed instance missing'
    rows = list(block.getRows())
    fixed = []
    for i in insts.values():
        if i.getName() not in names and str(i.getPlacementStatus()) in {'FIRM','LOCKED','COVER'}:
            b = i.getBBox()
            fixed.append((b.xMin(), b.yMin(), b.xMax(), b.yMax()))
    placed = []
    receipt = []
    for m in moves:
        i = insts[m['name']]
        master = i.getMaster()
        assert not master.isBlock() and 'DFF' in master.getName(), 'only existing flop cells may move'
        w, h = master.getWidth(), master.getHeight()
        tx, ty = (round(v * unit) for v in m['new'])
        old = i.getLocation()
        choices = sorted(rows, key=lambda r: abs(r.getOrigin()[1] + h / 2 - ty))
        found = None
        for row in choices[:20]:
            x0, y0 = row.getOrigin()
            pitch = row.getSite().getWidth()
            bb = row.getBBox()
            x = round((tx - w / 2 - x0) / pitch) * pitch + x0
            for delta in [0] + [d for j in range(1, 41) for d in (j, -j)]:
                xx = x + delta * pitch
                rect = (xx, y0, xx + w, y0 + h)
                if xx < bb.xMin() or xx + w > bb.xMax():
                    continue
                if any(overlap(rect, other) for other in fixed + placed):
                    continue
                found = (xx, y0, str(row.getOrient()), rect)
                break
            if found:
                break
        assert found, 'no legal reviewed neighborhood for ' + m['name']
        x, y, orient, rect = found
        i.setOrient(orient)
        i.setLocation(x, y)
        i.setPlacementStatus('FIRM')
        placed.append(rect)
        receipt.append(dict(name=m['name'], old_origin_um=[v/unit for v in old],
                            new_origin_um=[x/unit,y/unit], requested_center_um=m['new'],
                            orientation=orient, master=master.getName(), status='FIRM'))
    odb.write_db(db, os.environ['OUT'])
    Path(os.environ['RECEIPT']).write_text(json.dumps(dict(
        operation='existing flop relocation only', source=os.environ['ODB'],
        model=os.environ['MOVES'], moved=receipt, connectivity_changed=False,
        actual_geometry_gate='PENDING after native legalization'), indent=2)+'\n')
    print('KV_CONTROL_REACH placed', len(receipt), 'existing flops; connectivity unchanged')


main()
