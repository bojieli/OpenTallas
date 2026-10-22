#!/usr/bin/env python3
"""TOKSIM-HBM-su fork C: build results/rtl/toksim_hbm_su_1019/sfu/fragment.json from the committed bench logs."""
import json, re, sys, datetime
from pathlib import Path
WT = Path(__file__).resolve().parents[4]
O = WT/'results/rtl/toksim_hbm_su_1019/sfu'
CEN = json.load(open('/home/ubuntu/wt/toksim-hbm-1019/results/token_pass/measured_hbm_1019/census_shapes.json'))
SRC = 'claude/hd4g-gen2e3-1019@9787e078a (generic sources byte-equal to scoped_d4g for the bound modules)'
BR = 'claude/toksim-hbm-su-1019'
def keys(des, cls): return CEN[des]['classes'][cls]['shapes']
def kv(log, key):
    m = re.search(rf'\b{key}=(-?\d+)', log); return int(m.group(1)) if m else None
frag = {"designs": {"ds_ar": {}, "qwen": {}}}
# ---------------- QDQ_FP8
q1 = (O/'qdq/qdq1.log').read_text(); qm = (O/'qdq/qdq1_mut2.log').read_text()
ok = 'PASS HGI_QDQ_HOST_SPLIT_LOCKSTEP' in q1 and 'LOCKSTEP_FAIL' in qm
span = kv(q1, 'span_rq_to_record_done'); door = kv(q1, 'last_record_done')
sk = list(keys('ds_ar', 'FUSED.QDQ_FP8'))[0]; model = keys('ds_ar', 'FUSED.QDQ_FP8')[sk]['model_cost']
frag['designs']['ds_ar']['FUSED.QDQ_FP8'] = dict(law='shape_table', shapes={sk: dict(
    cycles=span, golden='PASS' if ok else 'FAIL', rtl_master='ot_hgi_qdq_host_split #(RL7,WC4,COMPACT1) (die hb_quant_NW)',
    rtl_source=SRC, bound_in_die=True, bench=f'{BR}:tools/hbm_static/toksim_su/sfu/run_qdq_span.sh + tb_toksim_qdq_split.sv',
    job='ot-epyc5 oth-ubuntu-922078-1792460461 /srv/opentallas-scratch/claude/toksim-hbm-su/sfu/out/qdq', verilator='5.050',
    notes=(f'512-word FP8 QDQ (qdqvec record 0 = DS production vector, out_0 re-checked = hdc_golden_v41.qdq_fp8 512/512) on the '
           f'split vs monolith lockstep: 16 beats, first VM read request -> record_done (bank commit) = {span} edges at 833 ps '
           f'(stream clock); doorbell -> record_done {door} (host target48 / record calendar issue at +8 included). Bench VM '
           f'model = fixed 7 edges at the quant pins (RL7); die GEN2c relay lanes to the NW banks NOT included. 8-record anchor '
           f're-run: split_last_write 158 (= 10-18 anchor), record pipeline 16 beats/record + 42-edge fill. Mutant RL5 -> '
           f'LOCKSTEP_FAIL (witness qdq/qdq1_mut2.log).'))},
    ratio=round(span/model, 3), grade='measured-current-d4g' if ok else 'measured-golden-FAIL', pending=[],
    where_model_wrong=f'price 25 = issue beats only (16 + dispatch); the record latency is 16 beats + 38-edge decoder/bank pipeline + 5 split edges = {span}')
# ---------------- ROW_NORM (reduction component only)
rows = {}
for c in ('d4096', 'seg128_q2', 'seg128_k1'):
    lg = (O/f'rms/{c}.log').read_text(); mut = (O/f'rms/{c}.mut_phase.log').read_text()
    comp = json.loads((O/f'rms/{c}.compile.txt').read_text().split(' ', 2)[2])
    rows[c] = dict(ok=lg.startswith('PASS') and 'FAIL' in mut, rows=comp)
d = rows['d4096']['rows']; red_d = d[0]['span'] + d[1]['span']
red_q = rows['seg128_q2']['rows'][1]['scalar_cycle'] + 1; red_k = rows['seg128_k1']['rows'][0]['span']
conv = 4/3
shp = keys('qwen', 'FUSED.ROW_NORM'); rn = {}
for k, v in shp.items():
    A = json.loads(k)['A'][1]
    case, red = ('d4096', red_d) if A == 4096 else (('seg128_q2', red_q) if A == 1024 else ('seg128_k1', red_k))
    lb = round(red*conv, 1)
    rn[k] = dict(cycles=None, golden='PASS' if rows[case]['ok'] else 'FAIL', rtl_master='ot_hbm_su_reduce_static (in ot_hbm_su_static_qcore, clk_red = pll_serial)',
        rtl_source=SRC, bound_in_die=True, bench=f'{BR}:tools/hbm_static/toksim_su/sfu/run_rms_reduce.sh + rms_reduce_compile.py (tb tools/hbm_static/su_reduce_tb.cpp)',
        job=f'ot-epyc5 oth-ubuntu-922126-1792460461 /srv/opentallas-scratch/claude/toksim-hbm-su/sfu/out/rms/{case}', verilator='5.050',
        measured_lower_bound=lb,
        notes=(f'NO FUSED.ROW_NORM engine/lowering exists in d4g (no norm engine in die.v; col_sfu grid lanes cannot reduce / '
               f'rsqrt: tools/hbm_layer_vehicle/sfu_fused_compile.py audit) -> it runs as the SU ss/rs/y chain. MEASURED here: '
               f'the sum-of-squares on the bound reducer (one operand/edge, LAT 9, RAW 10, csum8 + pairwise, exact cycles '
               f'+ bit-exact csum golden, phase mutant FAILS): {case} = {red} serial edges = {lb} edges at 833 ps '
               f'(serial 3:4). '
               + (f'(quarter 1024 squares {d[0]["span"]} + 4-root combine {d[1]["span"]}; the stree/RF transit of the 3 remote '
                  f'roots is NOT included) ' if case == 'd4096' else
                  ('(2 heads of 128 on one quarter: q_norm 8 heads / 4 quarters) ' if case == 'seg128_q2' else '(1 head of 128 a quarter: k_norm 2 heads) '))
               + 'NOT included: lane x*x issue/stage to the reducer, RF/stree scalar transit, rsqrt on the quarter-0 FULL lane side pipe, '
                 'the y = x*r*g pass with the HBM gain read (first access), VM drain. Lower bound only.'))
frag['designs']['qwen']['FUSED.ROW_NORM'] = dict(law='shape_table', shapes=rn, ratio=None, grade='pending',
    pending=[dict(job='none launched', result_path=None, what='full ROW_NORM record = SU ss/rs/y chain on ot_hbm_su_static_top; needs the SU lowering (fork A suvop machinery); compose from units/su.json SU.VOP q_norm.ss/rs/y measurements')],
    where_model_wrong=f'price 175/125 assumes a D4096 norm engine that d4g does not have; the bound reducer alone needs >= {round(red_d*conv)} (d4096) / {round(red_q*conv)} (q seg128) / {round(red_k*conv)} (k seg128) edges')
# ---------------- SFU.GLU
G = O/'glu'
def glu(d):
    p = G/d/'run.log'
    if not p.exists(): return None
    t = p.read_text(); m = re.search(r'TOKSIM_GLU_SPAN (.*?) \(', t)
    v = {k: int(x) for k, x in re.findall(r'(\w+)=(-?\d+)', m.group(1))} if m else {}
    v['pass'] = 'SFU_SPLIT_EQUIV PASS' in t and 'PASS canonical' in t
    v['fail'] = 'VM_QSWIGLU_WORD' in t or 'FAIL' in t
    return v
runs = {d.name: glu(d.name) for d in sorted(G.iterdir()) if d.is_dir()}
c = runs['glu_r15_w3072_o1_l190']; c0 = runs['glu_r15_w3072_o0_l377']; c20 = runs['glu_r20_w3072_o1_l190']
w768 = runs.get('glu_r15_w768_o1_l190')
sk = list(keys('qwen', 'SFU.GLU'))[0]; model = keys('qwen', 'SFU.GLU')[sk]['model_cost']
fails = sorted(k for k, v in runs.items() if v and v['fail'])
note = (f'Canonical Qwen3-8B swiglu fixture (hbm-sim P8191 L0, 3072 words, route scalar C; golden = machine u_glu words, '
        f'VM readback 3072/3072 exact) on ONE sfucore: ot_hgi_sfu_core_split2 (core of the bound split3) + programme store r10 '
        f'(D5) in lockstep (6.6k edges, 0 mismatch) with the reference split engine at R=15 die relays (LG_PATH 15) + LG pair '
        f'taps 14/11 (= die.v defaults) + 8 ot_vms_bank_static banks; 16 SiLU lanes, 16 words/edge in and out.  Span = '
        f'io_start_v -> last VM write done at the tap: overlap calendar (as compiled, make_qswiglu_io_calendar OVERLAP) '
        f'{c["ref_last_wdone"]} edges (first VM read {c["ref_first_rq"]}, first/last write {c["ref_first_wq"]}/{c["ref_last_wq"]}); '
        f'serial calendar (default) {c0["ref_last_wdone"]}; TAP 24/21 budget (= R 20 round trip) {c20["ref_last_wdone"]}. '
        f'Drain lag 190 rows after arith start is the minimum (SiLU horizon 46 + 122 + lead): earlier drains FAIL bit-exact '
        f'({", ".join(fails)}). 833 ps stream clock. ')
if w768 and w768.get('pass'):
    note += (f'Per-quadrant split (768 words a core, 4 cores in parallel; NOT what the fixture/compiler of record does): '
             f'{w768["ref_last_wdone"]} edges (glu_r15_w768_o1_l190 PASS).')
frag['designs']['qwen']['SFU.GLU'] = dict(law='shape_table', shapes={sk: dict(
    cycles=c['ref_last_wdone'], golden='PASS' if c['pass'] else 'FAIL',
    rtl_master='ot_hgi_sfu_core_split3 #(LWB15,LG_PATH15) [core split2] + ot_hgi_sfu_programme_store_r10 #(PAGE_AW1) + sfu LG pair taps',
    rtl_source=SRC, bound_in_die=True, bench=f'{BR}:tools/hbm_static/toksim_su/sfu/run_glu_span.sh + tb_toksim_glu_split.sv + gen_glu_case.py',
    job='ot-epyc9 oth-ubuntu-293088-1792460722 /srv/opentallas-scratch/claude/toksim-hbm-su/sfu/out/glu_r15_w3072_o1_l190', verilator='5.050',
    notes=note, tap_24_21_cycles=c20['ref_last_wdone'], serial_calendar_cycles=c0['ref_last_wdone'],
    per_core_768_cycles=(w768 or {}).get('ref_last_wdone') if w768 and w768.get('pass') else None)},
    ratio=round(c['ref_last_wdone']/model, 3), grade='measured-current-d4g' if c['pass'] else 'measured-golden-FAIL', pending=[],
    where_model_wrong=f'price 120 = "GLU fast path 60 / half width" estimate; one 16-lane SFU core needs 192 beats in + 192 out + the 168-edge SiLU horizon + 2x15 LG relays')
frag['designs']['qwen']['FUSED.ROW_NORM']['ratio_lower_bound'] = round(min(s['measured_lower_bound']/keys('qwen','FUSED.ROW_NORM')[k]['model_cost'] for k, s in frag['designs']['qwen']['FUSED.ROW_NORM']['shapes'].items()), 2)
json.dump(frag, open(O/'fragment.json', 'w'), indent=1)
print(json.dumps({c: {k: v.get('ratio') for k, v in frag['designs'][d_].items()} for d_ in frag['designs'] for c in [d_]}, indent=0))
