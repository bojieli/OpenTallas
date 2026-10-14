#!/usr/bin/env python3
"""Extract genuine control/return cells from a pre-memory-map Q source graph.

Preserves every original cell, connection, memory and kept arithmetic lane.
The result is a structural candidate, not a physical clock or timing contract.
"""
import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def extract(data, top):
    modules = data['modules']
    original = modules[top]
    aliases = defaultdict(set)
    for name, net in original['netnames'].items():
        if not net.get('hide_name'):
            for bit in net['bits']:
                if isinstance(bit, int):
                    aliases[bit].add(name)

    def owner(name):
        match = re.search(r'g_mac\[([01])\]', name)
        return 'return' + match[1] if match else 'control'

    groups = {name: {} for name in ('control', 'return0', 'return1')}
    kept = {}
    assignment = {}
    for name, cell in original['cells'].items():
        if 'ot_s81_q_lane_pair_native' in cell['type']:
            kept[name] = cell
            continue
        if 'MEMID' in cell.get('parameters', {}):
            group = owner(cell['parameters']['MEMID'])
        elif re.search(r'g_mac\[[01]\]', name):
            group = owner(name)
        else:
            ids = set()
            for port, bits in cell['connections'].items():
                if cell['port_directions'].get(port) == 'output':
                    for bit in bits:
                        for alias in aliases.get(bit, ()):
                            ids.update(re.findall(r'g_mac\[([01])\]', alias))
            group = 'return' + next(iter(ids)) if len(ids) == 1 else 'control'
        groups[group][name] = cell
        assignment[name] = group

    users = defaultdict(set)
    drivers = defaultdict(set)
    for group, cells in list(groups.items()) + [('parent', kept)]:
        for cell in cells.values():
            for port, bits in cell['connections'].items():
                direction = cell['port_directions'][port]
                for bit in bits:
                    if isinstance(bit, int):
                        users[bit].add(group)
                        if direction in ('output', 'inout'):
                            drivers[bit].add(group)
    for port in original['ports'].values():
        for bit in port['bits']:
            if isinstance(bit, int):
                users[bit].add('external')
                if port['direction'] in ('input', 'inout'):
                    drivers[bit].add('external')

    result = json.loads(json.dumps(data))
    parent = result['modules'][top]
    parent['cells'] = dict(kept)
    parent.pop('memories', None)
    receipts = []
    reassembled = dict(kept)
    for group, cells in groups.items():
        model = 'ot_s81_q_' + group + '_native_graph'
        used = {bit for cell in cells.values() for bits in cell['connections'].values()
                for bit in bits if isinstance(bit, int)}
        boundary = sorted(bit for bit in used if users[bit] - {group})
        ports = {}; connection = {}; directions = {}; pin_rows = []
        clock_bits = sorted({bit for cell in cells.values()
                             for port, bits in cell['connections'].items()
                             if port in ('CLK', 'RD_CLK', 'WR_CLK')
                             for bit in bits if isinstance(bit, int) and bit in boundary
                             and group not in drivers[bit]})
        for index, bit in enumerate(clock_bits):
            name = 'clock_' + str(index)
            ports[name] = {'direction': 'input', 'bits': [bit]}
            connection[name] = [bit]
            directions[name] = 'input'
            pin_rows.append({'port': name, 'index': 0, 'source_wire_id': bit,
                             'source_aliases': sorted(aliases.get(bit, ())),
                             'source_groups': sorted(drivers[bit]),
                             'peer_groups': sorted(users[bit] - {group}),
                             'role': 'actual source clock; independent physical binding OPEN'})
        # Each actual crossing wire is exposed once. Original source aliases
        # are retained in the packet so downstream pin assignment uses the ABI.
        for direction in ('input', 'output'):
            bits = [bit for bit in boundary if bit not in clock_bits and ('output' if group in drivers[bit] else 'input') == direction]
            name = 'out_bus' if direction == 'output' else 'in_bus'
            if not bits:
                continue
            ports[name] = {'direction': direction, 'bits': bits}
            connection[name] = bits
            directions[name] = direction
            pin_rows += [{'port': name, 'index': index, 'source_wire_id': bit,
                          'source_aliases': sorted(aliases.get(bit, ())),
                          'source_groups': sorted(drivers[bit]),
                          'peer_groups': sorted(users[bit] - {group})}
                         for index, bit in enumerate(bits)]
        memories = {name: memory for name, memory in original.get('memories', {}).items() if owner(name) == group}
        result['modules'][model] = {'attributes': {'keep_hierarchy': '1'}, 'ports': ports,
                                   'cells': cells, 'memories': memories,
                                   'netnames': {name: net for name, net in original['netnames'].items()
                                                if any(bit in used for bit in net['bits'])}}
        parent['cells']['u_' + group] = {'hide_name': 0, 'type': model, 'parameters': {},
                                       'attributes': {'keep_hierarchy': '1'},
                                       'port_directions': directions, 'connections': connection}
        reassembled.update(cells)
        receipts.append({'group': group, 'module': model, 'cells': len(cells),
                         'memories': list(memories), 'actual_boundary_bits': len(boundary),
                         'pin_source_mapping': pin_rows})
    # This exact compiler-graph comparison precedes synthesis or optimization:
    # no cell, edge, memory, lane, state or stage can be omitted by extraction.
    assert reassembled == original['cells']
    recovered_memories = {name: memory for group in groups for name, memory in
                          result['modules']['ot_s81_q_' + group + '_native_graph']['memories'].items()}
    assert recovered_memories == original.get('memories', {})
    return result, {'schema': 'opentallas.s81.q_native.source_graph_partition.v1',
                    'top': top, 'groups': receipts, 'kept_lanes': list(kept),
                    'exact_cell_connection_reconstruction': True,
                    'exact_memory_reconstruction': True,
                    'physical_admission': False,
                    'open': ['full production functional bench', 'independent actual five-root clock ABI',
                             'leaf mapped areas and sinks', 'assigned native pins/outlines', 'CTS and SS/FF route']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--top', default='ot_v41_rom_elem_q_qxpq_w10')
    args = ap.parse_args()
    result, receipt = extract(json.loads(args.source.read_text()), args.top)
    args.output.mkdir(parents=True, exist_ok=True)
    receipt['source_graph_sha256'] = hashlib.sha256(args.source.read_bytes()).hexdigest()
    (args.output / 'partitioned.json').write_text(json.dumps(result))
    (args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps([(g['group'], g['cells'], g['actual_boundary_bits']) for g in receipt['groups']]))


if __name__ == '__main__':
    main()
