#!/usr/bin/env python3
"""Inventory source elaboration; never qualify mapped area or physical admission."""
import argparse
import collections
from decimal import Decimal
import hashlib
import json
from pathlib import Path

REG = {'$dff', '$dffe', '$sdff', '$sdffe', '$sdffce', '$adff', '$adffe'}
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inventory(netlist):
    module = netlist['modules']['ot_v41_rom_elem_q_wake_w10']
    cells = module['cells']
    counts = collections.Counter(c['type'] for c in cells.values())
    registers = collections.Counter()
    clock_bits = collections.Counter()
    memories = []
    for name, cell in sorted(cells.items()):
        kind = cell['type']
        if kind in REG:
            width = len(cell['connections']['Q'])
            registers[kind] += width
            clock_bits[str(cell['connections']['CLK'])] += width
        elif kind == '$mem_v2':
            p = cell['parameters']
            fields = {k: int(p[k], 2) for k in ('SIZE', 'WIDTH', 'RD_PORTS', 'WR_PORTS')}
            size, width = fields['SIZE'], fields['WIDTH']
            clocks = cell['connections'].get('WR_CLK', [])
            unique_clocks = set(clocks)
            if len(unique_clocks) != 1:
                raise ValueError('memory requires explicit multi-clock lowering: '+name)
            clock_bits[str([clocks[0]])] += size*width
            fields.update(name=name, write_clock_net=str([clocks[0]]), storage_bits=size*width,
                          read_mux2_count=(size-1)*width*fields['RD_PORTS'],
                          write_mux2_count=size*width*fields['WR_PORTS'])
            memories.append(fields)
    storage = sum(x['storage_bits'] for x in memories)
    total = sum(registers.values()) + storage
    # Deliberately charge every retained memory bit as a clocked DFF.
    clock_endpoints = clock_bits.copy()
    for cell in cells.values():
        if cell["type"] == "ICGx1_ASAP7_75t_R":
            clock_endpoints[str(cell["connections"]["CLK"])] += 1
        elif cell["type"] == "ot_rom_4096x274_m8":
            clock_endpoints[str(cell["connections"]["clk"])] += 1
    buffer_groups = {}
    for net, sinks in sorted(clock_endpoints.items()):
        n = sinks
        levels = []
        # Conditional 32-fanout construction, not extracted CTS or spatial fit.
        for _ in range(14):
            n = (n + 31)//32
            levels.append(n)
        buffer_groups[net] = {'sinks': sinks, 'buffers_by_level': levels,
                              'buffer_count': sum(levels), 'activity_bound': 1}
    buffers = sum(g['buffer_count'] for g in buffer_groups.values())
    return {'schema': 'w10_q_elaboration_inventory_v1',
            'cell_counts': dict(sorted(counts.items())),
            'register_bits_by_type': dict(sorted(registers.items())),
            'storage_bits_by_clock_net': dict(sorted(clock_bits.items())),
            'conditional_clock_reserve': {'groups': buffer_groups,
                'buffer_count': buffers, 'buffer_input_cap_fF': str(Decimal(buffers)*Decimal('1.121')),
                'wire_guard2_cap_fF': str(Decimal(buffers)*500*Decimal('0.145426')*2),
                'scope': '14-stage fanout32/500um conditional reserve; phase, load and spatial fit unqualified',
                'power_W': None, 'peak_current_A': None, 'stop_credit': 0},
            'register_bits': sum(registers.values()), 'memories': memories,
            'memory_storage_bits': storage, 'conservative_storage_clock_sinks': total,
            'memory_read_mux2_count': sum(x['read_mux2_count'] for x in memories),
            'memory_write_mux2_count': sum(x['write_mux2_count'] for x in memories),
            'interface': {n: {'bits': len(p['bits']), 'direction': p['direction']}
                          for n, p in sorted(module['ports'].items())},
            'root_stop_credit': 0, 'physical_admission': False,
            'actual_mapped_standard_area_um2': None,
            'complete_area_bound_um2': None,
            'missing_bound_terms': ['combinational primitive construction',
              'clock buffers and phase', 'reset/enable lowering', 'fanout/hold repair',
              'local capture corridors', 'all-port escape and PG',
              'source-bound voltage/load/slew energy envelope', 'descriptor/hub composition'],
            'scope': 'source elaboration inventory; no synthesis-map, timing, fit or power qualification'}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--netlist', required=True)
    p.add_argument('--source', required=True); p.add_argument('--script', required=True)
    p.add_argument('--log', required=True); p.add_argument('--output', required=True)
    a=p.parse_args(); out=inventory(json.loads(Path(a.netlist).read_text()))
    out['inputs']={k:{'path':getattr(a,k),'sha256':sha(getattr(a,k))}
                   for k in ('netlist','source','script','log')}
    out['source']=json.loads(Path(a.source).read_text())
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')
if __name__=='__main__': main()
