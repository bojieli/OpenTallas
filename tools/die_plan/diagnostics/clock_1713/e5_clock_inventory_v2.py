"""Read-only native ODB clock ownership, NDR and exact F6 macro/IF census."""
import collections
import csv
import json
import os
from pathlib import Path
import odb

db = odb.dbDatabase.create()
odb.read_db(db, os.environ['CLOCK_ODB'])
block = db.getChip().getBlock()
rules = collections.Counter()
rule_rows = {}
for net in block.getNets():
    rule = net.getNonDefaultRule()
    key = rule.getName() if rule else 'DEFAULT'
    rules[key] += 1
    if rule and key not in rule_rows:
        layer_rows = []
        for layer in db.getTech().getLayers():
            x = rule.getLayerRule(layer)
            if x:
                layer_rows.append(dict(layer=layer.getName(), width=x.getWidth(), spacing=x.getSpacing()))
        rule_rows[key] = layer_rows

def clock_pin(inst):
    pins = [p for p in inst.getITerms() if p.isInputSignal() and
            (str(p.getMTerm().getSigType()) == 'CLOCK' or
             p.getMTerm().getName() in {'clk', 'CK', 'CLK', 'CP'})]
    if not pins and inst.getMaster().getName().startswith(('BUF', 'INV')):
        inputs = [p for p in inst.getITerms() if p.isInputSignal()]
        if len(inputs) == 1 and inputs[0].getNet():
            drivers = [p for p in inputs[0].getNet().getITerms() if p.isOutputSignal()]
            if len(drivers) == 1:
                return clock_pin(drivers[0].getInst())
    if len(pins) != 1:
        raise ValueError(f'{inst.getName()}: expected one clock pin, found {len(pins)}')
    return pins[0]

def ancestry(pin):
    path = []
    seen = set()
    net = pin.getNet()
    while net:
        if net.getName() in seen:
            raise ValueError('clock cycle: '+net.getName())
        seen.add(net.getName())
        drivers = [p for p in net.getITerms() if p.isOutputSignal()]
        if len(drivers) != 1:
            return dict(tap=None, depth=len(path), path=path, root=net.getName(), drivers=len(drivers))
        inst = drivers[0].getInst()
        if inst.getName().startswith('ot_dtap_'):
            return dict(tap=inst.getName(), depth=len(path), path=path)
        if not inst.getMaster().getName().startswith(('BUF', 'INV', 'HB', 'CK')):
            raise ValueError('non-buffer clock driver: '+inst.getName())
        path.append(inst.getName())
        inputs = [p for p in inst.getITerms() if p.isInputSignal()]
        if len(inputs) != 1:
            raise ValueError('non-unary clock buffer: '+inst.getName())
        net = inputs[0].getNet()
    raise ValueError('disconnected clock path')

groups = {}
missing = []
with open(os.environ['MACRO_IF_TSV']) as f:
    for row in csv.DictReader(f, delimiter='\t'):
        if row.get('class', '').lower() not in {'launch', 'capture'}:
            continue
        name = row['flop']
        inst = block.findInst(name)
        if not inst:
            missing.append(name)
            continue
        macro = row['macro']
        entry = groups.setdefault(macro, dict(interfaces={}))
        actual_pin=clock_pin(inst)
        endpoint=actual_pin.getInst().getName()+'/'+actual_pin.getMTerm().getName()
        entry['interfaces'][name] = dict(kind=row['class'], clock_endpoint=endpoint, **ancestry(actual_pin))
for macro, entry in groups.items():
    inst = block.findInst(macro)
    if not inst:
        raise ValueError('missing exact macro '+macro)
    actual_pin=clock_pin(inst)
    location=actual_pin.getAvgXY()
    if not location[0]: raise ValueError('macro clock has no physical pin geometry: '+macro)
    entry['macro_clock'] = dict(pin=actual_pin.getMTerm().getName(),xy=list(location[1:]),**ancestry(actual_pin))
    entry['tap_counts'] = dict(collections.Counter(v['tap'] for v in entry['interfaces'].values()))
    entry['depth_counts'] = dict(collections.Counter(v['depth'] for v in entry['interfaces'].values()))
result = dict(source_odb=os.environ['CLOCK_ODB'], ndr_net_counts=dict(rules),
              ndr_layer_rules=rule_rows, macros=groups, missing=sorted(set(missing)))
Path(os.environ['CLOCK_INVENTORY_OUT']).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(dict(ndr_net_counts=dict(rules), macros=len(groups),
                      interfaces=sum(len(x['interfaces']) for x in groups.values()),
                      missing=len(set(missing)))))
if missing:
    raise ValueError('exact F6 interface inventory does not match checkpoint')
