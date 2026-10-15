#!/usr/bin/env python3
"""Emit explicit quadrant headers and ABI from the real static slice ports."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / 'rtl/hbm_accel/generic/vm/static'
PARAMS = {'SW': (7, 5, 1, 0), 'SE': (0, 5, 1, 1),
          'NW': (4, 7, 3, 2), 'NE': (0, 7, 3, 3)}


def render():
    source = (DIR / 'ot_vms_slice_static.sv').read_text()
    header = source.split(')(\n', 1)[1].split('\n);', 1)[0]
    parsed = []
    for line in header.splitlines():
        m = re.fullmatch(r'\s*(input|output) wire\s*(?:\[([^\]]+)\])?\s*(\w+(?:,\w+)*)\s*,?\s*', line)
        if not m:
            raise ValueError(f'Unhandled declaration: {line!r}')
        direction, bounds, names = m.groups()
        for name in names.split(','):
            parsed.append((direction, bounds, name))
    abi = {'schema': 'opentallas.hbm.static-vm-quadrants.v1', 'quadrants': {},
           'historical_views': 'No closed bank/hub/ring view is aliased to these successors.',
           'clocks': 'Twelve separate physical roots; same compiler edge and phase; no asynchronous crossings.',
           'status': 'vmstat is a real three-edge bank/hub/ring aggregate; four quadrant outputs require a real die aggregator.',
           'missing_legacy_ports': {
               'svc_q_r': 'Replaced by actual service landing delivery dq; HBM commands originate at service/loader.',
               'vmap': 'HC aperture producer and consumer remain unimplemented; cannot delete requirement or tie it.',
               'dbk_mv': 'DMA-back command originates from DMA dispatch, not VM storage; actual static dispatch migration pending.'},
           'native_fields': {
               'rq': '{valid, mirror1/global_sector15}',
               'rr': '{valid,data256}',
               'wq,dq,kq': '{valid,sector16,data256,word_mask8}',
               'cq': '{valid,we,byte_addr32,data256,byte_mask32,tag16}',
               'cr': '{valid,tag16,we,data256}',
               'rslot': 'bank-major compiler select: 0..RG-1 read groups, RG packet',
               'wslot': 'bank-major compiler select: 0..WG-1 wide, WG COLL, WG+1 CW, WG+2 packet, WG+3 CCW, WG+4 DMA',
               'ring_tx_source': 'per direction 0transit/1hub/2mirror/3replay-response/4commit-ack',
               'response_enable,response_seq': 'compiler-reserved response edge/identity; absent ack faults at edge without waiting'},
           'clients': {'SW': {'read': ['SU/SFU/HC group', 'DMA back', 'SM xload', 'COLL', 'IDX'], 'write': ['SU/SFU/HC group'],
                              'records': ['argmax', 'coll', 'dma', 'hc', 'idx', 'sfu', 'su']},
                       'SE': {'read': ['SU/SFU/HC group', 'DMA back', 'SM xload', 'COLL', 'IDX'], 'write': ['SU/SFU/HC group'], 'records': []},
                       'NW': {'read': ['SU/SFU/HC group', 'DMA back', 'SM xload', 'CP', 'quant', 'COLL', 'IDX'],
                              'write': ['SU/SFU/HC group', 'CP', 'quant'], 'records': ['cp', 'fmv', 'fused', 'quant']},
                       'NE': {'read': ['SU/SFU/HC group', 'DMA back', 'SM xload', 'attention', 'HC engine', 'COLL', 'IDX'],
                              'write': ['SU/SFU/HC group', 'attention', 'HC engine'], 'records': []}},
           'client_status': 'Declared allocation; each real client source migration must be proved separately. SU F2 native path is at owner.',
           'qualification': 'Actual RTL composition; unit gates do not establish physical closure or full native token execution.'}
    modules = ['`timescale 1ns/1ps', '`default_nettype none']
    for quadrant, (nc, rg, wg, sid) in PARAMS.items():
        values = dict(NC=nc, RG=rg, WG=wg, CW=max(1, nc.bit_length()),
                      RB=rg.bit_length(), WB=(wg + 4).bit_length())
        ports, wiring, entries = [], [], []
        for direction, bounds, name in parsed:
            if name == 'sid':
                wiring.append(f'.sid(2\'d{sid})')
                continue
            if nc == 0 and name in ('cq', 'cr'):
                wiring.append(".cq(338'd0)" if name == 'cq' else '.cr(vacant_cr)')
                continue
            width = 1
            if bounds:
                upper, lower = bounds.rsplit(':', 1)
                upper = upper.replace('((NC>0)?NC:1)', str(max(nc, 1)))
                width = eval(upper, {'__builtins__': {}}, values) - int(lower) + 1
            ports.append(f"    {direction} wire " + (f'[{width-1}:0] ' if width != 1 else '') + name)
            wiring.append(f'.{name}({name})')
            entries.append(dict(name=name, direction=direction, bits=width))
        name = 'hfd_hgi_vms_static_' + quadrant
        modules += [f'module {name} (', ',\n'.join(ports), ');',
                    *( ["    wire [273:0] vacant_cr; // NC=0: no local clients exist."] if nc==0 else []),
                    f'    ot_vms_slice_static #(.NC({nc}),.RG({rg}),.WG({wg})) u_slice (',
                    '        ' + ',\n        '.join(wiring), '    );', 'endmodule']
        abi['quadrants'][quadrant] = dict(master=name, params=values, sid=sid, ports=entries)
    modules.append('`default_nettype wire')
    (DIR / 'hfd_hgi_vms_static.sv').write_text('\n'.join(modules) + '\n')
    path = ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(abi, indent=2) + '\n')


if __name__ == '__main__':
    render()
