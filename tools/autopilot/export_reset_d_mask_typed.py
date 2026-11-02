#!/usr/bin/env python3
"""Read-only OpenDB pin-typed connectivity export; run under openroad -python.
ODB and OUT environment variables select input checkpoint and output JSON.
No placement, routing, timing or shared geometry state is changed.
"""
import hashlib
import json
import os
from pathlib import Path

import odb


def norm(s):
    return s.strip().lstrip('\\').replace('\\[', '[').replace('\\]', ']')


source = Path(os.environ['ODB'])
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
cells, ports = {}, {}
for inst in block.getInsts():
    name = norm(inst.getName())
    if name in cells:
        raise RuntimeError('duplicate normalized instance ' + name)
    pins = {}
    for it in inst.getITerms():
        mt = it.getMTerm()
        if str(mt.getSigType()) in {'POWER', 'GROUND'}:
            continue
        net = it.getNet()
        pins[mt.getName()] = dict(net=None if net is None else norm(net.getName()),
                                 direction=str(mt.getIoType()), signal=str(mt.getSigType()))
    cells[name] = dict(master=inst.getMaster().getName(), ports=pins)
for bt in block.getBTerms():
    if str(bt.getSigType()) in {'POWER', 'GROUND'}:
        continue
    net = bt.getNet()
    ports[norm(bt.getName())] = dict(net=None if net is None else norm(net.getName()),
                                    direction=str(bt.getIoType()), signal=str(bt.getSigType()))
result = dict(schema='opentallas.typed_physical_connectivity.v1',
              source_odb=str(source), source_odb_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              cells=cells, ports=ports)
Path(os.environ['OUT']).write_text(json.dumps(result, separators=(',', ':')) + '\n')
print('TYPED_PHYSICAL_EXPORT', len(cells), 'cells', len(ports), 'ports')
