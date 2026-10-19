"""Read-only actual synthesized connectivity census; run with openroad -python.

Counts every instance input endpoint, including combinational and hard macro pins.
BUF/INV/HB stages are transparent for a second count. Clock and PG nets remain
in the inventory and are separately classified, never silently omitted.
"""
import collections
import hashlib
import json
import os
import re
import odb

path = os.environ['A0_ODB']
db = odb.dbDatabase.create()
odb.read_db(db, path)
block = db.getChip().getBlock()
transparent = re.compile(r'^(?:BUF|INV|HB)[A-Za-z0-9_]*ASAP7')
sequential = re.compile(r'(?:DFF|SDFF|DHL|DHL|LATCH)')
def label(pin):
    return pin.getInst().getName() + '/' + pin.getMTerm().getName()
def endpoints(net, seen=None):
    seen = set() if seen is None else seen
    if net.getId() in seen:
        return set()
    seen.add(net.getId())
    out = set()
    for pin in net.getITerms():
        if str(pin.getIoType()) != 'INPUT':
            continue
        inst = pin.getInst()
        if transparent.match(inst.getMaster().getName()):
            outputs = [p for p in inst.getITerms() if str(p.getIoType()) == 'OUTPUT' and p.getNet()]
            if len(outputs) == 1:
                out.update(endpoints(outputs[0].getNet(), seen))
                continue
        out.add(label(pin))
    out.update('PORT/' + p.getName() for p in net.getBTerms() if str(p.getIoType()) == 'OUTPUT')
    return out
drivers = []
for net in block.getNets():
    if str(net.getSigType()) in ('POWER', 'GROUND'):
        continue
    inputs = [label(p) for p in net.getITerms() if str(p.getIoType()) == 'INPUT']
    outputs = [p for p in net.getITerms() if str(p.getIoType()) == 'OUTPUT']
    ports = [p for p in net.getBTerms() if str(p.getIoType()) == 'INPUT']
    for pin in outputs + ports:
        inst = pin.getInst() if hasattr(pin, 'getInst') else None
        master = inst.getMaster().getName() if inst else 'INPUT_PORT'
        name = label(pin) if inst else 'PORT/' + pin.getName()
        leaves = sorted(endpoints(net))
        drivers.append(dict(driver=name, master=master, net=net.getName(),
                            sequential=bool(sequential.search(master)),
                            clock_nets=sorted({p.getNet().getName() for p in inst.getITerms()
                                if p.getNet() and (str(p.getMTerm().getSigType()) == 'CLOCK'
                                    or p.getMTerm().getName() in ('CK','CLK','CP','clk'))}) if inst else [],
                            clock=str(net.getSigType()) == 'CLOCK' or name.startswith('PORT/ck'),
                            direct=len(inputs), transparent_loads=len(leaves),
                            endpoints=leaves))
drivers.sort(key=lambda r: (-r['transparent_loads'], r['driver']))
registers = [r for r in drivers if r['sequential'] and not r['clock']]
bad = [r for r in registers if r['transparent_loads'] > 32]
result = dict(schema='opentallas.qwen.a0.actual_driver_census.v1',
              odb_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(),
              source='immutable NK c1r9f synthesized ODB; no placement/timing qualification',
              cells=len(block.getInsts()), masters=dict(collections.Counter(i.getMaster().getName() for i in block.getInsts())),
              drivers=len(drivers), register_outputs=len(registers),
              register_outputs_over32=len(bad), maximum_register_loads=max(r['transparent_loads'] for r in registers),
              violations=bad, all_drivers=drivers)
dbu = block.getDbUnitsPerMicron()
result['std_area_um2'] = sum(i.getMaster().getWidth()*i.getMaster().getHeight()/dbu**2
    for i in block.getInsts() if str(i.getMaster().getType()) != 'BLOCK')
result['hard_area_um2'] = sum(i.getMaster().getWidth()*i.getMaster().getHeight()/dbu**2
    for i in block.getInsts() if str(i.getMaster().getType()) == 'BLOCK')
with open(os.environ['A0_CENSUS'], 'w') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print('A0_ACTUAL_CENSUS', json.dumps({k:result[k] for k in ('cells','drivers','register_outputs','register_outputs_over32','maximum_register_loads')}))
for row in bad[:20]:
    print('A0_DRIVER', row['driver'], row['transparent_loads'])
