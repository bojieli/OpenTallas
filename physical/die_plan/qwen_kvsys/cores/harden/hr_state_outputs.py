#!/usr/bin/env python3
"""Disabled, opt-in zero-cycle recut of pure-state combinational outputs.

Adapted from the peer76 native coupon (16d3289c4). Stage clones the output
function with each state Q replaced by D and by its asynchronous reset value.
Yosys opt_expr must fold the reset cone before finish emits matching private
adffs. Mixed controls, primary inputs, opaque/memory/sequential dependencies,
initialized state and unknown reset values fail closed. Combinational x/z
literals are preserved exactly; the folded reset must still be known. This is a physical
register recut: no native state is changed and no cycle is added. Both native
and emitted equivalence plus a negative control remain required per candidate.
"""
import argparse
import copy
import json

ONE = format(1, '032b')
COMB = {'$not', '$pos', '$neg', '$and', '$or', '$xor', '$xnor', '$reduce_and',
        '$reduce_or', '$reduce_xor', '$reduce_xnor', '$reduce_bool', '$logic_not',
        '$logic_and', '$logic_or', '$shl', '$shr', '$sshl', '$sshr', '$shift',
        '$shiftx', '$lt', '$le', '$eq', '$ne', '$eqx', '$nex', '$ge', '$gt',
        '$add', '$sub', '$mul', '$div', '$mod', '$divfloor', '$modfloor',
        '$pow', '$mux', '$pmux', '$bmux', '$demux', '$bwmux', '$slice', '$concat'}


def stage(source, top, outputs):
    data = copy.deepcopy(source)
    m = data['modules'][top]
    cells, nets, ports = m['cells'], m['netnames'], m['ports']
    drivers = {}
    used = set()
    initialized = {b for n in nets.values() if 'init' in n.get('attributes', {}) for b in n['bits']}
    primary = {b for p in ports.values() if p['direction'] != 'output' for b in p['bits']}
    for name, c in cells.items():
        for pin, bits in c['connections'].items():
            used.update(b for b in bits if isinstance(b, int))
            if c['port_directions'][pin] == 'output':
                for i, b in enumerate(bits):
                    if isinstance(b, int):
                        if b in drivers: raise ValueError(f'multiple drivers: {b}')
                        drivers[b] = (name, i)
    nid = max(used | {1})

    def allocate():
        nonlocal nid
        nid += 1
        return nid

    todo = {}
    for ordinal, pin in enumerate(outputs):
        if '[' in pin:
            pn, ix = pin.rstrip(']').rsplit('[', 1)
            index = int(ix)
        else:
            pn, index = pin, 0
            if len(ports[pn]['bits']) != 1: raise ValueError(f'bit index required: {pn}')
        if ports[pn]['direction'] != 'output': raise ValueError(f'not an output: {pin}')
        b = ports[pn]['bits'][index]
        seen, stack, fs = set(), set(), set()

        def trace(bit):
            if bit in ('0', '1', 'x', 'z'): return
            if bit in stack: raise ValueError(f'{pin}: combinational loop')
            if bit in seen: return
            if bit in primary or not isinstance(bit, int) or bit not in drivers:
                raise ValueError(f'{pin}: primary input, undriven or unknown dependency {bit}')
            name, i = drivers[bit]
            c = cells[name]
            if c['type'] == '$adff':
                if bit in initialized: raise ValueError(f'{pin}: initialized state unsupported')
                rv = c['parameters']['ARST_VALUE'].zfill(len(c['connections']['Q']))
                if set(rv) - {'0', '1'}: raise ValueError(f'{pin}: unknown reset')
                fs.add(name); seen.add(bit); return
            if c['type'] not in COMB: raise ValueError(f'{pin}: opaque/non-combinational {c["type"]}')
            stack.add(bit)
            for p, bits in c['connections'].items():
                if c['port_directions'][p] == 'input':
                    for child in bits: trace(child)
            stack.remove(bit); seen.add(bit)

        trace(b)
        controls = {(tuple(cells[n]['connections']['CLK']), tuple(cells[n]['connections']['ARST']),
                     cells[n]['parameters']['CLK_POLARITY'], cells[n]['parameters']['ARST_POLARITY']) for n in fs}
        if len(controls) != 1: raise ValueError(f'{pin}: no common clock/reset state')
        todo[pin] = dict(port=pn, index=index, bit=b, template=sorted(fs)[0], ordinal=ordinal)
    for kind in ('next', 'reset'):
        cache = {}

        def clone(bit):
            if not isinstance(bit, int): return bit
            if bit in cache: return cache[bit]
            name, index = drivers[bit]
            c = cells[name]
            if c['type'] == '$adff':
                value = c['connections']['D'][index] if kind == 'next' else c['parameters']['ARST_VALUE'].zfill(len(c['connections']['Q']))[::-1][index]
                cache[bit] = value
                return value
            nc = copy.deepcopy(c)
            for p, bits in c['connections'].items():
                if c['port_directions'][p] == 'output':
                    nc['connections'][p] = [allocate() for _ in bits]
                    cache.update(zip(bits, nc['connections'][p]))
            for p, bits in c['connections'].items():
                if c['port_directions'][p] == 'input': nc['connections'][p] = [clone(x) for x in bits]
            nc['attributes'] = {}
            cells[f'hrs_{kind}_{len(cells)}'] = nc
            return cache[bit]

        for pin, t in todo.items():
            name = f'hrs_{kind}_{t["ordinal"]}'
            if name in nets: raise ValueError(f'candidate prefix already present: {name}')
            nets[name] = dict(hide_name=0, bits=[clone(t['bit'])], attributes=dict(keep=ONE))
            t[kind] = name
    return data, dict(top=top, enabled=False, added_cycles=0, outputs=todo)


def finish(source, manifest, mutant=False):
    data = copy.deepcopy(source)
    m = data['modules'][manifest['top']]
    nid = max(b for n in m['netnames'].values() for b in n['bits'] if isinstance(b, int))
    for pin, t in manifest['outputs'].items():
        reset = m['netnames'][t['reset']]['bits']
        nxt = m['netnames'][t['next']]['bits']
        if len(reset) != 1 or reset[0] not in ('0', '1'): raise ValueError(f'{pin}: reset not folded to a known constant: {reset}')
        orig = m['cells'][t['template']]
        c = copy.deepcopy(orig)
        nid += 1
        q = nid
        if mutant:
            nid += 1
            m['cells'][f'hrs_mut_{q}'] = dict(hide_name=0, type='$not', parameters=dict(A_SIGNED='0', A_WIDTH=ONE, Y_WIDTH=ONE), attributes={}, port_directions=dict(A='input', Y='output'), connections=dict(A=nxt, Y=[nid]))
            nxt = [nid]
        c['parameters'].update(WIDTH=ONE, ARST_VALUE=reset[0])
        c['connections'].update(D=nxt, Q=[q])
        c['attributes'] = dict(keep=ONE, src='hr_state_outputs exact next-state recut')
        m['cells'][f'hrs_private_{q}'] = c
        m['ports'][t['port']]['bits'][t['index']] = q
        m['netnames'][t['port']]['bits'][t['index']] = q
    for t in manifest['outputs'].values():
        for kind in ('next', 'reset'): m['netnames'][t[kind]]['attributes'] = {}
    receipt = dict(manifest, added_ff_bits=len(manifest['outputs']), mutant=mutant)
    return data, receipt


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['stage', 'finish']); ap.add_argument('pre'); ap.add_argument('post'); ap.add_argument('manifest')
    ap.add_argument('--top'); ap.add_argument('--output', action='append', default=[]); ap.add_argument('--mutant', action='store_true')
    a = ap.parse_args()
    if a.mode == 'stage':
        if not a.top or not a.output: ap.error('stage requires --top and --output')
        data, report = stage(json.load(open(a.pre)), a.top, a.output)
    else: data, report = finish(json.load(open(a.pre)), json.load(open(a.manifest)), a.mutant)
    with open(a.post, 'w') as f: json.dump(data, f)
    if a.mode == 'stage':
        with open(a.manifest, 'w') as f: json.dump(report, f, indent=2)
    print(json.dumps(dict(top=report['top'], outputs=len(report['outputs']), added_cycles=0, mutant=a.mutant)))


if __name__ == '__main__': main()
