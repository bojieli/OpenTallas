#!/usr/bin/env python3
"""KVJ-F 2026-10-17: joins for the KV-die gaps the stub audit left without an owner (stub_audit_1017.md K-1 / K-4 / K-12,
coordinator rule 0da).  Builds on kv_static.template() + kv_static_boot_join (boot_join, boot_cdc_join, host_admission_join).

ownership_join  (K-4, plan "Ownership x1, beside the host root")
  own_obs = qkd_kv_ownership_obs (rtl/qwen_sys/static_kv_20261014): the actual producers of the ownership calendar's open
  inputs and of the static D2D end's KV-local status (bench tools/qwen_static_kv/run_ownership_obs.sh):
    own_obs.stage_start / stage      <- layer_programme.stage_start / stage      (go = token start, stage 1 only)
    own_obs.word_valid               <- d2d.kvn_word_valid                       (link -> writer word)
    own_obs.es_sv / es_wv            <- wrn.es[288q+287] / wrn.es[288q], q = 0..3 (writer -> PC command / data valids)
    own_obs.own_active / own_fault   <- ownership.active / fault
    own_obs.group_drained / _fault   <- the 32 drain guards (same order as the calendar's)
    ownership.go / host_quiet / upstream_quiet <- own_obs.go / host_quiet / upstream_quiet
    d2d.kv_active_local / kv_drained_local / kv_flush_local <- own_obs
    drain_<st>_<g>.upstream_quiet / upstream_fault <- phase_<st>_<g>.idle_core / fault_core (the group's command upstream,
        same core domain; the PC-side debt is the guard's own ctrl / front / ring observations)
  die joins (kv_die --split, item 10): own_obs.host_launch_quiet / host_upstream_quiet <- the HOST root
  qkd_host_root_admission host_launch_quiet / host_upstream_quiet (synchronised inside own_obs).
  Parameter QUIET_WIN is compiler-priced (writer word -> es depth + es relay depth to the farthest PC): null here.

die_cfg_join  (K-12, coordinator 0da (d): functional config straps rejected; boot config load)
  diecfg = qkd_kv_die_cfg (POR-domain, written only by the dispatcher's pre-boot image target 10, DIECFG=1):
    diecfg.cfg_we / cfg_addr / cfg_data <- boot.diecfg_we / diecfg_addr / diecfg_data
    boot.diecfg_sealed / diecfg_fault   <- diecfg.sealed / fault
    ectl_a_<st>_<g>.cfg                 <- diecfg.ectl_a_cfg[5i +: 5], i = 8*stack + g   (replaces the identity strap)
    (RTL-BUILD-KV/FAULT P8: CAP=1 = the capability word; diecfg.fused_program_capability -> attention_programme and
     attn_root, kv_static_attn_join.capability_join)
  die joins: ECTL B / C cfg of group i <- diecfg.ectl_b_cfg / ectl_c_cfg[5i +: 5]; reset region r dly <-
  diecfg.rst_dly[8r +: 8] (qkd_rst_region roots of kv_die, D - d_r loaded by the HOST in pass 1; die_cfg_image()).

vport_join_check  (K-1): the template's landing rsp -> V port in<parity> and V port vq<parity> -> landing vreq edges are
  checked structurally (group 2k + parity of the port's stack); priced RT must be >= 9 (measured abutted join, bench
  tools/qwen_static_kv/run_landing_vport.sh; kv_die.VPORT_RT_SEG).

Never a die netlist; status stays INCOMPLETE_TEMPLATE_NOT_EMITTABLE.
"""
import argparse
import json
from pathlib import Path

import kv_static as K
import kv_static_boot_join as B
import kv_static_cfault_join as C

OBS = ('rtl/qwen_sys/static_kv_20261014/qkd_kv_ownership_obs.sv', 'qkd_kv_ownership_obs')
DCFG = ('rtl/qwen_sys/static_kv_20261014/qkd_kv_die_cfg.sv', 'qkd_kv_die_cfg')
STACKS = B.STACKS
VPORT_RT_SEG = 9
DIE_CFG_SEAL = 0x514b564443464731


def _ctx(graph, root):
    ins = {i['name']: i for i in graph['instances']}
    cache = {}

    def width_of(i, port):
        key = (i['source'], i['module'], tuple(sorted((k, v) for k, v in i['parameters'].items() if v is not None)))
        if key not in cache:
            ss = K.source(i['source'], i['module'], root)
            par = {k: v for k, v in i['parameters'].items() if k in ss['parameters']}
            par = {k: (1 if v is None else v) for k, v in par.items()}     # unpriced latencies never change port widths
            cache[key] = K.ports(ss, par)
        return cache[key][port]['width']

    def ep(n, p, lo=0, w=None):
        return dict(instance=n, port=p, lo=lo, width=width_of(ins[n], p) if w is None else w)
    return ins, width_of, ep


def _add_unpriced(graph, ins, name, path_module, params, root):
    """B._add with null (compiler-priced) parameters allowed: widths are evaluated with a placeholder of 1."""
    spec = K.source(*path_module, root)
    pp = K.ports(spec, {k: (1 if v is None else v) for k, v in params.items()})
    if name in ins:
        raise ValueError(f'instance {name} already present')
    i = dict(name=name, role='producer', source=path_module[0], module=path_module[1], sha256=spec['sha256'],
             parameters=dict(params), inputs={p: None for p, v in pp.items() if v['direction'] == 'input'})
    graph['instances'].append(i)
    ins[name] = i
    if not any(d['path'] == path_module[0] for d in graph['source_files']):
        import hashlib
        graph['source_files'].append(dict(path=path_module[0], sha256=hashlib.sha256((root / path_module[0]).read_bytes()).hexdigest()))
        graph['source_files'].sort(key=lambda d: d['path'])
    return i


def ownership_join(graph, root=K.ROOT, name='own_obs'):
    ins, width_of, ep = _ctx(graph, root)
    for need in ('ownership', 'layer_programme', 'd2d', 'wrn'):
        if need not in ins:
            raise ValueError(f'template instance {need} missing')
    o = _add_unpriced(graph, ins, name, OBS, dict(QUIET_WIN=None, MUT=0), root)
    guards = [f'drain_{st}_{g}' for st in STACKS for g in range(8)]
    own = ins['ownership']
    if own['inputs'].get('group_drained') != [ep(n, 'drained') for n in reversed(guards)]:
        raise ValueError('ownership group_drained order differs from the template')
    bound = []

    def bind(i, port, items):
        B._bind(i, port, items, width_of)
        bound.append(f'{i["name"]}.{port}')
    bind(o, 'stage_start', [ep('layer_programme', 'stage_start')])
    bind(o, 'stage', [ep('layer_programme', 'stage')])
    bind(o, 'word_valid', [ep('d2d', 'kvn_word_valid')])
    bind(o, 'es_sv', [ep('wrn', 'es', 288 * q + 287, 1) for q in (3, 2, 1, 0)])     # MSB first
    bind(o, 'es_wv', [ep('wrn', 'es', 288 * q, 1) for q in (3, 2, 1, 0)])
    bind(o, 'own_active', [ep('ownership', 'active')])
    bind(o, 'own_fault', [ep('ownership', 'fault')])
    bind(o, 'group_drained', [ep(n, 'drained') for n in reversed(guards)])
    bind(o, 'group_fault', [ep(n, 'fault') for n in reversed(guards)])
    for p in ('go', 'host_quiet', 'upstream_quiet'):
        bind(own, p, [ep(name, p)])
    for p in ('kv_active_local', 'kv_drained_local', 'kv_flush_local'):
        bind(ins['d2d'], p, [ep(name, p)])
    for st in STACKS:
        for g in range(8):
            d, ph = ins[f'drain_{st}_{g}'], f'phase_{st}_{g}'
            bind(d, 'upstream_quiet', [ep(ph, 'idle_core')])
            bind(d, 'upstream_fault', [ep(ph, 'fault_core')])
    hp = K.ports(K.source(*B.HOST, root), B._host_params(B.HOST, root))
    joins = []
    for cp, pp_ in (('host_launch_quiet', 'host_launch_quiet'), ('host_upstream_quiet', 'host_upstream_quiet')):
        if hp[pp_]['direction'] != 'output' or hp[pp_]['width'] != width_of(o, cp):
            raise ValueError(f'HOST root {pp_}: direction/width mismatch')
        joins.append(dict(consumer=f'{name}.{cp}', producer=f'host.{pp_}', width=hp[pp_]['width'],
                          host_master=f'{B.HOST[0]}:{B.HOST[1]}', domain='HOST clocks: synchronised inside own_obs'))
    graph.setdefault('die_joins', []).extend(joins)
    graph.setdefault('joins_added', []).append(dict(producer=f'{name}:{OBS[1]}', bound_inputs=len(bound), die_joins=len(joins),
        owner_note='KVJ-F 10-17: ownership go / quiet producers + D2D KV-local status; drain guard upstream = phase launch '
                   'core idle / fault; QUIET_WIN compiler-priced'))
    return bound, joins


def die_cfg_join(graph, root=K.ROOT, boot='boot', name='diecfg', nrst=B.DIE_CFG_NRST):
    ins, width_of, ep = _ctx(graph, root)
    if boot not in ins:
        raise ValueError('boot_join first')
    bpar = ins[boot]['parameters']
    if bpar.get('DIECFG') != 1 or bpar.get('NRST') != nrst or bpar.get('DIECAP') != 1:
        raise ValueError(f'dispatcher DIECFG=1 / NRST={nrst} / DIECAP=1 required, have {bpar}')
    c, _ = B._add(graph, ins, name, DCFG, dict(NRST=nrst, CAP=1, MUT=0), root)
    bound = []

    def bind(i, port, items):
        B._bind(i, port, items, width_of)
        bound.append(f'{i["name"]}.{port}')
    for p, sp in (('cfg_we', 'diecfg_we'), ('cfg_addr', 'diecfg_addr'), ('cfg_data', 'diecfg_data')):
        bind(c, p, [ep(boot, sp)])
    bind(ins[boot], 'diecfg_sealed', [ep(name, 'sealed')])
    bind(ins[boot], 'diecfg_fault', [ep(name, 'fault')])
    for s, st in enumerate(STACKS):
        for g in range(8):
            a = ins[f'ectl_a_{st}_{g}']
            cur = a['inputs'].get('cfg')
            if not (isinstance(cur, list) and len(cur) == 1 and 'strap' in cur[0]):
                raise ValueError(f'{a["name"]}.cfg: expected the template identity strap to replace')
            a['inputs']['cfg'] = None
            bind(a, 'cfg', [ep(name, 'ectl_a_cfg', 5 * (8 * s + g), 5)])
    joins = []
    for s, st in enumerate(STACKS):
        for g in range(8):
            i = 8 * s + g
            for e in ('b', 'c'):
                joins.append(dict(consumer=f'ectl_{e}:{st}:{g}.cfg', producer=f'{name}.ectl_{e}_cfg', lo=5 * i, width=5,
                                  note='ECTL B / C are die instances outside the static graph (kv_die --split)'))
    for r in range(nrst):
        joins.append(dict(consumer=f'rst_region[{r}].dly', producer=f'{name}.rst_dly', lo=8 * r, width=8,
                          note='qkd_rst_region root r of kv_die (its strap rdly_* is replaced); value D - d_r from the plan'))
    graph.setdefault('die_joins', []).extend(joins)
    graph.setdefault('joins_added', []).append(dict(producer=f'{name}:{DCFG[1]}', bound_inputs=len(bound), die_joins=len(joins),
        owner_note='KVJ-F 10-17: ECTL cfg + reset release delays boot-loaded (pre-boot target 10), coordinator 0da (d)'))
    return bound, joins


def die_cfg_image(ectl_a, ectl_b, ectl_c, dly, capability, ages=None):
    """The dispatcher target-10 image (64-bit words, address = index) for qkd_kv_die_cfg CAP=1: 32 ECTL words, len(dly) reset
    words, the capability word (data[0] = the fused attention-programme capability, RTL-BUILD-KV/FAULT P8), then the seal.
    ectl_*: 32 five-bit values (group 8*stack+g); dly: one 8-bit value per reset region; capability: 0 / 1.
    KV-BOOTAGE 10-19: ages = the 19 static-schedule age words (kv_bootage.image_ages(...)['words']) for qkd_kv_die_cfg_a
    AGES=1, placed between the capability word and the seal."""
    if capability not in (0, 1):
        raise ValueError('capability is one bit')
    if not (len(ectl_a) == len(ectl_b) == len(ectl_c) == 32):
        raise ValueError('32 ECTL groups required')
    if any(not 0 <= v < 32 for v in (*ectl_a, *ectl_b, *ectl_c)) or any(not 0 <= v < 256 for v in dly):
        raise ValueError('field out of range')
    if ages is not None and (len(ages) != 19 or any(not 0 <= v < (1 << 32) for v in ages)):
        raise ValueError('ages: 19 words of <= 32 bits (kv_bootage.words_of)')
    words = [a | (b << 5) | (c << 10) for a, b, c in zip(ectl_a, ectl_b, ectl_c)] + list(dly) + [capability] + \
        list(ages or []) + [DIE_CFG_SEAL]
    if len(words) > 256:
        raise ValueError('image exceeds the 8-bit die cfg address')
    return words


def vport_join_check(graph):
    """K-1: every V port side is the rsp face of landing group 2k + parity of its stack, and its vq face feeds that
    group's vreq; a priced RT is >= VPORT_RT_SEG (the measured abutted landing seg -> vport join)."""
    ins = {i['name']: i for i in graph['instances']}
    checked = 0
    for st in STACKS:
        for k in range(4):
            vp = ins[f'vport_{st}_{k}']
            for par in (0, 1):
                land = f'slg_{st}_{2 * k + par}'
                for p, sp in (('valid', 'rsp_valid'), ('vflag', 'rsp_v'), ('t', 'rsp_t'), ('epoch', 'rsp_epoch'), ('d', 'rsp_data')):
                    it = vp['inputs'][f'in{par}_{p}']
                    if not (it and len(it) == 1 and it[0].get('instance') == land and it[0]['port'] == sp and it[0]['lo'] == 0):
                        raise ValueError(f'{vp["name"]}.in{par}_{p}: must be {land}.{sp}')
                for p in ('valid', 't'):
                    it = ins[land]['inputs'][f'vreq_{p}']
                    if not (it and len(it) == 1 and it[0].get('instance') == vp['name'] and it[0]['port'] == f'vq{par}_{p}'):
                        raise ValueError(f'{land}.vreq_{p}: must be {vp["name"]}.vq{par}_{p}')
                checked += 1
            rt = vp['parameters'].get('RT')
            if rt is not None and rt < VPORT_RT_SEG:
                raise ValueError(f'{vp["name"]}: RT {rt} < {VPORT_RT_SEG} (landing seg vreq pin + VREQ latency 8)')
    return checked


def build(root=K.ROOT):
    graph, _ = K.template()
    bound = B.boot_join(graph, root)
    bound += B.boot_cdc_join(graph, root)
    bound += B.host_admission_join(graph, root)[0]
    bound += ownership_join(graph, root)[0]
    bound += die_cfg_join(graph, root)[0]
    bound += C.cfault_join(graph, root)[0]       # KVJ-SMALL (c): completion-fault OR tree -> HOST
    vport_join_check(graph)
    return graph, bound


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    graph, bound = build()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'static_join.template.json').write_text(json.dumps(graph, indent=2) + '\n')
    open_ = {i['name']: [p for p, v in i['inputs'].items() if v is None] for i in graph['instances']}
    (a.out / 'static_open_joins.json').write_text(json.dumps(dict(
        schema='opentallas.qwen_kv_static.open_joins.v1', bound=bound,
        unbound_inputs={k: v for k, v in open_.items() if v}, die_joins=graph.get('die_joins', []),
        native_qualified=False, physical_qualified=False), indent=2) + '\n')
    print(json.dumps(dict(bound=len(bound), open_instances=sum(1 for v in open_.values() if v), status=graph['status'])))


if __name__ == '__main__':
    main()
