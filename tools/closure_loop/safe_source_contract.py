#!/usr/bin/env python3
"""Source-only NEW-kit SAFE prototype. Not connected to gate/submit or production.

Input is a flattened mapped Yosys write_json and the exact native Liberty files.
Every logical input pin is counted, including reset, macro and constant loads.
Only a function-proven single-input/single-output BUF/INV is transparent.
Clock exemptions apply to Liberty clock pins, never to names or entire nets.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import gzip
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dft.liberty import _parse_groups, _read_text, _strip_heavy, parse_function, expr_vars, evaluate

SCHEMA = 'opentallas.safe_source_contract.prototype.v1'

class ContractError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ContractError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_cells(paths, snapshots=None):
    """Strict scalar adapter; unsupported buses/ports/three-state fail closed.

    The shared Liberty tokenizer/Boolean evaluator is reused, not its permissive
    cell merger (which replaces duplicate masters). Hashes cover original bytes.
    """
    cells = {}
    for path in paths:
        if snapshots is None:
            text = _read_text(Path(path))
        else:
            data = snapshots[str(path)]
            text = (gzip.decompress(data) if Path(path).suffix == '.gz' else data).decode('utf-8')
        root = _parse_groups(_strip_heavy(text))
        libraries = [b for n, _, b in root['groups'] if n == 'library']
        require(libraries, f'no library in {path}')
        for library in libraries:
            for name, args, body in library['groups']:
                if name != 'cell':
                    continue
                require(len(args) == 1 and args[0] not in cells, f'duplicate/invalid master {args}')
                master = args[0]
                pins, seq, macro = {}, [], False
                for kind, pargs, pb in body['groups']:
                    require(kind not in ('bus', 'bundle', 'latch', 'statetable'), f'unsupported {kind} in {master}')
                    if kind == 'pin':
                        require(len(pargs) == 1 and pargs[0] not in pins, f'duplicate pin {master}/{pargs}')
                        a = pb['attrs']
                        require(a.get('direction') in ('input', 'output'), f'unknown/inout direction {master}/{pargs}')
                        require('three_state' not in a, f'tristate {master}/{pargs}')
                        require(a.get('clock', 'false') in ('true', 'false'), f'invalid clock {master}/{pargs}')
                        pins[pargs[0]] = dict(direction=a['direction'], clock=a.get('clock') == 'true',
                                             function=a.get('function'), role='data')
                    elif kind == 'ff':
                        seq.append(pb['attrs'])
                    elif kind == 'memory':
                        macro = True
                require(pins, f'no pins {master}')
                require(len(seq) <= 1, f'multiple FF groups {master}')
                for ff in seq:
                    require('clocked_on' in ff, f'no clock function {master}')
                    clock_expr = parse_function(ff['clocked_on'])
                    clocks = expr_vars(clock_expr)
                    require(len(clocks) == 1 and clocks <= pins.keys(), f'unknown/compound FF clock {master}')
                    clock_pin = next(iter(clocks))
                    require(pins[clock_pin]['direction'] == 'input', f'noninput FF clock {master}')
                    require([evaluate(clock_expr, {clock_pin: v}) for v in (0, 1)] in ([0, 1], [1, 0]),
                            f'nonunary FF clock {master}')
                    for pin in clocks:
                        pins[pin]['clock'] = True
                    for attr in ('clear', 'preset'):
                        if attr in ff:
                            for pin in expr_vars(parse_function(ff[attr])):
                                require(pin in pins and pins[pin]['direction'] == 'input', f'unknown/noninput FF reset {master}/{pin}')
                                pins[pin]['role'] = 'reset'
                for pin, p in pins.items():
                    require(not p['clock'] or p['direction'] == 'input', f'output clock flag {master}/{pin}')
                    if p['clock']:
                        p['role'] = 'clock'
                ins = [p for p in pins if pins[p]['direction'] == 'input']
                outs = [p for p in pins if pins[p]['direction'] == 'output']
                require(outs, f'no output {master}')
                transparent = None
                if not seq and not macro and len(ins) == len(outs) == 1:
                    fn = pins[outs[0]]['function']
                    if fn is not None:
                        expr = parse_function(fn)
                        if expr_vars(expr) == set(ins):
                            truth = [evaluate(expr, {ins[0]: v}) for v in (0, 1)]
                            if truth in ([0, 1], [1, 0]):
                                transparent = (ins[0], outs[0], int(truth == [1, 0]))
                static = not ins and all(pins[p]['function'] in ('0', '1') for p in outs)
                role = 'ff' if seq else 'static' if static else 'macro' if macro or any(pins[p]['function'] is None for p in outs) else 'comb'
                cells[master] = dict(pins=pins, role=role, transparent=transparent)
    require(cells, 'empty native library set')
    return cells


def census(netlist, top, library, max_loads=32):
    require(type(max_loads) is int and 1 <= max_loads <= 32, 'max_loads must be 1..32')
    require(top in netlist.get('modules', {}), 'missing exact top')
    mod = netlist['modules'][top]
    drivers, loads, edges = defaultdict(list), defaultdict(list), {}
    driver_info, cell_info = {}, {}
    all_pins = set()

    def bit_ok(bit):
        require(type(bit) is int or bit in ('0', '1'), f'unknown/high-impedance bit {bit!r}')

    def driver(bit, identity, role, transparent=False):
        bit_ok(bit)
        require(type(bit) is int, f'driven literal {identity}')
        drivers[bit].append(identity)
        driver_info[identity] = dict(net=bit, role=role, transparent=transparent)

    def load(bit, identity, role, owner=None, owner_role=None, owner_master=None):
        bit_ok(bit)
        require(identity not in all_pins, f'duplicate endpoint {identity}')
        all_pins.add(identity)
        loads[bit].append(dict(pin=identity, role=role, owner=owner, owner_role=owner_role, owner_master=owner_master))

    for name, p in mod.get('ports', {}).items():
        require(p['direction'] in ('input', 'output'), f'inout/unknown top port {name}')
        for i, bit in enumerate(p['bits']):
            identity = f'port:{name}[{i}]'
            if p['direction'] == 'input':
                driver(bit, identity, 'input')
            else:
                load(bit, identity, 'output')
    for name, c in mod.get('cells', {}).items():
        require(c['type'] in library, f'unmapped/unknown master {name}:{c["type"]}')
        native = library[c['type']]
        connections = c['connections']
        require(set(connections) == set(native['pins']), f'missing/extra native pins {name}')
        cell_info[name] = native
        for pin, bits in connections.items():
            require(len(bits) == 1, f'non-scalar native pin {name}/{pin}')
            p = native['pins'][pin]
            require(c.get('port_directions', {}).get(pin) == p['direction'], f'direction mismatch {name}/{pin}')
            identity = f'cell:{name}/{pin}'
            if p['direction'] == 'output':
                driver(bits[0], identity, native['role'], native['transparent'] is not None)
            else:
                load(bits[0], identity, p['role'], name, native['role'], c['type'])
        if native['transparent']:
            ip, op, inversion = native['transparent']
            ib, ob = connections[ip][0], connections[op][0]
            edges[f'cell:{name}/{ip}'] = (ob, inversion)
    for bit, ids in drivers.items():
        require(len(ids) == 1, f'multiple drivers net {bit}: {ids}')
    for bit in loads:
        if bit in ('0', '1'):
            identity = f'literal:{bit}'
            driver_info[identity] = dict(net=bit, role='static', transparent=False)
        else:
            require(bit in drivers, f'undriven loaded net {bit}')

    def terminals(bit):
        # Path stack detects even unloaded BUF loops; parity remains explicit.
        todo, seen, endpoints, clocks = [(bit, 0, frozenset())], {}, {}, {}
        while todo:
            net, polarity, ancestry = todo.pop()
            require(net not in ancestry, f'transparent cycle at net {net}')
            if net in seen:
                require(seen[net] == polarity, f'ambiguous polarity reconvergence {net}')
                continue
            seen[net] = polarity
            for endpoint in loads.get(net, []):
                pin = endpoint['pin']
                if pin in edges:
                    nxt, inv = edges[pin]
                    todo.append((nxt, polarity ^ inv, ancestry | {net}))
                else:
                    item = dict(endpoint, inverted=bool(polarity))
                    (clocks if endpoint['role'] == 'clock' else endpoints)[pin] = item
        return list(sorted(endpoints.values(), key=lambda x:x['pin'])), list(sorted(clocks.values(), key=lambda x:x['pin']))

    records = []
    for identity, info in sorted(driver_info.items()):
        endpoints, clocks = terminals(info['net'])
        records.append(dict(driver=identity, **info, loads=len(endpoints), clock_loads=len(clocks),
                            endpoint_roles=dict(Counter(e['role'] for e in endpoints)),
                            sink_classes=dict(Counter(e['owner_role'] or 'top-output' for e in endpoints)),
                            clock_only=bool(clocks) and not endpoints,
                            endpoints=endpoints, clock_endpoints=clocks))
    inputs = []
    for r in records:
        if r['role'] != 'input':
            continue
        data = r['endpoints']
        # Reset/clock status is preserved rather than silently waived.
        registered = bool(data) and all(e['owner'] in cell_info and cell_info[e['owner']]['role'] == 'ff'
                                         and e['role'] == 'data' for e in data)
        inputs.append(dict(port=r['driver'], registered_data_endpoints_only=registered,
                           endpoint_roles=r['endpoint_roles'], clock_loads=r['clock_loads']))
    output_owners = defaultdict(list)
    for r in records:
        if not r['transparent']:
            for endpoint in r['endpoints']:
                if endpoint['role'] == 'output':
                    output_owners[endpoint['pin']].append(r)
    outputs = []
    for bit, endpoints in loads.items():
        for e in endpoints:
            if e['role'] != 'output':
                continue
            candidates = output_owners[e['pin']]
            require(len(candidates) == 1, f'ambiguous output ownership {e["pin"]}')
            owner = candidates[0]
            outputs.append(dict(port=e['pin'], driver=owner['driver'], role=owner['role'],
                                registered=owner['role'] == 'ff'))
    bad = [r['driver'] for r in records if r['loads'] > max_loads]
    literal_holds = [r['driver'] for r in records if r['driver'].startswith('literal:') and r['loads']]
    return dict(schema=SCHEMA, scope='source-prototype-only', top=top, max_allowed=max_loads,
                verdict='FAIL' if bad else 'HOLD' if literal_holds else 'PASS',
                unphysicalized_literals=literal_holds,
                boundary_qualification='not-qualified; input/output records require owner review',
                source_to_netlist_equivalence='not-proved; hashes identify supplied artifacts only', max_loads=max((r['loads'] for r in records), default=0),
                violations=bad, counts=dict(cells=len(cell_info), drivers=len(records), logical_endpoints=len(all_pins),
                                           roles=dict(Counter(r['role'] for r in records))),
                drivers=records, input_registration=inputs, output_ownership=outputs)


def run(contract_path):
    path = Path(contract_path).resolve()
    contract_bytes = path.read_bytes()
    c = json.loads(contract_bytes)
    require(set(c) <= {'schema','enabled','new_kit','production_activation','top','sources','netlist','libraries','max_loads'},
            'unknown contract fields')
    require(type(c.get('top')) is str and c['top'], 'exact nonempty top required')
    require(c.get('schema') == SCHEMA and c.get('enabled') is True and c.get('new_kit') is True,
            'explicit prototype schema/enabled/new_kit required')
    require(c.get('production_activation') is False, 'production activation is not authorized')
    resolved, snapshots, identities = {}, {}, {}
    for key in ('sources', 'netlist', 'libraries'):
        items = c[key] if key != 'netlist' else [c[key]]
        require(items and isinstance(items, list), f'empty {key}')
        resolved[key], identities[key] = [], []
        for item in items:
            require(isinstance(item, dict) and set(item) == {'path','sha256'}, f'invalid {key} identity')
            require(type(item['path']) is str and type(item['sha256']) is str and len(item['sha256']) == 64,
                    f'invalid {key} path/digest')
            p = (path.parent / item['path']).resolve()
            require(p.is_file(), f'{key} missing file {p}')
            data = p.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            require(digest == item['sha256'], f'{key} digest mismatch {p}')
            if key != 'sources':
                snapshots[str(p)] = data
            identities[key].append(dict(path=str(p), sha256=digest))
            require(str(p) not in resolved[key], f'duplicate {key} {p}')
            resolved[key].append(str(p))
    result = census(json.loads(snapshots[resolved['netlist'][0]]), c['top'],
                    native_cells(resolved['libraries'], snapshots), c.get('max_loads', 32))
    result['provenance'] = dict(contract_sha256=hashlib.sha256(contract_bytes).hexdigest(), inputs=identities, collector_sha256=sha(__file__),
                               liberty_parser_sha256=sha(Path(__file__).resolve().parents[1] / 'dft/liberty.py'))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('contract')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    try:
        result = run(a.contract)
    except (ContractError, ValueError, KeyError, IndexError, TypeError, OSError) as e:
        result = dict(schema=SCHEMA, scope='source-prototype-only', verdict='ERROR', error=str(e))
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f'SAFE_SOURCE_PROTOTYPE {result["verdict"]}')
    return 0 if result['verdict'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
