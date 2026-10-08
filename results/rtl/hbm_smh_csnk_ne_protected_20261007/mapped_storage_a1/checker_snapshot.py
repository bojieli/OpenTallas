#!/usr/bin/env python3
"""Read-only OpenDB check of protected front_s rail storage after actual mapping.

Run with OpenROAD's Python interpreter. OT_SM_ODB and OT_SM_RAILS_JSON name the
input checkpoint and a fresh output receipt. No design or timing is modified.
"""
import hashlib
import json
import os
from pathlib import Path

import odb


def normalized(name):
    return name.replace('\\', '')


def check(block):
    nets = {normalized(n.getName()): n for n in block.getNets()}
    rails = {}
    errors = []
    for rail in ('nonempty', 'empty'):
        name = 'u_rch.' + rail
        net = nets.get(name)
        path = []
        seen = set()
        while net is not None:
            nn = net.getName()
            if nn in seen:
                errors.append([rail, 'driver loop', nn])
                break
            seen.add(nn)
            drivers = [p for p in net.getITerms() if str(p.getIoType()) == 'OUTPUT']
            if len(drivers) != 1:
                errors.append([rail, 'expected one driver', nn, len(drivers)])
                break
            p = drivers[0]
            inst = p.getInst()
            master = inst.getMaster().getName()
            path.append(dict(net=nn, instance=inst.getName(), master=master, output=p.getMTerm().getName()))
            if master.upper().startswith('DFF'):
                rails[rail] = dict(storage_instance=inst.getName(), storage_master=master, driver_path=path)
                break
            # Permit only harmless mapping inversions/buffers; a synthesized
            # combinational copy of the other rail must never count as storage.
            if not master.upper().startswith(('BUF', 'INV')):
                errors.append([rail, 'non-buffer combinational driver', master])
                break
            inputs = [q for q in inst.getITerms() if str(q.getIoType()) == 'INPUT' and q.getNet() is not None]
            if len(inputs) != 1:
                errors.append([rail, 'ambiguous buffer/inverter input', inst.getName()])
                break
            net = inputs[0].getNet()
        if rail not in rails:
            errors.append([rail, 'no independent mapped DFF resolved', name])
    if len(rails) == 2 and rails['nonempty']['storage_instance'] == rails['empty']['storage_instance']:
        errors.append('both rails collapse to the same mapped storage instance')
    return dict(schema='opentallas.hbm.smh.mapped_rail_storage.v1',
                status='pass' if not errors and len(rails)==2 else 'fail',
                rails=rails, errors=errors,
                scope='distinct mapped storage for the two cached occupancy rails only',
                timing_qualified=False, fault_injection_scope='single cached state bit; existing count/pointers unchanged')


if __name__ == '__main__':
    source = Path(os.environ['OT_SM_ODB'])
    out = Path(os.environ['OT_SM_RAILS_JSON'])
    if out.exists():
        raise RuntimeError('refusing to overwrite rail-storage evidence')
    db = odb.dbDatabase.create()
    odb.read_db(db, str(source))
    result = check(db.getChip().getBlock())
    result['odb_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result['errors'])
    raise SystemExit(result['status'] != 'pass')
