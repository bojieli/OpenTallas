#!/usr/bin/env python3
"""MU.CURVE regeneration 2026-10-21 (lane TOK-RATE-1021/MUCURVE): latency-throughput points vs the A100 80GB baseline.

Successor of the plot in tools/token_pass_status.py (mu_curve_1020_*): same axes and baseline, CURRENT inputs only, every
point labelled MODEL or MEASURED.  No new runs (owner 10-21): inputs are read from pinned git objects.

  S81 DeepSeek   claude/s81-link5-cal-1021 @c028c373c results/arch/mu_s81_1018/calendar_{ar,mtp}.json
                 (L5B-CAL, direct-cabled; exact calendar arithmetic on the S81-BALANCE stage model of record,
                 whose stage spans are built on per-layer measured benches) -> MODEL
  Qwen ROM       claude/qw-toksched2-1020 @94cd97b7a results/token_pass/measured_qwen_1019/cycles.json
                 (toksim_compose of record: 1u REL 60.0% + NEWEST 2.8%; 4u = OVL link-schedule frame scaled by the
                 schedule ledger, NEWEST) -> MODEL
  A100 80GB      Qwen3-8B measured on a rented 1x A100 80GB (Vast; HANDOFF section 2) -> MEASURED
  DeepSeek ref   published 8x H100 single-user ~33 tok/s (no A100 DeepSeek number; side note) -> PUBLISHED

  python3 tools/token_pass_mu_curve_1021.py   # writes results/token_pass/mu_curve_1021.{json,png}
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/token_pass'
TAG = '1021'
S81_REV, S81_DIR = 'c028c373c', 'results/arch/mu_s81_1018'
QW_REV, QW_FILE = '94cd97b7a', 'results/token_pass/measured_qwen_1019/cycles.json'
A100_1U, A100_MU_USERS, A100_MU_AGG = 114.8, 102, 1681.0
DS_REF = 33.0


def gshow(rev, path):
    return json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{rev}:{path}']))


def build():
    ar = gshow(S81_REV, f'{S81_DIR}/calendar_ar.json')
    mtp = gshow(S81_REV, f'{S81_DIR}/calendar_mtp.json')
    qw = gshow(QW_REV, QW_FILE)['result']
    s81_src = f'claude/s81-link5-cal-1021 @{S81_REV} {S81_DIR}/calendar_%s.json'
    s81_grade = 'MODEL (calendar on the S81-BALANCE stage model; stage spans from per-layer measured benches; not an RTL token run)'
    pts = []
    # S81: the calendar's per-user rate is the period; one user sees the same period (static schedule, no batching gain).
    for cal, mode in ((ar, 'AR'), (mtp, 'MTP')):
        pu = cal['per_user_tok_s']
        pts.append(dict(design='s81_ds', mode=mode, users=1, per_user_tok_s=pu, aggregate_tok_s=pu, grade=s81_grade,
                        src=s81_src % mode.lower(), period_cycles=cal['period']))
        p = dict(design='s81_ds', mode=mode, users=cal['users'], per_user_tok_s=pu, aggregate_tok_s=cal['aggregate_tok_s'],
                 grade=s81_grade, src=s81_src % mode.lower(), period_cycles=cal['period'],
                 collisions=cal['lemma']['brute_force']['n_collisions'])
        if cal.get('fillers'):
            p.update(fillers=cal['fillers'], filler_tok_s=cal['filler_tok_s'])
        pts.append(p)
    q1, q4 = qw['1u'], qw['4u_scheduled']
    qsrc = f'claude/qw-toksched2-1020 @{QW_REV} {QW_FILE}'
    pts.append(dict(design='qwen_rom', mode='AR', users=1, per_user_tok_s=q1['tok_s'], aggregate_tok_s=q1['tok_s'],
                    grade='MODEL (toksim_compose: 60.0% REL + 2.8% NEWEST measured RTL stages, rest DIAG/PRICED; KV attention DIAG)',
                    src=qsrc, cycles_per_token=q1['cycles_per_token']))
    pts.append(dict(design='qwen_rom', mode='AR', users=4, per_user_tok_s=min(q4['per_user_tok_s']),
                    per_user_tok_s_all=q4['per_user_tok_s'], aggregate_tok_s=q4['aggregate_tok_s'],
                    grade='MODEL (OVL 4-user link-schedule frame, NEWEST, scaled by the schedule ledger; no paired serial-MU RTL bench)',
                    src=qsrc + ' result.4u_scheduled', note='x = slowest user'))
    for p in pts:
        base = A100_1U if p['design'] == 'qwen_rom' else DS_REF
        p['per_user_vs_baseline_x'] = round(p['per_user_tok_s'] / base, 1)
    a100 = [dict(users=1, per_user_tok_s=A100_1U, aggregate_tok_s=A100_1U, grade='MEASURED (A100 80GB, Vast, Qwen3-8B)'),
            dict(users=A100_MU_USERS, per_user_tok_s=round(A100_MU_AGG / A100_MU_USERS, 1), aggregate_tok_s=A100_MU_AGG,
                 grade='MEASURED (A100 80GB, Vast, Qwen3-8B)')]
    q4agg = q4['aggregate_tok_s']
    return dict(schema='opentallas.token_pass.mu_curve.v1', asof='2026-10-21', lane='TOK-RATE-1021/MUCURVE',
                label='MODEL points (calendar / composition on measured per-layer benches) vs MEASURED A100 80GB',
                points=pts, a100_qwen3_8b=a100,
                deepseek_reference=[dict(users=1, per_user_tok_s=DS_REF, aggregate_tok_s=DS_REF,
                                         grade='PUBLISHED 8x H100 single-user (no A100 DeepSeek measurement; side note)')],
                headline=dict(qwen_rom_4u_vs_a100_102u_aggregate_x=round(q4agg / A100_MU_AGG, 1),
                              qwen_rom_1u_vs_a100_1u_x=round(q1['tok_s'] / A100_1U, 1)),
                notes=['x = per-user decode rate (latency), y = aggregate tok/s per deployment (S81 = 520 dies + 520 HBM stacks, '
                       'direct-cabled; Qwen ROM = one compute+KV package; A100 = one 80 GB GPU). No iso-area normalisation here.',
                       'S81 MTP aggregate includes 4 filler users at %.1f tok/s.' % mtp['filler_tok_s'],
                       'S81 rate is the 81-stage L5B-CAL calendar; the 72-frame 241-stage release map has no MU calendar yet.',
                       'Superseded: mu_curve_1020_* (S81 46 x 836 / 10 x 2,653.9 compose; Qwen 4u 12,601.2 DIAG).'])


# label placement (offset points, alignment) per (design, mode, users)
OFFSETS = {('s81_ds', 'AR', 1): ((8, -4), 'left'), ('s81_ds', 'MTP', 1): ((8, -16), 'left'),
           ('qwen_rom', 'AR', 1): ((8, 4), 'left'), ('s81_ds', 'MTP', 9): ((8, 4), 'left')}


def plot(cv, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 5.6), dpi=130)
    col = dict(s81_ds='#3987e5', qwen_rom='#199e70')
    lab = dict(s81_ds='DeepSeek S81 (520 dies)', qwen_rom='Qwen3-8B ROM (compute+KV)')
    for d in col:
        for mode, mk in (('AR', 'o'), ('MTP', 's')):
            ps = sorted([p for p in cv['points'] if p['design'] == d and p['mode'] == mode], key=lambda p: p['users'])
            if not ps:
                continue
            ax.plot([p['per_user_tok_s'] for p in ps], [p['aggregate_tok_s'] for p in ps], marker=mk, ms=8, color=col[d],
                    mfc='white', mew=2, lw=2, ls='--', label=f'{lab[d]} {mode}  MODEL')
            for p in ps:
                t = f"{p['users']}u" + (f"+{p['fillers']}f" if p.get('fillers') else '')
                t += f"  {p['per_user_tok_s']:,.0f}/u, {p['aggregate_tok_s']:,.0f}"
                off, ha = OFFSETS.get((d, mode, p['users']), ((-8, 6), 'right'))
                ax.annotate(t, (p['per_user_tok_s'], p['aggregate_tok_s']), textcoords='offset points',
                            xytext=off, ha=ha, fontsize=7, color='#333333')
    a = cv['a100_qwen3_8b']
    ax.plot([p['per_user_tok_s'] for p in a], [p['aggregate_tok_s'] for p in a], marker='^', ms=8, color='black', lw=2,
            label='A100 80GB Qwen3-8B  MEASURED (Vast)')
    for p in a:
        ax.annotate(f"{p['users']}u  {p['per_user_tok_s']:,.1f}/u, {p['aggregate_tok_s']:,.0f}", (p['per_user_tok_s'], p['aggregate_tok_s']),
                    textcoords='offset points', xytext=(7, -12), fontsize=7, color='#333333')
    r = cv['deepseek_reference'][0]
    ax.plot([r['per_user_tok_s']], [r['aggregate_tok_s']], marker='x', color='grey', ms=8, ls='none',
            label='DeepSeek ref: 8x H100 1 user  PUBLISHED')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlim(8, 30000); ax.set_ylim(15, 2e5)
    ax.set_xlabel('per-user decode rate (tok/s)  -> lower latency')
    ax.set_ylabel('aggregate decode rate (tok/s)')
    ax.set_title('MU.CURVE latency-throughput vs A100 80GB  (2026-10-21)\n'
                 'hollow/dashed = MODEL (calendar / composition on measured per-layer benches); solid = MEASURED', fontsize=9)
    ax.grid(True, which='both', alpha=0.2)
    ax.legend(fontsize=7, loc='upper left')
    fig.tight_layout()
    fig.savefig(path)


def main():
    cv = build()
    (OUT / f'mu_curve_{TAG}.json').write_text(json.dumps(cv, indent=1) + '\n')
    plot(cv, OUT / f'mu_curve_{TAG}.png')
    for p in cv['points']:
        print(p['design'], p['mode'], p['users'], p['per_user_tok_s'], p['aggregate_tok_s'], p['grade'].split(' ')[0])


if __name__ == '__main__':
    main()
