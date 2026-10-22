#!/usr/bin/env python3
"""S81-L20 (10-19): end-to-end AR / MTP effect of the MEASURED L20 index scan on the S81 p4l (MU release) die, at 1 user
and at the multi-user owner configuration (46 AR users / 10 MTP + 1 filler), plus the structural fix options.

Measured inputs (no new pricing of the reader itself):
  * the p4l regional index reader dsdv_idx_rg (lane S81-IDXRD, RTL 4cc3975d1, Verilator 5.050, results/rtl/s81_idxrd_1018/
    sweep_1019.txt): scan P=3 PASS  L20 N 87,382 keys -> 16,895 cycles, L2 N 43,691 -> 8,702 cycles (hdr_to_last);
    P=2 FAILS fail-closed at every T0 (HBM-bound).  Two points give the measured reader law
        cycles(N) = 3 N / 16 + T0r,   T0r = 510.9 (L20) / 509.9 (L2)  -> 5.33 keys / cycle / die (16 regions, P = 3)
  * the TOK-S81-GAPS L20 cut replay 44,256 cycles vs price 30,635.4 (claude/tok-s81-gaps-1018 ae517d216) is NOT used as
    the L20 number: its bk_sel ingress (lower_bk) feeds the UNSHARDED 262,144 rank keys a die (32,772 rung beats,
    topk_local calendar issue 44,188), while the record design (S81-SCAND option D, k = 3) shards them over 3 dies
    (87,382 a die).  At k = 3 the reader (16,895) bounds the scan, not the rung (87,382 / 8 = 10,923).  -> compiler fix
    owed in lower_bk (NKEYS / K), recorded below as a finding.

Compositions (both are the models of record; nothing re-derived):
  1 user   results/arch/s81_idxrd_1018/b3_price.py (SCAND machinery: accepted_cost.solve on the 10-09 DS ROM DAG + MTP
           wave rule on the 10-18 composition basis) with per-layer reader-cycle overrides; basis = D_measured_reader
           (AR 1,224.1 / MTP 3,711.7 = S81 record).
  MU       tools/s81_dv/dv_mu_calendar.py (the record calendar: 46 AR users; 10 MTP + 1 filler) on the S81-BALANCE
           stage model results/arch/s81_balance_1018/compute.py, whose index scan term (HBM stream at 791.7 B/cycle a
           stack, 11.6 keys/cycle) is replaced on the chosen groups by the measured reader law on the group's own keys
           a die (D_CTX x 68 B / 68 B / shard).
Run: python3 results/arch/s81_l20_1019/l20_effect.py   (writes l20_effect.json beside it)
"""
import contextlib
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ measured reader (S81-IDXRD sweep_1019.txt)
MEAS = {'L20': (87382, 16895), 'L2': (43691, 8702)}          # keys a die, cycles (P = 3 PASS)
P_MEAS = 3
T0R = round(sum(c - P_MEAS * n / 16 for n, c in MEAS.values()) / len(MEAS), 1)


def reader(n, p=P_MEAS):
    """measured law: one key every p cycles in each of 16 regions + the measured start-up"""
    return math.ceil(p * n / 16 + T0R)


# ------------------------------------------------------------------ 1 user: the SCAND / B3 machinery of record
B3 = load('b3_price', ROOT / 'results/arch/s81_idxrd_1018/b3_price.py')
FULL = B3.FULL                                    # {2: L2, 8: L2, 14: L2, 20: L20} (layer -> key class)
rec_rd = dict(B3.meas_rd)                         # D_measured_reader: 3,724 (L2 class) / 7,700 (L20)


def su(reader_by_layer, xd_extra=None):
    """single-user AR / MTP with reader overrides; xd_extra {layer: extra merge/leg cycles} (window split)"""
    rd = dict(reader_by_layer)
    for L, x in (xd_extra or {}).items():
        rd[L] = rd[L] + x
    r = B3.compose(rd, rd)
    base = B3.S['D_measured_reader']
    r['vs_record'] = dict(ar_pct=round(100 * (r['ar_tok_s'] / base['ar_tok_s'] - 1), 2),
                          mtp_pct=round(100 * (r['mtp_tok_s'] / base['mtp_tok_s'] - 1), 2))
    r['reader_cycles'] = {f'L{L}': v for L, v in rd.items()}
    return r


meas_l20 = {**rec_rd, 20: MEAS['L20'][1]}
meas_all = {L: MEAS[lay][1] for L, (lay, _) in FULL.items()}
p2 = lambda d: {L: reader(B3.NKEYS[FULL[L][0]], 2) for L in d}      # P = 2 (the rung rate, 8 keys/cycle)
K3 = B3.K


def xd(k):
    return 2 * math.ceil((k - 1) / 2) * B3.LEG + B3.FINAL * (k - 1)


SU = {
    'record_D': su(rec_rd),
    'L20_measured': su(meas_l20),
    'all_scan_measured': su(meas_all),
    'fix_P2_reader_L20': su({**meas_all, 20: reader(B3.NKEYS['L20'], 2)}),
    'fix_P2_reader_all': su(p2(meas_all)),
    'fix_split_L20_k6': su({**meas_all, 20: reader(math.ceil(B3.NKEYS['L20'] * K3 / 6))},
                           {20: xd(6) - xd(K3)}),
    'L20only_fix_P2': su({**rec_rd, 20: reader(B3.NKEYS['L20'], 2)}),
    'L20only_fix_split_k6': su({**rec_rd, 20: reader(math.ceil(B3.NKEYS['L20'] * K3 / 6))}, {20: xd(6) - xd(K3)}),
}

# ------------------------------------------------------------------ multi-user: the record calendar on the patched model
CAL = load('dv_mu_calendar', ROOT / 'tools/s81_dv/dv_mu_calendar.py')
L20_GROUP = 'S029'                                  # dv_mu_calendar.DUP_LAYER: S029 owns layer 20


def mu(groups_measured, p=P_MEAS, shard=None, n_ar=None):
    m = CAL.load_model()
    if shard:
        m.sh_all = dict(m.sh_all, **shard)
    orig = m.group_occ
    BPC = m.BPC_STACK

    def occ(g, shard=4, stacks_per_die=1, **kw):
        if g['id'] not in groups_measured or g['idx_score_cycles'] <= 0:
            return orig(g, shard=shard, stacks_per_die=stacks_per_die, **kw)
        keys_die = m.SCAN_BYTES[g['idx_score_cycles']] / m.IDX_B / (shard * stacks_per_die)
        # measured cycles, expressed in the model's pre-K units (group_occ multiplies its classes by K)
        meas = reader(keys_die, p) / m.K
        # the same scan term group_occ uses, inverted: an effective B/cycle that yields `meas`, plus no other change
        m.BPC_STACK = m.SCAN_BYTES[g['idx_score_cycles']] / (shard * stacks_per_die * meas)
        try:
            return orig(g, shard=shard, stacks_per_die=stacks_per_die, **kw)
        finally:
            m.BPC_STACK = BPC
    m.group_occ = occ
    st = CAL.stage_windows(m)
    d = CAL.design(m)
    out = {}
    for mode in ('ar', 'mtp'):
        cal = CAL.calendar_ar(m, st, d, n_ar) if mode == 'ar' else CAL.calendar_mtp(m, st, d)
        rec = CAL.record(mode, m, st, d, cal, None)
        g = {x['id']: x for x in st}
        out[mode] = dict(users=rec['users'], fillers=rec['fillers'], period=rec['period'], slot=rec['slot'],
                         per_user_tok_s=rec['per_user_tok_s'], aggregate_tok_s=rec['aggregate_tok_s'],
                         lemma=rec['lemma']['brute_force']['result'],
                         s029=dict(occ=g[L20_GROUP]['occ'], step=g[L20_GROUP]['step'], span=g[L20_GROUP]['span']),
                         nonrep_max=rec['lemma']['premise']['nonrep_window_max'],
                         first_fail=next((t for t in (rec.get('search') or []) if t['result'] == 'FAIL'), None))
    out['single_user_model'] = dict(ar=d['single_user_ar'], mtp=d['single_user_mtp'], T_ar=d['T_ar'], T_mtp=d['T_mtp'])
    out['dies'] = d['dies']
    return out


FULLG = ['S002', 'S011', 'S020', 'S029']
MU = {
    'record': mu(()),
    'L20_measured': mu((L20_GROUP,)),
    'all_full_scan_measured': mu(tuple(FULLG)),
    'fix_P2_reader_all': mu(tuple(FULLG), p=2),
    'fix_split_L20_shard20': mu(tuple(FULLG), shard={L20_GROUP: 20}),
    'fix_split_L20_shard20_P2': mu(tuple(FULLG), p=2, shard={L20_GROUP: 20}),
    'L20only_fix_P2': mu((L20_GROUP,), p=2),
    'L20only_fix_split_shard20': mu((L20_GROUP,), shard={L20_GROUP: 20}),
}
# a third copy of S029 only (+10 dies): copies are used round-robin on the uniform calendar, so every copy's gap is a
# multiple of the slot; S029 at the measured occupancy needs gaps >= 3 slots -> N divisible by 3, and the other seven
# 2-copy groups need N even -> N divisible by 6, N <= floor(P / non-replicated window max)
_r = MU['L20_measured']['ar']
_n = max(n for n in range(1, int(_r['period'] // _r['nonrep_max']) + 1) if n % 6 == 0
         and 3 * _r['period'] / n >= _r['s029']['occ'])
MU_COPY3 = dict(users=_n, aggregate_tok_s=round(_n * _r['per_user_tok_s']),
                vs_record_agg_pct=round(100 * (_n * _r['per_user_tok_s'] / MU['record']['ar']['aggregate_tok_s'] - 1), 2),
                added_dies=10, rule='N % 6 == 0 (3 copies of S029 x 2 copies of the other 7 groups), 3 P / N >= S029 occ, '
                                    'N <= P / non-replicated max')
for k, v in MU.items():
    b = MU['record']
    for mode in ('ar', 'mtp'):
        v[mode]['vs_record_agg_pct'] = round(100 * (v[mode]['aggregate_tok_s'] / b[mode]['aggregate_tok_s'] - 1), 2)

# ------------------------------------------------------------------ ledger rule check (AGENTS accepted cost)
RULE = dict(per_unit_pct=5.0, per_design_pct=15.0, ledger='accepted-cost ledger (owner 10-13)')
su20 = SU['L20_measured']['vs_record']
mu20 = {m: MU['L20_measured'][m]['vs_record_agg_pct'] for m in ('ar', 'mtp')}
within = all(abs(min(0.0, x)) <= RULE['per_unit_pct'] for x in (su20['ar_pct'], su20['mtp_pct'], mu20['ar'], mu20['mtp']))

out = dict(
    schema='opentallas.s81_l20_effect.v1', lane='S81-L20', date='2026-10-19',
    grade='composed: measured reader cycles (RTL bench) in the models of record (SCAND solve 1 user; S81-BALANCE '
          'stage model + record MU calendar)',
    measured_reader=dict(points=MEAS, P=P_MEAS, t0_cycles=T0R, keys_per_cycle_die=round(16 / P_MEAS, 2),
                         law='cycles = P N / 16 + T0', source='results/rtl/s81_idxrd_1018/sweep_1019.txt (RTL 4cc3975d1)',
                         p2='FAIL fail-closed at T0 400..3000 (HBM-bound: per-PC request depth DQ 8 vs ~235-cycle '
                            'HBM latency), so the P=2 rows are a FIX TARGET, not a measurement; S81-L20 probe '
                            'dq_probe_1019.txt: DQ 16/15 fails P=2 identically to DQ 8 (nerr 2040 / 301) -> request '
                            'depth is not the limit; no measured P=2 reader exists'),
    recommendation='split the L20 index window over 2x dies (MU: S029 keys over its 10 dies + 10 dies of a neighbouring '
                   'non-scan group, shard 20; 1 user: k = 6): no added silicon, MU 46 users kept (AR -0.01 %, MTP +0.04 %), '
                   '1 user AR -0.45 % / MTP -1.95 % vs record; caveat: the helper dies\' HBM PC windows must be calendared '
                   '(the MU lemma does not model them yet)',
    tok_cut_replay=dict(L20=44256, price=30635.4,
                        why_not_used='lower_bk feeds 262,144 unsharded rank keys a die into bk_sel (32,772 rung '
                                     'beats); the record design shards them k = 3 (87,382 a die): compiler fix owed '
                                     '(lower_bk NKEYS / K) before the cut replay measures the record L20'),
    single_user=SU, multi_user=MU, multi_user_s029_three_copies=MU_COPY3, rule=RULE,
    l20_within_rule=within)
(HERE / 'l20_effect.json').write_text(json.dumps(out, indent=1) + '\n')
for k, v in SU.items():
    print(f"SU {k:22s} AR {v['ar_tok_s']:8.1f} ({v['vs_record']['ar_pct']:+.2f}%)  MTP {v['mtp_tok_s']:8.1f} "
          f"({v['vs_record']['mtp_pct']:+.2f}%)  rd {v['reader_cycles']}")
for k, v in MU.items():
    a, t = v['ar'], v['mtp']
    print(f"MU {k:26s} AR {a['users']:2d} x {a['per_user_tok_s']:7.1f} = {a['aggregate_tok_s']:6d} ({a['vs_record_agg_pct']:+.2f}%) "
          f"S029 occ {a['s029']['occ']} | MTP {t['users']}+{t['fillers']} = {t['aggregate_tok_s']:6d} "
          f"({t['vs_record_agg_pct']:+.2f}%) S029 step {t['s029']['step']} nonrep {t['nonrep_max']} slot {t['slot']} "
          f"| 1u model AR {v['single_user_model']['ar']} MTP {v['single_user_model']['mtp']}")
print('MU S029 3 copies (+10 dies):', MU_COPY3)
print('L20 within rule (<= 5 % a unit, 1 user and MU):', within)
