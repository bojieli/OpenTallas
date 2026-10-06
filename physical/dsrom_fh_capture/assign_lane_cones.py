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
import os
from pathlib import Path
import re
import odb

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--input', default=os.environ.get('FHCONE_INPUT'), required=not os.environ.get('FHCONE_INPUT'))
ap.add_argument('--output', default=os.environ.get('FHCONE_OUTPUT'), required=not os.environ.get('FHCONE_OUTPUT'))
ap.add_argument('--receipt', default=os.environ.get('FHCONE_RECEIPT'), required=not os.environ.get('FHCONE_RECEIPT'))
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
for lane, g in sorted(groups.items()):
    cells = list(g.getInsts())
    assert not any(i.getMaster().isBlock() for i in cells)
    area = sum(i.getMaster().getWidth()*i.getMaster().getHeight() for i in cells)/1e6
    padded = sum((i.getMaster().getWidth()+4*54)*i.getMaster().getHeight() for i in cells)/1e6
    receipt['groups'].append(dict(lane=lane, members=len(cells), area_um2=area, padded_area_um2=padded))
odb.write_db(db, a.output)
receipt['output_sha256'] = hashlib.sha256(Path(a.output).read_bytes()).hexdigest()
receipt.update(geometry_changed=False, macro_pins_changed=False, logic_changed=False,
               added_cycles=0, source_RTL='fd25e1e26c8e50f543a200b7bb46346fabc6c72d')
Path(a.receipt).write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps(receipt, indent=2))
