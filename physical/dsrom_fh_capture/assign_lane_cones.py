#!/usr/bin/env python3
"""Assign mapped combinational cones to their existing single-lane fences.

Run with OpenROAD -python against a retained ODB. Fixed macros, placement,
rows, PG and pins are unchanged. Sequential cells stop propagation. A cone
with multiple lane sources remains shared; unknown parent/control sources
add no lane ownership. This is physical grouping only, with no logic edit.
"""
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import re
import odb

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--input', default=os.environ.get('FHCONE_INPUT'), required=not os.environ.get('FHCONE_INPUT'))
ap.add_argument('--output', default=os.environ.get('FHCONE_OUTPUT'), required=not os.environ.get('FHCONE_OUTPUT'))
ap.add_argument('--receipt', default=os.environ.get('FHCONE_RECEIPT'), required=not os.environ.get('FHCONE_RECEIPT'))
ap.add_argument('--rect-strips', action='store_true', default=os.environ.get('FHCONE_RECT_STRIPS') == '1')
a = ap.parse_args()
assert Path(a.input).resolve() != Path(a.output).resolve()
assert not Path(a.output).exists()
db = odb.dbDatabase.create()
odb.read_db(db, a.input)
b = db.getChip().getBlock()
insts = list(b.getInsts())
groups = {int(g.getName().removeprefix('fh_lane_')): g for g in b.getGroups()
          if re.fullmatch(r'fh_lane_\d+', g.getName())}
assert set(groups) == set(range(64))
index = {i.getId(): n for n, i in enumerate(insts)}
owner = [0] * len(insts)
inputs, outputs, drivers = {}, {}, {}
comb = set()
for n, i in enumerate(insts):
    group = i.getGroup()
    if group and re.fullmatch(r'fh_lane_\d+', group.getName()):
        owner[n] = 1 << int(group.getName().removeprefix('fh_lane_'))
    if i.getMaster().isBlock():
        m = re.search(r'g_bank\[(\d+)\]', i.getName().replace('\\', ''))
        assert m
        owner[n] = 1 << int(m[1])
    ins, outs = [], []
    for t in i.getITerms():
        net = t.getNet()
        if not net or str(t.getSigType()) != 'SIGNAL':
            continue
        nid = net.getId()
        typ = str(t.getIoType())
        if typ == 'INPUT':
            ins.append(nid)
        elif typ == 'OUTPUT':
            outs.append(nid)
            assert nid not in drivers, ('multiple mapped drivers', net.getName())
            drivers[nid] = n
    inputs[n], outputs[n] = ins, outs
    # ASAP7 sequential masters are DFF*. Macro timing boundaries stop here too.
    if outs and not i.getMaster().isBlock() and not re.match(r'^(DFF|SDFF|LATCH|TAPCELL)', i.getMaster().getName()):
        comb.add(n)
children = {n: [] for n in comb}
degree = {}
for n in comb:
    parents = {drivers[x] for x in inputs[n] if x in drivers and drivers[x] in comb}
    degree[n] = len(parents)
    for p in parents:
        children[p].append(n)
q = deque(n for n in comb if degree[n] == 0)
visited = 0
while q:
    n = q.popleft()
    for net in inputs[n]:
        if net in drivers:
            owner[n] |= owner[drivers[net]]
    visited += 1
    for c in children[n]:
        degree[c] -= 1
        if degree[c] == 0:
            q.append(c)
assert visited == len(comb), ('combinational cycle / unsupported mapped boundary', len(comb)-visited)
added = [0] * 64
shared = 0
for n in comb:
    mask = owner[n]
    if mask and mask & (mask-1) == 0:
        lane = mask.bit_length()-1
        old = insts[n].getGroup()
        if old is None:
            groups[lane].addInst(insts[n])
            added[lane] += 1
        else:
            assert old.getName() == f'fh_lane_{lane}', ('preexisting mixed-lane group', insts[n].getName())
    elif mask & (mask-1):
        shared += 1
        # Never silently keep a mislabeled mixed-lane cell in a lane fence.
        assert insts[n].getGroup() is None, ('mixed-lane grouped cone', insts[n].getName())
receipt = dict(input_sha256=hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),
               added_by_lane=added, mapped_combinational_cells=len(comb),
               shared_multilane_combinational_cells=shared, groups=[])
dbu = db.getTech().getDbUnitsPerMicron()
assert dbu == 1000
row0 = list(b.getRows())[0]
origin = row0.getOrigin()
site = row0.getSite()
sx, sy = site.getWidth(), site.getHeight()
def rect(box):
    return (box.xMin(), box.yMin(), box.xMax(), box.yMax())
rows = [rect(row.getBBox()) for row in b.getRows()]
taps = [rect(i.getBBox()) for i in insts if i.getMaster().getName().startswith('TAPCELL')]
def intersection(x, y):
    return max(0, min(x[2], y[2])-max(x[0], y[0])) * max(0, min(x[3], y[3])-max(x[1], y[1])) / 1e6
macros = {}
for i in insts:
    if i.getMaster().isBlock():
        lane = int(re.search(r'g_bank\[(\d+)\]', i.getName().replace('\\', '')).group(1))
        macros[lane] = rect(i.getBBox())
assert set(macros) == set(range(64))
for lane, g in sorted(groups.items()):
    cells = list(g.getInsts())
    assert not any(i.getMaster().isBlock() for i in cells)
    area = sum(i.getMaster().getWidth()*i.getMaster().getHeight() for i in cells)/1e6
    padded = sum((i.getMaster().getWidth()+4*54)*i.getMaster().getHeight() for i in cells)/1e6
    region = g.getRegion()
    old = list(region.getBoundaries())
    assert len(old) == 1
    box = rect(old[0])
    if a.rect_strips:
        # Entirely above the real29.7um SRAM plus its2um row halo, with
        # additional escape space. Boundaries land on actual std-cell sites.
        x1 = origin[0] + math.ceil((box[0]-origin[0])/sx)*sx
        x2 = origin[0] + math.floor((box[2]-origin[0])/sx)*sx
        y1 = origin[1] + math.ceil((macros[lane][1]+33000-origin[1])/sy)*sy
        y2 = origin[1] + math.floor((box[3]-origin[1])/sy)*sy
        box = (x1, y1, x2, y2)
        assert y1 >= macros[lane][3]+2000 and x1<x2 and y1<y2
        # In 26Q3-1510, dbBox.destroy leaves the old boundary linked in
        # the serialized region. Replace the region, preserving its group
        # and every member, instead of leaving two overlapping boundaries.
        member_ids = {i.getId() for i in cells}
        name, region_type = region.getName(), region.getRegionType()
        region.removeGroup(g)
        odb.dbRegion.destroy(region)
        region = odb.dbRegion.create(b, name)
        region.setRegionType(region_type)
        region.addGroup(g)
        odb.dbBox.create(region, *box)
        assert {i.getId() for i in g.getInsts()} == member_ids
        assert [rect(x) for x in region.getBoundaries()] == [box]
    usable = sum(intersection(box, row) for row in rows) - sum(intersection(box, tap) for tap in taps)
    assert padded < usable*0.95, ('guard5 row capacity exceeded', lane, padded, usable)
    receipt['groups'].append(dict(lane=lane, members=len(cells), area_um2=area, padded_area_um2=padded,
                                  rectangle_dbu=box, usable_after_taps_um2=usable,
                                  capacity_after_guard5_um2=usable*0.95,
                                  guarded_padded_fraction=padded/(usable*0.95)))
odb.write_db(db, a.output)
# Verify the actual serialized geometry consumed by GPL, not an in-memory
# rectangle receipt. C16 exposed that these can differ after box deletion.
check = odb.dbDatabase.create()
odb.read_db(check, a.output)
check_groups = {g.getName(): g for g in check.getChip().getBlock().getGroups()}
for row in receipt['groups']:
    g = check_groups[f"fh_lane_{row['lane']}"]
    assert [rect(x) for x in g.getRegion().getBoundaries()] == [tuple(row['rectangle_dbu'])]
    assert len(list(g.getInsts())) == row['members']
receipt['serialized_regions_verified'] = 64
receipt['output_sha256'] = hashlib.sha256(Path(a.output).read_bytes()).hexdigest()
receipt.update(geometry_changed=a.rect_strips, macro_geometry_changed=False,
               region_geometry_changed=a.rect_strips, macro_pins_changed=False, logic_changed=False,
               added_cycles=0, source_RTL='fd25e1e26c8e50f543a200b7bb46346fabc6c72d')
Path(a.receipt).write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
