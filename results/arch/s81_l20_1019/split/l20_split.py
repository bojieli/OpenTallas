#!/usr/bin/env python3
"""S81-L20SPLIT (10-19, coordinator decision 0li): the L20 index scan split over 2x the dies, compiled and checked.

What this writes (split.json beside it):
  rank_tree   the static per-rank plan compiled by tools/s81_dv/layer_prog/lower_bk.py (job_rank_tree) for k = 1 (no
              shard: the pre-10-19 lower_bk), k = 3 (option D record) and k = 6 (the split): per die its key range,
              query arrival, reader-paced bk_sel ingress, children merged on lane 3 (REBASE + sparse BEAT words),
              egress window; the root's selection == the fixture attn.idx.topk_local of the rank (shard closure)
  bench       the compiled bk_sel jobs on the REAL dsdv_bk_sel (die.v u_bk_sel straps), Verilator 5.050 (fleet):
              k=6 root / internal / leaf, k=3 root, TP4 final; mutants corrupt / early (committed witnesses)
  layer       the recompiled L20 programme (dv_layer_compile, G8R2 tree, layerbench fixtures) and its cut_3S replay
  single_user 1-user AR / MTP on the SCAND/B3 machinery of record (results/arch/s81_idxrd_1018/b3_price.py):
              record D, measured reader k=3 (no split), the decision's priced split (k=6), the COMPILED split
  multi_user  the MU calendar (tools/s81_dv/dv_mu_calendar.py --l20-split) with the helper dies' HBM / svc windows,
              model windows and compiled windows (the longest helper bk_sel occupancy of the rank tree)
  ledger      the accepted-cost row (S81.L20_SPLIT) values
Run:  python3 results/arch/s81_l20_1019/split/l20_split.py [--fixtures DIR]
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools/s81_dv/layer_prog'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import lower_bk as B  # noqa: E402

FX_DEFAULT = '/home/ubuntu/scratch/layerbench-s81/fixtures/L20'
BENCH = HERE / 'bench'
LAYER = HERE / 'layer'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def jl(p):
    return json.loads(Path(p).read_text())


def rank_trees(fx):
    out = {}
    for kd in (1, 3, 6):
        plans, r = B.job_rank_tree(fx, k_dies=kd, t_q=0)
        occ = {d['die']: d['last_egress'] - d['t_q'] for d in r['per_die']}
        out[str(kd)] = dict(tree={str(k): v for k, v in r['tree'].items()}, closure=r['closure'],
                            chain_cycles=r['root_last_egress'], per_die=r['per_die'],
                            keys_die=max(d['keys'] for d in r['per_die']),
                            reader_cycles=B.reader_cycles(max(d['keys'] for d in r['per_die'])),
                            helper_occupancy_max=max(v for d, v in occ.items() if d != 0) if kd > 1 else None,
                            root_occupancy=occ[0])
    return out


def bench_summary():
    cases = {}
    if not BENCH.exists():
        return dict(status='not run')
    for d in sorted(p for p in BENCH.iterdir() if p.is_dir()):
        cr = d / 'check_result.json'
        if not cr.exists():
            continue
        c, m = jl(cr), jl(d / 'meta.json')
        cases[d.name] = dict(pass_=c['pass_'], mismatches=c['mismatches'], expected_beats=c['expected_beats'],
                             mutant=m.get('mutant'), t_first_in=m['t_first_in'], t_last_in=m['t_last_in'],
                             window=m['window'], golden_ok=m['golden_ok'], shard=m.get('shard'),
                             span_edges=m['window'][1] - m['t_first_in'] + 1)
    base = [v for v in cases.values() if not v['mutant']]
    muts = [v for v in cases.values() if v['mutant']]
    ver = (BENCH / 'verilator.version').read_text().strip() if (BENCH / 'verilator.version').exists() else None
    return dict(vehicle='REAL dsdv_bk_sel (die.v u_bk_sel straps tap_k 0x11 sink_k 0x10 ik 4 ek 5 uid 0x5B), stimulus '
                        'at the unit pins from lower_bk gen --job tree / topk_final (tools/s81_dv/layer_prog/bk/'
                        'run_bk_layer.sh); every IDX / DONE egress beat checked at its compiled vo_s edge',
                verilator=ver, cases=cases,
                result='PASS %d/%d bit-exact at the compiled edges, mutants FAIL %d/%d' % (
                    sum(v['pass_'] for v in base), len(base), sum(not v['pass_'] for v in muts), len(muts)),
                pass_=all(v['pass_'] for v in base) and all(not v['pass_'] for v in muts) and bool(base))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', default=FX_DEFAULT)
    a = ap.parse_args(argv)
    fx = Path(a.fixtures)
    man = fx / 'manifest.sha256'
    rt = rank_trees(fx)
    bench = bench_summary()

    # ---------------------------------------------------------------- 1 user (SCAND / B3 machinery of record)
    B3 = load('b3_price', ROOT / 'results/arch/s81_idxrd_1018/b3_price.py')
    rec_rd = dict(B3.meas_rd)
    K3 = B3.K
    xd = lambda k: 2 * math.ceil((k - 1) / 2) * B3.LEG + B3.FINAL * (k - 1)
    ADD = 116                                             # idx.score adders (scand: reader + 116)
    TOPK_LOCAL = 4225.0                                   # DAG attn.idx.topk_local L20 (token_path_20261009)
    rec_chain = rec_rd[20] + ADD + TOPK_LOCAL + xd(K3)    # record D: reader + adders + local select + legs/merge
    base = B3.S['D_measured_reader']

    def su(rd, extra=None):
        rd = dict(rd)
        for L, x in (extra or {}).items():
            rd[L] = rd[L] + x
        r = B3.compose(rd, rd)
        r['vs_record'] = dict(ar_pct=round(100 * (r['ar_tok_s'] / base['ar_tok_s'] - 1), 2),
                              mtp_pct=round(100 * (r['mtp_tok_s'] / base['mtp_tok_s'] - 1), 2))
        r['l20_chain_cycles'] = round(rd[20] + ADD + TOPK_LOCAL + xd(K3), 1)
        return r
    n3, n6 = rt['3']['keys_die'], rt['6']['keys_die']
    price_split = B.reader_cycles(n6) + ADD + TOPK_LOCAL + xd(6)
    price_k3meas = B.reader_cycles(n3) + ADD + TOPK_LOCAL + xd(3)
    comp3 = rt['3']['chain_cycles'] + ADD
    comp6 = rt['6']['chain_cycles'] + ADD
    SU = {
        'record_D': su(rec_rd),
        'k3_measured_reader_priced': su(rec_rd, {20: price_k3meas - rec_chain}),
        'split_k6_priced (decision 0li)': su(rec_rd, {20: price_split - rec_chain}),
        'k3_compiled_tree': su(rec_rd, {20: comp3 - rec_chain}),
        'split_k6_compiled_tree': su(rec_rd, {20: comp6 - rec_chain}),
    }
    single = dict(
        basis='B3.compose on the 10-09 DS ROM DAG + 10-18 composition, L20 idx path = reader + 116 adders + '
              'topk_local + legs/merge (record D: 7,700 + 116 + 4,225 + 1,814 = %d); compiled rows replace that path '
              'by the rank tree (query at the home die -> merged 512 out of the root, measured reader law + bk_sel '
              'rung + LEG 729 an edge) + 116; TP4 topk_merge 551 + topk_final 178 priced in every row' % rec_chain,
        chains=dict(record_D=rec_chain, k3_measured_reader_priced=price_k3meas, split_k6_priced=price_split,
                    k3_compiled=comp3, split_k6_compiled=comp6,
                    compiled_vs_priced_split_pct=round(100 * (comp6 / price_split - 1), 2),
                    split_gain_compiled=comp3 - comp6, split_gain_priced=price_k3meas - price_split),
        rows=SU)

    # ---------------------------------------------------------------- multi-user (record calendar + helper windows)
    C = load('dv_mu_calendar', ROOT / 'tools/s81_dv/dv_mu_calendar.py')
    sp = dict(C.SPLIT_L20)
    mu_keys = math.ceil(1048576 / sp['shard'])
    hw_ar = rt['6']['helper_occupancy_max'] + math.ceil(B.READER_P * (mu_keys - n6) / 16)
    rd_mu = B.reader_cycles(mu_keys)
    hw_mtp = rd_mu + 6 * (hw_ar - rd_mu)
    compiled = dict(sp, helper_window_ar=hw_ar, helper_window_mtp=hw_mtp,
                    helper_window_source='split.json rank_tree.6.helper_occupancy_max (+ reader time for the MU '
                                         'shard: %d keys a die vs %d); MTP = one shared key read + 6 x (select + '
                                         'merge) -- the B3 shared read the record MU calendar assumes for S029 itself'
                                         % (mu_keys, n6))
    no_share = dict(compiled, helper_window_mtp=6 * hw_ar,
                    helper_window_source='as compiled, MTP = 6 x AR: p4l has ONE query store (no B3 shared read, '
                                         'MU.BAL.SX.4) -- a sensitivity: the record MTP calendar assumes the shared '
                                         'read on S029 itself too')
    MU = {}
    for tag, spl in (('no_split_measured_reader', None), ('split_model_windows', True), ('split_compiled_windows', compiled),
                     ('split_compiled_no_shared_read', no_share)):
        MU[tag] = {}
        for mode in ('ar', 'mtp'):
            if spl is None:
                m = C.load_model()
                C.apply_split(m, dict(sp, shard=10))        # S029 measured reader at its own 10 dies, no helpers
                st = C.stage_windows(m)
                d = C.design(m)
                cal = C.calendar_ar(m, st, d) if mode == 'ar' else C.calendar_mtp(m, st, d)
                r = C.record(mode, m, st, d, cal)
                chk = None
            else:
                r = C.build(mode, split=spl)
                chk = r['l20_split']['check']
            MU[tag][mode] = dict(users=r['users'], fillers=r['fillers'], per_user_tok_s=r['per_user_tok_s'],
                                 aggregate_tok_s=r['aggregate_tok_s'], period=r['period'], slot=r['slot'],
                                 lemma=r['lemma']['brute_force']['result'],
                                 helper=None if chk is None else {k: chk[k] for k in (
                                     'result', 'helper_window', 'helper_own_window', 'helper_busy_pct', 'n_collisions',
                                     'own_offset_first_feasible', 'own_offset_any', 'keys_die', 'collisions')})
    recm = {mode: jl(ROOT / f'results/arch/mu_s81_1018/calendar_{mode}.json') for mode in ('ar', 'mtp')}
    for v in MU.values():
        for mode in ('ar', 'mtp'):
            v[mode]['vs_record_agg_pct'] = round(100 * (v[mode]['aggregate_tok_s'] / recm[mode]['aggregate_tok_s'] - 1), 2)

    # ---------------------------------------------------------------- layer programme + cut replay
    layer = jl(LAYER / 'summary.json') if (LAYER / 'summary.json').exists() else dict(status='not run')

    # ---------------------------------------------------------------- ledger row values
    su_c = SU['split_k6_compiled_tree']['vs_record']
    mu_c = MU['split_compiled_windows']
    ledger = dict(group='S81.L20_SPLIT', price=round(rec_chain, 1), decision_price=round(price_split, 1), measured=round(comp6, 1),
                  e2e_loss_pct=dict(ar=round(max(0.0, -su_c['ar_pct']), 2), mtp=round(max(0.0, -su_c['mtp_pct']), 2)),
                  mu_loss_pct=dict(ar=round(max(0.0, -mu_c['ar']['vs_record_agg_pct']), 2),
                                   mtp=round(max(0.0, -mu_c['mtp']['vs_record_agg_pct']), 2)))
    out = dict(schema='opentallas.s81_l20_split.v1', lane='S81-L20SPLIT', date='2026-10-19',
               decision='coordinator 0li (HANDOFF 10-19 ~15:45): adopt the split of the L20 index scan over 2x the dies',
               fixtures=dict(dir=str(fx), manifest_sha256=hashlib.sha256(man.read_bytes()).hexdigest() if man.exists() else None),
               grade='compiled static plan (lower_bk) + RTL bench of every bk_sel job shape (Verilator 5.050) + measured '
                     'reader law (dsdv_idx_rg P=3) + measured cross-die leg 729; compositions on the models of record',
               rank_tree=rt, bench=bench, layer=layer, single_user=single, multi_user=MU,
               mu_helper_windows=dict(ar=hw_ar, mtp=hw_mtp, source=compiled['helper_window_source']), ledger=ledger)
    (HERE / 'split.json').write_text(json.dumps(out, indent=1) + '\n')
    print('rank tree chains (q -> root egress):', {k: v['chain_cycles'] for k, v in rt.items()},
          'closure', {k: v['closure'] for k, v in rt.items()})
    print('bench:', bench.get('result'))
    print('1u chains:', single['chains'])
    for k, v in SU.items():
        print(f"SU {k:32s} AR {v['ar_tok_s']:8.1f} ({v['vs_record']['ar_pct']:+.2f}%)  MTP {v['mtp_tok_s']:8.1f} "
              f"({v['vs_record']['mtp_pct']:+.2f}%)")
    for k, v in MU.items():
        print(f"MU {k:26s} AR {v['ar']['users']} = {v['ar']['aggregate_tok_s']} ({v['ar']['vs_record_agg_pct']:+.2f}%) "
              f"helper {v['ar']['helper']} | MTP {v['mtp']['users']}+{v['mtp']['fillers']} = {v['mtp']['aggregate_tok_s']} "
              f"({v['mtp']['vs_record_agg_pct']:+.2f}%) helper {v['mtp']['helper']}")
    print('ledger:', ledger)


if __name__ == '__main__':
    main()
