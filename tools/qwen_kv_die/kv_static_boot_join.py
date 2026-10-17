#!/usr/bin/env python3
"""Q-KVJOIN 2026-10-17: join the EXISTING boot producer into the static compiler-join template.

The static-join template (kv_static.template) leaves every cfg_we/cfg_addr/cfg_data input unbound.  Their actual
producer already exists in RTL: qkd_static_kv_boot_dispatch (rtl/qwen_sys/static_kv_20261014), the initialization-only
consumer of the authenticated HOST loader replay (targets 1 layer / 2 writer programme / 3 ownership / 4 landing
calendars / 5 front calendars / 6..9 controller calendars, then ISA target 0).

This module binds only the CORE-domain sinks whose widths match the dispatcher exactly:
  layer_programme cfg   <- layer_we / layer_addr[8:0] / layer_data[63:0]       (target 1)
  writer_programme cfg  <- writer_we / writer_addr[7:0] / writer_data[63:0]    (target 2)
  ownership cfg         <- ownership_we / ownership_addr[1:0] / ownership_data (target 3)
  lcal_<st>_<g> cfg     <- landing_we[8*stack+g] / group_addr / group_data     (target 4)
The group index 8*stack+g uses the template's cfg_stack straps (WS 0, WN 1, ES 2, EN 3); the controller order of
target 6..9 (32*(target-6)+pc) already matches the pc_path {cfg_stack, pc} straps.

Left OPEN on purpose (no width-exact producer; see /home/ubuntu/claude-takeover-20261007/kv_static_join_plan.md):
  * the HBM-domain sinks fcal cal cfg (hck) and pc_path cal_cfg_* / cal_seal (cal_hck) must pass a real
    qkd_static_kv_boot_cdc; the dispatcher has no front_last and drives a 5-bit controller_addr into the CDC's 8-bit
    cfg_addr, so a dispatcher successor (front_last[31:0], 8-bit controller_addr) is required first;
  * the dispatcher's own inputs (boot_pr / boot_image_* from qkd_host_root_admission, which the die's
    qkd_host_root_pt lacks; sink_applied from qkd_static_kv_boot_observe; local_configured; execution_active).
Never a die netlist; status stays INCOMPLETE_TEMPLATE_NOT_EMITTABLE.
"""
import argparse
import hashlib
import json
from pathlib import Path

import kv_static as K

BOOT = ('rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv', 'qkd_static_kv_boot_dispatch')
STACKS = ('WS', 'WN', 'ES', 'EN')
CORE_CFG = {   # sink instance -> (we source, we bit or None, addr source, data source)
    'layer_programme': ('layer_we', None, 'layer_addr', 'layer_data'),
    'wprg': ('writer_we', None, 'writer_addr', 'writer_data'),
    'ownership': ('ownership_we', None, 'ownership_addr', 'ownership_data'),
}


def boot_join(graph, root=K.ROOT, name='boot'):
    """Add the actual boot dispatcher (role 'producer') and bind every width-exact core-domain cfg input."""
    spec = K.source(*BOOT, root)
    params = dict(MUT=0)
    pp = K.ports(spec, params)
    ins = {i['name']: i for i in graph['instances']}
    if name in ins:
        raise ValueError(f'instance {name} already present')
    inputs = {p: None for p, v in pp.items() if v['direction'] == 'input'}
    graph['instances'].append(dict(name=name, role='producer', source=BOOT[0], module=BOOT[1], sha256=spec['sha256'],
                                   parameters=params, inputs=inputs))
    if not any(d['path'] == BOOT[0] for d in graph['source_files']):
        graph['source_files'].append(dict(path=BOOT[0], sha256=hashlib.sha256((root / BOOT[0]).read_bytes()).hexdigest()))
        graph['source_files'].sort(key=lambda d: d['path'])
    sinks = dict(CORE_CFG)
    for s, st in enumerate(STACKS):
        for g in range(8):
            sinks[f'lcal_{st}_{g}'] = ('landing_we', 8 * s + g, 'group_addr', 'group_data')
    bound = []
    for sink, (we, bit, addr, data) in sinks.items():
        i = ins[sink]
        ss = K.source(i['source'], i['module'], root)     # width only: the VMAP gap of wprg stays a template gap
        sp = K.ports(ss, {k: v for k, v in i['parameters'].items() if k in ss['parameters']})
        for port, src, lo, w in (('cfg_we', we, bit or 0, 1), ('cfg_addr', addr, 0, None), ('cfg_data', data, 0, None)):
            w = sp[port]['width'] if w is None else w
            if (bit is None and port == 'cfg_we' and pp[src]['width'] != 1) or (port != 'cfg_we' and pp[src]['width'] != w):
                raise ValueError(f'{sink}.{port}: dispatcher {src} width {pp[src]["width"]} != {w}')
            if i['inputs'].get(port) is not None:
                raise ValueError(f'{sink}.{port} already bound')
            i['inputs'][port] = [dict(instance=name, port=src, lo=lo, width=w)]
            bound.append(f'{sink}.{port}')
    graph.setdefault('joins_added', []).append(dict(producer=f'{name}:{BOOT[1]}', bound_inputs=len(bound),
        open_producer_inputs=sorted(inputs), owner_note='Q-KVJOIN 10-17: core-domain cfg only; HBM-domain cfg needs a '
        'boot_cdc-compatible dispatcher successor; dispatcher inputs need qkd_host_root_admission + boot_observe'))
    return bound


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    graph, _ = K.template()
    bound = boot_join(graph)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'static_join.template.json').write_text(json.dumps(graph, indent=2) + '\n')
    open_ = {i['name']: [p for p, v in i['inputs'].items() if v is None] for i in graph['instances']}
    (a.out / 'static_open_joins.json').write_text(json.dumps(dict(
        schema='opentallas.qwen_kv_static.open_joins.v1', bound_by_boot_join=bound,
        unbound_inputs={k: v for k, v in open_.items() if v}, native_qualified=False, physical_qualified=False), indent=2) + '\n')
    print(json.dumps(dict(bound=len(bound), open_bits_instances=sum(1 for v in open_.values() if v), status=graph['status'])))


if __name__ == '__main__':
    main()
