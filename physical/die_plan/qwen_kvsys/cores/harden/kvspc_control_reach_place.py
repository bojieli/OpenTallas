"""Relocate reviewed existing KV control flops on legal rows; no connectivity changes.
ODB=... MOVES=<reviewed model JSON> OUT=... RECEIPT=... openroad -python -exit THIS.py
The caller legalizes neighboring movable cells and runs the ordinary geometry/timing gates.
"""
import json
import os
import re
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
    # FIRM flops remain resizable by ordinary timing repair. Reserve the largest
    # pin-compatible drive variant plus two sites per side, so a legal x1 seed
    # cannot grow into an adjacent FIRM flop (observed R27 hr_q x1 -> x3).
    masters = [m for lib in db.getLibs() for m in lib.getMasters()]
    def growth_width(master):
        family = re.sub(r'x[0-9]+(?=_ASAP7_)', 'xDRIVE', master.getName())
        pins = {p.getName() for p in master.getMTerms()}
        return max([master.getWidth()] + [m.getWidth() for m in masters
                   if re.sub(r'x[0-9]+(?=_ASAP7_)', 'xDRIVE', m.getName()) == family
                   and m.getHeight() == master.getHeight()
                   and {p.getName() for p in m.getMTerms()} == pins])
    pad = 2 * min(r.getSite().getWidth() for r in rows)
    fixed = []
    for i in insts.values():
        if i.getName() not in names and str(i.getPlacementStatus()) in {'FIRM','LOCKED','COVER'}:
            b = i.getBBox()
            growth = growth_width(i.getMaster()) - i.getMaster().getWidth() if 'DFF' in i.getMaster().getName() else 0
            fixed.append((b.xMin() - pad, b.yMin(), b.xMax() + growth + pad, b.yMax()))
    placed = []
    receipt = []
    for m in moves:
        i = insts[m['name']]
        master = i.getMaster()
        assert not master.isBlock() and 'DFF' in master.getName(), 'only existing flop cells may move'
        w, h = master.getWidth(), master.getHeight()
        reserved_w = growth_width(master)
        tx, ty = (round(v * unit) for v in m['new'])
        old = i.getLocation()
        if 'expected_master' in m:
            assert master.getName() == m['expected_master'], 'reviewed master changed'
        if 'expected_origin_um' in m:
            assert all(abs(old[j]/unit-m['expected_origin_um'][j]) < .0011 for j in range(2)), 'reviewed origin changed'
        connections = {p.getMTerm().getName(): p.getNet().getName() if p.getNet() else None
                       for p in i.getITerms()}
        choices = sorted(rows, key=lambda r: abs(r.getOrigin()[1] + h / 2 - ty))
        found = None
        for row in choices[:20]:
            x0, y0 = row.getOrigin()
            pitch = row.getSite().getWidth()
            bb = row.getBBox()
            x = round((tx - w / 2 - x0) / pitch) * pitch + x0
            for delta in [0] + [d for j in range(1, 41) for d in (j, -j)]:
                xx = x + delta * pitch
                rect = (xx - pad, y0, xx + reserved_w + pad, y0 + h)
                if rect[0] < bb.xMin() or rect[2] > bb.xMax():
                    continue
                if any(overlap(rect, other) for other in fixed + placed):
                    continue
                found = (xx, y0, str(row.getOrient()), rect)
                break
            if found:
                break
        assert found, 'no legal reviewed neighborhood for ' + m['name']
        x, y, orient, rect = found
        # OpenDB refuses setLocation on an already-FIRM recovery checkpoint.
        # Unlock only the reviewed target for this atomic move, then refix it.
        i.setPlacementStatus('PLACED')
        i.setOrient(orient)
        i.setLocation(x, y)
        i.setPlacementStatus('FIRM')
        assert connections == {p.getMTerm().getName(): p.getNet().getName() if p.getNet() else None
                               for p in i.getITerms()}, 'connectivity changed'
        placed.append(rect)
        receipt.append(dict(name=m['name'], old_origin_um=[v/unit for v in old],
                            new_origin_um=[x/unit,y/unit], requested_center_um=m['new'],
                            orientation=orient, master=master.getName(), status='FIRM',
                            reserved_growth_width_um=reserved_w/unit, padding_per_side_um=pad/unit))
    odb.write_db(db, os.environ['OUT'])
    Path(os.environ['RECEIPT']).write_text(json.dumps(dict(
        operation='existing flop relocation only', source=os.environ['ODB'],
        model=os.environ['MOVES'], moved=receipt, connectivity_changed=False,
        actual_geometry_gate='PENDING after native legalization'), indent=2)+'\n')
    print('KV_CONTROL_REACH placed', len(receipt), 'existing flops; connectivity unchanged')


main()
