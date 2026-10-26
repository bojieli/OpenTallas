#!/usr/bin/env python3
"""FT-KV 10-23 (FT-PLAN, owner-approved): static-schedule stage counts of the KV die at the M8/M9 relay reach.

ESTIMATE, pre FT-TOOL census: re-derives every die bus's relay stage count for a longer one-cycle hop (REACH-M89:
KV 1.2 mm on M8/M9, results/arch/die_reach_m89_1022.json) and the static-schedule constants that depend on them, with
the schedule rules of tools/qwen_kv_die/kv_static_params (static_model.json 'rule'):

    ECTL   RESPONSE_LAT = 8 + krq + krs, equal for every group  -> 8 + max_g(krq_min + krs_min)
    VPORT  RT = 9 + pvvq + pvrs (both sides equal)               -> 9 + max(pvvq_min + pvrs_min)
           W  = pvrq + O equal on all 16 ports (O = pad)          -> max(pvrq_min)
           RL = 4 + W + DQ + RT, FIRST_INPUT_AGE = RL + 1         (DQ kept per port as today)
    PV     PV_LEAD = D(ks_pvst); F_DLY = 1 + (D(ks_pvfst) - PV_LEAD) + D(ks_pvfin) [+ face land]

Per bus, two bounds, the smaller one is the plan value (never below 0):
  * hop bound   : today's stages were placed at hop <= reach_now (446 um), so the path is <= (s + 1) x reach_now and
                  needs at most ceil((s + 1) x reach_now / reach_new) - 1 stages.  Wrong only for PADDED buses (the
                  schedule equalises them), which is why the distance bound exists.
  * distance    : ceil(detour x Manhattan(src centre, dst centre) / reach_new) - 1, only when both ends are single
                  instances in the dump (a cluster centroid is not a pin).
The schedule constants then take the max over their equalisation group, so padding stays a schedule decision; the
fewer relays it needs are where the stages go.  Inputs are the GEN's case_kv/relay_stages.json + static_model.json and
the coordinator's insts.tsv dump of the same lineage.  Output: one JSON (results/arch/ft_kv_stage_plan_1023.json).
"""
import argparse
import collections
import json
import math
import re
from pathlib import Path


def load_insts(path):
    I = {}
    for ln in Path(path).read_text().splitlines():
        n, m, x, y, w, h, o = ln.split('\t')
        I[n] = (float(x) + float(w) / 2, float(y) + float(h) / 2, m)
    return I


def stages_new(s_now, dist, reach_now, reach_new, detour):
    hop = max(0, math.ceil((s_now + 1) * reach_now / reach_new - 1e-9) - 1)
    if dist is None:
        return hop, hop, None
    dst = max(0, math.ceil(detour * dist / reach_new - 1e-9) - 1)
    return min(hop, dst), hop, dst


def plan(rs, sm, I, reach_now=446.0, reach_new=1200.0, detour=1.25):
    buses = []
    for b in rs['buses']:
        s, d = b['src']['inst'], b['dst']['inst']
        dist = None
        if s in I and d in I:
            dist = abs(I[s][0] - I[d][0]) + abs(I[s][1] - I[d][1])
        new, hop, dst = stages_new(b['stages'], dist, reach_now, reach_new, detour)
        buses.append(dict(id=b['id'], bid=b['bid'], width=b['width'], domain=b['domain'], stages_now=b['stages'],
                          dist_um=None if dist is None else round(dist, 1), hop_bound=hop, dist_bound=dst,
                          stages_new=new))
    by_bid = collections.defaultdict(list)
    for b in buses:
        by_bid[b['bid']].append(b)
    S = sm['static_schedule']['schedule']
    P = sm['static_schedule']['paths']

    def pmin(k):
        bs = by_bid.get(k)
        return max(x['stages_new'] for x in bs) if bs else None

    out = dict(ectl={}, vport={}, pv={}, unresolved=[])
    # ECTL: krq_<g> + krs_<g>, one RESPONSE_LAT for every group (the closed rt80 children read one constant)
    grp = {}
    for k in P:
        m = re.fullmatch(r'kr([qs])_(\w+_\d+)', k)
        if m:
            grp.setdefault(m.group(2), {})[m.group(1)] = pmin(k)
    tot = [v['q'] + v['s'] for v in grp.values() if v.get('q') is not None and v.get('s') is not None]
    rl_now = sorted({v['RESPONSE_LAT'] for v in S['ectl'].values()})
    out['ectl'] = dict(groups={g: dict(krq_min=v.get('q'), krs_min=v.get('s')) for g, v in sorted(grp.items())},
                       RESPONSE_LAT_now=rl_now, RESPONSE_LAT_new=8 + max(tot) if tot else None,
                       pad_stages_now=sum(P[f'krq_{g}'] + P[f'krs_{g}'] for g in grp),
                       pad_stages_new=sum(max(tot) for _ in grp) if tot else None)
    # VPORT
    rt = []
    wq = []
    for k in P:
        if k.startswith(('pvvq_', 'pvrs_')):
            pass
    sides = collections.defaultdict(dict)
    for k in P:
        m = re.fullmatch(r'(pvvq|pvrs)_(\w+_\d+)_(\d)', k)
        if m:
            sides[(m.group(2), m.group(3))][m.group(1)] = pmin(k)
        m = re.fullmatch(r'pvrq_(\w+_\d+)', k)
        if m:
            wq.append(pmin(k))
    rt = [v['pvvq'] + v['pvrs'] for v in sides.values() if None not in (v.get('pvvq'), v.get('pvrs'))]
    RT = 9 + max(rt) if rt else None
    W = max(x for x in wq if x is not None) if wq else None
    dq = sorted({v['DQ'] for v in S['vport'].values()})
    out['vport'] = dict(RT_now=sorted({v['RT'] for v in S['vport'].values()}), RT_new=RT,
                        W_now=sorted({v['W'] for v in S['vport'].values()}), W_new=W, DQ_kept=dq,
                        RL_now=S['pv']['RL'], RL_new=(4 + W + max(dq) + RT) if None not in (W, RT) else None)
    if out['vport']['RL_new'] is not None:
        out['vport']['FIRST_INPUT_AGE_new'] = out['vport']['RL_new'] + 1
    # PV start / fin
    pvst, pvfst, pvfin = pmin('ks_pvst'), pmin('ks_pvfst'), pmin('ks_pvfin')
    A = S['attn']
    out['pv'] = dict(PV_LEAD_now=A['PV_LEAD'], PV_LEAD_new=pvst, F_DLY_now=A['F_DLY'],
                     F_DLY_new=(1 + (pvfst - pvst) + pvfin + A.get('face_land_fin', 0)) if None not in (pvst, pvfst, pvfin) else None,
                     pvp_now=A['pvp'], pvp_new=[pmin('ks_pvp0'), pmin('ks_pvp1')],
                     note='pvfin start alignment D(ks_pvfst) - PV_LEAD == D(ks_pvp_p) must hold: pad the shorter side')
    for k in P:
        if not re.match(r'(kr[qs]|pvvq|pvrs|pvrq)_', k) and k not in ('pvst_0', 'pvst_1', 'pvp_0', 'pvp_1', 'pvfst', 'fin') \
                and not k.startswith('O_'):
            out['unresolved'].append(k)
    tot_now = sum(b['width'] * b['stages_now'] for b in buses)
    tot_new = sum(b['width'] * b['stages_new'] for b in buses)
    return dict(schema='opentallas.ft_kv_stage_plan.v0', status='ESTIMATE (pre FT-TOOL census; centre distances)',
                reach_now_um=reach_now, reach_new_um=reach_new, detour=detour,
                totals=dict(buses=len(buses), stages_now=sum(b['stages_now'] for b in buses),
                            stages_new=sum(b['stages_new'] for b in buses), bit_stages_now=tot_now,
                            bit_stages_new=tot_new, ratio=round(tot_now / max(tot_new, 1), 2)),
                schedule=out, buses=buses)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--relay-stages', required=True)
    ap.add_argument('--static-model', required=True)
    ap.add_argument('--insts', required=True)
    ap.add_argument('--reach-now', type=float, default=446.0)
    ap.add_argument('--reach-new', type=float, default=1200.0)
    ap.add_argument('--detour', type=float, default=1.25)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    doc = plan(json.loads(Path(a.relay_stages).read_text()), json.loads(Path(a.static_model).read_text()),
               load_insts(a.insts), a.reach_now, a.reach_new, a.detour)
    doc['inputs'] = dict(relay_stages=a.relay_stages, static_model=a.static_model, insts=a.insts)
    Path(a.out).write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(dict(totals=doc['totals'], ectl={k: v for k, v in doc['schedule']['ectl'].items() if k != 'groups'},
                          vport=doc['schedule']['vport'], pv=doc['schedule']['pv'],
                          unresolved=doc['schedule']['unresolved']), indent=1))


if __name__ == '__main__':
    main()
