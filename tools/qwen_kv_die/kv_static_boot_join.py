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

HBM-domain sinks (KVJ-A 10-17, boot_cdc_join; dispatcher successor with front_last[31:0] and 8-bit controller_addr):
  bcdc_f_<st>_<g>  qkd_static_kv_boot_cdc HAS_SEAL=0  <- front_we[8*s+g] / group_addr / group_data / front_last[8*s+g]
                   -> fcal_<st>_<g> cfg_we / cfg_addr[7:0] / cfg_data
  bcdc_c_<st>_<pc> qkd_static_kv_boot_cdc HAS_SEAL=1  <- controller_we[i] / controller_addr / controller_data /
                   controller_last[i], i = 32*cfg_stack + pc (the pc_path straps; target 6+cfg_stack, word 32*pc+a)
                   -> pc_<st>_<pc> cal_cfg_we / cal_cfg_addr (sink_addr[4:0]) / cal_cfg_data / cal_seal
  boot_obs         qkd_static_kv_boot_observe  <- the 160 applied_hbm / fault_hbm / fault_core, index [31:0] = front
                   group 8*s+g, [159:32] = 32 + i; -> boot.sink_applied / boot.sink_fault
Bench: rtl/test/qwen_static_kv/tb_static_boot_dispatch_cdc.sv composes exactly this graph (setup_ready rises).
Left OPEN on purpose: every clock/reset entry (ck/rst_n/hck/hrst_n; die clock tree, item 10), and the dispatcher's
HOST-side inputs (boot_pr / boot_image_* from qkd_host_root_admission, item 3; local_configured; execution_active).
Never a die netlist; status stays INCOMPLETE_TEMPLATE_NOT_EMITTABLE.
"""
import argparse
import hashlib
import json
from pathlib import Path

import kv_static as K

BOOT = ('rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv', 'qkd_static_kv_boot_dispatch')
# MU-KV-BOOT 10-19 (OT_KV_MU=1): target 1 in the MU form (471 words: rows, digest, epoch, GAP[4][36] at 326..469, seal at
# 470) for qkd_static_kv_layer_programme_mu; the wrapper keeps the original dispatcher (MU 0 = the original)
BOOT_MU = ('rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_boot_dispatch_mu.sv', 'qkd_static_kv_boot_dispatch_mu')
if K.MU:
    BOOT = BOOT_MU
CDC = ('rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_cdc.sv', 'qkd_static_kv_boot_cdc')
OBS = ('rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_cdc.sv', 'qkd_static_kv_boot_observe')
# KVJ-A 10-17 item 3: the die's HOST root is qkd_host_root_admission (kv_die.HOST_RT_FILE); it is a kv_die master, not a
# static-graph instance, so its edges to the static subsystem are recorded as die joins (wired by kv_die --split, item 10)
HOST = ('rtl/qwen_sys/split_20261014/qkd_host_root_admission.sv', 'qkd_host_root_admission')
DIE_CFG_NRST = 43     # KVJ-F: regional reset roots of the KV die (stub audit K-12: 344 dly bits / 8); kv_die must match
HOST_DIE_JOINS = [   # (consumer instance, port, producer instance, port); 'host' = the die HOST root master
    ('boot', 'boot_pr', 'host', 'boot_pr'), ('boot', 'boot_image_target', 'host', 'boot_image_target'),
    ('boot', 'boot_image_ready', 'host', 'boot_image_ready'), ('boot', 'boot_image_fault', 'host', 'boot_image_fault'),
    ('boot', 'boot_image_epoch', 'host', 'boot_image_epoch'), ('boot', 'boot_image_digest', 'host', 'boot_image_digest'),
    ('host', 'static_setup_ready', 'boot', 'setup_ready'),
    ('host', 'native_reserved', 'ownership', 'native_reserved'), ('host', 'ownership_valid', 'ownership', 'ownership_valid'),
]
STACKS = ('WS', 'WN', 'ES', 'EN')
ES_CFG = {'cfg_we': 'es_cfg_we', 'cfg_addr': 'es_cfg_addr', 'cfg_data': 'es_cfg_data'}
ES_CFG_SINKS = ('fanr', 'emb_join')    # KVJ-C3 PC chain root + join4_cal: one shared boot bus (ESCFG targets 12 / 13)
LINK_CFG = {'cfg_tx_we': 'link_cfg_tx_we', 'cfg_rx_we': 'link_cfg_rx_we', 'cfg_addr': 'link_cfg_addr', 'cfg_data': 'link_cfg_data'}
CORE_CFG = {   # sink instance -> (we source, we bit or None, addr source, data source)
    'layer_programme': ('layer_we', None, 'layer_addr', 'layer_data'),
    'wprg': ('writer_we', None, 'writer_addr', 'writer_data'),
    'ownership': ('ownership_we', None, 'ownership_addr', 'ownership_data'),
}


def boot_join(graph, root=K.ROOT, name='boot'):
    """Add the actual boot dispatcher (role 'producer') and bind every width-exact core-domain cfg input."""
    spec = K.source(*BOOT, root)
    # KVJ-F 10-17: DIECFG=1 (pre-boot target 10 -> qkd_kv_die_cfg: ECTL cfg + regional reset delays, coordinator 0da (d));
    # its diecfg_* faces are joined by kv_static_kvjf_join.die_cfg_join
    # KVJ-SMALL 10-17 (KV-INT gap item 12): LINKCFG=1 adds image target 11 (order 1..9, 11, 0) -> the static D2D link end's
    # calendar cfg port (66 words, kv_static_programme.link_cfg_words; bench tools/qwen_static_kv/run_link_cfg_boot.sh)
    # KVJ-SMALL b2 10-17 (KVJ-C3 open): ESCFG=1 adds targets 12 / 13 (order 1..9, 11, 12, 13, 0) -> the shared boot bus of
    # the PC chain root (fanr) and join4_cal (emb_join) (kv_static_programme.es_cfg_words; bench run_es_cfg_boot.sh)
    # RTL-BUILD-KV/FAULT 10-18 (P8): DIECAP=1 -> target 10 carries the die cfg capability word (qkd_kv_die_cfg CAP=1)
    params = dict(MUT=0, DIECFG=1, NRST=DIE_CFG_NRST, LINKCFG=1, ESCFG=1, DIECAP=1, **({'MU': 1, 'WMUT': 0} if K.MU else {}))
    if K.MU:   # KV-CTL mu2 10-19: setup_ready registered 2 edges (SRQ=2) in the MU release kvs_ctl (p1 in->out -698 ps);
        params['SRQ'] = 2   # MU-KV-CTL3: passed through qkd_static_kv_boot_dispatch_mu to the original
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
    links = [i for i in graph['instances'] if i['role'] == 'link']
    for li in links:                                     # the link end's calendar cfg port (core domain, pin-registered)
        ls = K.source(li['source'], li['module'], root)
        lp = K.ports(ls, {k: v for k, v in li['parameters'].items() if k in ls['parameters']})
        for port, src in LINK_CFG.items():
            if lp[port]['width'] != pp[src]['width'] or pp[src]['direction'] != 'output':
                raise ValueError(f'{li["name"]}.{port}: dispatcher {src} width {pp[src]["width"]} != {lp[port]["width"]}')
            if li['inputs'].get(port) is not None:
                raise ValueError(f'{li["name"]}.{port} already bound')
            li['inputs'][port] = [dict(instance=name, port=src, lo=0, width=lp[port]['width'])]
            bound.append(f'{li["name"]}.{port}')
    for sn in ES_CFG_SINKS:                              # one registered bus fanned to both (each pin-registers it)
        if sn not in ins:
            continue
        si = ins[sn]
        ss = K.source(si['source'], si['module'], root)
        sp = K.ports(ss, {k: v for k, v in si['parameters'].items() if k in ss['parameters']})
        for port, src in ES_CFG.items():
            if sp[port]['width'] != pp[src]['width'] or pp[src]['direction'] != 'output':
                raise ValueError(f'{sn}.{port}: dispatcher {src} width {pp[src]["width"]} != {sp[port]["width"]}')
            if si['inputs'].get(port) is not None:
                raise ValueError(f'{sn}.{port} already bound')
            si['inputs'][port] = [dict(instance=name, port=src, lo=0, width=sp[port]['width'])]
            bound.append(f'{sn}.{port}')
    graph.setdefault('joins_added', []).append(dict(producer=f'{name}:{BOOT[1]}', bound_inputs=len(bound),
        open_producer_inputs=sorted(inputs), owner_note='Q-KVJOIN 10-17: core-domain cfg only; HBM-domain cfg needs a '
        'boot_cdc-compatible dispatcher successor; dispatcher inputs need qkd_host_root_admission + boot_observe'))
    return bound


def _add(graph, ins, name, path_module, params, root):
    if name in ins:
        raise ValueError(f'instance {name} already present')
    spec = K.source(*path_module, root)
    pp = K.ports(spec, params)
    i = dict(name=name, role='producer', source=path_module[0], module=path_module[1], sha256=spec['sha256'],
             parameters=dict(params), inputs={p: None for p, v in pp.items() if v['direction'] == 'input'})
    graph['instances'].append(i)
    ins[name] = i
    if not any(d['path'] == path_module[0] for d in graph['source_files']):
        graph['source_files'].append(dict(path=path_module[0], sha256=hashlib.sha256((root / path_module[0]).read_bytes()).hexdigest()))
        graph['source_files'].sort(key=lambda d: d['path'])
    return i, pp


def _bind(i, port, items, width_of):
    if i['inputs'].get(port, 0) is not None:
        raise ValueError(f'{i["name"]}.{port} already bound or absent')
    if sum(it['width'] for it in items) != width_of(i, port):
        raise ValueError(f'{i["name"]}.{port}: width mismatch')
    i['inputs'][port] = items


def boot_cdc_join(graph, root=K.ROOT, boot='boot'):
    """KVJ-A 10-17: 32 front + 128 controller boot CDCs and the boot observer between the dispatcher and the
    HBM-domain cfg sinks (fcal cfg, pc_path cal_cfg/cal_seal).  Requires boot_join first.  Returns bound inputs."""
    ins = {i['name']: i for i in graph['instances']}
    if boot not in ins:
        raise ValueError('boot_join first')
    bp = K.ports(K.source(*BOOT, root), ins[boot]['parameters'])
    for p, w in (('front_last', 32), ('controller_addr', 8), ('controller_last', 128)):
        if bp.get(p, {}).get('width') != w:
            raise ValueError(f'dispatcher successor required: {p} width {bp.get(p)}')
    cache = {}

    def width_of(i, port):
        key = (i['source'], i['module'], tuple(sorted(i['parameters'].items())))
        if key not in cache:
            ss = K.source(i['source'], i['module'], root)
            cache[key] = K.ports(ss, {k: v for k, v in i['parameters'].items() if k in ss['parameters']})
        return cache[key][port]['width']

    def ep(n, p, lo=0, w=None):
        return dict(instance=n, port=p, lo=lo, width=width_of(ins[n], p) if w is None else w)
    bound = []
    order = [None] * 160          # observer index -> cdc name
    for s, st in enumerate(STACKS):
        for g in range(8):
            k = 8 * s + g
            n = f'bcdc_f_{st}_{g}'
            c, _ = _add(graph, ins, n, CDC, dict(HAS_SEAL=0, MUT=0), root)
            for p, it in (('cfg_we', ep(boot, 'front_we', k, 1)), ('cfg_addr', ep(boot, 'group_addr')),
                          ('cfg_data', ep(boot, 'group_data')), ('cfg_last', ep(boot, 'front_last', k, 1))):
                _bind(c, p, [it], width_of); bound.append(f'{n}.{p}')
            f = ins[f'fcal_{st}_{g}']
            for p, sp in (('cfg_we', 'sink_we'), ('cfg_addr', 'sink_addr'), ('cfg_data', 'sink_data')):
                _bind(f, p, [ep(n, sp, 0, width_of(f, p))], width_of); bound.append(f'{f["name"]}.{p}')
            order[k] = n
    pcs = [i for i in graph['instances'] if i['role'] == 'pc_path']
    if len(pcs) != 128:
        raise ValueError('128 pc_path required')
    for pc in pcs:
        st_strap, pc_strap = pc['inputs']['cfg_stack'], pc['inputs']['pc']
        if not (len(st_strap) == 1 and 'strap' in st_strap[0] and len(pc_strap) == 1 and 'strap' in pc_strap[0]):
            raise ValueError(f'{pc["name"]}: identity straps required')
        idx = 32 * st_strap[0]['strap'] + pc_strap[0]['strap']
        n = 'bcdc_c_' + pc['name'][3:]
        c, _ = _add(graph, ins, n, CDC, dict(HAS_SEAL=1, MUT=0), root)
        for p, it in (('cfg_we', ep(boot, 'controller_we', idx, 1)), ('cfg_addr', ep(boot, 'controller_addr')),
                      ('cfg_data', ep(boot, 'controller_data')), ('cfg_last', ep(boot, 'controller_last', idx, 1))):
            _bind(c, p, [it], width_of); bound.append(f'{n}.{p}')
        for p, sp, w in (('cal_cfg_we', 'sink_we', None), ('cal_cfg_addr', 'sink_addr', 5),
                         ('cal_cfg_data', 'sink_data', None), ('cal_seal', 'sink_seal', None)):
            _bind(pc, p, [ep(n, sp, 0, width_of(pc, p) if w is None else w)], width_of); bound.append(f'{pc["name"]}.{p}')
        if order[32 + idx] is not None:
            raise ValueError(f'duplicate controller index {idx}')
        order[32 + idx] = n
    if None in order:
        raise ValueError('incomplete boot observer order')
    o, _ = _add(graph, ins, 'boot_obs', OBS, {}, root)
    for p, sp in (('applied_hbm', 'applied_hbm'), ('fault_hbm', 'fault_hbm'), ('fault_leaf_core', 'fault_core')):
        _bind(o, p, [ep(n, sp, 0, 1) for n in reversed(order)], width_of); bound.append(f'boot_obs.{p}')   # MSB first
    _bind(ins[boot], 'sink_applied', [ep('boot_obs', 'applied_core')], width_of)
    _bind(ins[boot], 'sink_fault', [ep('boot_obs', 'fault_core')], width_of)
    bound += [f'{boot}.sink_applied', f'{boot}.sink_fault']
    graph.setdefault('joins_added', []).append(dict(producer='boot_cdc x160 + boot_obs', bound_inputs=len(bound),
        owner_note='KVJ-A 10-17: HBM-domain cfg through actual boot CDCs; clocks/resets and HOST-side dispatcher inputs open'))
    return bound


def host_admission_join(graph, root=K.ROOT, boot='boot', host=HOST):
    """KVJ-A 10-17 item 3: dispatcher inputs from inside the static graph (execution_active <- the static D2D end's svc
    execution_active, local_configured <- {ownership, writer programme, layer programme}.configured) and the width-checked
    die joins to the HOST root admission master (boot_pr / boot_image_*, static_setup_ready, native_reserved /
    ownership_valid).  Refuses a HOST root without the admission ports (e.g. qkd_host_root_pt)."""
    ins = {i['name']: i for i in graph['instances']}
    if boot not in ins:
        raise ValueError('boot_join first')
    hp = K.ports(K.source(*host, root), {k: v for k, v in _host_params(host, root).items()})

    def pw(n, p):
        if n == 'host':
            if p not in hp:
                raise ValueError(f'HOST root {host[1]} has no port {p}: admission variant required')
            return hp[p]
        i = ins[n]
        ss = K.source(i['source'], i['module'], root)
        return K.ports(ss, {k: v for k, v in i['parameters'].items() if k in ss['parameters']})[p]
    links = [i['name'] for i in graph['instances'] if i['role'] == 'link']
    if len(links) != 1:
        raise ValueError('one static D2D end required')
    bound = []
    b = ins[boot]
    for port, items in (('execution_active', [(links[0], 'execution_active')]),
                        ('local_configured', [('ownership', 'configured'), ('wprg', 'configured'), ('layer_programme', 'configured')])):
        its = []
        for n, sp in items:
            if pw(n, sp)['direction'] != 'output':
                raise ValueError(f'{n}.{sp} is not an output')
            its.append(dict(instance=n, port=sp, lo=0, width=pw(n, sp)['width']))
        if b['inputs'].get(port) is not None or sum(x['width'] for x in its) != pw(boot, port)['width']:
            raise ValueError(f'{boot}.{port}: already bound or width mismatch')
        b['inputs'][port] = its
        bound.append(f'{boot}.{port}')
    joins = []
    for cn, cp, pn, pp in HOST_DIE_JOINS:
        c, p = pw(cn, cp), pw(pn, pp)
        if c['direction'] != 'input' or p['direction'] != 'output' or c['width'] != p['width']:
            raise ValueError(f'die join {pn}.{pp} -> {cn}.{cp}: direction/width mismatch')
        joins.append(dict(consumer=f'{cn}.{cp}', producer=f'{pn}.{pp}', width=c['width'],
                          host_master=f'{host[0]}:{host[1]}' if 'host' in (cn, pn) else None))
    if any(j['consumer'].startswith(boot + '.') and b['inputs'].get(j['consumer'].split('.')[1]) is not None for j in joins):
        raise ValueError('die-joined dispatcher input already bound in the static graph')
    graph.setdefault('die_joins', []).extend(joins)
    graph.setdefault('joins_added', []).append(dict(producer='static D2D svc + core configured flags; HOST admission die joins',
        bound_inputs=len(bound), die_joins=len(joins),
        owner_note='KVJ-A 10-17: dispatcher HOST inputs come from the admission root master (kv_die --split wires die_joins, item 10)'))
    return bound, joins


def _host_params(host, root):
    spec = K.source(*host, root)
    out = {}
    for k in spec['parameters']:
        out[k] = dict(ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1, NL=2).get(k)
    # header defaults for every other parameter (die binding sets only the four above)
    import re
    txt = re.sub(r'//[^\n]*', '', (root / host[0]).read_text())
    hdr = txt[txt.index('module ' + host[1]):]
    for k in out:
        if out[k] is None:
            m = re.search(r'\b' + k + r'\s*=\s*([^,)]+)', hdr)
            out[k] = int(eval(m.group(1), {})) if m else 0
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    graph, _ = K.template()
    bound = boot_join(graph)
    bound += boot_cdc_join(graph)
    bound += host_admission_join(graph)[0]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'static_join.template.json').write_text(json.dumps(graph, indent=2) + '\n')
    open_ = {i['name']: [p for p, v in i['inputs'].items() if v is None] for i in graph['instances']}
    (a.out / 'static_open_joins.json').write_text(json.dumps(dict(
        schema='opentallas.qwen_kv_static.open_joins.v1', bound_by_boot_join=bound,
        unbound_inputs={k: v for k, v in open_.items() if v}, native_qualified=False, physical_qualified=False), indent=2) + '\n')
    print(json.dumps(dict(bound=len(bound), open_bits_instances=sum(1 for v in open_.values() if v), status=graph['status'])))


if __name__ == '__main__':
    main()
