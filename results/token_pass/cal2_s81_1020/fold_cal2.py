#!/usr/bin/env python3
"""S81-CAL (MU.S81.CAL, 10-20): price the 10-20 structural cycles of the S81 p4l-MU release die into the token pricer
and the multi-user calendar, for BOTH pinned stage-count candidates.  Static schedule: every delta is a fixed number of
added edges (1 edge = one 1.2 GHz die cycle) on a named op of the token DAG critical path; nothing is re-measured here.
Base = the S81-CAL1 fold (results/token_pass/cal1_s81_1019: RATEFIX and TOKSIM-S81B composers, CAL1 ledger folded).

New ledger (per critical occurrence):
  XG5_X      +2  every field op instance: x path of the merged rs+xs4 tile ot_s81sl_xg5 = main xg + 2 edges uniformly
                 (claude/s81-xg5-1020 @ff736425d, xg5_bench PASS at +dextra=2, witnesses committed).        MEASURED-RTL
  XG5_RING   +1  every field op instance: issuer relay on the rstop ring (ring + 1 edge, same branch).        MEASURED-RTL
  COLL7      +4  every TP4 collective phase (coll class; AR = RS + AG = 2): ot_s81ph_coll_lane_safe4 REACH=1
                 register hops at the off-die boundary, +1 tx + 3 rx (rx 2-stage landing / RX_STAGES 3->5 / core landing)
                 (claude/s81-coll7-1020 8efb5b0b7/344f2113b, tb_coll_reach7 + 3 mutant witnesses caebd6e15).  BENCH-RTL
                 The reverse ACK relay +2 is NOT on the data path (static schedule: it only lengthens the replay
                 window), reported as a sensitivity (+2 a phase).
  IDX3R      +62 every attn.idx.score instance, 122-frame / 140-stage variant ONLY: non-inline dsdv_idx_rg3 reader in the
                 PHY corner strips (lanes/S81-DIE11.md spec): fixed HBM round trip 6..36 a controller pair (3/8/13/18
                 stations each way at 405 um; pairs run in parallel -> the worst pair, 36, bounds the job) + 21 edges
                 once a job on the W->E score/query chain; absorbed by raising T0 (no throughput change at P3 scan /
                 P4 gather).  MEASURED (rg3 bench, 10-20 17:58): worst pair +41 (T0 floor), chain +21.  The 116-frame / 201-stage fallback keeps the
                 in-line idx3 readers (0 added).
  STAGE_HOP  (N - 120) stage hops x (1006 + 2) edges: the token DAG record has 120 stage hops (58 placed
                 substage_hop at 1006 = link_rt 652 + full-KP4 PHY 209 ns + UCIe 10 ns + wire, and 62 unplaced at
                 the same law); each added stage is one more hop on the critical path (AR token, once an MTP verify step)
                 plus the CAL1 per-phase XDIE guard +1 and LEPCAP +1.  N = 140 (122 frames, primary) / 201 (116 frames,
                 fallback) from the pinned stage maps (ep9 codex-s81-stage124-1020 stage_map_f122_140 / stage_map_201,
                 capacity campaigns f122_140 / req201 still running there; not re-run).                       MODEL
NOT priced here (owed by the physical-stage occupancy calendar): the per-stage re-split of a layer's routed-expert
field ops and collectives when one layer spans 2-3 physical stages (the 59 legacy Sxxx groups of dv_mu_calendar are
not the 140 / 201 physical stage windows; DECISIONS_FOR_CLAUDE 13:04 / 13:08).

  python3 results/token_pass/cal2_s81_1020/fold_cal2.py      # -> edge_deltas_s{140,201}.json, fold.json, table
then dv_mu_calendar.py --edge-deltas edge_deltas_s<N>.json --tag cal2_s<N> (fleet) and re-run this script (MU rows).
"""
import collections
import hashlib
import importlib.util
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
ROOT = H.parents[2]
CAL1 = ROOT / 'results/token_pass/cal1_s81_1019'
spec = importlib.util.spec_from_file_location('fold_cal1', CAL1 / 'fold_cal1.py')
C1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C1)
F = C1.F
HOP_REF = 120                  # stage hops in the token DAG record (58 placed + 27 + 35 unplaced)
HOP_CYC = 1006                 # ds_rom.json substage_hop (measured+vendor)
HOP_PHASE = 2                  # CAL1 XDIE_GUARD2 +1 and LEPCAP_INPIPE +1 a crossing phase
IDX3_RT = (11, 41)             # MEASURED rg3 bench (claude/s81-idx3r-1020 @8ccaf446f): request +s+4, response +s+1
                               # -> +2s+5 a pair = 11/21/31/41 for s = 3/8/13/18; T0 floor +41 (worst pair)
IDX3_CHAIN = 21                # MEASURED: W->E XD = 21 stations once a job
LEDGER = dict(
    XG5_X=dict(edges=2, per='field op instance', grade='measured-RTL bench', src='claude/s81-xg5-1020 @ff736425d'),
    XG5_RING=dict(edges=1, per='field op instance', grade='measured-RTL bench', src='claude/s81-xg5-1020 @ff736425d'),
    COLL7=dict(edges=4, per='coll crossing phase (+1 tx, +3 rx)', grade='bench-RTL', src='claude/s81-coll7-1020 344f2113b'),
    IDX3R=dict(edges=IDX3_RT[1] + IDX3_CHAIN, per='attn.idx.score instance (122-frame variants only)',
               grade='measured-RTL bench (rg3 vs rg2, T0 sweep +<=40 priced +41)',
               src='claude/s81-idx3r-1020 @8ccaf446f results/rtl/s81_idx3r_1020 (lanes/S81-IDX3R.md)'),
    STAGE_HOP=dict(edges=HOP_CYC + HOP_PHASE, per='stage hop above the 120 of the DAG record', grade='MODEL',
                   src='ep9 codex-s81-stage124-1020 stage_map_f122_140 / stage_map_201'),
)
SENS = dict(COLL7_ACK=2)       # a coll phase, not on the data path
VARIANTS = {140: dict(frames=122, role='PRIMARY', idx3_noninline=True,
                      stage_map='ep9:/srv/opentallas-scratch/claude/codex-s81-stage124-1020/stage_map_f122_140.json',
                      campaign='f122_140.exact.log (margin f122_148)'),
            148: dict(frames=122, role='MARGIN', idx3_noninline=True,
                      stage_map='ep9:/srv/opentallas-scratch/claude/codex-s81-stage124-1020/stage_map_f122_148.json',
                      campaign='f122_148.exact.log (148/148 PASS)'),
            201: dict(frames=116, role='FALLBACK', idx3_noninline=False,
                      stage_map='ep9:/srv/opentallas-scratch/claude/codex-s81-stage124-1020/stage_map_201.json',
                      campaign='req201.exact.log (margin req212)')}


def node_delta(n, idx3):
    d = collections.Counter()
    if n.get('cls') == 'field':
        d['XG5_X'] += 2
        d['XG5_RING'] += 1
    if n.get('cls') == 'coll':
        d['COLL7'] += 4 * C1.phases(n)
    if idx3 and n['id'].endswith('attn.idx.score'):
        d['IDX3R'] += IDX3_RT[1] + IDX3_CHAIN
    return d


def count(wl, idx3):
    dag = json.loads(C1.DAGS[wl].read_text())
    tot, per_layer, by_op, ack = collections.Counter(), collections.Counter(), {}, 0
    for n in dag['nodes']:
        if not n.get('critical'):
            continue
        if n.get('cls') == 'coll':
            ack += SENS['COLL7_ACK'] * C1.phases(n)
        d = node_delta(n, idx3)
        if not d:
            continue
        tot.update(d)
        k = re.sub(r'^(V\.)?(L\d+|mtp\.\d+)\.', '', n['id'])
        r = by_op.setdefault(k, dict(n=0, edges=collections.Counter()))
        r['n'] += 1
        r['edges'].update(d)
        L = C1.layer_of(n)
        if L is not None and n['id'].startswith(('L', 'V.L')):
            per_layer[L] += sum(d.values())
    return dict(total=sum(tot.values()), by_delta=dict(tot), per_layer=dict(sorted(per_layer.items())),
                per_layer_max=max(per_layer.values()), per_layer_mean=round(sum(per_layer.values()) / len(per_layer), 1),
                by_op={k: dict(n=v['n'], edges=dict(v['edges'])) for k, v in sorted(by_op.items())},
                sensitivity_coll_ack_edges=ack)


def main():
    cal1 = json.loads((CAL1 / 'fold.json').read_text())['results']
    ed1 = json.loads((CAL1 / 'edge_deltas.json').read_text())
    out = dict(schema='opentallas.s81_cal2.fold.v1', lane='S81-CAL (MU.S81.CAL, parent LEAD9-S81)', ledger=LEDGER,
               sensitivity=SENS, hop_ref=HOP_REF, base='results/token_pass/cal1_s81_1019/fold.json (CAL1 folded)',
               variants={})
    for N, v in VARIANTS.items():
        cnt = {wl: count(wl, v['idx3_noninline']) for wl in C1.DAGS}
        dh = N - HOP_REF
        hop = dh * (HOP_CYC + HOP_PHASE)
        rec = dict(v, stages=N, added_stage_hops=dh, stage_hop_edges=hop, structural=cnt, composers={})
        for name, r in cal1.items():
            rec['composers'][name] = {}
            for wl, w in r['workloads'].items():
                tau = 4.159 if wl == 'mtp' else 1.0
                T0 = w['T_after']
                ds = cnt[wl]['total']
                T1 = T0 + ds + hop
                row = dict(T_cal1=T0, tok_s_cal1=w['tok_s_after'], structural_edges=ds, stage_hop_edges=hop,
                           T_after=round(T1, 1), tok_s_after=round(F * tau / T1, 1),
                           pct_vs_cal1=round(100 * (T0 / T1 - 1), 3),
                           tok_s_structural_only=round(F * tau / (T0 + ds), 1),
                           tok_s_with_ack_sens=round(F * tau / (T1 + cnt[wl]['sensitivity_coll_ack_edges']), 1))
                calp = ROOT / f'results/arch/mu_s81_1018/calendar_{wl}_cal2_s{N}.json'
                if calp.exists():
                    c = json.loads(calp.read_text())
                    eff = max(T1, c['period'])
                    row['multi_user_legacy_groups'] = dict(
                        calendar=str(calp.relative_to(ROOT)), users=c['users'], fillers=c.get('fillers', 0),
                        period=c['period'], slot=c['slot'], lemma=c['lemma']['brute_force']['result'],
                        per_user_tok_s=round(F * tau / eff, 1), aggregate_tok_s=round(c['users'] * F * tau / eff),
                        bound='calendar period' if c['period'] >= T1 else 'per-user token',
                        caveat='59 legacy Sxxx stage windows (not the physical stage windows): projection only')
                rec['composers'][name][wl] = row
        # calendar input: CAL1 per-stage bound + the new largest per-layer delta; T deltas = CAL1 + new + hops
        ed = dict(schema='opentallas.s81_cal1.edge_deltas.v1', variant=f's{N}',
                  per_stage_edges=ed1['per_stage_edges'] + max(cnt[wl]['per_layer_max'] for wl in cnt),
                  T_ar_edges=ed1['T_ar_edges'] + cnt['ar']['total'] + hop,
                  T_mtp_edges=ed1['T_mtp_edges'] + cnt['mtp']['total'] + hop,
                  base_cal1=dict(per_stage_edges=ed1['per_stage_edges'], T_ar_edges=ed1['T_ar_edges'],
                                 T_mtp_edges=ed1['T_mtp_edges'], ledger=ed1['ledger_digest']),
                  source='results/token_pass/cal2_s81_1020/fold_cal2.py')
        ed['ledger_digest'] = hashlib.sha256(json.dumps(LEDGER, sort_keys=True).encode()).hexdigest()[:16]
        (H / f'edge_deltas_s{N}.json').write_text(json.dumps(ed, indent=1, sort_keys=True) + '\n')
        rec['calendar_edge_deltas'] = f'edge_deltas_s{N}.json'
        out['variants'][f's{N}'] = rec
    (H / 'fold.json').write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    for k, rec in out['variants'].items():
        s = rec['structural']
        print(f"{k} ({rec['role']}, {rec['frames']} frames): +{rec['added_stage_hops']} hops = +{rec['stage_hop_edges']:,} | "
              f"structural AR +{s['ar']['total']} MTP +{s['mtp']['total']} (per layer max {s['ar']['per_layer_max']}, "
              f"mean {s['ar']['per_layer_mean']}) {s['ar']['by_delta']}")
        for name, r in rec['composers'].items():
            a, m = r['ar'], r['mtp']
            mu = ' | MU ' + ' / '.join(str(r[w].get('multi_user_legacy_groups', {}).get('aggregate_tok_s')) for w in ('ar', 'mtp'))
            print(f"   {name:12s} AR {a['tok_s_cal1']:,.1f} -> {a['tok_s_after']:,.1f} ({a['pct_vs_cal1']}%) "
                  f"MTP {m['tok_s_cal1']:,.1f} -> {m['tok_s_after']:,.1f} ({m['pct_vs_cal1']}%){mu}")


if __name__ == '__main__':
    main()
