#!/usr/bin/env python3
"""TOKSIM-S81C/GATH: build GATH.json (elements record) from the committed run logs in this directory.

  python3 -I mk_gath_json.py OUT.json BRANCH@COMMIT
gather: every gather/runs/run_<L>_v<ds>_g0.log with verdict PASS counts; per layer class the WORST owner view
(max gather_span) is the per-instance value. The 16-view sweep (gather16 job) adds its logs to gather/runs/.
"""
import json
import re
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
OUT, BR = Path(sys.argv[1]), sys.argv[2]
kv = lambda line: {k: v for k, v in re.findall(r'(\w+)=(\S+)', line or '')}


def grab(p, tag):
    return next((l for l in p.read_text().splitlines() if l.startswith(tag + ' ')), None)


# ---------------- gather
views = {}
for p in sorted((D / 'gather/runs').glob('run_L*_v??_g0.log')):
    m = re.match(r'run_(L\d+)_v(\d)(\d)_g0', p.stem)
    g, s = kv(grab(p, 'GATH_T')), kv(grab(p, 'SVCRS'))
    if not g or s.get('verdict') != 'PASS':
        continue
    views.setdefault(m.group(1), {})[f'{m.group(2)},{m.group(3)}'] = dict(
        span=int(g['gather_span']), own_reads=int(g['own_reads']), se_checked=int(s['se_checked']),
        sc_checked=int(s['sc_checked']) if 'sc_checked' in s else None, log=str(p.relative_to(D)))
worst = {L: max(v.values(), key=lambda x: x['span']) for L, v in views.items()}
iso = kv(grab(D / 'gather/runs/run_L2_v00_g800.log', 'GATH_T'))
mut = D / 'gather/runs/run_L2_v00_mut_g0.log'
mut_s = kv(grab(mut, 'SVCRS'))
n16 = {L: len(v) for L, v in views.items()}
by_old = {}
if 'L2' in worst:
    by_old['808.0'] = worst['L2']['span']
if 'L20' in worst:
    by_old['819.0'] = worst['L20']['span']
REL = dict(module='dsdv_svc_att (SEL_IDS scanner + owned-row fetch, x16 inside dsdv_svc_rs / dsdv_svc_rs_entry) + dsfd_svc_pc',
           source='origin/claude/s81-bind-mu4-1019@19bf4121e (protect-libs = TOKSIM-S81/SU base_d0s0, git archive 19bf4121e)',
           blob='dsdv_svc_rs 2906d36c92, dsdv_svc_att 44a0ee844c, dsfd_svc_pc 9f119b7f67', in_release_source=True)
gather = dict(
    op='attn.gather', dag_cls='select', n_crit=8, old_cycles_per_instance=[808.0, 811.0, 819.0], by_old=by_old,
    per_layer={L: w['span'] for L, w in worst.items()},
    grade='measured-release-RTL',
    definition='SEL_IDS frame header driven on both entries\' q pins (tb cycle t_sel, compiled static issue, +static_io=1) -> '
               'last beat of the last OWNED selected-row HBM read driven on the slice r_data (all 16 slices), +1 '
               '(GATH_T gather_span = own_done_last - t_sel + 1). On p4l-MU the die gathers only the rows its stacks own '
               '(id[5:4] die, id[7:6] stack; ~1/16 of 512); the other rows arrive on ROWS frames = attn.rows_allgather '
               '(separate DAG node). SEL_IDS is issued 1 cycle after WIN_LOAD (both DAG nodes start together); '
               'isolated (sel_gap 800, window load done) the span is identical (L2 view 0,0: %s) -> the span is the '
               'slice SEL scanner (one rank a cycle over 512 ranks) + the last fetch, not HBM queueing' % iso.get('gather_span'),
    shape='production: 512 real selected compressed positions (attn.idx.topk_final) of the L2 (ratio 2, 524,287 rows) / L20 '
          '(ratio 1, 1,048,575 rows + this position\'s new row) fixtures, T 640 (128 window + 512), 16 heads (TP4 rank 0), '
          'the stored 288-B FP4 rows from the fixture state (+ real +-1/+-256 neighbours in HBM), 16 real dsdv_svc_rs '
          'slices (DIE 0, ST 0); owner views (die,stack) by id relabelling: measured %s of 16 per layer; per instance = '
          'the worst view' % n16,
    views=views, bit_exact=True,
    golden='fixture (released DeepSeek-V4.1-Flash checkpoint dba1be0a + golden shard ctx1048576_seed20260930) asserted '
           'bitwise in toksim_gath_vectors.py: stored rows decode == ops attn.gather / attn.window_load / '
           'attn.rows_allgather, engine products x attn_scale == attn.scores, P.V == attn.pv (heads 0..15); RTL: every held '
           'row\'s 16-head scores (root beats + SE rows) and all 2,048 P.V words bit-exact (sc_errors=se_errors=pv_errors=0), '
           'which covers every gathered owned row',
    rtl=REL,
    bench='rtl/dsrom_sys/s81_dv/svc_rs/test/tb_toksim_gath.sv (observation copy of tb_dsdv_svc_rs ec50132: +sel_gap, GATH_T '
          'line; checks unchanged) + tools/s81_dv/layer_prog/toksim_gath_vectors.py @' + BR,
    evidence='results/rtl/toksim_s81c_gath_1019/gather/runs/*.log (GATH_T + SVCRS lines); cases/*.case.json',
    job='ot-run ot-epyc7 oth-ubuntu-408318-1792477093 (6 runs); 16-view sweep ot-epyc6 oth-ubuntu-447079-1792480437',
    edges_owed='+2 (L20 B1 svc splice: +1 station edge each way on svc_rs<->rg2 rq/rd when dsdv_idx_rg binds; not in mu4c); '
               'HBM boundary = bench model latency 40 (static) -- a real HBM latency adds (lat - 40) once (one fetch at the tail)',
    note='mutant witness: one E2M1 code of an owned selected row (id 252934, rank 258) flipped in the HBM image -> %s '
         '(sc_errors %s, se_errors %s, pv_errors %s; gather/runs/run_L2_v00_mut_g0.log). L24..L36 (re-index, old 811): no '
         'fixture -> old number kept (selection shape is the same 512 of 16,384 candidates; expect the same scanner-bound '
         'span).' % (mut_s.get('verdict'), mut_s.get('sc_errors'), mut_s.get('se_errors'), mut_s.get('pv_errors')))
# ---------------- window_load
wl = {}
for s in (1, 2):
    h = kv(grab(D / f'window_load/run_base_s{s}.log', 'SVCLOW_HBMT'))
    v = kv(grab(D / f'window_load/run_base_s{s}.log', 'SVCLOW'))
    assert v['verdict'] == 'PASS'
    wl[s] = int(h['rd_done_last_preGO']) - 116 + 1
lat = {}
for L in (100, 180):
    h = kv(grab(D / f'window_load/run_lat{L}_s1.log', 'SVCLOW_HBMT'))
    v = kv(grab(D / f'window_load/run_lat{L}_s1.log', 'SVCLOW'))
    lat[L] = dict(span=int(h['rd_done_last_preGO']) - 116 + 1, n_rd_preGO=int(h['n_rd_preGO']), verdict=v['verdict'],
                  first_fault_code=v.get('first_fault_code'))
w = max(wl.values())
g_wl = sorted({kv(grab(p, 'GATH_T'))['winload_span'] for p in (D / 'gather/runs').glob('run_L*_g*.log') if grab(p, 'GATH_T')})
window = dict(
    op='attn.window_load', dag_cls='hbm', n_crit=32, old_cycles_per_instance=[169.9, 207.1, 265.9, 300.9],
    by_old={'300.9': w, '169.9': w, '265.9': w, '207.1': w}, cycles=w,
    grade='measured-release-RTL',
    definition='WIN_LOAD frame at the entry q pins (compiled cycle 116 of the lower_svc image, tb cycles) -> last window-row '
               'HBM read beat returned to the slices before GO, all 16 slices (SVCLOW_HBMT rd_done_last_preGO - 116 + 1); '
               '127 window rows + the own row, 2,112 sector reads (16 slices x 2 PCs x 64 code + 2 scale)',
    shape='L0 fixture job (TP4 rank 0, 16 heads, T 128) on the 16 real dsdv_svc_rs, compiled frames (lower_svc), HBM = '
          'elastic per-PC model DQ 8 credits, latency 40 + rand 0..15 (seeds 1 / 2: %d / %d). The window job is the same '
          '128-row load in every layer class: in the T-640 L2 / L20 gather vehicles (static latency 40) WIN_LOAD -> last '
          'window read = %s with the gather issued 1 cycle later (window reads all precede the owned-row reads), so the '
          'gather does not stretch it; idx-scan HBM contention (old 265.9 / 207.1 classes) cannot be exercised: dsdv_idx_rg '
          'is not bound on mu4c (both nodes are off the critical path)' % (wl[1], wl[2], ','.join(g_wl)),
    bit_exact=True,
    golden='L0 fixture (released checkpoint): all 128 x 16 root scores + 16 x 128 SE rows bit-exact vs fixture attn.scores, '
           '160 P.V words vs fixture attn.pv (the window rows are the operands); L2/L20 vehicles: see attn.gather',
    rtl=dict(REL, module='dsdv_svc_att window source (x16) + dsfd_svc_pc'),
    bench='tools/s81_dv/layer_prog/svc/tb_svc_lower.sv@claude/toksim-s81-idx-1019 394cef884 (main bench_svc + observation-only '
          'SVCLOW_HBMT); collected from TOKSIM-S81/IDX ot-epyc9 oth-ubuntu-245201-1792460502',
    evidence='results/rtl/toksim_s81c_gath_1019/window_load/run_base_s{1,2}.log (SVCLOW_HBMT, SVCLOW verdict=PASS); mutant '
             'witnesses run_slot_s1.log / run_late_s1.log FAIL as required',
    job='IDX ot-epyc9 oth-ubuntu-245201-1792460502 (collected); latency sweep ot-epyc9 oth-ubuntu-765919-1792477075',
    edges_owed='+2 (L20 B1 svc splice, as attn.gather)',
    latency_sensitivity=lat,
    note='FINDING: the window load is HBM credit x latency bound (DQ 8 outstanding per PC, 66 reads a PC): +lat 100 -> %d '
         'cycles (PASS); +lat 180 -> only %d of 2,112 reads before GO, verdict %s (fault %s): the compiled W_SLACK 560 '
         '(lower_svc: WIN_LOAD -> GO) assumes <= 56-edge HBM latency. The measured %d holds only at the bench model latency.'
         % (lat[100]['span'], lat[180]['n_rd_preGO'], lat[180]['verdict'], lat[180]['first_fault_code'], w))
rec = dict(cls='GATH', written='2026-10-20 PT', agent_branch=BR, ops=[gather, window])
OUT.write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(dict(gather=dict(by_old=by_old, views={L: {k: x['span'] for k, x in v.items()} for L, v in views.items()}),
                      window=dict(by_old=window['by_old'], lat={k: (v['span'], v['verdict']) for k, v in lat.items()}))))
