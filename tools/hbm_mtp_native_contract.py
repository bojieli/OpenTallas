"""Real hfd_mtp_x pin coverage and zero-logic native bus composition.

This is a wiring facade around the existing registered controller, not a
replacement physical view. The published x-master route remains authoritative.
"""
import json
from pathlib import Path


INVENTORY = 'results/rtl/hbm_mtp_20261009_inventory/inventory.json'


def peer(name):
    if name in ('clk', 'rst_n'):
        return 'clock'
    if name.startswith('lg_'):
        return 'su_red'
    if name.startswith(('x_', 't_')):
        return 'router'
    if name in ('u_v', 'u_ready', 'u_id', 'u_mask', 'u_last'):
        return 'coll'
    return 'cmdproc'


def model(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    inv = json.loads((root / INVENTORY).read_text())
    groups = {}
    for port in inv['ports']:
        owner = peer(port['name'])
        if owner == 'clock':
            continue
        prefix = 'f_' if port['direction'] == 'input' else 't_'
        key = prefix + owner
        group = groups.setdefault(key, dict(direction=port['direction'], bits=0, fields=[]))
        group['fields'].append(dict(port=port['name'], lsb=group['bits'], width=port['width']))
        group['bits'] += port['width']
    assert {n: g['bits'] for n, g in groups.items()} == dict(
        f_cmdproc=129, t_cmdproc=494, f_su_red=523, f_router=59,
        t_router=58, t_coll=19, f_coll=1)
    assert sum(g['bits'] for g in groups.values()) == sum(p['width'] for p in inv['ports'])-2
    return dict(schema='opentallas.hbm-mtp-native-contract.v1', adopted=False,
        default_enabled=False, controller_master=inv['master'],
        controller_source=inv['source_commit'], controller_inventory=INVENTORY,
        groups=groups,
        arithmetic='unchanged existing full-shape registered controller',
        emitted_tokens='e_v/e_tok/e_idx to command/token-loop path; not collective',
        expert_union='u_v/u_id/u_mask/u_last to collective, u_ready returns from collective',
        compute=dict(MACs_per_cycle=0, intensity='control only'),
        memory=dict(bytes_per_cycle=0, macros=0),
        replicas=1, mux_demux_fanout='direct wires; no extra mux or fanout',
        routing=dict(signal_tracks=sum(g['bits'] for g in groups.values()),
            channel_capacity_qualified=False),
        area=dict(mapped_controller_um2=inv['mapped_stdcell_area_um2'],
            reserved_slot_um=[466.56, 200.88], facade_extra_cells=0,
            controller_fits_reserved_area=True, native_pin_context_qualified=False),
        latency=dict(facade_added_cycles=0,
            controller_registered_pin_and_skid_cycles='existing ot_hfd_mtp_core contract'),
        qualification='port coverage exact; endpoint producers and real pin views still require integration')


def render_rtl(contract):
    lines = ['`timescale 1ns/1ps', '`default_nettype none',
        '// Default-off wiring facade. Physical x-master closure does not qualify these bus pins.',
        'module hfd_mtp_native #(parameter integer ENABLE=0) (',
        '  input wire clk, input wire rst_n,']
    declarations = []
    for name, group in contract['groups'].items():
        width = group['bits']
        direction = 'input' if group['direction'] == 'input' else 'output'
        declarations.append(f'  {direction} wire [{width-1}:0] {name}')
    lines.append(',\n'.join(declarations))
    lines += [');', '  generate if (ENABLE == 0) begin: off']
    for name, group in contract['groups'].items():
        if group['direction'] == 'output':
            lines.append(f"    assign {name} = '0;")
    lines += ['  end else begin: on', '    hfd_mtp_x core (', '      .clk(clk), .rst_n(rst_n),']
    bindings = []
    for name, group in contract['groups'].items():
        for field in group['fields']:
            port, lsb, width = field['port'], field['lsb'], field['width']
            bindings.append(f'      .{port}({name}[{lsb} +: {width}])')
    lines += [',\n'.join(bindings), '    );', '  end endgenerate',
              'endmodule', '`default_nettype wire', '']
    return '\n'.join(lines)
