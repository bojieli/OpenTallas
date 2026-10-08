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


def storage(inst):
    outputs=[]
    pins={}
    for pin in inst.getITerms():
        net=pin.getNet()
        pins[pin.getMTerm().getName()]=None if net is None else net.getName()
        if str(pin.getIoType())=='OUTPUT' and net is not None:
            loads=[dict(instance=q.getInst().getName(), master=q.getInst().getMaster().getName(),
                        pin=q.getMTerm().getName()) for q in net.getITerms() if str(q.getIoType())=='INPUT']
            outputs.append(dict(net=net.getName(),pin=pin.getMTerm().getName(),loads=loads))
    return dict(storage_instance=inst.getName(),storage_master=inst.getMaster().getName(),
                connections=pins,outputs=outputs)


def check(block):
    nets = {normalized(n.getName()): n for n in block.getNets()}
    rails = {}
    errors = []
    for rail in ('nonempty', 'empty'):
        name = 'u_rch.' + rail
        net = nets.get(name)
        path = []
        seen = set()
        if net is None:
            # ASAP7 QN mapping can absorb the named positive-polarity wire
            # while retaining its independently named sequential cell.
            matches=[i for i in block.getInsts()
                     if normalized(i.getName()).startswith(name+'$_DFF_')
                     and i.getMaster().getName().upper().startswith('DFF')]
            if len(matches)==1:
                rails[rail]=dict(storage(matches[0]),lookup='source-named mapped DFF; positive-polarity net absorbed')
            else:
                errors.append([rail,'missing net and nonunique source-named storage',len(matches)])
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
                rails[rail] = dict(storage(inst),driver_path=path,lookup='named net driver trace')
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
        elif not any(o['loads'] for o in rails[rail]['outputs']):
            errors.append([rail,'mapped storage has no live output loads'])
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
