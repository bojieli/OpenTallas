#!/usr/bin/env python3
"""KV-ECTL4 2026-10-18 (coordinator 0gs (d)): ONE K round trip for every ECTL frame of the static KV die.

The ECTL frame qkd_ectl3_kiss_st is a wires-only cluster of hardened children whose static K schedule is RTL parameters:
A's K issuer compares each landing response with the request it sent RESPONSE_LAT edges earlier (identity line
RESPONSE_LAT deep), A / B / C expect the row ROW_RETURN_LAT = RESPONSE_LAT + 7 edges after the request generator, and the
K row is read at QK_ISSUE_AGE - 2 (static_qk_calendar write-before-read: QK_ISSUE_AGE = RESPONSE_LAT + 11).  One hardened
child serves all 32 frames only if every frame sees the SAME round trip, so this pass pads each frame's K REQUEST chain
(ectl_<st>_<f>.rq -> slg_<st>_<g>.kreq, 38 b; the 1,062-b response is never padded) with
    pads = ECTLK_RESPONSE_LAT - (8 + krq + krs)
relay stations at its sink end (kv_bundle_eq machinery: same relay masters, same clock trunk, every hop within reach).
A frame whose natural round trip already exceeds the budget fails the GEN (the plan must move the frame, or the budget
and the hardened children change together).  Static schedule only: no credit, no ready, no runtime re-timing.

    equalize(K, m)   kv_die.build() under OT_KV_STATIC_DIE (OT_KV_K_RT_EQ, default 1); records m['k_rt_eq']
"""
import os
import re

import kv_bundle_eq as BEQ
import kv_static_die as KSD

LANDING_SEG = 8


def on():
    return os.environ.get('OT_KV_K_RT_EQ', '1') == '1'


def pairs(m):
    """[(st, g, ectl inst, slg inst)] from the plan's krq_<st>_<g> buses (ectl.rq -> slg.kreq)"""
    out = {}
    for b in m['buses']:
        if b is None:
            continue
        mt = re.match(r'krq_(WS|WN|ES|EN)_([0-7])$', b[0])
        if not mt:
            continue
        src = BEQ._norm(b[3][0])
        out[(mt.group(1), int(mt.group(2)))] = src[0]
    if len(out) != 32:
        raise ValueError(f'kv_k_rt_eq: expected 32 krq_<st>_<g> chains, found {len(out)}')
    return [(st, g, e, f'slg_{st}_{g}') for (st, g), e in sorted(out.items())]


def equalize(K, m, target=None):
    target = KSD.ECTLK_RESPONSE_LAT if target is None else target
    by = {i.name: i for i in m['insts']}
    bundles, nat, over = {}, {}, []
    ps = pairs(m)
    for st, g, e, s in ps:
        if e not in by or s not in by:
            raise ValueError(f'kv_k_rt_eq: {e} / {s} missing in the plan')
        bundles[f'K.rt_{st}_{g}'] = [(e, 'rq', s)]
    rsp = {}

    def plan_fn(name, stages, walk):
        (e, port, s), q = next(iter(stages.items()))
        hits = [v[0] for k, v in walk((s, 'krsp')).items() if k[0] == e]
        if len(hits) != 1:
            raise ValueError(f'kv_k_rt_eq: {s}.krsp reaches {e} {len(hits)} times')
        r = LANDING_SEG + q + hits[0]
        nat[name] = dict(krq=q, krs=hits[0], round_trip=r)
        rsp[name] = hits[0]
        if r > target:
            over.append(f'{name} {r}')
        return {(e, port, s): max(0, target - r)}
    m = BEQ.equalize(K, m, bundles=bundles, plan_fn=plan_fn, record_key='k_rt_eq',
                     rule=f'every ECTL frame K round trip 8 + krq + krs padded to ECTLK_RESPONSE_LAT {target} on the '
                          f'request chain at its sink end (tools/qwen_kv_die/kv_k_rt_eq.py)')
    if over:
        raise ValueError(f'kv_k_rt_eq: natural K round trip over the budget {target}: {over} (move the frames or raise '
                         f'ECTLK_RESPONSE_LAT and re-harden the qkd_ectl3_kiss_st children together)')
    m['k_rt_eq'].update(target=target, natural=nat, qk_issue_age=KSD.ECTLK_QK_ISSUE_AGE,
                        natural_max=max(v['round_trip'] for v in nat.values()),
                        natural_min=min(v['round_trip'] for v in nat.values()))
    return m


# KVR-DERIVE 10-19 (QW-KVATTN2 finding 2): qkd_pv16_vport has ONE RT for both of its sides (vq0 -> group {k, 0} -> i0 and
# vq1 -> group {k, 1} -> i1), so the two V round trips 9 + vq + rs of a port must be equal.  The shorter side's 15-b V get
# chain (vport.vq<g> -> slg.vreq) is padded at its sink end (kv_bundle_eq machinery, core-clock pads).  The port's RT is
# then 9 + the common relay count; the kit's hard RT (kv_static_die.tile_ages VPORT_RT) is checked by kv_static_params.
def vport_side_eq_on():
    return os.environ.get('OT_KV_VPORT_SIDE_EQ', '1') == '1'


def equalize_vport_sides(K, m):
    by = {i.name: i for i in m['insts']}
    bundles = {}
    for st in KSD.STACKS:
        for k in range(4):
            vp = f'vport_{st}_{k}'
            if vp in by and all(f'slg_{st}_{2 * k + g}' in by for g in (0, 1)):
                bundles[f'V.rt_{st}_{k}'] = [(vp, f'vq{g}', f'slg_{st}_{2 * k + g}') for g in (0, 1)]
    if not bundles:
        return m
    nat = {}

    def plan_fn(name, stages, walk):
        tot = {}
        for (vp, port, s), q in stages.items():
            hits = [v[0] for kk, v in walk((s, 'rsp')).items() if kk[0] == vp]
            if len(hits) != 1:
                raise ValueError(f'kv_vport_side_eq: {s}.rsp reaches {vp} {len(hits)} times')
            tot[(vp, port, s)] = q + hits[0]
        t = max(tot.values())
        nat[name] = dict(sides=[tot[x] for x in sorted(tot, key=lambda x: x[1])], RT=KSD.VPORT_RT_SEG + t)
        return {x: t - v for x, v in tot.items()}
    m = BEQ.equalize(K, m, bundles=bundles, plan_fn=plan_fn, record_key='vport_side_eq',
                     rule='every V port: vq0 + rs0 == vq1 + rs1 (pads on the shorter 15-b V get chain at its sink end; '
                          'tools/qwen_kv_die/kv_k_rt_eq.py equalize_vport_sides)')
    m['vport_side_eq'].update(natural=nat, RT={n_[2:]: v['RT'] for n_, v in nat.items()})
    return m
