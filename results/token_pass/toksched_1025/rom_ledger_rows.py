#!/usr/bin/env python3
"""TOK-SCHED 10-25: add (propose + accept, COORD-approved) the three ROM-design cycle-change rows to the accepted-cost
ledger from this directory's committed price records.  Idempotent: re-running replaces the proposed rows (an already
accepted row is left alone).   rom_ledger_rows.py [--ledger PATH]"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from throughput import accepted_cost as ac  # noqa: E402

HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT)
ap = argparse.ArgumentParser()
ap.add_argument('--ledger', default=str(ac.LEDGER))
a = ap.parse_args()
led = ac.load_ledger(a.ledger)
DATE = '2026-10-25'


def wl(model, b, n, tb, tn, **kw):
    return dict(model=model, base_cycles=b, cycles=n, added_cycles=round(n - b, 1), tok_s_before=tb, tok_s_after=tn,
                e2e_loss_pct=round(ac.loss_pct(b, n), 3), **kw)


rows = []
# (a) S81 vsw LR=1
v = json.loads((ROOT / 'results/token_pass/tokds_vsw_lr1_1309/vsw_price_delta.json').read_text())['workloads']
rows.append(dict(
    design='s81', unit='S81.VSW_LR1 (ot_s81sl_vsw LR=1 default, main 8d6af30b15: +1 output edge a SW/SWR command in every '
                       'S81 slice; lower_vs SW16 191->192, SWR 195->196; L14 span 28081.9->28082.9)',
    measured=40.0, per_workload=dict(
        ar=wl('compose_tok_ds + dv_mu_calendar_phys REL241 single user on the 241-stage map (plan of record at main '
              '05f9f5c69, ADOPT178 base)', v['ar']['map_old_cycles'], v['ar']['map_new_cycles'], v['ar']['old_tok_s'],
              v['ar']['new_tok_s'], dag_added_cycles=v['ar']['dag_added_cycles']),
        mtp=wl('same, MTP causal six-position pipeline law of record, tau 4.159', v['mtp']['map_old_cycles'],
               v['mtp']['map_new_cycles'], v['mtp']['old_tok_s'], v['mtp']['new_tok_s'],
               dag_added_cycles=v['mtp']['dag_added_cycles'])),
    evidence=f'results/token_pass/tokds_vsw_lr1_1309/vsw_price_delta.json {REL}/vsw_recheck/compose_1u.json',
    note='Codex codex/l14-schedule-1309 841db2c43 (on main as c967be25c): lower_vs VS_DUR SW +VSW_LR_CYCLES, '
         'dv_layer_compile dependency edge on ffn.(shared_)swiglu, compose_tok_ds transform_current_profile. TOK-SCHED '
         '10-25 re-ran compose_tok_ds on main 05f9f5c69 (identical: AR 1,528,917.6 map / 1,387,278.6 DAG, MTP 1,815,279.6 '
         '/ 1,794,545.8, calendars PASS) and the L14 layer_schedule (28,081.9 -> 28,082.9). Cross-check on the ledger '
         'token-path DAG (accepted_cost compute --match ffn swiglu --node-delta 1): AR +40 (40 of 80 runs critical), '
         'MTP +48 (43 critical + 5 wave). Analytical composition, not a bound-RTL token run.',
    approval='COORD/TOK-SCHED 2026-10-25: owner-approved vsw LR=1 (owner 10-25 11:59)'))
# (b) QC MIF=1
m = json.loads((HERE / 'qc_mif/mif_summary_raw.json').read_text())
b0, b1, b2 = m['bound_current'], m['bound_su_plus1'], m['bound_su_plus2']
rows.append(dict(
    design='qwen_rom', unit='QC.SRAM_MIF1 (qfd_dv_s8x_vmr / _btab / _prog MIF=1 on sl_W5_su_c, main 32620f9399: vmr q, '
                            'bs_q, p_q one edge later; +2 serial edges a SU command)',
    measured=float(b2['cycles_per_token'] - b0['cycles_per_token']), per_workload=dict(
        ar=wl('toksim_compose (engine 94cd97b7a, compiler f0ef9ad67, bound s8exp_wf3 ages; Codex '
              'results/uarch/qwen_s8_crom_price_1025 recipe) bound_current with every SU-derived output/retire age +2',
              b0['cycles_per_token'], b2['cycles_per_token'], b0['tok_s'], b2['tok_s'],
              lower_bound_plus1=dict(cycles=b1['cycles_per_token'], tok_s=b1['tok_s'],
                                     e2e_loss_pct=round(ac.loss_pct(b0['cycles_per_token'], b1['cycles_per_token']), 3)),
              chained_layer=[b0['chained'], b2['chained']], l0_cold=[b0['l0_cold'], b2['l0_cold']])),
    evidence=f'{REL}/qc_mif/mif_summary_raw.json {REL}/qc_mif/bound_su_plus2.json',
    note='Charged +2 a SU command = Codex tools/uarch_model.py qwen_sram_if_mif_model (codex/qc-mif-1309 c9cdec9e2: '
         'program fetch start +1, memory/head reply +1; group/head/fetch exact gates PASS, mutants caught). Lower bound '
         '+1 (memory reply only): +433 cyc, 0.151 %. Linear: +12 cycles a chained layer and +13 cold per edge (Codex '
         'CROM +3 = 288,025 reproduced exactly as the +3 point). Base = bound_current 286,726 (4,186.9 tok/s), PREDICTED '
         'only; current QC token price HELD. Binding .MIF(1) is a pending QC plan/RTL delta; re-price with fresh MIF1 '
         'compiler ages.',
    approval='COORD/TOK-SCHED 2026-10-25: QC sl_W5_su_c MIF=1 approved (GEOM-REVIEW F6 structural fix)'))
# (c) KV v3.9r lane-cycle table + L663
k = json.loads((HERE / 'kv_v39r/kv_v39r_price.json').read_text())
p, ub = k['priced']['ar'], k['bracket_upper']['ar']
rows.append(dict(
    design='qwen_rom', unit='KV.PLAN_V39R_LANES (KV plan v3.9r claude/path-kv-rebase-1025 3832299dfb: 839 lanes vs main '
                            'lat_v39pd; d2d rx +2 / kvs_attn tx +4 a request, embedding chain +47 a token; L663 host FDI '
                            '34->42 (main) / 35 (v3.9r) = 0 token cycles)',
    measured=float(p['added_cycles']), per_workload=dict(
        ar=dict(model='lane-class model on the token-path DAG (kv_v39r_price.py): 36 attention requests x (d2d rx '
                      'bundle + kvs_attn tx bundle) + embedding (rx + px hop + worst PC chain + slot + row tx)',
                base_cycles=p['base_cycles'], cycles=p['cycles'], added_cycles=p['added_cycles'],
                tok_s_before=p['tok_s_before'], tok_s_after=p['tok_s_after'], e2e_loss_pct=p['e2e_loss_pct'],
                bracket_upper=ub)),
    evidence=f'{REL}/kv_v39r/kv_v39r_price.json {REL}/kv_v39r/lane_cycle_delta_vs_main.json',
    note=('Priced: per attention request d2d rx landed bundle sys_c->hub_C 56->58 (+2) + kvs_attn tx hub_C->sys_c '
          'L1427/L1428 51->55 (+4) = +6 x 36 = 216; embedding (once a token) serial upper bound +47 (rx 2 + px hop 2 + '
          'worst PC broadcast chain hub_Wo->pc_*_7..0 +31 + emb tx slot L344 +7 + row tx +5). L663 '
          'hub_Wi.o_host_fdi->io_W3 (host FDI, 1044 b): boot/admission/host IO, no host node on the token path -> 0. '
          'NOT priced: interior attention lanes (vport/slg +8, pv rows/pvw y_valid +16, ahub/astk +7, hroot/hsl +5, '
          f'acal +5 max) that the hardened equalisation budgets (PV_W, ECTLK RESPONSE_LAT) absorb only while inside the '
          f'budget; if every family were serial once a request: +{ub["added_cycles"]} cyc, {ub["e2e_loss_pct"]} % '
          '(bracket). No KV static calendar on main consumes per-lane plan cycles; the bound KV token vehicle (KV-TOK) '
          'is the measurement. On the QC bound composition base (286,726) the priced +263 is 0.092 %.'),
    approval='COORD/TOK-SCHED 2026-10-25: KV v3.9r rebase (PATH-KV-REBASE) + KV-OBST L663 34->42 approved'))

for r in rows:
    row = ac.make_row(r['design'], r['unit'], 0.0, r['measured'], r['per_workload'], r['evidence'], 'committed_bench',
                      note=r['note'], date=DATE)
    row['share_basis'] = 'modelled'
    old = ac.find(led, r['design'], r['unit'])
    if old and old['status'] == 'accepted':
        print('kept accepted', r['design'], r['unit'][:40])
        continue
    ac.propose(led, row)
    ac.accept(led, r['design'], r['unit'], root=ROOT, note=r['approval'])
    row['accepted_date'] = DATE
    print(r['design'], r['unit'][:50], row['e2e_loss_pct'], row['status'])
ac.save_ledger(led, a.ledger)
bad = ac.check(led, ROOT)
print('check:', bad or 'OK')
for d in ('s81', 'qwen_rom'):
    print(d, json.dumps(led['totals'][d]))
