#!/usr/bin/env python3
"""S81-CAL1 (MU.S81.CAL.1, 10-19): fold the closed RTL / compiler EDGE deltas into the S81 token pricer and the
multi-user compiled calendar.  Static schedule: each delta is a fixed number of added edges on a named op; nothing
is re-measured here and no other cycle is touched.

Ledger (one edge = one 1.2 GHz die cycle; per occurrence on the critical path of the token DAG):
  CAPC2_PINPIPE  +2  every field (QF producer) op instance: ot_s81sl_capc2 +1 in / +1 out on every cap port
                     (claude/s81-capc2-cal-1019 1e559612c, gate 1f4c80cf6).  Reset +2 = boot only, 0 a token.
  CAP_EDLD       +24 every field op instance whose composed cycles were NOT measured on the L16/E24 cap
                     (ot_s81sl_cap EDLY 24 on E-column R02/R03 return words, WL3DLY 16 on W lane-3 R01 words; TOK2
                     claude/tok2-capld-1019 636f4c670).  Bound: the op's last return word is an E word (+24; W lane 3
                     = +16).  RATEFIX wq_b (fullsix P126, --shifts R01 16 / R02,R03 24 on the L16/E24 exe) already
                     carries it -> exempt in the RATEFIX composition; TOKSIM-S81B composes wq_b from the old number
                     -> charged there.
  XDIE_GUARD2    +1  every crossing phase (AG / P2P / hop = 1 phase, AR = RS + AG = 2): fluid guard 2 / window 3
                     (claude/xdie-s81-mu-1019 eb0d31c63; deadline = 563 + ceil(q) + guard).
  LEPCAP_INPIPE  +1  every crossing phase (ot_s81sl_lep_core IN_PIPE on ro, eec2dca41 / bb66563eb; not in mu3 /
                     mu4c, so the XDIE FLAT 563 does not carry it) + 2 a token (t_host in, t_kd out).
  VPX_P6         +13 every attn.a_allgather instance: lower_vpx P 5 -> 6 (Codex 73879e4d2) with the TOK4 send-frame
                     fix -2 (6ea6ea0a9): last of the 14 RD sends of a leg +13 (legs of the 3 end slices run in
                     parallel).  The other gathers / allreduces are not lowered by lower_vpx (GAP: rows not placed)
                     -> no compiled delta; HOP +2 of 07ff2cc83 = frame artefact (TOK4) -> 0.
Not folded (unmeasured / not closed): SVC4 attw landing +6 / production engine +12 a score beat (S81-SVC5 pending),
SMWIRE SOT +3 q words, the vpx issue-rate bound (see sensitivity).

Outputs (this directory): edge_deltas.json (ledger + per-workload counts + per-stage bound for dv_mu_calendar
--edge-deltas), fold.json (both composers, before / after, MU), printed table.

  python3 results/token_pass/cal1_s81_1019/fold_cal1.py
"""
import collections
import hashlib
import json
import math
import re
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[2]
F = 1.2e9
DAGS = {'ar': ROOT / 'results/arch/token_path_20261009/ds_rom.json',
        'mtp': ROOT / 'results/arch/token_path_20261009/ds_rom_mtp.json'}
COMPOSERS = {
    'RATEFIX': dict(cycles=ROOT / 'results/token_pass/ratefix_s81_1019/both_p126_t276/cycles.json',
                    ref='claude/s81-ratefix-1019@ff8fa3745 (tools/toksim_s81_compose.py, scenario both_p126_t276: '
                        'TOKSIM-S81 records + wq_b P126 + top-k INDEXED13/t276)',
                    edld_exempt={'attn.wq_b'}),
    'TOKSIM-S81B': dict(cycles=H / 'inputs/toksim_s81b_953d8d510_cycles.json',
                        ref='claude/toksim-s81b-1019@953d8d510 (strict bit_exact composer; wq_b NOT folded)',
                        edld_exempt=set()),
}
LEDGER = dict(
    CAPC2_PINPIPE=dict(edges=2, per='field op instance', src='claude/s81-capc2-cal-1019 1e559612c (gate 1f4c80cf6)'),
    CAP_EDLD=dict(edges=24, per='field op instance not measured on the L16/E24 cap', src='claude/tok2-capld-1019 636f4c670'),
    XDIE_GUARD2=dict(edges=1, per='crossing phase', src='claude/xdie-s81-mu-1019 eb0d31c63 (out_g2 rerun live)'),
    LEPCAP_INPIPE=dict(edges=1, per='crossing phase (+2 a token: t_host / t_kd)', src='claude/s81-lepcap-1019 bb66563eb (RTL eec2dca41)'),
    VPX_P6=dict(edges=13, per='attn.a_allgather instance', src='Codex 73879e4d2 + claude/s81-tok4-1019 6ea6ea0a9'),
)
SENS_P = 6                 # vpx RD-beat issue period (lower_vpx beat_period with CFG_AT 4 / LO 16)
LANE_R = 4096 / 3069       # lane slot rate, cycles a beat (xdie fluid model)
# beats a peer of each gather phase in the xdie gate (gen_golden.py; 128-B beats)
NB = {'a_allgather': 8, 'router_allgather': 3, 'rows_allgather': 132, 'topk_merge': 32, 'cand.merge': 128,
      'argmax_merge': 1, 'out_allreduce': 40, 'combine_allreduce': 40}


def phases(n):
    """crossing phases of one coll / hop node (0 = not a die-die crossing of the TP4 / stage calendar)"""
    op = n['id']
    if n.get('cls') not in ('coll', 'hop'):
        return 0
    if op.endswith('lead_flit'):
        return 0
    if op.endswith('unplaced_hops'):
        return 62                         # '62 more stage hops + cable flight (not placed in the record)'
    if op.endswith('token.return'):
        return 8                          # '8 x (link_rt endpoint + PHY + cable)'
    return 2 if op.endswith('allreduce') else 1


def node_delta(n, exempt):
    d = collections.Counter()
    if n.get('cls') == 'field':
        d['CAPC2_PINPIPE'] += 2
        if n.get('op') not in exempt:
            d['CAP_EDLD'] += 24
    p = phases(n)
    d['XDIE_GUARD2'] += p
    d['LEPCAP_INPIPE'] += p
    if n['id'].endswith('attn.a_allgather'):
        d['VPX_P6'] += 13
    return d


def sens(n):
    """vpx issue-rate bound: a gather leg issued at one RD beat every P edges instead of the xdie gate's line rate
    (lane-bound at R): extra = (P - R) (nb - 1) a phase.  NOT folded (only a_allgather is lowered; production row
    placement may spread legs over more slices)."""
    if n.get('cls') != 'coll':
        return 0.0
    for k, nb in NB.items():
        if n['id'].endswith(k):
            return (2 if k.endswith('allreduce') else 1) * (SENS_P - LANE_R) * (nb - 1)
    return 0.0


def layer_of(n):
    L = n.get('layer')
    if isinstance(L, int):
        return L
    m = re.match(r'(?:V\.)?L(\d+)\.', n['id'])
    return int(m.group(1)) if m else None


def count(wl, exempt):
    dag = json.loads(DAGS[wl].read_text())
    tot, by_op, per_layer, s = collections.Counter(), {}, collections.Counter(), 0.0
    for n in dag['nodes']:
        if not n.get('critical'):
            continue
        d = node_delta(n, exempt)
        if not d:
            s += sens(n)
            continue
        tot.update(d)
        k = re.sub(r'^(V\.)?(L\d+|mtp\.\d+)\.', '', n['id'])
        r = by_op.setdefault(k, dict(n=0, edges=collections.Counter()))
        r['n'] += 1
        r['edges'].update(d)
        L = layer_of(n)
        if L is not None and n['id'].startswith(('L', 'V.L')) and phases(n) < 8:
            per_layer[L] += sum(d.values())
        s += sens(n)
    tot['LEPCAP_INPIPE'] += 2             # t_host in + t_kd out, once a token / step
    return dict(total=sum(tot.values()), by_delta=dict(tot),
                by_op={k: dict(n=v['n'], edges=dict(v['edges']), sum=sum(v['edges'].values())) for k, v in sorted(by_op.items())},
                per_layer_max=max(per_layer.values()) if per_layer else 0, per_layer=dict(sorted(per_layer.items())),
                sensitivity_vpx_issue_rate=round(s, 1))


def main():
    res, deltas = {}, {}
    for name, c in COMPOSERS.items():
        r = json.loads(c['cycles'].read_text())
        cnt = {wl: count(wl, c['edld_exempt']) for wl in DAGS}
        deltas[name] = cnt
        out = dict(composer=c['ref'], workloads={}, multi_user={})
        for wl, w in r['workloads'].items():
            tau = w.get('tau') or 1.0
            T0, dT = w['T_cycles_fixed'], cnt[wl]['total']
            T1 = T0 + dT
            out['workloads'][wl] = dict(T_before=T0, tok_s_before=w['tok_s'], delta_edges=dT, T_after=round(T1, 1),
                                        tok_s_after=round(F * tau / T1, 1), pct=round(-100 * dT / T1, 3),
                                        by_delta=cnt[wl]['by_delta'],
                                        sensitivity_vpx_issue_rate_edges=cnt[wl]['sensitivity_vpx_issue_rate'],
                                        tok_s_with_sensitivity=round(F * tau / (T1 + cnt[wl]['sensitivity_vpx_issue_rate']), 1))
        res[name] = out
    # calendar input: one stage holds <= one layer (attn + next FFN) -> per-stage bound = the largest layer delta of
    # either composer (worst case), T deltas = the RATEFIX token deltas (the larger of the two is used: conservative)
    ps = max(deltas[n][wl]['per_layer_max'] for n in deltas for wl in DAGS)
    ed = dict(schema='opentallas.s81_cal1.edge_deltas.v1', ledger=LEDGER,
              per_stage_edges=ps,
              T_ar_edges=max(deltas[n]['ar']['total'] for n in deltas),
              T_mtp_edges=max(deltas[n]['mtp']['total'] for n in deltas),
              counts=deltas,
              source='results/token_pass/cal1_s81_1019/fold_cal1.py')
    ed['ledger_digest'] = hashlib.sha256(json.dumps(LEDGER, sort_keys=True).encode()).hexdigest()[:16]
    (H / 'edge_deltas.json').write_text(json.dumps(ed, indent=1, sort_keys=True) + '\n')
    # MU: users x F tau / max(T_after, calendar period) with the folded calendar (if it has been run)
    for mode in ('ar', 'mtp'):
        p = ROOT / f'results/arch/mu_s81_1018/calendar_{mode}_cal1.json'
        cal = json.loads(p.read_text()) if p.exists() else None
        for name in res:
            w = res[name]['workloads'][mode]
            tau = 4.159 if mode == 'mtp' else 1.0
            if cal:
                P, users = cal['period'], cal['users']
                eff = max(w['T_after'], P)
                res[name]['multi_user'][mode] = dict(
                    users=users, fillers=cal.get('fillers', 0), calendar=str(p.relative_to(ROOT)), period=P,
                    slot=cal['slot'], lemma=cal['lemma']['brute_force']['result'],
                    latency_user=cal['lemma']['latency_user']['result'],
                    per_user_tok_s=round(F * tau / eff, 1), aggregate_tok_s=round(users * F * tau / eff),
                    bound='calendar period' if P >= w['T_after'] else 'per-user token')
    (H / 'fold.json').write_text(json.dumps(dict(schema='opentallas.s81_cal1.fold.v1', results=res,
                                                 edge_deltas='edge_deltas.json'), indent=1, sort_keys=True) + '\n')
    for name, o in res.items():
        a, m = o['workloads']['ar'], o['workloads']['mtp']
        mu = o['multi_user']
        print(f"{name:12s} AR {a['tok_s_before']:,.1f} -> {a['tok_s_after']:,.1f} (+{a['delta_edges']:,} edges) | "
              f"MTP {m['tok_s_before']:,.1f} -> {m['tok_s_after']:,.1f} (+{m['delta_edges']:,}) | "
              f"MU {mu.get('ar', {}).get('aggregate_tok_s')} / {mu.get('mtp', {}).get('aggregate_tok_s')} | "
              f"sens AR {a['tok_s_with_sensitivity']:,.1f} MTP {m['tok_s_with_sensitivity']:,.1f}")
    print('per-stage', ps, 'T_ar', ed['T_ar_edges'], 'T_mtp', ed['T_mtp_edges'])


if __name__ == '__main__':
    main()
