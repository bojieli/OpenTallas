#!/usr/bin/env python3
"""HBM-PRETREE2 (10-20): SU.VOP reduction records re-measured on the PRETREE=1 static SU (closed HH-6 pre-tree bound in
ot_hbm_su_static_top: 16 x ot_hbm_su_red_pretree_s in the pgslices + 4 x ot_hbm_su_red_pretree_j in the qcores),
programmes from prod_compile.py --pretree (reduction = the MODEL's csum8 / ordered max order, asserted at compile).
Writes units/su.json (reduction shapes replaced; other SU.VOP shapes unchanged) and keeps the as-built table in
units_variants/su_asbuilt_1019.json.
usage: update_su_pt.py RESULTS_DIR BRANCH@SHA   (RESULTS_DIR/<record>/{programme.json,sim_mr10_pt.log})"""
import json, re, shutil, sys
from pathlib import Path
H = Path(__file__).resolve().parent.parent
RES, SRC = Path(sys.argv[1]), sys.argv[2]
K = lambda d: json.dumps(d, sort_keys=True)
V = lambda n, m=1, f='FP32': ['VM', n, m, f]
MAP = {
 'ds_q_norm_ss': ('ds_ar', dict(A=V(160, 8), R=V(1))),
 'ds_kv_norm_ss': ('ds_ar', dict(A=V(64, 8), R=V(1))),
 'ds_route_total': ('ds_ar', dict(A=V(6), R=V(1))),
 'ds_attend_max640': ('ds_ar', dict(A=V(640), R=V(1))),
 'ds_attend_exp_sum640': ('ds_ar', dict(A=V(640), B=V(640), O=V(640), R=V(1))),
 'ds_attend_max128': ('ds_ar', dict(A=V(128), R=V(1))),
 'ds_attend_exp_sum128': ('ds_ar', dict(A=V(128), B=V(128), O=V(128), R=V(1))),
 'qw_softmax_max': ('qwen', dict(A=V(8192, 8), R=V(1, 8))),
}
LAW = ('qwen', dict(A=V(8192, 8), B=V(1, 8), O=V(8192, 8), R=V(1, 8)), ('qw_softmax_exp_sum_r1', 'qw_softmax_exp_sum_r2', 'qw_softmax_exp_sum_r3'), 8)
JOB = 'ot-epyc5:/srv/opentallas-scratch/claude/hbm-pretree2/suvop/vec_pt'
MASTER = ('ot_hbm_su_static_top PRETREE=1 (16 x ot_hbm_su_static_pgslice + ot_hbm_su_red_pretree_s [closed '
          'hbm_su_pretree_s_1018-p3-1dad69123] + 4 x ot_hbm_su_static_qcore + ot_hbm_su_red_pretree_j + ot_hbm_su_stree_net)')


def rec(name):
    d = RES / name
    p = json.loads((d / 'programme.json').read_text())
    t = (d / 'sim_mr10_pt.log').read_text() if (d / 'sim_mr10_pt.log').exists() else ''
    m = re.search(r'^SU_TOP (PASS|FAIL).*$', t, re.M)
    return p, (m.group(1) if m else 'NONE')


su = json.loads((H / 'units/su.json').read_text())
(H / 'units_variants').mkdir(exist_ok=True)
ab = H / 'units_variants/su_asbuilt_1019.json'
if not ab.exists(): shutil.copy(H / 'units/su.json', ab)
asb = json.loads(ab.read_text())
out = {}
for r, (des, shp) in MAP.items():
    p, v = rec(r)
    sk = K(shp); e = su['designs'][des]['SU.VOP']['shapes'][sk]
    old = asb['designs'][des]['SU.VOP']['shapes'][sk].get('cycles')
    pt = p['pretree']
    e.update(cycles=p['cycles_stream_833ps'] if v == 'PASS' else None, golden=v, rtl_master=MASTER, rtl_source=SRC,
             bound_in_die=False, bench='tools/hbm_static/toksim_su/suvop/{tb_toksim_su_top.sv PRETREE=1,prod_compile.py --pretree,run_toksim_su.sh PT=1} record ' + r,
             job=f'{JOB}/{r}', verilator='5.050', asbuilt_cycles=old,
             notes=(f"PRE-TREE: serial {p['cycles_serial']} edges (x4/3 stream); {p['issues']} issues on {p['lanes_per_quarter']} "
                    f"lanes/quarter, QPR {pt['qpr']} (quarter run {pt['quarter_run_words']} words, {pt['blocks_per_row']} blocks/row), "
                    f"tree_cmd at emit+{p['issue_to_write']}, reducer operand +PT_RED {pt['pt_red']}; order = model csum8 / ordered max "
                    f"(asserted vs hdc_golden_v41.csum per row); as-built (1 lane/quarter/edge) {old}; model {e.get('model_cost')}; "
                    f"die bind owed (GEN2e4 has no su_pt / PRETREE sucore: NOTICE lanes/L2H-GEN2E.md)"))
    out[r] = (p['cycles_serial'], p['cycles_stream_833ps'], v, old, e.get('model_cost'))
des, shp, recs, rows = LAW
pts = [(json.loads((RES / r / 'programme.json').read_text())['rows'],) + rec(r) for r in recs]
xs = [x[0] for x in pts]; ys = [x[1]['cycles_serial'] for x in pts]
n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs); icp = my - slope * mx
est = icp + slope * rows
ok = all(x[2] == 'PASS' for x in pts)
sk = K(shp); e = su['designs'][des]['SU.VOP']['shapes'][sk]
old = asb['designs'][des]['SU.VOP']['shapes'][sk].get('cycles')
e.update(cycles=round(est * 4 / 3, 2) if ok else None, golden='PASS' if ok else 'FAIL', rtl_master=MASTER, rtl_source=SRC,
         bound_in_die=False, law='affine_rows', bench='prod_compile.py --pretree records ' + ','.join(recs), job=f'{JOB}/qw_softmax_exp_sum_r*',
         verilator='5.050', asbuilt_cycles=old,
         notes=(f"PRE-TREE law affine in rows: measured {dict(zip(xs, ys))} serial edges (1/2/3 rows, all {'PASS' if ok else 'NOT ALL PASS'}) "
                f"-> {icp:.1f} + {slope:.2f} x rows -> {rows} rows {est:.1f} serial; the {rows}-row record needs 1,024 store rows on the "
                f"32 SFU lanes/quarter (> 512) -> split by the compiler; as-built {old}; model {e.get('model_cost')}; die bind owed"))
out['qw_softmax_exp_sum(8 rows, law)'] = (round(est, 1), round(est * 4 / 3, 2), 'PASS' if ok else 'FAIL', old, e.get('model_cost'))
for des in ('ds_ar', 'qwen'):
    ent = su['designs'][des]['SU.VOP']; num = den = mm = 0.0
    for sk, e in ent['shapes'].items():
        if e.get('cycles') is not None and e.get('golden') == 'PASS' and e.get('model_cost'):
            num += e['n'] * e['cycles']; den += e['n'] * e['model_cost']; mm += e['n'] * e['model_cost']
    ent['ratio'] = round(num / den, 4) if den else None
    ent['measured_model_sum'] = round(mm, 1)
    ent['grade'] = 'measured-current-d4g (reductions: pre-tree bench-bound, die bind owed)'
su['note_pretree2'] = ('HBM-PRETREE2 10-20: SU reduction records re-measured with the closed HH-6 pre-tree bound in the static SU '
                       'bench (PRETREE=1) and model-order lowering; as-built table kept in units_variants/su_asbuilt_1019.json')
su['branch'] = SRC.split('@')[0]
(H / 'units/su.json').write_text(json.dumps(su, indent=1) + '\n')
(H / 'pretree2/su_pt_summary.json').write_text(json.dumps(
    {k: dict(serial=a, stream=b, golden=c, asbuilt_stream=d, model=m) for k, (a, b, c, d, m) in out.items()}, indent=1) + '\n')
for k, v in out.items(): print(k, v)
for des in ('ds_ar', 'qwen'): print(des, 'SU.VOP ratio', su['designs'][des]['SU.VOP']['ratio'])
