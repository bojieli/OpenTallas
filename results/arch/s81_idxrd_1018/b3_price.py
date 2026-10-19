#!/usr/bin/env python3
"""S81-IDXRD/B3 (10-18): analytic price of the S81 "B3" 6-query index scorer (RELEASE_TREE MU.BAL.SX.4), no RTL.

B3 = score all 6 MTP verify positions per index-key read.  Basis = option D k=3 (results/arch/s81_scand_1018:
keys of a full-scan layer sharded over the 1-stack HBM of 3 dies, partial top-k merged on the TP all-gather path;
measured DS ROM AR 1,224.1 / MTP 3,711.7).  The p4l reader under construction (lane S81-IDXRD, branch
claude/s81-idxrd-1018, rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv, not yet on main): 16 regional readers a die, each
1 x ot_hdc_v41x_idx_engine NK 1 (IH 32, NB 4); landing = 2 x ot_sram_1r1w_256x256 a region (one per PC, one 256-b read a
cycle each; a key's two code sectors sit on ONE PC -> 1 key / 2 cycles a region = 8 keys/cycle/die); scores leave on ONE
276-b BK V rung (2 beats a 16-score word = 8 scores/cycle) into dsdv_bk_sel.  One HBM3E stack delivers 11.35 keys/cycle
(measured, reader_1stack.json 87,382 keys / 7,700 cycles).

Composition: the SCAND machinery (tools/throughput/accepted_cost.solve on the 10-09 DS ROM DAG + the MTP wavefront rule,
added to the 10-18 composition basis T0), with per-layer reader-cycle overrides.  The B3 extension of the wave rule:
a stage's 6 positions share ONE scan, so its per-position wave occupancy is (stage cycles - shared scan cycles)
(the S81-BALANCE B3 rule "the 6 positions join at the scan stage", compute.py group_occ hbm_mtp_step).
Run from anywhere; writes b3_price.json next to this file.
"""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('accepted_cost', ROOT / 'tools/throughput/accepted_cost.py')
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)


def jl(p):
    return json.loads((ROOT / p).read_text())


F = 1.2e9
K = 3                                   # option D stages
LEG, FINAL = 729.0, 178.0               # scand.py (measured leg, modelled final select a stage)
XD = 2 * math.ceil((K - 1) / 2) * LEG + FINAL * (K - 1)       # 1,814 legs + 12 x 512 merge
FULL = {2: ('L2', 'csa2_full_L2_clk833'), 8: ('L2', 'csa2_full_L2_clk833'), 14: ('L2', 'csa2_full_L2_clk833'),
        20: ('L20', 'csa1_full_L20_clk833')}
REINDEX = (24, 28, 32, 36)
NQ = 6                                  # MTP verify positions
REGIONS = 16
T0_RD = 600                             # reader start-up (brief: ~T0 600 cycles)
RUNG_SCORES = 8                         # 276-b BK V rung: 2 beats a 16-score word
Q_WORDS = 64                            # IDX job payload words a query (dsdv_idx_rg.sv header) on the 513-b q chain
HBM_KPC = 87382 / 7700                  # measured keys/cycle/die (1 stack), reader_1stack.json

meas = jl('results/arch/s81_scand_1018/reader_1stack.json')
assert meas['status'] == 'pass'
r1 = {}
for r in meas['runs']:
    r1[r['die_keys']] = max(r1.get(r['die_keys'], 0), r['cycles'])
reader4 = {r['name']: r['cycles'] for r in jl('results/rtl/dsrom_1m_measured_20261004/reader.json')['runs']}
REIDX_D = jl('results/arch/s81_scanchk_1018/scan_stacks.json')['per_stack_count']['1']['idx_score_delta_cycles']['L24']
NKEYS = {lay: math.ceil(meas['rank_keys'][lay] / K) for lay in ('L20', 'L2')}     # 87,382 / 43,691 a die

ar_doc = jl('results/arch/token_path_20261009/ds_rom.json')
mtp_doc = jl('results/arch/token_path_20261009/ds_rom_mtp.json')
tau = mtp_doc['totals']['tau']
comp = jl('results/arch/token_path_1018/ds_rom.json')['workloads']
T0 = {wl: comp[wl]['T_token_cycles'] - sum(t['total'] for t in comp[wl]['terms']
                                            if 'scan_stacks_p4l' in t['slot'] or 'scan_d' in t['slot'])
      for wl in ('ar', 'mtp')}


def solve(doc, reader, shared=None):
    """reader: {layer: reader cycles on the token path}; shared: {layer: scan cycles shared by the 6 positions}."""
    shared = shared or {}
    dl = {L: reader[L] - reader4[n] + XD for L, (_, n) in FULL.items()}
    dl.update({L: REIDX_D for L in REINDEX})
    nodes, edges = doc['nodes'], doc['edges']
    byid = {n['id']: n for n in nodes}
    delta, sh = {}, {}
    for n in nodes:
        if n.get('op') == 'attn.idx.score' and n.get('layer') in dl:
            delta[n['id']] = dl[n['layer']]
            sh[n['id']] = shared.get(n['layer'], 0.0)
    base, _ = ac.solve(nodes, edges)
    wave = [n['id'] for n in nodes if n.get('op') == 'wave.busy']
    wadd, worst = 0.0, None
    if wave:
        stages = [g for g in doc.get('groups', []) if g.get('kind') in ('stage', 'layer', 'embed')]
        cyc = {g['id']: g['cycles'] + sum(delta[k] - sh[k] for k in delta if byid[k].get('group') == g['id'])
               for g in stages}
        worst0 = max(g['cycles'] for g in stages)
        worst = max(cyc, key=cyc.get)
        wadd = cyc[worst] - worst0
        delta = dict(delta)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wadd
    new, _ = ac.solve(nodes, edges, delta)
    return dict(added=round(new - base, 1), wave_per_position=round(wadd, 1), wave_stage=worst)


def compose(reader_ar, reader_mtp, shared=None):
    a, m = solve(ar_doc, reader_ar), solve(mtp_doc, reader_mtp, shared)
    Ta, Tm = T0['ar'] + a['added'], T0['mtp'] + m['added']
    return dict(ar_tok_s=round(F / Ta, 1), mtp_tok_s=round(F * tau / Tm, 1), T_ar=round(Ta, 1), T_mtp=round(Tm, 1),
                mtp_wave_per_position=m['wave_per_position'], mtp_wave_stage=m['wave_stage'])


def per_layer(f):
    return {L: f(lay) for L, (lay, _) in FULL.items()}


meas_rd = per_layer(lambda lay: r1[NKEYS[lay]])                                      # 7,700 / 3,724
rung_rd = per_layer(lambda lay: math.ceil(NKEYS[lay] / RUNG_SCORES) + T0_RD)         # N/8 + 600
qx = (NQ - 1) * Q_WORDS                                                              # 5 more query frames
b3_hbm = {L: v + qx for L, v in meas_rd.items()}
b3_6r = {L: v + qx for L, v in rung_rd.items()}
b3_1r = per_layer(lambda lay: math.ceil(NQ * NKEYS[lay] / RUNG_SCORES) + T0_RD + qx)

S = {
    'D_measured_reader': dict(
        what='option D k=3 as recorded (measured W11 reader, HBM-bound 11.35 keys/cycle); scand.json by_k.3 check',
        **compose(meas_rd, meas_rd)),
    'D_rung_bound_reader': dict(
        what='option D k=3 with the p4l reader now built (1 key / 2 cycles a region, one 276-b rung): scan N/8 + 600',
        reader_cycles={f'L{L}': v for L, v in rung_rd.items()}, **compose(rung_rd, rung_rd)),
    'B3_hbm_rate': dict(
        what='B3 at the HBM rate: 544-b landing reads (1 key/cycle a region), 6 engines a region, egress >= 68 '
             'scores/cycle (12 rungs / 12 select quarters); scan shared by 6 positions (+320 q-chain cycles)',
        reader_cycles={f'L{L}': v for L, v in b3_hbm.items()}, **compose(meas_rd, b3_hbm, b3_hbm)),
    'B3_six_rungs': dict(
        what='B3 on today\'s landing (8 keys/cycle/die), 6 engines a region, 6 rungs -> 6 select quarters; '
             'scan N/8 + 600 shared by 6 positions',
        reader_cycles={f'L{L}': v for L, v in b3_6r.items()}, **compose(rung_rd, b3_6r, b3_6r)),
    'B3_single_rung': dict(
        what='B3 on today\'s single rung: 6 queries x N scores through 8 scores/cycle -> 6N/8 + 600 shared',
        reader_cycles={f'L{L}': v for L, v in b3_1r.items()}, **compose(rung_rd, b3_1r, b3_1r)),
}
ref = jl('results/arch/s81_scand_1018/scand.json')['by_k']['3']['composition_1018']
assert abs(S['D_measured_reader']['ar_tok_s'] - ref['ar']['tok_s']) < 0.15, (S['D_measured_reader'], ref)
assert abs(S['D_measured_reader']['mtp_tok_s'] - ref['mtp']['tok_s']) < 0.15, (S['D_measured_reader'], ref)
for k, v in S.items():
    for base, tag in (('D_measured_reader', 'vs_D'), ('D_rung_bound_reader', 'vs_D_rung')):
        b = S[base]
        v[tag] = dict(ar_pct=round(100 * (v['ar_tok_s'] / b['ar_tok_s'] - 1), 2),
                      mtp_pct=round(100 * (v['mtp_tok_s'] / b['mtp_tok_s'] - 1), 2))

# ------------------------------------------------------------------ requirements a die
QBITS = 32 * (512 + 32 + 16)                            # one query: 32 heads x (codes + scales + BF16 weight)
req = dict(
    keys_per_die=NKEYS, hbm_keys_per_cycle=round(HBM_KPC, 2),
    key_queries_per_cycle_die=round(NQ * HBM_KPC, 1), key_queries_per_cycle_region=round(NQ * HBM_KPC / REGIONS, 2),
    today_key_queries_per_cycle_die=REGIONS * 0.5,
    query_store_bits=dict(one_query=QBITS, b3_per_region=NQ * QBITS, b3_per_die=NQ * QBITS * REGIONS,
                          today_per_die=QBITS * REGIONS,
                          note='each NK 1 engine holds its query (hslice per head); 6 stores = 6 engines a region, or a '
                               'changed engine with 6 query banks'),
    engines=dict(unchanged_engine_per_region=NQ, per_die=NQ * REGIONS, added_per_die=(NQ - 1) * REGIONS,
                 mac_minimum_per_region=math.ceil(NQ * HBM_KPC / REGIONS),
                 note='an unchanged NK 1 engine scores one query at 1 key/cycle -> 6 a region (0.71 duty at HBM '
                      'rate, 0.5 on today\'s landing); 5 a region is the MAC floor but needs a query-switching engine'),
    landing=dict(today='2 x 256-b reads a key on one PC macro -> 1 key / 2 cycles a region (8 keys/cycle/die < 11.35)',
                 b3_hbm_rate='1 key/cycle a region needs a 544-b read: split each PC landing into 2 macros (code '
                             'sectors in parallel) -> +2 ot_sram_1r1w_256x256 a region',
                 required_keys_per_cycle_region=round(HBM_KPC / REGIONS, 3)),
    egress=dict(scores_per_cycle_needed=round(NQ * HBM_KPC, 1), rung_scores_per_cycle=RUNG_SCORES,
                rungs_at_hbm_rate=NQ * math.ceil(HBM_KPC / RUNG_SCORES), rungs_at_8_keys=NQ,
                select_quarters_needed=dict(hbm_rate=NQ * math.ceil(HBM_KPC / RUNG_SCORES), eight_keys=NQ),
                bk_sel_quarters_today=4,
                single_rung='6 x N scores through 8/cycle = 6N/8 cycles = the same as 6 separate N/8 scans: no gain',
                local_partial_topk='per-region top-512 for each query = 96 selectors a die (>= 96 x 0.121 mm2 = '
                                   '11.6 mm2 + merge) and still 16 x 512 candidates a query: rejected'),
    q_chain_extra_cycles=qx)

# ------------------------------------------------------------------ area (sources in SRC)
HSLICE_UM2 = 17915.9      # closed ot_hdc_v41x_idx_hslice (one head x one key) die area 172.8 x 103.68 um
HSLICE_STD_UM2 = 10586.2  # same route, std-cell instance area
SRAM_UM2 = 172.824 * 41.064
BKSEL_UM2 = 673.92 * 1192.32
SELTQ2_UM2 = 121306.0
DIE_MM2 = 799.2
DIES = 520
eng_mm2 = 32 * HSLICE_UM2 / 1e6
eng_std_mm2 = 32 * HSLICE_STD_UM2 / 1e6
q_mm2 = BKSEL_UM2 / 4 / 1e6
add_eng = (NQ - 1) * REGIONS


def area(engines, macros, quarters):
    mm2 = engines * eng_mm2 + macros * SRAM_UM2 / 1e6 + quarters * q_mm2
    return dict(engines_added=engines, sram_macros_added=macros, select_quarters_added=quarters,
                engines_mm2=round(engines * eng_mm2, 2), engines_std_cell_mm2=round(engines * eng_std_mm2, 2),
                landing_mm2=round(macros * SRAM_UM2 / 1e6, 3), select_mm2=round(quarters * q_mm2, 2),
                per_die_mm2=round(mm2, 2), per_die_pct=round(100 * mm2 / DIE_MM2, 2),
                x520_mm2=round(mm2 * DIES), x96_scan_dies_mm2=round(mm2 * 96))


AREA = dict(
    unit=dict(engine_nk1_mm2=round(eng_mm2, 3), engine_nk1_std_cell_mm2=round(eng_std_mm2, 3),
              sram_256x256_mm2=round(SRAM_UM2 / 1e6, 5), select_quarter_mm2=round(q_mm2, 3),
              select_quarter_lower_mm2=round(SELTQ2_UM2 / 1e6, 3), die_mm2=DIE_MM2, dies=DIES),
    B3_hbm_rate=area(add_eng, 2 * REGIONS, NQ * math.ceil(HBM_KPC / RUNG_SCORES) - 4),
    B3_six_rungs=area(add_eng, 0, NQ - 4),
    note='engines dominate: +80 NK 1 engines a die (6 a region).  Wires not priced: 6-12 x 276-b score chains through '
         'the 16 regions and into bk_sel; bk_sel multi-segment control (today single-segment) is RTL work.  '
         'x96 = only the dies of the duplicated full-scan groups (a die variant; owner prefers few die types).')
SRC = dict(
    composition='results/arch/s81_scand_1018/scand.py (machinery), reader_1stack.json, scand.json by_k.3',
    dag='results/arch/token_path_20261009/ds_rom.json, ds_rom_mtp.json; tools/throughput/accepted_cost.py',
    basis='results/arch/token_path_1018/ds_rom.json',
    reader_rtl='rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv (branch claude/s81-idxrd-1018, lane S81-IDXRD; read only)',
    engine_rtl='rtl/hdc/v41x/ot_hdc_v41x_idx.sv ot_hdc_v41x_idx_engine (NK keys/cycle, IH/8 chunks of hslices)',
    hslice_area='results/closure_loop/idx_hslice_rt_a-i1012-63dc36f91/verdict.json (CLOSED); metadata '
                '/home/ubuntu/closed_archive/ot_hdc_v41x_idx_hslice/idx_hslice_rt_a-i1012-63dc36f91 '
                'finish__design__die__area 17,915.9 um2, instance stdcell 10,586.2 um2',
    sram='physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.lef SIZE '
         '172.824 x 41.064',
    bk_sel='rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv header (673.92 x 1,192.32 cluster, 4 quarters; '
           'results/rtl/s81_dv_1016/bk_units_bk2/vcut_plan.json)',
    selt_q2='results/closure_loop/s81b-selt_q2-frprildb-4b0140c9a-tc-rd/verdict.json (CLOSED); closed_archive '
            'metadata finish__design__die__area 121,306 um2',
    die='results/arch/s81_balance_1018/compute.py (claude/s81-balance-1018 61f744110) S81 die_mm2 799.2; MU config '
        '520 dies (lanes/MU-S81.md)',
    balance_b3='summary.json same commit: B2 3,724.3 -> B3 3,829.1 MTP (+2.81 %), T_mtp -36,670.6 cycles')

b3 = S['B3_hbm_rate']
REC = dict(
    adopt=False,
    rule='AGENTS.md: adopt only if >= 1 % of per-user rate; owner 10-16 "only significant gains"; accepted-cost '
         'ledger <= 5 %/unit',
    reason=(f"B3 at the HBM rate gains MTP +{b3['vs_D']['mtp_pct']} % single-user (AR 0) for +"
            f"{AREA['B3_hbm_rate']['per_die_mm2']} mm2 a die (+{AREA['B3_hbm_rate']['per_die_pct']} % of 799 mm2, "
            f"{AREA['B3_hbm_rate']['x520_mm2']:,} mm2 over 520 dies), plus 12 score rungs and multi-segment bk_sel: "
            f"over 1 % but not significant against ~6 % silicon and a 6x scorer the die does not have (vs the rung-bound "
            f"reader B3 on 6 rungs is +{S['B3_six_rungs']['vs_D_rung']['mtp_pct']} % for {AREA['B3_six_rungs']['per_die_mm2']} mm2).  B3 on today's "
            f"single rung loses (6N/8 + 320: MTP {S['B3_single_rung']['mtp_tok_s']}).  The larger, cheaper item is the "
            f"1-query reader itself: the rung-bound p4l reader loses AR {S['D_rung_bound_reader']['vs_D']['ar_pct']} % "
            f"/ MTP {S['D_rung_bound_reader']['vs_D']['mtp_pct']} % against the measured-reader D -> make it reach the "
            "stack rate first (544-b landing read = +32 SRAM 256x256 = 0.23 mm2 a die, engine already 1 key/cycle, "
            "2 rungs into 2 of bk_sel's 4 existing quarters + merge)."),
    upper_bound_caveat='the B3 wave rule assumes the 6 positions meet at each scan stage without re-serialising the '
                       'post-scan work at every one of the 4 scan stages; that re-bunching is not modelled, so the B3 '
                       'gain is an upper bound')

out = dict(schema='opentallas.s81_idxrd_b3_price.v1', lane='S81-IDXRD/B3', date='2026-10-18',
           grade='analytic (no RTL); reader terms measured-old-RTL (D) or rung-bound formula; area from closed tiles',
           basis_T_cycles={k: round(v, 1) for k, v in T0.items()}, tau=tau, legs_and_merge=XD,
           requirements=req, scenarios=S, area=AREA, recommendation=REC, sources=SRC)
(HERE / 'b3_price.json').write_text(json.dumps(out, indent=1) + '\n')
for k, v in S.items():
    print(f"{k:22s} AR {v['ar_tok_s']:8.1f} MTP {v['mtp_tok_s']:8.1f}  vs D {v['vs_D']}  wave/pos "
          f"{v['mtp_wave_per_position']} @ {v['mtp_wave_stage']}")
print({k: AREA[k]['per_die_mm2'] for k in ('B3_hbm_rate', 'B3_six_rungs')}, AREA['unit'])
