#!/usr/bin/env python3
"""OpenROAD -python helper: exact first captures and native cell area, no placement claim.
Requires native_census.py/textbook_lint.py from the pinned adopted helper revision
on PYTHONPATH. Liberty paths must be the actual synthesis-loaded set.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import odb
from native_census import liberty_roles

p = argparse.ArgumentParser(__doc__)
p.add_argument('--odb', required=True)
p.add_argument('--liberty', action='append', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
roles, receipts = liberty_roles(a.liberty)
db = odb.dbDatabase.create()
odb.read_db(db, a.odb)
b = db.getChip().getBlock()
u = b.getDbUnitsPerMicron()
loads = collections.defaultdict(list)
outputs = collections.defaultdict(list)
ports = collections.defaultdict(list)
cell_rows = []
for inst in b.getInsts():
    master = inst.getMaster()
    role = roles[master.getName()]
    ins, outs, clocks = [], [], []
    for it in inst.getITerms():
        mt, net = it.getMTerm(), it.getNet()
        if str(mt.getSigType()) in ('POWER', 'GROUND') or net is None:
            continue
        pr = role['pins'][mt.getName()]
        if pr.get('clock'):
            clocks.append({'pin': mt.getName(), 'net': net.getName()})
        elif str(mt.getIoType()) == 'INPUT':
            ins.append(it)
        elif str(mt.getIoType()) == 'OUTPUT':
            outs.append(it)
    for it in ins:
        loads[it.getNet().getId()].append((inst, it, role['sequential'], clocks))
    if not role['sequential']:
        outputs[inst.getId()] = [it.getNet().getId() for it in outs]
    cell_rows.append({'instance': inst.getName(), 'master': master.getName(),
                      'sequential': role['sequential'],
                      'area_um2': master.getWidth() * master.getHeight() / (u * u)})
for bt in b.getBTerms():
    if bt.getNet() and str(bt.getIoType()) == 'OUTPUT':
        ports[bt.getNet().getId()].append(bt.getName())
rows = []
for bt in b.getBTerms():
    if str(bt.getIoType()) != 'INPUT' or not bt.getNet():
        continue
    name = bt.getName()
    # Clock-role classification is semantic, not a signal-name exemption.
    initial = bt.getNet().getId()
    reached, todo = set(), [(initial, 0)]
    captures, output_paths, deadends = {}, [], []
    while todo:
        net, depth = todo.pop()
        if net in reached:
            continue
        reached.add(net)
        for op in ports.get(net, []):
            output_paths.append({'port': op, 'combinational_cells': depth})
        if not loads.get(net) and not ports.get(net):
            deadends.append(net)
        for inst, it, seq, clocks in loads.get(net, []):
            if seq:
                key = inst.getName() + '/' + it.getMTerm().getName()
                captures[key] = {'capture': key, 'master': inst.getMaster().getName(),
                                 'clock_pins': clocks,
                                 'one_traversed_path_combinational_cells': depth}
            else:
                todo.extend((n, depth + 1) for n in outputs[inst.getId()])
    rows.append({'input': name, 'first_captures': list(captures.values()),
                 'combinational_output_paths': output_paths,
                 'deadend_net_ids': deadends,
                 'scope': 'distinct first sequential data captures; depth is one traversed path, not STA/max depth'})
up = [r for r in rows if r['input'].startswith('up_in[')]
report = {'schema': 'opentallas.e86_first_capture_and_area.v1',
          'odb_sha256': hashlib.sha256(Path(a.odb).read_bytes()).hexdigest(),
          'liberty': receipts, 'cells': len(cell_rows),
          'sequential_cells': sum(r['sequential'] for r in cell_rows),
          'standard_cell_area_um2': sum(r['area_um2'] for r in cell_rows),
          'input_rows': rows, 'up_in_bits': len(up),
          'up_in_all_have_first_capture': bool(up) and all(r['first_captures'] for r in up),
          'up_in_combinational_to_outputs': sum(len(r['combinational_output_paths']) for r in up),
          'scope': 'native topology/Liberty roles only; no cell functional model, placement/reach/setup/hold or maximum-depth qualification'}
Path(a.out).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('liberty', 'input_rows')}))
