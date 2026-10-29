"""Place-only PROG candidate: evacuate combinational congestion from one SRAM corner.

All macros, flops, clock cells, pins, masters and nets remain unchanged. The selected
INV/NAND/OA logic moves into the unused east street; native rows and all existing
footprints/placement blockages define its legal sites. No P&R or timing is run here.
"""
import bisect
import hashlib
import json
import os
from pathlib import Path
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ['ODB'])
b = db.getChip().getBlock()
scale = db.getTech().getDbUnitsPerMicron()
targets = json.loads(Path(os.environ['TARGETS']).read_text()) if os.environ.get('TARGETS') else {}

def rr(obj):
    return [getattr(obj, k)() for k in ('xMin', 'yMin', 'xMax', 'yMax')]

def selected(i):
    m = i.getMaster().getName()
    r = rr(i.getBBox())
    if targets:
        if i.getName() in targets:
            assert m.startswith(('DFF', 'ASYNC_DFF')), i.getName()
            return True
        return False
    # Preserve every register and every clock/buffer/tap cell, even if unmarked.
    if not m.startswith(('INV', 'NAND', 'NOR', 'OA', 'AO', 'AND', 'OR', 'XOR', 'XNOR')):
        return False
    if i.isDoNotTouch() or str(i.getPlacementStatus()) in ('LOCKED', 'COVER'):
        return False
    for t in i.getITerms():
        n = t.getNet()
        if n and (str(n.getSigType()) == 'CLOCK' or n.getName().startswith('ot_ms_')):
            return False
    return 270.6 * scale < r[0] < 281 * scale and 118.8 * scale < r[1] < 140.4 * scale

owned = {i.getName(): i for i in b.getInsts() if selected(i)}
assert owned, 'No combinational cells in the recorded hotspot'
rows = []
for row in b.getRows():
    r = rr(row.getBBox())
    if row.getSpacing() > 0 and (targets or (r[1] >= 108 * scale and r[3] <= 151.2 * scale)):
        lo, hi = (r[0], r[2]) if targets else (max(r[0], int(285.12 * scale)), min(r[2], int(319.68 * scale)))
        if hi > lo:
            rows.append(dict(y=r[1], ey=r[3], rx=r[0], pitch=row.getSpacing(),
                             orient=row.getOrient(), free=[(lo, hi)]))
rows.sort(key=lambda r: r['y'])
ys = [r['y'] for r in rows]
assert rows
maxheight = max(r['ey'] - r['y'] for r in rows)

def cut(box):
    x0, y0, x1, y1 = box
    for j in range(bisect.bisect_left(ys, y0 - maxheight), len(rows)):
        row = rows[j]
        if row['y'] >= y1:
            break
        if row['ey'] <= y0:
            continue
        result = []
        for a, z in row['free']:
            if x1 <= a or x0 >= z:
                result.append((a, z))
            else:
                if a < x0:
                    result.append((a, x0))
                if x1 < z:
                    result.append((x1, z))
        row['free'] = result

for i in b.getInsts():
    if i.getName() not in owned:
        cut(rr(i.getBBox()))
for obj in b.getBlockages():
    cut(rr(obj.getBBox()))

before = {i.getName(): (i.getMaster().getName(), tuple(rr(i.getBBox())),
                       str(i.getOrient()), str(i.getPlacementStatus())) for i in b.getInsts()}
moves = []
for name, i in sorted(owned.items()):
    old = rr(i.getBBox())
    width, height = i.getMaster().getWidth(), i.getMaster().getHeight()
    target = targets.get(name)
    gx, gy = ([round(z * scale) for z in target['origin']] if target else
              [max(old[0] + round(21.6 * scale), round(287.28 * scale)), old[1]])
    region = [round(z * scale) for z in target['region']] if target else None
    best = None
    for row in rows:
        if row['ey'] - row['y'] != height:
            continue
        if region and not (region[1] <= row['y'] and row['ey'] <= region[3]):
            continue
        for a, z in row['free']:
            if region:
                a, z = max(a, region[0]), min(z, region[2])
            if target and 'pin' in target:
                px, py = [v * scale for v in target['pin']]
                spare = target['pin_limit_um'] * scale - abs(row['y'] + height / 2 - py)
                if spare < 0:
                    continue
                a = max(a, int(px - spare - width / 2 + .999))
                z = min(z, int(px + spare + width / 2))
            pitch, rx = row['pitch'], row['rx']
            lo = rx + ((a - rx + pitch - 1) // pitch) * pitch
            hi = rx + ((z - width - rx) // pitch) * pitch
            if lo > hi:
                continue
            x = min(hi, max(lo, rx + round((gx - rx) / pitch) * pitch))
            score = abs(x - gx) + abs(row['y'] - gy)
            item = (score, row['y'], x, row)
            if best is None or item[:3] < best[:3]:
                best = item
    assert best, f'No legal east-street site: {name}'
    _, y, x, row = best
    i.setPlacementStatus('PLACED')
    i.setOrient(row['orient'])
    i.setLocation(x, y)
    i.setPlacementStatus('FIRM')
    new = rr(i.getBBox())
    cut(new)
    moves.append(dict(name=name, master=i.getMaster().getName(),
                      old=[v / scale for v in old], new=[v / scale for v in new]))

for i in b.getInsts():
    if i.getName() in owned:
        continue
    assert before[i.getName()] == (i.getMaster().getName(), tuple(rr(i.getBBox())),
                                  str(i.getOrient()), str(i.getPlacementStatus()))
out = Path(os.environ['OUT'])
odb.write_db(db, str(out))
record = dict(verdict='PLACEMENT_CANDIDATE_ONLY', source=os.environ['ODB'], output=str(out),
              moved=len(moves), added_cells=0, added_cycles=0, other_cells_unchanged=True,
              max_move_um=max(abs(m['new'][0]-m['old'][0])+abs(m['new'][1]-m['old'][1]) for m in moves),
              moves=moves)
out.with_suffix('.json').write_text(json.dumps(record, indent=1)+'\n')
print('PROG_CORNER_SPREAD', record['moved'], 'moved', record['max_move_um'], 'um max')
