#!/usr/bin/env python3
"""Check actual hard-child receive/transmit flop cuts in source Yosys hierarchy.

This proves source connectivity only; physical pin placement, route, reach,
clock insertion and phi-R delivery remain independent sign-off requirements.
"""
import argparse
import collections
import json
from pathlib import Path


def check(source):
    modules = json.loads(Path(source).read_text())['modules']
    top = modules['ot_s81_hcx_projection_partition']
    rows = []
    primitive_parent = []

    def primitives(name, path, bound):
        for cn, cell in modules[name].get('cells', {}).items():
            kind = cell['type']
            cp = path + '/' + cn
            connections = {pin: [bound.get(bit, (path, bit)) if not isinstance(bit, str) else bit for bit in bits]
                           for pin, bits in cell['connections'].items()}
            if kind in modules and not modules[kind].get('attributes', {}).get('blackbox'):
                child_bound = {}
                for pin, port in modules[kind]['ports'].items():
                    for local, net in zip(port['bits'], connections.get(pin, [])):
                        child_bound[local] = net
                yield from primitives(kind, cp, child_bound)
            else:
                yield cell, connections

    for cn, cell in top.get('cells', {}).items():
        kind = cell['type']
        if kind not in modules or modules[kind].get('attributes', {}).get('blackbox'):
            primitive_parent.append([cn, kind])
            continue
        mod = modules[kind]
        bindings = {bit: ('pin', bit) for port in mod['ports'].values() for bit in port['bits']}
        flat = list(primitives(kind, cn, bindings))
        sinks = collections.defaultdict(list)
        flop_q = set()
        for primitive, connections in flat:
            typ = primitive['type']
            ff = typ.startswith('$') and 'ff' in typ.lower()
            if ff:
                flop_q.update(connections.get('Q', []))
            dirs = primitive.get('port_directions', {})
            if typ in modules:
                dirs = {pin: val['direction'] for pin, val in modules[typ]['ports'].items()}
            for pin, nets in connections.items():
                if dirs.get(pin) == 'input':
                    for net in nets:
                        sinks[net].append((typ, pin, ff))
        bad_inputs, bad_outputs, unused_inputs = [], [], []
        input_bits = output_bits = 0
        for pin, port in mod['ports'].items():
            if pin in ('clk', 'rst_n'):
                continue
            for index, bit in enumerate(port['bits']):
                net = ('pin', bit)
                label = f'{pin}[{index}]'
                if port['direction'] == 'input':
                    input_bits += 1
                    uses = sinks.get(net, [])
                    if not uses:
                        unused_inputs.append(label)
                    bad = [(typ, name) for typ, name, ff in uses if not (ff and name == 'D')]
                    if bad:
                        bad_inputs.append({'pin': label, 'first_logic': bad})
                elif port['direction'] == 'output':
                    output_bits += 1
                    if not isinstance(bit, str) and net not in flop_q:
                        bad_outputs.append(label)
        rows.append({'instance': cn, 'module': kind, 'data_input_bits': input_bits,
                     'data_output_bits': output_bits, 'inputs_before_flop': bad_inputs,
                     'outputs_without_flop': bad_outputs, 'unused_data_inputs': unused_inputs,
                     'pass': not bad_inputs and not bad_outputs})
    return {'scope': __doc__, 'hard_children': len(rows), 'parent_primitive_cells': primitive_parent,
            'pass': not primitive_parent and all(row['pass'] for row in rows), 'rows': rows}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = check(a.source)
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'hard_children': result['hard_children'], 'parent_primitive_cells': result['parent_primitive_cells'],
                      'pass': result['pass'], 'failed_children': [r['instance'] for r in result['rows'] if not r['pass']]}, indent=2))
