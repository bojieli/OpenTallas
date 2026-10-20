#!/usr/bin/env python3
"""Token-pass tracker, MU curve and freeze checklist (lane TOKEN-REC, 2026-10-19).

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
STATUS_ASOF = '2026-10-19 18:30 PDT'

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
        E('L0 dense attention (die)', 'DIAG', 'S81 10-13 layer record (old die); p4l cut_0S L0 replay PASS partial', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.1'),
        E('L2 sparse attention + indexer (die)', 'DIAG', 'old 10-13 record; p4l index reader/helper transport missing', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.2'),
        E('L14 Engram layer (die)', 'DIAG', 'old 10-13 record; p4l row-read integration open', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.3'),
        E('L20 compressed layer (die)', 'REL', 'partial: L20 k=6 split bk_sel job shapes RTL bench (Verilator 5.050), split.json; full layer open', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.4'),
        E('LM head (die)', 'DIAG', 'old record; real fold/gain/G8-NX-XB producer missing on p4l', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.5'),
        E('MTP draft layer (die)', 'DIAG', 'old record; draft body after real head producer', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.6'),
        E('Layer bench cut from p4l GEN netlist', 'MISS', 'VPX slice bench base PASS; DV layer-programme compiler ED23 FAIL', 'LEAD2-S81/TOK2', 'TOK.DS.BENCH'),
        E('TP4 collectives + hops (array)', 'REL', 'xdie_s81_1019: 12,096 beats bit-exact by compiled deadline; G8R2 p4m die RTL + HF-3 lanes + KP4 PHY', 'LEAD2-S81/XDIE', 'TOK.DS.XDIE'),
        E('Off-chip PHY/switch legs', 'PRICE', 'modelled-PHY constants (17.5% of AR token cycles)', 'LEAD2-S81/XDIE', 'TOK.DS.XDIE'),
    ],
    ('ds_rom', 'mu'): [
        E('46-user AR / 10-user MTP calendar', 'PRICE', 'calendar_ar/mtp.json brute-force lemma PASS (modelled, 0 collisions)', 'LEAD2-S81/MU', 'MU.TOK'),
        E('Multi-user collectives (3 users)', 'REL', 'xdie_s81_1019 mu_real: 18,132 beats bit-exact, 3,840 MU tags, 0 faults', 'LEAD2-S81/XDIE', 'TOK.DS.XDIE.5'),
        E('Multi-user collectives on MU die ceaed19c4', 'MISS', 'xdie-s81-mu u/a/c/x jobs running', 'LEAD2-S81/XDIE', 'TOK.DS.XDIE.5'),
        E('Host plane N outstanding + MTP seed', 'REL', 'partial: SEQHOST_MU on die master; NS47 ph0-5 PASS, 6-10 live', 'LEAD2-S81/MU', 'MU.TOK.DS4'),
        E('Per-user layer benches', 'MISS', 'TOK.DS.LAYER.MU FAIL (QF child F1@1801); producers owed', 'LEAD2-S81/TOK2', 'TOK.DS.LAYER.MU'),
        E('lep tag + second landing + A/B select', 'MISS', 'v1 matrix live; v2 unrun', 'LEAD2-S81/LEPCAP', 'MU.TOK.DS3'),
    ],
    ('qwen_rom', '1u'): [
        E('L0 layer (compute die)', 'DIAG', 'qwen_layer_tput_1013 old vehicle (98.4% of token cycles); no dv2f19 layer run', 'LEAD2-QW/QW-TOK3', 'TOK.QW.LAYER.1'),
        E('Lc chained layer x35 (compute die)', 'DIAG', 'old 10-13; near+far matvec exact on real ROM (component only)', 'LEAD2-QW/QW-TOK3', 'TOK.QW.LAYER.2'),
        E('LM head', 'DIAG', 'old 10-13 head 3,048 cyc; waits last-layer TP8 gold', 'LEAD2-QW/QW-TOK3', 'TOK.QW.LAYER.3'),
        E('KV attention 1u (KV die)', 'MISS', 'r2 u1 sim running on repaired GEN9 vehicle (no cycles yet)', 'KV-TOK3', 'TOK.QW.KV'),
        E('Layer bench from GEN netlists + programme compiler', 'MISS', 'tt_ctlm deployment programme (G-C3) missing', 'LEAD2-QW/QW-TOK3', 'TOK.QW.BENCH'),
        E('36-layer TP4 golden', 'MISS', 'canonical gold P7712/8191 running on ep5', 'QW-TOK3', 'TOK.QW.BENCH.2'),
        E('Compute <-> KV D2D (1u)', 'DIAG', 'pair_r2 PASS on dv2f14bn (pre-release); dh2 1u PASS', 'QW-TOK3', 'TOK.QW.XDIE'),
        E('TP8 all-reduce windows', 'DIAG', 'old vehicle windows 2,184/layer; TP8 unit bench 862 evidence only', 'LEAD2-QW/QW-TOK3', 'TOK.QW.SCHED'),
    ],
    ('qwen_rom', 'mu'): [
        E('4-user calendar (op-level, chunked head)', 'PRICE', 'mu_qwen_1018: 14,054 agg modelled occupancy / 12,568 priced', 'LEAD2-QW/QW-TOK3', 'MU.TOK.QW'),
        E('2-user sequencer (layer granularity)', 'DIAG', 'mu_qwen_1018/tok pos2: 9,290.9 agg measured cmd stream; windows old+priced', 'LEAD2-QW/QW-TOK3', 'MU.TOK.QW'),
        E('NU4 stage cuts', 'REL', 'partial: NU4 stage cuts PASS on dv2f18dh2', 'LEAD2-QW/QW-TOK3', 'MU.TOK.QW'),
        E('4-user KV attention', 'MISS', 'KV-TOK3 u4 after u1; G7 WSQK QK-only', 'KV-TOK3', 'TOK.QW.KV'),
        E('4-user compute <-> KV pair', 'MISS', 'cal_mu SYSFACE MU PASS; 4u pair TB owed', 'QW-TOK3', 'TOK.QW.XDIE'),
        E('4-user golden (gold4)', 'MISS', 'armed trigger after canonical gold', 'QW-TOK3', 'MU.TOK.QW'),
    ],
    ('hbm_gen_ds', '1u'): [
        E('L0 / L1 / L2 / L3 MoE / L14 / L20.. layers (die)', 'PRICE', 'priced_layers (S2 compiler schedule) + LH-REPRICE3 measured unit latencies', 'LEAD2-HBM/L2H-TOK', 'TOK.HDS.VEH.1'),
        E('d4g record -> per-unit image compiler (R6)', 'MISS', 'R6 native run live on ep5 / earlier exit 1; classify terminal', 'LEAD2-HBM/L2H-TOK', 'TOK.HDS.VEH.2'),
        E('Quadrant (SW) cutter + bench', 'MISS', 'needs GEN2e4 die.v + R6 multi-group', 'LEAD2-HBM/L2H-TOK', 'TOK.HDS.VEH.4'),
        E('Cross-die collectives (AG/RS144/COLL)', 'DIAG', 'xdie_hbm_1018/1019 on GEN2 RTL; die must bind COLL ROWS256/AR_ITER', 'LEAD2-HBM/L2H-TOK', 'TOK.HDS.XDIE'),
        E('Unit latency re-price on GEN2e4 depths', 'PRICE', 'hbm_reprice_1019 (LH-REPRICE3); DS 1,406.1 accepted, -35% vs 1,905.4', 'LEAD2-HBM/L2H-BW', 'TOK.HDS.PRICE'),
    ],
    ('hbm_gen_ds', 'mu'): [
        E('HBM multi-user', 'PRICE', 'NOT IN THIS RELEASE (owner 10-18 23:45: next release); 2-request admission study only', 'HBM-NEXT', '-'),
    ],
    ('hbm_gen_qwen', '1u'): [
        E('L0 layer (d4g vehicle)', 'DIAG', 'L0p0 rec17/23 PASS, rec6/10 FAIL -> R6; on GEN2 vehicle', 'LEAD2-HBM/L2H-TOK', 'TOK.HQ.LAYER'),
        E('L1..L35 + head', 'PRICE', 'HGI-1 sim exact TP8 + price_per_layer (TP8 948.8 basis)', 'LEAD2-HBM/L2H-TOK', 'TOK.HQ'),
        E('TP8 all-reduce (cross-die)', 'DIAG', 'xdie_hbm_1019 Qwen AR on GEN2 RTL (2,926 cyc/layer)', 'LEAD2-HBM/L2H-TOK', 'TOK.HQ'),
        E('Qwen fixture / calibration on d4g', 'MISS', 'unqualified', 'LEAD2-HBM/L2H-TOK', 'TOK.HQ'),
    ],
    ('hbm_gen_qwen', 'mu'): [
        E('HBM multi-user', 'PRICE', 'NOT IN THIS RELEASE (owner 10-18 23:45: next release)', 'HBM-NEXT', '-'),
    ],
}

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


def verdict(d, u):
    if d.startswith('hbm') and u == 'mu':
        return 'NOT IN RELEASE'
    return 'NOT RUN'  # no design has a full token measured on its release die (10-19)


def curve(ix):
    des, mu = ix['designs'], ix.get('multi_user', {}).get('ds_rom', {})
    pts = []
    ar, mtp = des['ds_rom']['ar'], des['ds_rom']['mtp']
    pts += [dict(design='ds_rom', mode='AR', users=1, per_user_tok_s=ar['tok_s'], aggregate_tok_s=ar['tok_s'],
                 grade='PRICED (composed; %.1f%% current-RTL cycles)' % ar['pct_measured_current_rtl'])]
    if mu.get('ar', {}).get('available'):
        m = mu['ar']
        pts.append(dict(design='ds_rom', mode='AR', users=m['users'], per_user_tok_s=m['per_user_tok_s'],
                        aggregate_tok_s=m['aggregate_tok_s'], grade='PRICED (modelled calendar x composed per-user)'))
    pts.append(dict(design='ds_rom', mode='MTP', users=1, per_user_tok_s=mtp['tok_s'], aggregate_tok_s=mtp['tok_s'],
                    grade='PRICED (composed)'))
    if mu.get('mtp', {}).get('available'):
        m = mu['mtp']
        pts.append(dict(design='ds_rom', mode='MTP', users=m['users'], per_user_tok_s=m['per_user_tok_s'],
                        aggregate_tok_s=m['aggregate_tok_s'], grade='PRICED (modelled calendar)'))
    q = des['qwen_rom']['ar']
    pts.append(dict(design='qwen_rom', mode='AR', users=1, per_user_tok_s=q['tok_s'], aggregate_tok_s=q['tok_s'],
                    grade='PRICED (composed; old-RTL layer cycles)'))
    pts.append(dict(design='qwen_rom', mode='AR', users=2, per_user_tok_s=round(9290.9 / 2, 1), aggregate_tok_s=9290.9,
                    grade='DIAG (2-user sequencer cmd stream measured; windows old-RTL + priced)'))
    pts.append(dict(design='qwen_rom', mode='AR', users=4, per_user_tok_s=2321.0, aggregate_tok_s=14054.0,
                    per_user_note='4,769 / 4,642 / 2,321 / 2,321 (slowest shown)', grade='PRICED (modelled occupancy)'))
    for d in ('hbm_gen_ds', 'hbm_gen_qwen'):
        w = des[d]['ar']
        pts.append(dict(design=d, mode='AR', users=1, per_user_tok_s=w['tok_s'], aggregate_tok_s=w['tok_s'],
                        grade='PRICED (composed incl. LH-REPRICE3)'))
    for p in pts:
        base = 114.8 if p['design'] in ('qwen_rom', 'hbm_gen_qwen') else 33.0
        p['per_user_vs_baseline_x'] = round(p['per_user_tok_s'] / base, 1)
    return dict(schema='opentallas.token_pass.mu_curve.v1', asof=STATUS_ASOF, label='PRICED until TOK.FREEZE measures it',
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
                    ls='--', label=f'{lab[d]} {mode} (PRICED)')
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
    ax.set_title('MU.CURVE latency-throughput vs A100 80GB  -  PRICED until the token pass measures it', fontsize=10)
    ax.grid(True, which='both', alpha=0.25)
    ax.legend(fontsize=7, loc='upper left')
    fig.tight_layout()
    fig.savefig(path)


def md(st, cv):
    L = [f'# Token-pass tracker (TOKEN-REC, {STATUS_ASOF})', '',
         'Owner gate: per-layer RTL sims on the CURRENT RELEASE dies + static schedule + inter-die traffic, real cycles, '
         '1-user AND multi-user, every design. Grades are against the RELEASE dies: REL = measured on the release die '
         'build; DIAG = measured on an older/diagnostic die or old vehicle (does not count); PRICE = analytic/calendar '
         'only; MISS = bench/vehicle missing. Generated by tools/token_pass_status.py from results/arch/token_path_1018 '
         '(token_compose_xdie --check PASS) + the RELEASE_TREE TOKEN lines.', '',
         '## Summary', '',
         '| design | users | verdict | composed tok/s (grade) | REL | DIAG | PRICE | MISS | release die |',
         '|---|---|---|---|---|---|---|---|---|']
    for k, s in st['cells'].items():
        L.append(f"| {s['design']} | {s['users']} | **{s['verdict']}** | {s['rate']} | {s['tally']['REL']} | {s['tally']['DIAG']} | "
                 f"{s['tally']['PRICE']} | {s['tally']['MISS']} | {RELEASE_DIES[s['design']]} |")
    L += ['', 'No design has a single layer fully measured on its release die. Measured-on-release-die evidence today is '
          'collectives (S81 TP4 + 3-user MU tags) and partial slices (S81 L20 split jobs, SEQHOST_MU, Qwen NU4 cuts).', '']
    for k, s in st['cells'].items():
        L += [f"## {s['design']} - {s['users']}", '', '| element | grade | evidence / build | owner | tree |', '|---|---|---|---|---|']
        L += [f"| {r['element']} | {r['grade']} | {r['evidence']} | {r['owner']} | {r['tree']} |" for r in s['elements']]
        L.append('')
    L += ['## MU.CURVE (PRICED)', '', 'Plot: results/token_pass/mu_curve_1019.png; data mu_curve_1019.json.', '',
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
        w = ix['designs'][d]['ar']
        if u == '1u':
            rate = f"{w['tok_s']:,} AR ({w['pct_measured_current_rtl']}% cur-RTL per compose)"
            if d == 'ds_rom':
                rate += f"; MTP {ix['designs'][d]['mtp']['tok_s']:,}"
        elif d == 'ds_rom':
            m = ix['multi_user']['ds_rom']
            rate = f"{m['ar']['users']}u AR {m['ar']['aggregate_tok_s']:,} / {m['mtp']['users']}u MTP {m['mtp']['aggregate_tok_s']:,} (modelled)"
        elif d == 'qwen_rom':
            rate = '4u 14,054 agg (modelled)'
        else:
            rate = '-'
        cells[f'{d}.{u}'] = dict(design=d, users='1-user' if u == '1u' else 'multi-user', verdict=verdict(d, u), rate=rate,
                                 tally=tally(rows), elements=rows, release_die=RELEASE_DIES[d])
    st = dict(schema='opentallas.token_pass.status.v1', asof=STATUS_ASOF, compose_index='results/arch/token_path_1018/index.json',
              compose_generated_from=ix['generated_from'], cells=cells)
    return st, curve(ix)


def page(pd, st, cv):
    ix = json.loads((pd / 'index.json').read_text())
    for e in ix['designs']:
        d = e['design']
        blk = dict(asof=STATUS_ASOF, release_die=RELEASE_DIES.get(d, ''), record='results/token_pass/status_1019.md',
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
    (OUT / 'status_1019.json').write_text(json.dumps(st, indent=1) + '\n')
    (OUT / 'mu_curve_1019.json').write_text(json.dumps(cv, indent=1) + '\n')
    (OUT / 'status_1019.md').write_text(md(st, cv))
    plot(cv, OUT / 'mu_curve_1019.png')
    for pd in a.page_data:
        page(Path(pd).expanduser(), st, cv)
    for c in st['cells'].values():
        print(f"{c['design']:13s} {c['users']:10s} {c['verdict']:15s} {c['tally']}  {c['rate']}")


if __name__ == '__main__':
    main()
