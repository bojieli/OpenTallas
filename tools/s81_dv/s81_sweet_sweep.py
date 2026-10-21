#!/usr/bin/env python3
"""S81-SWEET (10-20): die count vs throughput sweep of the S81 DeepSeek array (owner: find the sweet spot; balanced pipeline).

For each stage count S (40 dense stages + S - 40 expert-only stages, the 8 map-declared copy-B layers kept):
  1. min-max re-deal (mucal_stage_rebalance.plan/build, generalised to S - 40 expert-only stages): binary search on the
     dense-window bound B, DP over layers for the fewest expert-only stages; exact linear ROM law q0 + 72 N (asserted on
     every 140/148 exact spec); calendar rows <= 4096.
  2. the physical calendar (dv_mu_calendar_phys.build, --compose romopt --alap, 1 context) on that map: users with 0
     collisions by the brute-force checker, N+1 FAULT and injected-shift FAULT negatives, AR and MTP.
  3. dies = 4 S + 4 x copy-B stages (8) + 52 other; stage occupancy balance = max / mean per stage copy.

Balancing variants (owner 10-20 clarification, min-max stage time):
  --dsplit       ROM re-deal + compiler: the ffn pre-expert segment D (norm, router, top6, shared expert, 3,053 cyc)
                 leaves the dense stage and runs on the first downstream stage holding experts of the layer (dense
                 stage = attention only, no head experts there).  ROM: the shared expert + router move with it; MODEL:
                 every expert-only stage capped at 112 experts (1 expert of q words reserved), dense q0 not lowered.
  --copies L=k   HARDWARE (+4 dies a copy): k TP4 copies of dense layer L (default: the 8 map copy-B layers x2).

  s81_sweet_sweep.py --out DIR [--stages 140 144 ...] [--dsplit] [--copies 2=3 8=3 14=3 20=3 1=2] [--tag T]
"""
from __future__ import annotations

import argparse
import functools
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import dv_mu_calendar_phys as M      # noqa: E402
import mucal_stage_rebalance as R    # noqa: E402

BASE = ROOT / 'results/token_pass/mucal140b_s81_1020/stage_map_rb140.json'
SEG = ROOT / 'results/token_pass/mucal140b_s81_1020/calendar_rb140_ar.json'
OTHER_DIES = 52
M.composed = functools.lru_cache(maxsize=None)(M.composed)      # the composer is map independent: run it once


def make_map(S, out, dsplit=False, kcopies=None):
    base = json.loads(BASE.read_text())
    seg = {int(k[1:]): v for k, v in json.loads(SEG.read_text())['layer_segments'].items()}
    caps = base['rebalance']['caps']
    idx_src = tuple(caps['idx_src'])
    base['_idx_src'] = idx_src
    rows = {}
    for s in base['stages']:
        if len(s['layers']) == 1:
            rows[s['layers'][0]] = s['calendar_rows']
    assert sorted(rows) == list(range(R.NL))
    cap = [(R.EXP_CAP * R.SLOPE - R.Q0[R.cls_of(L, idx_src)]) // R.SLOPE for L in range(R.NL)]
    kc = {L: (2 if L in R.DUP else 1) for L in range(R.NL)}
    kc.update(kcopies or {})
    copies = [float(kc[L]) for L in range(R.NL)]
    win0, cap0 = R.window, R.EXP_CAP
    if dsplit:
        seg = {L: dict(v, D=0.0) for L, v in seg.items()}
        R.window = lambda sg, L, t, h, E, C: win0(sg, L, t, h, E, C) if h == 0 else 1e18
        R.EXP_CAP = cap0 - 1
    nexp = S - R.NL
    E, C = seg[0]['E'], seg[0]['C']
    cand = sorted({R.window(seg, L, t, h, E, C) / copies[L] for L in range(R.NL) for t in range(0, 8)
                   for h in range(0, 8)})
    lo, hi, best = 0, len(cand) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        r = R.plan(seg, cap, rows, copies, cand[mid])
        if r and r[0] <= nexp:
            best, hi = (cand[mid], r), mid - 1
        else:
            lo = mid + 1
    B, (used, choice) = best
    st = R.build(base, seg, B, choice, nexp)
    R.window, R.EXP_CAP = win0, cap0
    for s in st:
        if s['dense_layer'] is not None:
            s['copies'] = kc[s['dense_layer']]
            s['copy_b'] = kc[s['dense_layer']] > 1
            assert not (dsplit and any(l == s['dense_layer'] for l, _, _ in s['experts']))
    for s in st:
        s['calendar_rows'] = sum(rows[l] for l in s['layers'])
    assert sum(s['n_experts'] for s in st) == R.NL * R.NE and len(st) == S
    if dsplit:                                               # the shared expert + router words move with D (MODEL)
        for s in st:
            if s['dense_layer'] is None:
                s['model_load'] += R.SLOPE
                s['model_fill_pct'] = round(100 * s['model_load'] / R.DEPTH, 2)
    assert all(s['model_load'] <= R.DEPTH - 1 and s['calendar_rows'] <= R.CAL_ROWS for s in st)
    m = {k: v for k, v in base.items() if k not in ('stages', 'verdict', '_idx_src', 'rebalance')}
    m['plan'] = f'S81-SWEET min-max re-deal on {S} stages (base rb140 dense order / copy-B), model bound {B:.0f}'
    m['rebalance'] = dict(bound_model=round(B, 1), expert_stages_min=used, expert_stages=nexp,
                          per_layer=[dict(layer=L, head=choice[L][0], tail_on_next_dense=choice[L][1]) for L in range(R.NL)])
    m['stages'] = st
    m['stages_count'] = S
    out.write_text(json.dumps(m, indent=1) + '\n')
    return m, B, used


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True)
    ap.add_argument('--stages', type=int, nargs='+', default=[140, 144, 148, 152, 156, 164, 172, 180, 200])
    ap.add_argument('--dsplit', action='store_true')
    ap.add_argument('--copies', nargs='*', default=[])
    ap.add_argument('--tag', default='')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for S in a.stages:
        kc = {int(x.split('=')[0]): int(x.split('=')[1]) for x in a.copies}
        mp = out / f'stage_map_s{S}{a.tag}.json'
        try:
            m, B, used = make_map(S, mp, a.dsplit, kc)
        except (TypeError, AssertionError) as e:            # no feasible plan at this stage count
            print(json.dumps(dict(variant=a.tag or 'redeal', stages=S, infeasible=repr(e)[:120])), flush=True)
            continue
        recs = M.build(mp, 'romopt', alap=True, unqualified=True, contexts=1, dsplit=a.dsplit)
        ncopy = sum(s['copies'] - 1 for s in m['stages'] if s['dense_layer'] is not None)
        dies = 4 * S + 4 * ncopy + OTHER_DIES
        dense_eff = [w['occ'] / w['copies'] for w in recs['ar']['stage_windows'] if w['dense_layer'] is not None]
        row = dict(variant=a.tag or 'redeal', stages=S, dies=dies, dense_balance=round(max(dense_eff) / statistics.mean(dense_eff), 2), bound_model=round(B), expert_stages_min=used,
                   max_fill_pct=max(s['model_fill_pct'] for s in m['stages']),
                   dense_with_experts=sum(1 for s in m['stages'] if s['dense_layer'] is not None and s['n_experts']))
        for mode in ('ar', 'mtp'):
            r = recs[mode]
            key = 'step' if mode == 'mtp' else 'occ'
            eff = [w[key] / w['copies'] for w in r['stage_windows']]
            top = max(r['stage_windows'], key=lambda w: w[key] / w['copies'])
            ok = (r['checker']['result'] == 'PASS' and r['checker']['negative_n_plus_1']['result'] == 'FAULT'
                  and r['checker']['negative_injected_shift']['result'] == 'FAULT')
            row[mode] = dict(users=r['users'], per_user=r['per_user_tok_s'], agg=r['aggregate_tok_s'],
                             per_die=round(r['aggregate_tok_s'] / dies, 2), period=r['period'],
                             max_occ=round(max(eff)), mean_occ=round(statistics.mean(eff)),
                             balance=round(max(eff) / statistics.mean(eff), 2),
                             top=f"{top['stage']} L{top['dense_layer']} x{top['copies']}",
                             checker='PASS+neg' if ok else 'CHECK', why=r['search'][:2])
            (out / f'calendar_s{S}{a.tag}_{mode}.json').write_text(json.dumps(
                {k: v for k, v in r.items() if k not in ('timeline_log', 'slots')}, indent=1) + '\n')
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / f'sweep{a.tag}.json').write_text(json.dumps(rows, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
