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
