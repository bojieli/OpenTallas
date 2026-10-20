#!/usr/bin/env python3
"""TOKSIM-S81/IDX: write elements/IDX.json from collected evidence + this lane's two fleet runs (if collected)."""
import json, re, sys, os
from pathlib import Path

W = Path('/home/ubuntu/scratch/toksim-s81/idx_work')
OUT = Path('/home/ubuntu/scratch/toksim-s81/elements/IDX.json')
REL = 'origin/claude/s81-bind-mu4-1019@19bf4121e'
BR = 'claude/toksim-s81-idx-1019'

# ---- this lane's runs (collected into W/coll by the collector step) ----
bk = {}
for d in sorted((W / 'coll' / 'bk').glob('*')) if (W / 'coll' / 'bk').exists() else []:
    try:
        m = json.load(open(d / 'meta.json'))
        v = (d / 'verdict.txt').read_text()
    except Exception:
        continue
    vd = json.loads(v.split('BK_LAYER ', 1)[1].split(' ', 1)[1]) if 'BK_LAYER' in v else {}
    bk[d.name] = dict(pass_=vd.get('pass_'), mismatches=vd.get('mismatches'), t_first_in=m.get('t_first_in', 100),
                      t_last_in=m['t_last_in'], window=m['window'], shard=m.get('shard'),
                      span_edges=m['window'][1] - m.get('t_first_in', 100) + 1 if m.get('window') else None,
                      verdict=v.strip().splitlines()[0][:200])
svc = None
sl = W / 'coll' / 'svc' / 'run_base_s1.log'
if sl.exists():
    t = sl.read_text()
    g = lambda pat: (re.search(pat, t) or [None, None])[1]
    svc = {k: int(g(k + r'=(-?\d+)')) for k in ('rd_req_first', 'rd_req_last', 'rd_done_last_preGO', 'n_rd_preGO',
                                                 'n_rd_postGO', 'go', 'first_score', 'last_score', 'wr_first', 'wr_last')
           if g(k + r'=(-?\d+)') is not None}
    svc['verdict'] = g(r'verdict=([A-Z]+)')
    svc['line_hbmt'] = next((l for l in t.splitlines() if l.startswith('SVCLOW_HBMT')), None)
    svc['line_sched'] = next((l for l in t.splitlines() if l.startswith('SVCLOW_SCHED')), None)

ops = []
ID_RD = dict(module='dsdv_idx_rg (x16 regional reader/scorer, exact engine ot_hdc_v41x_idx_engine)',
             source='claude/s81-idxrd-1018@4cc3975d1 (= release-source blob)', blob='04944da27c4c8c146e0b2c4d74887050b9ef1b5e',
             in_release_source=False)
ops.append(dict(
    op='attn.idx.score', dag_cls='hbm', n_crit=8, old_cycles_per_instance=[873.0, 2951.0, 5937.0],
    cycles=8702, cycles_by_layer={'L2': 8702, 'L8': 8702, 'L14': 8702, 'L20_split_k6': 8702, 'L20_recordD_k3': 16895,
                                  'L24': 5829, 'L28': 5829, 'L32': 5829, 'L36': 5829},
    grade='measured-newest-element-RTL',
    definition='reader IDX job header at u_idxrg_0.qi -> last BK score beat at the chain tail (bk_sel V ingress), '
               'TB_IDXRD_STATS hdr_to_last; index layers = scan of the die shard, re-index layers L24..L36 = GATHER mode',
    shape='scan: N 43,691 keys a die (L2/L8/L14 k=3; L20 k=6 split = 43,689..43,691 -> same N), P=3 slot; L20 record D k=3 '
          'N 87,382; re-index: NB 2,048 candidate blocks = 16,384 keys, P=4; 16 regions + 16 real dsfd_ctrl_rg2 + refresh-aware '
          'per-PC HBM model (NPC 32), T0 400 / 1500',
    bit_exact=True,
    golden='independent certified ot_hdc_v41x_idx_engine (NK 16) on the bench key table (seeded synthetic keys, not the '
           'fixture keys); output decoded by the real dsdv_bk_vin, every header/BEAT word compared; nerr 0',
    rtl=ID_RD, bench='rtl/dsrom_sys/s81_dv/idx/test/{tb_dsdv_idx_rg.sv,idxrd_campaign.sh}@claude/s81-idxrd-1018 ef165a825',
    evidence='claude/s81-idxrd-1018:results/rtl/s81_idxrd_1018/sweep_1019.txt lines sw_l2_p3 (hdr_to_last 8702 PASS), '
             'sw_l20_p3 (16895 PASS), sw_g_p4 (5829 PASS); P=2 FAIL fail-closed (HBM-bound ~5.0-5.3 keys/cycle/die)',
    job='collected (ot-epyc4 10-19 ~03:00, Verilator 5.050); no rerun',
    edges_owed='none folded: the dsdv_idx_rg station adds +1 core cycle each way on the slice HBM path (binding.json), not on this op',
    note='Release die mu4c die.v does NOT instantiate dsdv_idx_rg (16 dsfd_ctrl_rg2, 14+2 svc_rs, 1 bk_sel, 1 bk_col; '
         'MU.BAL.SX.3 open): the file/blob is in the release source tree but unbound, hence newest-element grade. '
         'Newer reader ed2822e11 (claude/s81-l20sub-1019 04e86d694, SRAM-backed scale RF/item queue) is NOT bench-passing: '
         'its rd_base campaign BUILD_FAILED on ot-epyc8 17:22 (logs /home/ubuntu/scratch/s81-l20sub/logs/rd_base.log) -> L20 lane. '
         'FINDING: the p4l reader is HBM-bound: 8,702 cyc for 43,691 keys vs the old W11 1-stack reader 3,724 (SCAND reader_1stack, '
         'measured-old-RTL) that record D / scand.json charge, 2.34x; L20 k=3 16,895 vs 7,700. Re-index 5,829 vs old 873 (+783 SCANCHK). '
         'Excludes the q fan-out / tree legs (729 a rank-tree edge, S81-L20SPLIT) and the topk_merge transport (551).'))

bk_rel = 'main:results/rtl/s81_layer_tput_1018/compiler/bench_bk (RTL sha256 == release source for every RTL file)'
BKSEL = dict(module='dsdv_bk_sel (u_bk_sel; dsdv_bksel_q quarters, ot_s81ph_sel native selector)', source=REL,
             blob='dsdv_bk_sel 196333b150da, dsdv_bksel_c a65b9f8ee9, ot_s81ph_sel ea5838cc8a, dsdv_bk_v d97a90508c',
             in_release_source=True)
k3 = {k: v for k, v in bk.items() if not k.endswith('mut_corrupt')}
k3_ok = bool(k3) and all(v['pass_'] for v in k3.values())
mut = bk.get('L2_k3_d0_mut_corrupt')
cbl = {'L20_split_k6_root': 19278, 'L20_split_k6_mid': 14220, 'L20_split_k6_leaf': 9421, 'L20_recordD_k3_root': 22633,
       'L2_k1_unsharded(pre-shard)': 17103, 'L14_k1_unsharded(pre-shard)': 17103, 'L20_k1_unsharded(pre-shard)': 33487,
       'L24..L36_reindex': None}
for k, v in sorted(k3.items()):
    cbl[k] = v['span_edges']
root_k3 = [v['span_edges'] for k, v in k3.items() if k.endswith('_d0')]
ops.append(dict(
    op='attn.idx.topk_local', dag_cls='select', n_crit=8, old_cycles_per_instance=[230.0, 262.0, 2176.0, 2177.0, 2190.0, 4225.0],
    cycles=(max(root_k3) if root_k3 else None), cycles_by_layer=cbl,
    grade='measured-release-RTL' if k3_ok else 'pending',
    definition='first BK ingress beat at u_bk_sel vi_s (query/scan start) -> last IDX egress beat at vo_s (drain window end); '
               'ingress PACED BY THE MEASURED READER LAW (3N/16 + 511) and children merged on lane 3 (static rank tree, '
               'lower_bk job tree) -> this span CONTAINS the die\'s attn.idx.score scan; the selector itself adds the '
               'tail after the last ingress (281..286 edges measured, 640 budget)',
    shape='k=3 shard (L2/L8/L14): 43,691 keys a die, rank tree {0:[1,2]}, 512 selected, real layerbench fixtures; '
          'L20 k=6 split: 43,689..43,691 keys a die, tree {0:[1,3],1:[2],3:[4,5]}',
    bit_exact=(k3_ok or None),
    golden='fixture attn.idx.topk_local of the rank (lower_bk check: every IDX/DONE egress beat at its compiled vo_s edge, '
           'ties to lower position); shard closure: root selection == fixture topk_local',
    rtl=BKSEL,
    bench='tools/s81_dv/layer_prog/{lower_bk.py gen --job tree,bk/run_bk_layer.sh,bk/tb_bk_layer.sv}@' + BR + ' 394cef884 '
          '(from claude/s81-l20split-1019 19906ec2f) on the release RTL files',
    evidence=('ot-epyc9:/srv/opentallas-scratch/claude/toksim-s81-idx/stim/bk_stim/<case>/{run.log,verdict.txt,meta.json}; '
              'copies ' + str(W / 'coll/bk') + '; L20 split: claude/s81-l20split-1019:results/arch/s81_l20_1019/split/split.json '
              'bench.cases (Verilator 5.050, newer dsdv_bk_v 58696ce9f = per-lane live flop copies, cycle-identical)'),
    job='ot-run unit on ot-epyc9 (log /home/ubuntu/scratch/toksim-s81/IDX_bk_k3.otrun.log)',
    edges_owed='bk_sel rung relays (+1 a direction, cc9078d48) are inside the measured RTL; L20SPLIT tree legs 729 a child edge '
               'are in the root span; none else',
    note='DAG op changed meaning on p4l: old topk_local (2,176..4,225) was a selector-only price after the scores; on the p4l die '
         'the scan streams into bk_sel and the measured span covers scan + select (+ child merge). Do NOT add attn.idx.score '
         'on top for the same die; compose idx.score (reader, 8,702) + select tail, or use this span alone. '
         'Mutant corrupt on L2 k3 root: ' + (('FAIL as required (' + str(mut['mismatches']) + ' mismatches)') if mut and mut['pass_'] is False else 'not collected') +
         '. Re-index layers L24..L36 topk_local (230/262): no fixture / no bench -> old numbers remain (measured-old-RTL).'))

ops.append(dict(
    op='attn.idx.topk_final', dag_cls='select', n_crit=8, old_cycles_per_instance=[178.0],
    cycles=6698, cycles_by_layer={'L2': 6554, 'L8(=L2 shape)': 6554, 'L14': 6541, 'L20': 6698, 'newest_INDEXED13_L20': 1033},
    grade='measured-release-RTL',
    definition='first candidate ingress beat at u_bk_sel vi_s -> last IDX egress beat (span_edges); 4 x 512 TP4 local '
               'selections as REBASE + 2-beat sparse words on the 276-b rung',
    shape='production: 2,048 real candidates (4 x 512) from the layerbench fixtures, 512 selected, sorted output',
    bit_exact=True, golden='fixture attn.idx.topk_final (sorted), every egress beat at its compiled edge',
    rtl=BKSEL,
    bench='tools/s81_dv/layer_prog/bk/{run_bk_layer.sh,tb_bk_layer.sv} + lower_bk.py (main)',
    evidence=bk_rel + ' runs/{L2,L14,L20}_topk_final (PASS, mismatches 0, span 6554/6541/6698) + witness m_corrupt/m_early FAIL; '
             're-measured L20 6,698 in claude/s81-l20split-1019 split/bench/k1_final',
    job='collected, no rerun',
    edges_owed='none',
    note='Rung-ingress bound (5,826..5,983 ingress edges for the sparse format; selector tail 283). Newest bench-passing element '
         'RTL: OT_S81PH_SEL_INDEXED13 (codex/s81-topk-final-1019 dddad6bb9, ot_s81ph_sel 51dc31078, default OFF, compiler '
         '--bk-indexed13): 1,033 actual / 1,037 reserved, bit-exact 5 positive + 3 mutants FAIL (results/arch/s81_topk_final_1019/'
         'bench/indexed13) -- grade measured-newest-element-RTL, not in the release source; physical quarter view not qualified. '
         'FAN32 (d58faf9b0) / SUCC (07fb519c3) / FIFO_SRAM variants are 0-edge exact (same cycles).'))

ops.append(dict(
    op='attn.gather', dag_cls='select', n_crit=8, old_cycles_per_instance=[808.0, 811.0, 819.0],
    cycles=None, grade='measured-old-RTL',
    definition='old DAG: selected-index -> gathered KV rows (selector/collector job + crossings)',
    shape=None, bit_exact=None, golden=None,
    rtl=dict(module='dsdv_bk_col (u_bk_col) / svc_rs sparse row load', source=REL, blob='dsdv_bk_col bd6f6c3d02', in_release_source=True),
    bench=None, evidence='old DAG node (dsrom_1m_allmeasured patch); S81-TOPK-FINAL / LEAD2-S81-TOPK: "IDX consumer -> gather" GAP',
    job=None, edges_owed=None,
    note='No release-RTL vehicle: the release die has no compiled runtime IDX(bk_sel vo_s) -> sparse-gather consumer (explicit '
         'GAP in S81-TOPK-FINAL / LEAD2-S81-TOPK); old 808..819 kept. (dsdv_idx_rg GATHER mode is the re-index SCORE pass, '
         'charged under attn.idx.score L24..L36, not this op.)'))

wl = None
if svc and svc.get('verdict') == 'PASS' and svc.get('rd_done_last_preGO', -1) >= 0:
    wl = svc['rd_done_last_preGO'] - 116 + 1
ops.append(dict(
    op='attn.window_load', dag_cls='hbm', n_crit=32, old_cycles_per_instance=[169.9, 207.1, 265.9, 300.9],
    cycles=wl, grade=('measured-release-RTL' if wl else 'pending'),
    definition='WIN_LOAD frame at the entry q pins (compiled cycle 116, bench tb cycles) -> last window-row HBM read beat '
               'returned to the slices (last read completion before GO), all 16 slices; 127 window rows + own row',
    shape='L0 fixture, T 128 window, TP4 rank 0 heads 0..15, 16 real dsdv_svc_rs slices (DIE 0, ST 0 = die.v), elastic '
          'per-PC HBM model DQ 8, latency 40..55 + queue (seed 1)',
    bit_exact=(True if wl else None),
    golden='all 128 x 16 root scores + 16 x 128 SE rows bit-exact vs fixture attn.scores (the window rows are the score operands)',
    rtl=dict(module='dsdv_svc_rs x14 + dsdv_svc_rs_entry x2 (dsdv_svc_att, dsfd_svc_pc)', source=REL,
             blob='dsdv_svc_rs 2906d36c92, dsdv_svc_att 44a0ee844c', in_release_source=True),
    bench='tools/s81_dv/layer_prog/svc/tb_svc_lower.sv@' + BR + ' 394cef884 (main 3b3a2062c bench + observation-only SVCLOW_HBMT line)',
    evidence=('ot-epyc9:/srv/opentallas-scratch/claude/toksim-s81-idx/out_svc/run_base_s1.log: ' + (svc['line_hbmt'] or '') if svc else 'pending'),
    job='ot-run unit on ot-epyc9 (log /home/ubuntu/scratch/toksim-s81/IDX_svc_wl.otrun.log)',
    edges_owed='none',
    note='Same vehicle as main bench_svc (3b3a2062c, RTL sha256 == release). HBM latency is the bench model (elastic off-die '
         'boundary); n_crit 32 = the window layers; index layers load the same T 128 window. ' +
         (('raw: ' + json.dumps({k: svc[k] for k in svc if not k.startswith('line')})) if svc else '')))

sc = None
if svc and svc.get('verdict') == 'PASS':
    sc = svc['last_score'] - svc['go']
ops.append(dict(
    op='attn.scores', dag_cls='hbm', n_crit=40, old_cycles_per_instance=[49.9, 103.9],
    cycles=(sc if sc is not None else 161), grade='measured-release-RTL',
    definition='GO frame (scores start, window landed) -> last root score beat at the fold root (SVCLOW_SCHED last_score - go); '
               'first score beat at GO + 130, 32 root beats over 31 cycles',
    shape='L0 fixture, T 128, 16 heads (TP4 rank 0), 16 real dsdv_svc_rs slices',
    bit_exact=True, golden='fixture attn.scores bitwise (golden dots x attn_scale), 2,048 scores, order checked',
    rtl=dict(module='dsdv_svc_rs x16 (dsdv_svc_att score exchange dsdv_svc_sx)', source=REL,
             blob='dsdv_svc_rs 2906d36c92, dsdv_svc_att 44a0ee844c', in_release_source=True),
    bench='main:tools/s81_dv/layer_prog/svc/tb_svc_lower.sv@3b3a2062c (+ this lane rerun)',
    evidence='main:results/rtl/s81_layer_tput_1018/compiler/bench_svc/run_base_s1.log SVCLOW_SCHED go=1555 first_score=1685 '
             'last_score=1716 verdict=PASS (seeds 1/2), mutants slot/late FAIL',
    job='collected; rerun inside the window_load job',
    edges_owed='none',
    note='Old 49.9 was the attention-tile score pass from the first score; the 161 here includes the q.k pipeline fill on the '
         'slices from GO (130) + 31 beat cycles. The P path (bench_svc_p, 85340f61a on-die P) is NOT in the release svc_rs blob.'))

ops.append(dict(
    op='ffn.top6_order', dag_cls='select', n_crit=40, old_cycles_per_instance=[44.0],
    cycles=56, grade='measured-release-RTL',
    definition='last router SC beat at the gunit V stop pins -> ids CTL row out (router_ids_latency_edges.stop_pins); covers '
               'ffn.top6 + ffn.top6_order (bias add + ot_hdc_select_tree select+order in one pass, dsdv_gunit_l1)',
    shape='DeepSeek-V4.1 router: 384 experts (448 slots) scores + bias, K 6, 8 golden cases',
    bit_exact=True, golden='tools/hdc_golden_v41 Model.moe router ids/weights (random hidden, verbatim golden ops); select tree '
                           'blob (sha 70d4a572) exact on all 40 layers\' golden 1M router scores (10-04 select_tree.json)',
    rtl=dict(module='dsdv_gunit (L1 leaf: ot_dsrom_su_bias_select + ot_hdc_select_tree K6)', source=REL,
             blob='dsdv_gunit_l1 20a72b9901, dsdv_gunit fd4692ee01, ot_hdc_select_tree 13be105dc7', in_release_source=True),
    bench='rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh (release source)',
    evidence='main:results/rtl/s81_dv_units_1017/gunit3/bench_receipt.json router_ids_latency_edges {stop_pins 56, unit_pins 68} '
             'PASS + mutants 1,4..9 FAIL (gunit3 39fb77eac = last change to the release gunit files)',
    job='collected, no rerun', edges_owed='unit_pins - stop_pins = 12 rung feedthrough edges (compiler-known router_tree rung stages)',
    note='Budget top6 + top6_order 52.9 -> measured 56 (1.059x). Use 56 for the pair; ffn.top6 = 0 separately.'))
ops.append(dict(
    op='ffn.top6', dag_cls='select', n_crit=40, old_cycles_per_instance=[8.9],
    cycles=0, grade='measured-release-RTL', definition='merged into ffn.top6_order (one dsdv_gunit_l1 select pass)',
    shape='see ffn.top6_order', bit_exact=True, golden='see ffn.top6_order', rtl=ops[-1]['rtl'], bench=ops[-1]['bench'],
    evidence=ops[-1]['evidence'], job='collected', edges_owed='none',
    note='Op merged on p4l: the 56 of ffn.top6_order includes the old top6 8.9 (+3 SU crossing adders no longer exist on the DV gunit).'))

ops.append(dict(
    op='attn.idx.l20_split_chain (S81-L20SPLIT)', dag_cls='select', n_crit=1, old_cycles_per_instance=[13855.0],
    cycles=19391, grade='measured-newest-element-RTL',
    definition='L20 index chain: q at the home die -> root bk_sel last egress (rank tree k=6) + topk_merge window '
               '(compiled static plan, RTL bench of every bk_sel job shape)',
    shape='k=6 shards 43,689..43,691 keys, real L20 fixture', bit_exact=True,
    golden='root selection == fixture topk_local; every egress beat at its compiled edge (5/5 PASS, mutants corrupt/early FAIL)',
    rtl=dict(BKSEL, source='claude/s81-l20split-1019@19906ec2f', blob=BKSEL['blob'].replace('dsdv_bk_v d97a90508c', 'dsdv_bk_v 58696ce9f (newer: per-lane live flops, cycle-identical)'), in_release_source=False),
    bench='results/arch/s81_l20_1019/split/l20_split.py + tools/s81_dv/layer_prog/bk',
    evidence='claude/s81-l20split-1019:results/arch/s81_l20_1019/split/split.json single_user.chains.split_k6_compiled 19,391 '
             '(record D 13,855; priced split 18,309); bench.cases k6 root span 19,278; cut_3S replay 31,481 PASS (partial)',
    job='collected', edges_owed='L20SPLIT tree legs 729 a child edge (in chain); TX re-encode slot grid TX_SM 1600 (S81-L20DIE, '
                                'not yet in this measurement)',
    note='Reader pace in the chain = the measured dsdv_idx_rg law; the reader itself is not bound on the release die. '
         'Option D 1-stack scan (results/arch/s81_scand_1018/scand.json, W11 reader, measured-old-RTL): 87,382 keys 7,700 / '
         '43,691 3,724 -- superseded by the p4l reader 16,895 / 8,702 (see attn.idx.score).'))

rec = dict(cls='IDX', written='2026-10-19 ' + os.popen('TZ=America/Los_Angeles date +%H:%M').read().strip() + ' PT',
           agent_branch=BR, release_source=REL,
           release_die_note='mu4c die.v binds dsdv_bk_sel x1, dsdv_bk_col x1, dsdv_svc_rs x14 + entry x2, dsfd_ctrl_rg2 x16, '
                            'dsdv_gunit x1; NO dsdv_idx_rg (index reader) -> MU.BAL.SX.3',
           ops=ops)
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(rec, open(OUT, 'w'), indent=1)
print('wrote', OUT, 'bk cases', sorted(bk), 'svc', bool(svc))
