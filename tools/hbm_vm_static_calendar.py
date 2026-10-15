#!/usr/bin/env python3
"""Compile native VM port calendars into the actual programme-SRAM word ABI."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['client_seq', 'response_enable', 'response_seq', 'bank_enable',
          'bank_client', 'hub_ring_enable', 'hub_ring_client', 'rslot_v',
          'wslot_v', 'rslot', 'wslot', 'ring_tx_enable', 'ring_tx_source',
          'replay_enable', 'replay_source', 'lg_local_read', 'lg_local_write']


def layout(abi, quadrant):
    shape = abi['quadrants'][quadrant]
    ports = {p['name']: p for p in shape['ports']}
    ports.update(lg_local_read=dict(bits=24), lg_local_write=dict(bits=24))
    fields, cursor = [], 0
    for field in FIELDS:
        bits = ports[field]['bits']
        fields.append(dict(name=field, bits=bits, lo=cursor))
        cursor += bits
    if cursor > 223:
        raise ValueError('calendar exceeds actual protected macro payload')
    return dict(quadrant=quadrant, params=shape['params'], fields=fields,
                bits=cursor, startup_edges=4, sustained_calendars_per_edge=1)


def pack(spec, values):
    unknown = set(values) - set(FIELDS)
    if unknown:
        raise ValueError(f'Unknown native calendar fields: {sorted(unknown)}')
    result = 0
    for field in spec['fields']:
        value = values.get(field['name'], 0)
        if isinstance(value, str):
            value = int(value, 0)
        if not isinstance(value, int) or not 0 <= value < (1 << field['bits']):
            raise ValueError(f"{field['name']} does not fit {field['bits']} bits")
        result |= value << field['lo']
    return result


def compile_schedule(spec, schedule):
    base = schedule.get('base', 0)
    loops = schedule.get('loops', 1)
    cycles = schedule['cycles']
    if not (0 <= base < 1024 and cycles and base + len(cycles) <= 1024):
        raise ValueError('Programme must occupy a nonempty range of actual 1024-word SRAM')
    if not 1 <= loops <= 65535:
        raise ValueError('Loop count must fit the actual nonzero 16-bit counter')
    writes = []
    for offset, values in enumerate(cycles):
        pc = base + offset
        word = (0xc7a1 << 240) | (pc << 224) | pack(spec, values)
        writes.append(dict(addr=pc, data=f'{word:064x}'))
    return dict(schema='opentallas.hbm.native-calendar-programme.v1', layout=spec,
                configuration_writes=writes,
                start=dict(base=base, limit=base+len(cycles), loops=loops),
                output_edges=len(cycles)*loops,
                first_output_after_start=4,
                configuration='Writes and launch are consumed by real input pin registers; no ready/credit path',
                limits='Caller must prove these calendars against actual producer requests, transport latency and response identities.')


def emit_wrappers(abi):
    text = ['`timescale 1ns/1ps', '`default_nettype none']
    layouts = {}
    for quadrant in ('SW', 'SE', 'NW', 'NE'):
        spec = layout(abi, quadrant)
        layouts[quadrant] = spec
        ports = ['input wire clk,rst_n,cfg_we', 'input wire [9:0] cfg_addr',
                 'input wire [255:0] cfg_data', 'input wire start_v',
                 'input wire [9:0] start_base', 'input wire [10:0] start_limit',
                 'input wire [15:0] start_loops',
                 'output wire calendar_v,active,done,fault', 'output wire [31:0] ordinal']
        for field in spec['fields']:
            width = f"[{field['bits']-1}:0] " if field['bits'] > 1 else ''
            ports.append('output wire ' + width + field['name'])
        text += [f'module hfd_hgi_vm_calendar_{quadrant} (',
                 '    ' + ',\n    '.join(ports), ');',
                 f"    wire [{spec['bits']-1}:0] calendar;",
                 f"    ot_vms_calendar_static #(.W({spec['bits']})) u_programme (",
                 '        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),',
                 '        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),',
                 '        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));']
        for field in spec['fields']:
            text.append(f"    assign {field['name']}=calendar[{field['lo']}+:{field['bits']}];")
        text.append('endmodule')
    text.append('`default_nettype wire')
    out = ROOT / 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv'
    out.write_text('\n'.join(text) + '\n')
    out = ROOT / 'results/arch/hbm_vm_calendar_1015/native_layouts.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(layouts, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emit-wrappers', action='store_true')
    parser.add_argument('--quadrant', choices=['SW', 'SE', 'NW', 'NE'])
    parser.add_argument('--schedule', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    abi = json.loads((ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
    if args.emit_wrappers:
        emit_wrappers(abi)
    if args.schedule:
        if not args.quadrant or not args.out:
            parser.error('--schedule requires --quadrant and --out')
        result = compile_schedule(layout(abi, args.quadrant), json.loads(args.schedule.read_text()))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
