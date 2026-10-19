"""Bounded read-only graph trace of committed A0 native source; no tool build."""
import collections
import functools
import gzip
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parent / 'qwen_a0_ownership_1019'
SOURCE = HERE.parent / 'qwen_a0_reset_1019/r3/candidate.v.gz'
text = gzip.open(SOURCE, 'rt').read()
abstracts = json.load(gzip.open(BASE / 'native_abstracts.json.gz'))['masters']
ownership = json.loads((BASE / 'ownership.json').read_text())
cells = {}
for match in re.finditer(r'\\(\S+)\s+\\(\S+)\s+\((.*?)\);', text, re.S):
    master, name, body = match.groups()
    pins = dict(re.findall(r'\.\\(\S+)\s*\(\\(\S+)\s*\)', body))
    if pins:
        cells[name] = (master, pins)
assert len(cells) == ownership['source_cells']

def output_pins(master, pins):
    if master in abstracts:
        return [p for p in pins if abstracts[master]['pins'][p]['direction'] == 'OUTPUT']
    return [p for p in pins if p in ('Y', 'QN', 'Q', 'H', 'L')]

drivers = {}
consumers = collections.defaultdict(list)
for name, (master, pins) in cells.items():
    outs = output_pins(master, pins)
    for pin, net in pins.items():
        if pin in outs:
            assert net not in drivers, (net, name)
            drivers[net] = (name, pin)
        else:
            consumers[net].append((name, pin))
census = json.load(gzip.open(SOURCE.parent / 'census.json.gz'))
for row in census['all_drivers']:
    for endpoint in row['endpoints']:
        if endpoint.startswith('PORT/'):
            value = ('PORT', endpoint.split('/', 1)[1])
            if value not in consumers[row['net']]:
                consumers[row['net']].append(value)

@functools.lru_cache(None)
def downstream(net):
    result = set()
    for name, pin in consumers[net]:
        if name == 'PORT':
            result.add('PORT/' + pin)
            continue
        master, pins = cells[name]
        if master.startswith('DFF') or master in abstracts:
            result.add(name + '/' + pin)
        else:
            for op in output_pins(master, pins):
                result.update(downstream(pins[op]))
    return frozenset(result)

@functools.lru_cache(None)
def upstream(net):
    if net not in drivers:
        return frozenset(['PORT_OR_ASSIGN/' + net])
    name, pin = drivers[net]
    master, pins = cells[name]
    if master.startswith(('DFF', 'TIE')) or master in abstracts:
        return frozenset([name + '/' + pin])
    outs = output_pins(master, pins)
    result = set()
    for ip, value in pins.items():
        if ip not in outs:
            result.update(upstream(value))
    return frozenset(result)

def describe(endpoint):
    name, pin = endpoint.rsplit('/', 1)
    if name not in cells:
        return {'endpoint': endpoint, 'kind': 'port_or_assign'}
    master, pins = cells[name]
    return {'endpoint': endpoint, 'master': master,
            'kind': 'hard_macro' if master in abstracts else 'sequential',
            'clock': pins.get('CLK'),
            'semantic_outputs': [pins[p] for p in output_pins(master, pins)],
            'physical_coordinate': None}

rows = []
protected_cells = set()
def protect_next_D(net):
    if net not in drivers:
        return
    name, pin = drivers[net]
    master, pins = cells[name]
    if master.startswith(('DFF', 'TIE')) or master in abstracts or name in protected_cells:
        return
    protected_cells.add(name)
    for ip, value in pins.items():
        if ip not in output_pins(master, pins):
            protect_next_D(value)
for root in ownership['roots']:
    if root['master'].startswith('DFF'):
        protect_next_D(root['canonical_native_inputs']['D']['net'])
for root in ownership['roots']:
    endpoints = []
    union = set()
    for sink in root['terminal_ownership']:
        endpoint = sink['endpoint']
        name, pin = endpoint.rsplit('/', 1)
        if name == 'PORT':
            boundaries = [endpoint]
        else:
            master, pins = cells[name]
            if master.startswith('DFF') or master in abstracts:
                boundaries = [endpoint]
            else:
                boundaries = sorted(set().union(*(downstream(pins[p]) for p in output_pins(master, pins))))
        union.update(boundaries)
        endpoints.append({'native_terminal': endpoint, 'first_storage_or_macro_boundaries': boundaries})
    inputs = {pin: {'net': item['net'], 'source_boundaries': sorted(upstream(item['net']))}
              for pin, item in root['canonical_native_inputs'].items()}
    protected = [x['native_terminal'] for x in endpoints
                 if x['native_terminal'].rsplit('/', 1)[0] in protected_cells]
    rows.append({'driver': root['driver'], 'canonical_inputs': inputs,
                 'original_canonical_D_cone_terminals_keep_original_root': protected,
                 'native_terminal_count': len(endpoints),
                 'terminals': endpoints, 'unique_boundaries': [describe(x) for x in sorted(union)]})

out = {'schema': 'opentallas.a0.topology_source_trace.v1',
       'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
       'source_cells': len(cells), 'roots': rows,
       'cut': 'Stop at each actual native DFF input or hard-macro input; do not cross storage.',
       'physical_ownership_qualified': False,
       'note': 'Shared combinational cones may have several storage owners. No centroid or arbitrary owner selected.'}
with gzip.open(HERE / 'source_boundaries.json.gz', 'wt') as f:
    json.dump(out, f, indent=2)
summary = [{'driver': x['driver'], 'terminal_count': x['native_terminal_count'],
            'boundary_count': len(x['unique_boundaries']),
            'boundary_kinds': dict(collections.Counter(b['kind'] for b in x['unique_boundaries'])),
            'boundary_clocks': dict(collections.Counter(b.get('clock') or b['kind'] for b in x['unique_boundaries'])),
            'protected_original_D_cone_terminal_count': len(x['original_canonical_D_cone_terminals_keep_original_root']),
            'canonical_inputs': x['canonical_inputs']} for x in rows]
(HERE / 'source_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps([{k: v for k, v in x.items() if k != 'canonical_inputs'} for x in summary], indent=2))
