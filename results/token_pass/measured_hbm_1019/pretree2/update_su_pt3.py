#!/usr/bin/env python3
"""HBM-PRETREE3 (10-20): SU.VOP reduction records MEASURED on the PRETREE=1 static SU (closed HH-6 pre-tree
hbm_su_pretree_s_1018-p3 bound in ot_hbm_su_static_top; source claude/hbm-pretree2-1020@a5cc6f083, Verilator 5.050,
direct RTL, model csum8 / ordered-max goldens) -> units/su.json + the two --measured inputs for the census.

Measured serial edges are read from each record's sim log (last_lg_write + WR - dispatch) and must equal the compiler's
cycles_serial; stream = serial x 4/3 (0.9 GHz serial domain on 833 ps stream edges).

Qwen softmax (census shape 8192 x 8 rows, one record per layer, a TP-4-era shape):
  tp8  (PRIMARY) the TP-8 die holds 1 KV head = 4 q heads (kv1 attention records are already dropped), so the record
       is the measured 4-row programme: max_r4 (378 serial, codex/hbm-pretree-pickup-1020) and the no-reset 2+2 phased
       exp_sum_r4 (1422 serial, 4098 VM reads/writes, 2 phase-2 causal mutants FAIL).
  8row (conservative variant) census rows taken literally: qw_softmax_max 8-row measured directly (506 serial);
       exp_sum = two back-to-back measured phased-4 programmes (2 x 1422; no overlap credited).
No affine-in-rows law is used.
usage: update_su_pt3.py BRANCH@SHA  (writes units/su.json [tp8], pretree2/m_pt3_{tp8,8row}.json, pretree2/su_pt_summary.json)"""
import copy, json, re, shutil, sys
from pathlib import Path
H = Path(__file__).resolve().parent.parent          # measured_hbm_1019
R = H.parents[2]
P = H / 'pretree2'
T = P / 'production_terminal'
SRC = sys.argv[1]
K = lambda d: json.dumps(d, sort_keys=True)
V = lambda n, m=1, f='FP32': ['VM', n, m, f]
JOB = 'ot-epyc5:/srv/opentallas-scratch/claude/hbm-pretree2/suvop'
MASTER = ('ot_hbm_su_static_top PRETREE=1 (16 x ot_hbm_su_static_pgslice + ot_hbm_su_red_pretree_s [closed '
          'hbm_su_pretree_s_1018-p3-1dad69123] + 4 x ot_hbm_su_static_qcore + ot_hbm_su_red_pretree_j + ot_hbm_su_stree_net)')


def meas(log, dispatch):
    t = log.read_text()
    m = re.search(r'last_lg_write_edge=(\d+).*WR=(\d+)', t)
    ok = bool(re.search(r'^SU_TOP PASS\b', t, re.M)) and not re.search(r'^SU_TOP (FAIL|ERROR)\b', t, re.M)
    return (int(m.group(1)) + int(m.group(2)) - dispatch), ('PASS' if ok else 'FAIL')


DS = {
 'ds_q_norm_ss': dict(A=V(160, 8), R=V(1)),
 'ds_kv_norm_ss': dict(A=V(64, 8), R=V(1)),
 'ds_route_total': dict(A=V(6), R=V(1)),
 'ds_attend_max640': dict(A=V(640), R=V(1)),
 'ds_attend_exp_sum640': dict(A=V(640), B=V(640), O=V(640), R=V(1)),
 'ds_attend_max128': dict(A=V(128), R=V(1)),
 'ds_attend_exp_sum128': dict(A=V(128), B=V(128), O=V(128), R=V(1)),
}
QMAX = K(dict(A=V(8192, 8), R=V(1, 8)))
QEXP = K(dict(A=V(8192, 8), B=V(1, 8), O=V(8192, 8), R=V(1, 8)))

su = json.loads((H / 'units/su.json').read_text())
ab = H / 'units_variants/su_asbuilt_1019.json'
if not ab.exists():
    shutil.copy(H / 'units/su.json', ab)
asb = json.loads(ab.read_text())
summ = {}


def put(tab, des, sk, serial, verdict, rec, job, note):
    e = tab['designs'][des]['SU.VOP']['shapes'][sk]
    old = asb['designs'][des]['SU.VOP']['shapes'][sk].get('cycles')
    e.update(cycles=round(serial * 4 / 3, 2) if verdict == 'PASS' else None, golden=verdict, rtl_master=MASTER,
             rtl_source=SRC, bound_in_die=False, verilator='5.050', asbuilt_cycles=old, job=job,
             bench='tools/hbm_static/toksim_su/suvop/{tb_toksim_su_top.sv PRETREE=1, prod_compile.py --pretree} ' + rec,
             notes=(f'PRE-TREE measured: {note}; serial {serial} edges (x4/3 stream); model csum8/ordered-max order; '
                    f'as-built {old}; model {e.get("model_cost")}; die bind owed (GEN2e4 has no su_pt slots)'))
    return dict(serial=serial, stream=e['cycles'], golden=verdict, asbuilt_stream=old, model=e.get('model_cost'), n=e.get('n'))


for r, shp in DS.items():
    p = json.loads((T / 'vec_pt' / r / 'programme.json').read_text())
    s, v = meas(T / 'vec_pt' / r / 'sim_mr10_pt.log', p['dispatch_edge'])
    assert s == p['cycles_serial'], (r, s, p['cycles_serial'])
    summ[r] = put(su, 'ds_ar', K(shp), s, v, r, f'{JOB}/vec_pt/{r}', f'record {r}, {p["issues"]} issues, QPR {p["pretree"]["qpr"]}')

# Qwen measured components
qm8 = json.loads((T / 'vec_pt/qw_softmax_max/programme.json').read_text())
s_max8, v_max8 = meas(T / 'vec_pt/qw_softmax_max/sim_mr10_pt.log', qm8['dispatch_edge'])
mr4 = json.loads((P / 'qw4_admission/runtime/summary.json').read_text())
s_max4, v_max4 = meas(P / 'qw4_admission/runtime/max_r4.log', mr4['dispatch_edge'])
assert s_max4 == mr4['measured_serial_edges']
ph = json.loads((P / 'phase4/runtime_summary.json').read_text())
s_exp4, v_exp4 = meas(P / 'phase4/runtime.log', ph['charged_dispatch_edge'])
assert s_exp4 == ph['actual_serial_edges']
assert ph['causal_phase_failures']['source_alias']['verdict'] == ph['causal_phase_failures']['scalar_stale']['verdict'] == 'REJECTED'

base_su = copy.deepcopy(su)
v8 = copy.deepcopy(base_su)
summ['qw_softmax_max'] = put(su, 'qwen', QMAX, s_max4, v_max4, 'qw4_admission max_r4', f'{JOB}/codex_qw4/max_r4',
                             'TP-8 die = 4 q heads: 4-row record max_r4 (MAX-mode tamper witness REJECTED)')
summ['qw_softmax_exp_sum'] = put(su, 'qwen', QEXP, s_exp4, v_exp4, 'phase4 exp_sum_r4_phased', f'{JOB}/codex_qw4/exp_sum_r4_phased',
                                 'TP-8 die = 4 q heads: no-reset 2+2 phased exp_sum_r4 (4098 VM rd/wr, 16 scalars; '
                                 'source-alias + stale-scalar mutants FAIL)')
summ['qw_softmax_max_8row'] = put(v8, 'qwen', QMAX, s_max8, v_max8, 'qw_softmax_max', f'{JOB}/vec_pt/qw_softmax_max',
                                  '8-row record measured directly')
summ['qw_softmax_exp_sum_8row'] = put(v8, 'qwen', QEXP, 2 * s_exp4, v_exp4, '2 x phase4 exp_sum_r4_phased',
                                      f'{JOB}/codex_qw4/exp_sum_r4_phased', '8 rows = two back-to-back measured phased-4 programmes')
for r, shp in DS.items():
    v8['designs']['ds_ar']['SU.VOP']['shapes'][K(shp)] = su['designs']['ds_ar']['SU.VOP']['shapes'][K(shp)]

for tab in (su, v8):
    for des in ('ds_ar', 'qwen'):
        ent = tab['designs'][des]['SU.VOP']; num = den = 0.0
        for e in ent['shapes'].values():
            if e.get('cycles') is not None and e.get('golden') == 'PASS' and e.get('model_cost'):
                num += e['n'] * e['cycles']; den += e['n'] * e['model_cost']
        ent['ratio'] = round(num / den, 4) if den else None
        ent['measured_model_sum'] = round(den, 1)
        ent['grade'] = 'measured-pretree-bench (reductions on bound HH-6 pre-tree in static SU; die bind owed)'
    tab['note_pretree3'] = ('HBM-PRETREE3 10-20: SU reduction records measured on PRETREE=1 static SU; Qwen softmax at the TP-8 '
                            '4-row shape (variant m_pt3_8row keeps 8 rows); as-built table units_variants/su_asbuilt_1019.json')
    tab['branch'] = SRC.split('@')[0]
(H / 'units/su.json').write_text(json.dumps(su, indent=1) + '\n')
(H / 'units_variants/su_pretree_8row.json').write_text(json.dumps(v8, indent=1) + '\n')

rel = json.loads((H / 'measured_rel.json').read_text())
fr = json.loads((R / 'results/rtl/toksim_hbm_su_1019/sfu/rownorm_fix/fragment.json').read_text())
for name, tab in (('tp8', su), ('8row', v8)):
    a = copy.deepcopy(rel)
    for des in ('ds_ar', 'qwen'):
        a['designs'][des]['SU.VOP'] = tab['designs'][des]['SU.VOP']
    rn = a['designs']['qwen']['FUSED.ROW_NORM']
    for k, v in fr['shapes'].items():
        assert k in rn['shapes'], k
        rn['shapes'][k] = dict(rn['shapes'][k], **{x: v[x] for x in ('cycles', 'golden')}, notes='HH-6 pre-tree: ' + str(v.get('notes', ''))[:300])
    rn['grade'] = fr['grade']
    a.setdefault('sources', {})['SU.VOP'] = f'units/su.json (HBM-PRETREE3 {name})'
    (P / f'm_pt3_{name}.json').write_text(json.dumps(a, indent=1) + '\n')
(P / 'su_pt_summary.json').write_text(json.dumps(dict(source=SRC, records=summ,
    ratio=dict(tp8={d: su['designs'][d]['SU.VOP']['ratio'] for d in ('ds_ar', 'qwen')},
               row8={d: v8['designs'][d]['SU.VOP']['ratio'] for d in ('ds_ar', 'qwen')})), indent=1) + '\n')
for k, v in summ.items():
    print(k, v)
print('ratio tp8', {d: su['designs'][d]['SU.VOP']['ratio'] for d in ('ds_ar', 'qwen')},
      '8row', {d: v8['designs'][d]['SU.VOP']['ratio'] for d in ('ds_ar', 'qwen')})
