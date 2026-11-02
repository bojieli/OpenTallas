"""Place reviewed existing clock buffers into vacant legal row sites; no netlist edits.
ODB=... MOVES=... OUT=... RECEIPT=... openroad -python -exit THIS.py
All other instance locations/orientations and all target connections must remain exact.
The caller performs native placement, complete TT/FF, clock-root and DRV checks.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import odb


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main():
    model = json.loads(Path(os.environ['MOVES']).read_text())
    assert model['schema'] == 'opentallas.kv.clock_branch_moves.v1'
    moves = model['proposal']
    assert len(moves) == 2 and len({x['name'] for x in moves}) == 2
    db = odb.dbDatabase.create()
    odb.read_db(db, os.environ['ODB'])
    block = db.getChip().getBlock()
    u = block.getDbUnitsPerMicron()
    insts = {x.getName(): x for x in block.getInsts()}
    names = {x['name'] for x in moves}
    assert names <= insts.keys()

    def untouched_state():
        h = hashlib.sha256()
        for n, i in sorted(insts.items()):
            if n not in names:
                h.update(repr((n, i.getMaster().getName(), tuple(i.getLocation()), str(i.getOrient()))).encode())
        return h.hexdigest()

    before = untouched_state()
    bins, rectangles = {}, []
    step = round(4.0 * u)
    margin = round(.108 * u)  # two native ASAP7 sites on either side

    def keys(rect):
        return ((x, y) for x in range(math.floor(rect[0] / step), math.floor(rect[2] / step) + 1)
                for y in range(math.floor(rect[1] / step), math.floor(rect[3] / step) + 1))

    def reserve(rect):
        k = len(rectangles)
        rectangles.append(rect)
        for tile in keys(rect):
            bins.setdefault(tile, []).append(k)

    for n, i in insts.items():
        if n in names:
            continue
        b = i.getBBox()
        if b.xMax() > b.xMin() and b.yMax() > b.yMin():
            reserve((b.xMin() - margin, b.yMin(), b.xMax() + margin, b.yMax()))
    for b in block.getBlockages():
        r = b.getBBox()
        reserve((r.xMin(), r.yMin(), r.xMax(), r.yMax()))
    receipts = []
    for m in moves:
        i = insts[m['name']]
        master = i.getMaster()
        assert master.getName() == m['master'] == 'BUFx24_ASAP7_75t_R'
        assert not master.isBlock()
        old = tuple(i.getLocation())
        assert all(abs(old[j] / u - m['old_origin_um'][j]) < .0011 for j in range(2))
        assert str(i.getOrient()) == m['old_orientation']
        connections = {p.getMTerm().getName(): p.getNet().getName() if p.getNet() else None
                       for p in i.getITerms()}
        assert connections['A'] == m['input_net'] and connections['Y'] == m['output_net']
        assert str(i.findITerm('A').getNet().getSigType()) == 'CLOCK'
        assert str(i.findITerm('Y').getNet().getSigType()) == 'CLOCK'
        w, h = master.getWidth(), master.getHeight()
        tx, ty = [round(x * u) for x in m['new_center_um']]
        found = None
        for row in sorted(block.getRows(), key=lambda r: abs(r.getOrigin()[1] + h / 2 - ty))[:24]:
            x0, y0 = row.getOrigin()
            pitch = row.getSite().getWidth()
            bounds = row.getBBox()
            xx = round((tx - w / 2 - x0) / pitch) * pitch + x0
            for d in [0] + [q for k in range(1, 81) for q in (k, -k)]:
                x = xx + d * pitch
                r = (x, y0, x + w, y0 + h)
                if x < bounds.xMin() or x + w > bounds.xMax():
                    continue
                nearby = {k for key in keys(r) for k in bins.get(key, [])}
                if any(overlap(r, rectangles[k]) for k in nearby):
                    continue
                found = (x, y0, str(row.getOrient()), r)
                break
            if found:
                break
        assert found, 'no vacant legal reviewed neighborhood: ' + m['name']
        x, y, orient, rect = found
        assert orient in ('R0', 'MX'), 'unexpected row orientation'
        i.setOrient(orient)
        i.setLocation(x, y)
        i.setPlacementStatus('FIRM')
        reserve((rect[0] - margin, rect[1], rect[2] + margin, rect[3]))
        assert connections == {p.getMTerm().getName(): p.getNet().getName() if p.getNet() else None
                               for p in i.getITerms()}
        receipts.append(dict(name=m['name'], master=master.getName(), old_origin_um=[v/u for v in old],
                             actual_origin_um=[x/u, y/u], requested_center_um=m['new_center_um'],
                             actual_orientation=orient, connections=connections))
    assert untouched_state() == before, 'another instance moved'
    odb.write_db(db, os.environ['OUT'])
    Path(os.environ['RECEIPT']).write_text(json.dumps(dict(
        operation='two existing noninverting clock buffers moved only', moved=receipts,
        other_instance_state_sha256=before, target_connections_unchanged=True,
        clock_identity_constraints_cycles_unchanged=True,
        native_placement_TT_FF_DRV_root_checks='PENDING'), indent=2) + '\n')
    print('KV_CLOCK_BRANCH_MOVED', len(receipts), 'buffers; all other instances and target nets unchanged')


main()
