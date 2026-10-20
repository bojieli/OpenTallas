#!/usr/bin/env python3
"""Token-pass tracker, MU curve and freeze checklist (lane TOKEN-REC 2026-10-19; TOKEN-LEAD2 2026-10-20: measured RECORDS, TAG-named outputs).

Owner rule (token-pass-release-gate-1018): the token pass = per-layer RTL sims on the CURRENT RELEASE dies + static schedule
+ inter-die traffic, real cycles, single-user AND multi-user, for every design.  This tool does not measure anything: it
joins (a) the graded composition of record (tools/token_compose_xdie.py -> results/arch/token_path_1018/) with (b) the
per-element state below (curated from the RELEASE_TREE TOKEN lines and the owning lane files on the date in STATUS_ASOF)
and writes:

  results/token_pass/status_1019.{json,md}   design x {1-user, multi-user}: each layer / collective -> measured on a
                                             release die / measured on an older or diagnostic die / priced / missing
  results/token_pass/mu_curve_1019.{json,png}  latency-throughput points vs the A100 80GB baseline, PRICED until the
                                             token pass measures them
  --page-data DIR                            adds token_pass_1019 to each design file of the fleet-viz token page

Grades used here are against the RELEASE dies (owner mu-dies-are-release-dies-1019), which is stricter than the compose
tool's "measured-current-RTL" (that one counts the 10-18 single-user dies GEN2 / dv2f14 / kvs14c as current):
  REL   measured in RTL on the release die build (or its byte-identical sources)
  DIAG  measured in RTL, but on an older / diagnostic die or old vehicle (does not count for the pass)
  PRICE analytic or calendar-modelled only
  MISS  no measurement and the bench/vehicle does not exist yet

  python3 tools/token_pass_status.py [--page-data tools/fleet_viz/explorer/token/data ~/.local/share/fleet-viz/explorer/token/data]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / 'results/arch/token_path_1018'
OUT = ROOT / 'results/token_pass'
STATUS_ASOF = '2026-10-20 05:05 PDT'
TAG = '1020_0505'

RELEASE_DIES = {
    'ds_rom': 'S81 p4l-MU (520 dies; die gates est. 10-22..24)',
    'qwen_rom': 'Qwen compute dv2f19g2 -> GEN3 dv2f19g3 + KV/system kvs14 GEN9',
    'hbm_gen_ds': 'HBM d4g GEN2e4 (GEN2/GEN2d diagnostic)',
    'hbm_gen_qwen': 'HBM d4g GEN2e4 (GEN2/GEN2d diagnostic)',
}

# (element, grade, evidence / build, owner lane, tree id)
E = lambda el, g, ev, own, tid: dict(element=el, grade=g, evidence=ev, owner=own, tree=tid)
ELEMENTS = {
    ('ds_rom', '1u'): [
        E('Per-family component benches composed (p4l release RTL)', 'REL', 'partial: toksim-s81e 1fd2cdf8f (sparse a_proj front L8/14/28/32/36 measured): AR 836.0 at 81.02% measured / MTP 2,653.9 at 72.21%; GL24 64/64 owner views PASS d5fcf23d5; PHY 12.0% modelled; S81-WQBP P126/P231 candidate 901.8/2,832 (36163250c) awaits COORD adoption', 'TOKEN-LEAD2', 'TOK.DS'),
        E('L0 dense attention (die)', 'REL', 'partial: cut_7 L0 MU-A slice 564/564 + hop 480/480 PASS, 3 mutants CAUGHT (S81-TOK4 63b8a0d5e); full layer open', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.1'),
        E('L2 sparse attention + indexer (die)', 'DIAG', 'old 10-13 record; p4l index reader/helper transport missing', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.2'),
        E('L14 Engram layer (die)', 'DIAG', 'old 10-13 record; CAP L2/L14 512CW+512VP capture PASS (component); row-read integration open', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.3'),
        E('L20 compressed layer (die)', 'REL', 'partial: L20 k=6 split bk_sel job shapes RTL bench (Verilator 5.050), split.json; full layer open', 'LEAD4-S81/L20', 'TOK.DS.LAYER.4'),
        E('LM head (die)', 'DIAG', 'old record; real fold/gain/G8-NX-XB producer missing on p4l', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.5'),
        E('MTP draft layer (die)', 'DIAG', 'old record; draft body after real head producer', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.6'),
        E('DV layer-programme compiler (full layer)', 'MISS', 'private CAP512/VP512 source-derived proof 2ea06839c; 8-frame lowering + consumer retire/deadline OPEN', 'TOKEN-LEAD2/S81-CAP', 'TOK.DS.BENCH.1'),
        E('TP4 collectives + hops (array)', 'REL', 'xdie_s81: SU strict 12,096/12,096 bit-exact (480895e39); c_g1 guard-2 WIN/INV PASS', 'TOKEN-LEAD2', 'TOK.DS.XDIE.5'),
        E('Off-chip PHY/switch legs', 'PRICE', 'modelled-PHY constants (12.0% of AR / 10.9% of MTP token cycles)', 'TOKEN-LEAD2', 'TOK.DS.XDIE.5'),
    ],
    ('ds_rom', 'mu'): [
        E('46-user AR / 10-user MTP calendar', 'REL', 'partial: slot issue measured on release seq_host/fixed_issue RTL, 0 collisions (cal1 152d70002); per-user = 1u compose', 'TOKEN-LEAD2', 'MU.S81.CAL'),
        E('Multi-user collectives on MU die (u5, guard 2)', 'REL', 'u_ar46d 278,024 beats 46/46 + u_mtp10d 60,440 beats 10/10 WIN/INV PASS; realshift ar46r/mtp10r live ep5', 'TOKEN-LEAD2', 'TOK.DS.XDIE.5'),
        E('Host plane N outstanding + MTP seed', 'REL', 'partial: SEQHOST_MU on die master; NS47 ph0-5 PASS, 6-10 state owed', 'LEAD4-S81/MU', 'MU.TOK.DS4'),
        E('Per-user layer benches', 'REL', 'partial: L0 MU-A slice (prog_L0_mu_A) 564/564 PASS; other layers + QF producers owed', 'LEAD4-S81/TOK2', 'TOK.DS.LAYER.MU'),
        E('lep tag + second landing + A/B select', 'MISS', 'lepmu{a,h}_dr gates; hier v2 d7cb08cb2 unrun', 'LEAD4-S81/MUBUF3', 'MU.TOK.DS3'),
    ],
    ('qwen_rom', '1u'): [
        E('L0 + chained layer x35 (compute die, GEN3 rel)', 'REL', 'partial: toksim-qw2 4eeeaf287 gen3 DV ages + priced die edges folded: 254,125 cyc/token, 62.8% REL / 26.9% DIAG / 9.8% PRICED', 'TOKEN-LEAD2/TOK-QW', 'TOK.QW.LAYER.2'),
        E('Attention return (dr words + o_proj stream)', 'DIAG', 'no gen3 attn bench mode (compiled 119 vs measured 98)', 'TOKEN-LEAD2/TOK-QW', 'TOK.QW.LAYER.1'),
        E('LM head', 'PRICE', 'priced 3,101 cyc; head span RTL owed (QW-SEGCAL head WIP)', 'LEAD4-QW', 'TOK.QW.LAYER.3'),
        E('KV attention 1u (KV die GEN9)', 'MISS', 'tb_kvattn_rel job3 (src fafc28231, ep5 out_fafc28231) still in Verilator build at 05:01 (live since 02:20); KV service 1,779 on kvs14c stand-in = DIAG', 'TOKEN-LEAD2/TOK-KVATT', 'TOK.QW.KV'),
        E('Layer-programme compiler (tt_ctlm deployment)', 'MISS', 'tt_ctlm deployment programme (G-C3) missing; STORE BLOCKED', 'LEAD4-QW', 'TOK.QW.BENCH.1'),
        E('36-layer TP4 golden', 'MISS', 'canonical driver done 21:13; gold4 ISA golds generated (not RTL), provenance FAIL retained', 'LEAD4-QW', 'TOK.QW.BENCH.2'),
        E('Compute <-> KV D2D (1u)', 'DIAG', 'dh2 1u PASS; shared D2D transport native proof c92c2be9d; release pair owed', 'LEAD4-QW', 'TOK.QW.XDIE'),
        E('TP8 all-reduce windows', 'REL', 'TP8 AR E 286 per window measured (composer REL)', 'TOKEN-LEAD2/TOK-QW', 'TOK.QW.SCHED'),
    ],
    ('qwen_rom', 'mu'): [
        E('4-user link schedule (OVL D2D pair full frame)', 'DIAG', '12,601.2 agg scheduled (users 4,383/4,109/2,192/1,918; die edges folded, toksim-qw2 4eeeaf287); OVL not in gen3 -> NEWEST, not release', 'TOKEN-LEAD2/TOK-QW', 'MU.TOK.QW'),
        E('NU4 stage cuts', 'REL', 'partial: NU4 stage cuts PASS on dv2f18dh2', 'LEAD4-QW', 'MU.TOK.QW'),
        E('4-user KV attention', 'MISS', 'u4 T1k/4k/8k in tb_kvattn_rel job2 (terminated); KV-TOK3 controlled_n identity FAIL', 'TOKEN-LEAD2/TOK-KVATT', 'MU.QW.KVATT'),
        E('4-user compute <-> KV pair (serial MU calendar)', 'MISS', 'release uses serial MU calendar; paired 4u TB absent', 'LEAD4-QW', 'TOK.QW.XDIE'),
        E('4-user golden (gold4)', 'MISS', 'four shared-prefix ISA golds generated, not RTL', 'LEAD4-QW', 'MU.TOK.QW'),
    ],
    ('hbm_gen_ds', '1u'): [
        E('Per-unit benches composed on the static schedule', 'REL', 'partial: toksim-hbm 20c323c47 combined 1,109.7; used cycles 12.3% bound-measured / 63.8% measured-not-bound / 24.0% model', 'TOKEN-LEAD2/TOK-HBM', 'TOK.HDS'),
        E('SU reductions through bound HH-6 pre-tree', 'MISS', 'PRETREE2 a5cc6f083: max4/phased4 PASS (Qwen); census --measured fold owed', 'LEAD4-HBM/PRETREE', 'TOK.HDS'),
        E('d4g record -> per-unit image compiler (R6)', 'MISS', 'R6 native exit 1 17:48; collect + classify', 'LEAD4-HBM/L2H-TOK', 'TOK.HDS.VEH.2'),
        E('Quadrant (SW) cutter + bench', 'MISS', 'needs GEN2e4 die.v + R6 multi-group', 'LEAD4-HBM/L2H-TOK', 'TOK.HDS.VEH.4'),
        E('Cross-die collectives (AG/RS144/COLL)', 'DIAG', 'xdie_hbm on GEN2 RTL; die must bind COLL ROWS256/AR_ITER', 'LEAD4-HBM/L2H-TOK', 'TOK.HDS.XDIE'),
    ],
    ('hbm_gen_ds', 'mu'): [
        E('HBM multi-user', 'PRICE', 'NOT IN THIS RELEASE (owner 10-18 23:45: next release; HNEXT 4-user 4,251 priced)', 'HNEXT', '-'),
    ],
    ('hbm_gen_qwen', '1u'): [
        E('Per-unit benches composed (packed INT8 SM.MATVEC + SU.VOP)', 'REL', 'partial: toksim-hbm 20c323c47 combined 372.2; used cycles 10.6% bound / 80.8% not-bound / 8.6% model', 'TOKEN-LEAD2/TOK-HBM', 'TOK.HQ'),
        E('Softmax reductions (pre-tree + MAX)', 'MISS', 'as-built ingress-bound exp_sum 22,316 vs 590/rec; bound pre-tree+MAX est ~990 (unmeasured)', 'LEAD4-HBM/PRETREE', 'TOK.HQ'),
        E('L0 layer (d4g vehicle)', 'DIAG', 'L0p0 rec17/23 PASS, rec6/10 FAIL -> R6; on GEN2 vehicle', 'LEAD4-HBM/L2H-TOK', 'TOK.HQ.LAYER'),
        E('TP8 all-reduce (cross-die)', 'DIAG', 'xdie_hbm_1019 Qwen AR on GEN2 RTL (2,926 cyc/layer); COLL 1.24x', 'LEAD4-HBM/L2H-TOK', 'TOK.HQ'),
    ],
    ('hbm_gen_qwen', 'mu'): [
        E('HBM multi-user', 'PRICE', 'NOT IN THIS RELEASE (owner 10-18 23:45: next release)', 'HNEXT', '-'),
    ],
}

# Composition of record per design (TOKEN-LEAD2 10-20): latest measured records, not the 10-18 compose index.
RECORDS = {
    'ds_rom': dict(src='claude/toksim-s81e-1020 1fd2cdf8f results/token_pass/measured_s81_1019/cycles.json (on Codex GL24 d5fcf23d5)',
                   ar=836.0, ar_pct=81.02, mtp=2653.9, mtp_pct=72.21, mu_ar=(46, 836.0, 38456.0), mu_mtp=(10, 2653.9, 26539.0),
                   prev='834.0 AR / 2,649.1 MTP (10-20 02:45 status)'),
    'qwen_rom': dict(src='claude/toksim-qw2-1020 4eeeaf287 results/token_pass/measured_qwen_1019', ar=4724.0, ar_pct=62.8,
                     mu=(4, 1917.6, 12601.2, '4,383 / 4,109 / 2,192 / 1,918'), prev='5,141.3 (10-20 02:45 status, die edges not folded)'),
    'hbm_gen_ds': dict(src='claude/toksim-hbm-1019 20c323c47 measured_hbm_1019/combined_1020', ar=1109.7, ar_pct=12.3, pct_label='bound-measured; 76.1% incl. measured-not-bound',
                       prev='1,233.4 (10-19 compose incl. LH-REPRICE3)'),
    'hbm_gen_qwen': dict(src='claude/toksim-hbm-1019 20c323c47 measured_hbm_1019/combined_1020', ar=372.2, ar_pct=10.6, pct_label='bound-measured; 91.4% incl. measured-not-bound',
                         prev='403.2 (10-19 compose incl. LH-REPRICE3)'),
}

FLAGS = [
    'S81 MTP 2,653.9 accepted tok/s is BELOW the owner floor (DS ROM MTP > ~3,000, owner 10-15); AR 836.0 is -31% vs the 1,212.6 compose (owner ledger: <= 15% total/design); S81-WQBP candidate 901.8/2,832 still below the floor. Coordinator/owner decision needed.',
    'HBM-Qwen 372.2 tok/s as-built (softmax reductions ingress-bound); HH-6 pre-tree + MAX bind is the release lever (est ~990, unmeasured).',
    'Qwen KV attention on GEN9 has NO measurement yet: tb_kvattn_rel job3 still building on ep5 (05:01); Qwen 1u falls 5,141.3 -> 4,724.0 once priced die edges are folded (toksim-qw2).',
]

# A100 80GB baseline (owner compare-against-a100-same-node-1018; HANDOFF section 2): Qwen3-8B measured on Vast.
A100 = [dict(users=1, per_user_tok_s=114.8, aggregate_tok_s=114.8, grade='MEASURED (A100 80GB, Vast)'),
        dict(users=102, per_user_tok_s=round(1681 / 102, 1), aggregate_tok_s=1681.0, grade='MEASURED (A100 80GB, Vast)')]
DS_REF = [dict(users=1, per_user_tok_s=33.0, aggregate_tok_s=33.0,
               grade='PUBLISHED 8x H100 single-user (no A100 measurement; different node, side note only)')]


def load_comp():
    ix = json.loads((COMP / 'index.json').read_text())
    return ix


def tally(rows):
    t = {g: 0 for g in ('REL', 'DIAG', 'PRICE', 'MISS')}
    for r in rows:
        t[r['grade']] += 1
    return t


def verdict(d, u, rows):
    if d.startswith('hbm') and u == 'mu':
        return 'NOT IN RELEASE'
    # No design has a full token measured on its release die (10-20). PARTIAL = some release-die RTL measurement composed.
    return 'PARTIAL' if any(r['grade'] == 'REL' for r in rows) else 'NOT RUN'


def curve(ix):
    pts = []
    r = RECORDS['ds_rom']
    pts.append(dict(design='ds_rom', mode='AR', users=1, per_user_tok_s=r['ar'], aggregate_tok_s=r['ar'],
                    grade='PARTIAL (%.2f%% measured on p4l component benches)' % r['ar_pct']))
    u, pu, ag = r['mu_ar']
    pts.append(dict(design='ds_rom', mode='AR', users=u, per_user_tok_s=pu, aggregate_tok_s=ag,
                    grade='PARTIAL (calendar slot issue on release RTL x 1u compose; MU collectives u5 PASS)'))
    pts.append(dict(design='ds_rom', mode='MTP', users=1, per_user_tok_s=r['mtp'], aggregate_tok_s=r['mtp'],
                    grade='PARTIAL (%.2f%% measured)' % r['mtp_pct']))
    u, pu, ag = r['mu_mtp']
    pts.append(dict(design='ds_rom', mode='MTP', users=u, per_user_tok_s=pu, aggregate_tok_s=ag,
                    grade='PARTIAL (calendar on release RTL x 1u compose)'))
    q = RECORDS['qwen_rom']
    pts.append(dict(design='qwen_rom', mode='AR', users=1, per_user_tok_s=q['ar'], aggregate_tok_s=q['ar'],
                    grade='PARTIAL (%.1f%% REL, KV attention DIAG)' % q['ar_pct']))
    u, pu, ag, note = q['mu']
    pts.append(dict(design='qwen_rom', mode='AR', users=u, per_user_tok_s=pu, aggregate_tok_s=ag, per_user_note=note + ' (slowest shown)',
                    grade='DIAG (OVL link schedule, not release gen3)'))
    for d in ('hbm_gen_ds', 'hbm_gen_qwen'):
        w = RECORDS[d]
        pts.append(dict(design=d, mode='AR', users=1, per_user_tok_s=w['ar'], aggregate_tok_s=w['ar'],
                        grade='PARTIAL (unit benches composed; %.1f%% bound-measured)' % w['ar_pct']))
    for p in pts:
        base = 114.8 if p['design'] in ('qwen_rom', 'hbm_gen_qwen') else 33.0
        p['per_user_vs_baseline_x'] = round(p['per_user_tok_s'] / base, 1)
    return dict(schema='opentallas.token_pass.mu_curve.v1', asof=STATUS_ASOF, label='PARTIAL: composed from measured records; TOK.FREEZE measures the final',
                points=pts, a100_qwen3_8b=A100, deepseek_reference=DS_REF,
                notes=['x = per-user decode rate (latency), y = aggregate tok/s per deployment (S81 = 520 dies + 520 stacks; '
                       'Qwen ROM = one compute+KV package; A100 = one 80 GB GPU).',
                       'Iso-area/iso-power normalisation is not applied here (owner rule: count logic + HBM area both sides).',
                       'Qwen baseline = A100 80GB measured; DeepSeek has no A100 number (published 8x H100 single-user, side note).'])


def plot(cv, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.5, 5.6), dpi=130)
    col = dict(ds_rom='#3987e5', qwen_rom='#199e70', hbm_gen_ds='#9085e9', hbm_gen_qwen='#c98500')
    lab = dict(ds_rom='DS ROM S81 (520 dies)', qwen_rom='Qwen ROM (compute+KV)', hbm_gen_ds='HBM-DS d4g', hbm_gen_qwen='HBM-Qwen d4g')
    for d in col:
        for mode, mk in (('AR', 'o'), ('MTP', 's')):
            ps = sorted([p for p in cv['points'] if p['design'] == d and p['mode'] == mode], key=lambda p: p['users'])
            if not ps:
                continue
            ax.plot([p['per_user_tok_s'] for p in ps], [p['aggregate_tok_s'] for p in ps], marker=mk, color=col[d],
                    ls='--', label=f'{lab[d]} {mode} (PARTIAL)')
            for p in ps:
                ax.annotate(f"{p['users']}u", (p['per_user_tok_s'], p['aggregate_tok_s']), textcoords='offset points',
                            xytext=(5, 4), fontsize=7, color=col[d])
    a = cv['a100_qwen3_8b']
    ax.plot([p['per_user_tok_s'] for p in a], [p['aggregate_tok_s'] for p in a], marker='^', color='black', lw=2,
            label='A100 80GB Qwen3-8B (MEASURED)')
    for p in a:
        ax.annotate(f"{p['users']}u", (p['per_user_tok_s'], p['aggregate_tok_s']), textcoords='offset points', xytext=(5, -10), fontsize=7)
    r = cv['deepseek_reference'][0]
    ax.plot([r['per_user_tok_s']], [r['aggregate_tok_s']], marker='x', color='grey', ms=8, ls='none',
            label='DeepSeek ref: published 8x H100, 1 user')
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel('per-user decode rate (tok/s)  -> lower latency')
    ax.set_ylabel('aggregate decode rate (tok/s)')
    ax.set_title(f'MU.CURVE latency-throughput vs A100 80GB  -  measured records {STATUS_ASOF} (PARTIAL)', fontsize=10)
    ax.grid(True, which='both', alpha=0.25)
    ax.legend(fontsize=7, loc='upper left')
    fig.tight_layout()
    fig.savefig(path)


def md(st, cv):
    L = [f'# Token-pass tracker (TOKEN-LEAD2, {STATUS_ASOF})', '',
         'Owner gate: per-layer RTL sims on the CURRENT RELEASE dies + static schedule + inter-die traffic, real cycles, '
         '1-user AND multi-user, every design. Grades are against the RELEASE dies: REL = measured on the release die '
         'build; DIAG = measured on an older/diagnostic die or old vehicle (does not count); PRICE = analytic/calendar '
         'only; MISS = bench/vehicle missing. Generated by tools/token_pass_status.py from the latest measured records '
         '(RECORDS: measured_s81/qwen/hbm) + the RELEASE_TREE TOKEN lines. PARTIAL = release-die RTL evidence composed, '
         'no full token measured.', '',
         '## Summary', '',
         '| design | users | verdict | composed tok/s (grade) | REL | DIAG | PRICE | MISS | release die |',
         '|---|---|---|---|---|---|---|---|---|']
    for k, s in st['cells'].items():
        L.append(f"| {s['design']} | {s['users']} | **{s['verdict']}** | {s['rate']} | {s['tally']['REL']} | {s['tally']['DIAG']} | "
                 f"{s['tally']['PRICE']} | {s['tally']['MISS']} | {RELEASE_DIES[s['design']]} |")
    L += ['', 'No design has a full token measured on its release die. Source of each composed rate:', '']
    L += [f"- {d}: {r['src']} (was {r['prev']})" for d, r in RECORDS.items()]
    L += ['', '## Flags for the coordinator / owner', ''] + [f'- {f}' for f in FLAGS] + ['']
    for k, s in st['cells'].items():
        L += [f"## {s['design']} - {s['users']}", '', '| element | grade | evidence / build | owner | tree |', '|---|---|---|---|---|']
        L += [f"| {r['element']} | {r['grade']} | {r['evidence']} | {r['owner']} | {r['tree']} |" for r in s['elements']]
        L.append('')
    L += ['## MU.CURVE (PARTIAL)', '', f'Plot: results/token_pass/mu_curve_{TAG}.png; data mu_curve_{TAG}.json.', '',
          '| design | mode | users | per-user tok/s | aggregate tok/s | per-user vs baseline | grade |', '|---|---|---|---|---|---|---|']
    for p in cv['points']:
        L.append(f"| {p['design']} | {p['mode']} | {p['users']} | {p['per_user_tok_s']:,} | {p['aggregate_tok_s']:,} | "
                 f"{p['per_user_vs_baseline_x']}x | {p['grade']} |")
    for p in cv['a100_qwen3_8b']:
        L.append(f"| A100 80GB Qwen3-8B | AR | {p['users']} | {p['per_user_tok_s']} | {p['aggregate_tok_s']:,} | 1.0x | {p['grade']} |")
    L.append(f"| DeepSeek reference | AR | 1 | 33 | 33 | 1.0x | {DS_REF[0]['grade']} |")
    L += ['', 'Baselines: Qwen designs vs A100 114.8 tok/s (1 user); DeepSeek designs vs the published 8x H100 33 tok/s '
          '(no A100 DeepSeek number exists). Multi-user A100: 1,681 tok/s aggregate at 102 users (16.5 per user).', '']
    return '\n'.join(L) + '\n'


def build():
    ix = load_comp()
    cells = {}
    for (d, u), rows in ELEMENTS.items():
        r = RECORDS[d]
        if u == '1u':
            rate = f"{r['ar']:,} AR ({r['ar_pct']}% {r.get('pct_label', 'measured')})"
            if d == 'ds_rom':
                rate += f"; MTP {r['mtp']:,} ({r['mtp_pct']}%)"
        elif d == 'ds_rom':
            rate = (f"{r['mu_ar'][0]}u AR {r['mu_ar'][2]:,} agg ({r['mu_ar'][1]:,}/user) / "
                    f"{r['mu_mtp'][0]}u MTP {r['mu_mtp'][2]:,} agg ({r['mu_mtp'][1]:,}/user)")
        elif d == 'qwen_rom':
            rate = f"{r['mu'][0]}u {r['mu'][2]:,} agg (OVL link schedule, DIAG)"
        else:
            rate = '-'
        cells[f'{d}.{u}'] = dict(design=d, users='1-user' if u == '1u' else 'multi-user', verdict=verdict(d, u, rows), rate=rate,
                                 tally=tally(rows), elements=rows, release_die=RELEASE_DIES[d])
    st = dict(schema='opentallas.token_pass.status.v1', asof=STATUS_ASOF, records=RECORDS, flags=FLAGS,
              compose_index='results/arch/token_path_1018/index.json', compose_generated_from=ix['generated_from'], cells=cells)
    return st, curve(ix)


def page(pd, st, cv):
    ix = json.loads((pd / 'index.json').read_text())
    for e in ix['designs']:
        d = e['design']
        blk = dict(asof=STATUS_ASOF, release_die=RELEASE_DIES.get(d, ''), record=f'results/token_pass/status_{TAG}.md',
                   cells=[dict(users=c['users'], verdict=c['verdict'], rate=c['rate'], tally=c['tally'])
                          for c in st['cells'].values() if c['design'] == d],
                   curve=[p for p in cv['points'] if p['design'] == d],
                   baseline=(cv['a100_qwen3_8b'] if 'qwen' in d else cv['deepseek_reference']))
        files = [e['file']] + ([e['mtp']['file']] if e.get('mtp', {}).get('file') else [])
        for f in files:
            p = pd / f
            if not p.exists():
                continue
            doc = json.loads(p.read_text())
            doc['token_pass_1019'] = blk
            p.write_text(json.dumps(doc, separators=(',', ':')) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--page-data', nargs='*', default=[])
    a = ap.parse_args()
    st, cv = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'status_{TAG}.json').write_text(json.dumps(st, indent=1) + '\n')
    (OUT / f'mu_curve_{TAG}.json').write_text(json.dumps(cv, indent=1) + '\n')
    (OUT / f'status_{TAG}.md').write_text(md(st, cv))
    plot(cv, OUT / f'mu_curve_{TAG}.png')
    for pd in a.page_data:
        page(Path(pd).expanduser(), st, cv)
    for c in st['cells'].values():
        print(f"{c['design']:13s} {c['users']:10s} {c['verdict']:15s} {c['tally']}  {c['rate']}")


if __name__ == '__main__':
    main()
