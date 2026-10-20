#!/usr/bin/env python3
"""TOKSIM-HBM-su fork A: collect the SU.VOP record bench results into suvop/fragment.json (brief schema).
usage: make_fragment.py RESULTS_DIR CENSUS_SHAPES OUT   (RESULTS_DIR/<profile>/<record>/{programme.json,sim_<profile>.log})"""
import json, re, sys
from pathlib import Path

RES, CENSUS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
BR = sys.argv[4] if len(sys.argv) > 4 else 'claude/toksim-hbm-su-1019'
K = lambda d: json.dumps(d, sort_keys=True)
V = lambda n, m=1, f='FP32': ['VM', n, m, f]
# record -> (design, census SHAPE_KEY)
MAP = {
 'ds_res_copy': ('ds_ar', dict(A=V(20480), O=V(20480))),
 'ds_moe_sum0': ('ds_ar', dict(A=V(53), C=V(53), O=V(53))),
 'ds_moe_sum2': ('ds_ar', dict(A=V(53), C=V(53), D=V(53), O=V(53))),
 'ds_q_norm_y': ('ds_ar', dict(A=V(1280), B=V(1280), C=V(1280), O=V(1280))),
 'ds_kv_norm_y': ('ds_ar', dict(A=V(512), B=V(512), C=V(512), O=V(512))),
 'ds_scores_bias': ('ds_ar', dict(A=V(384), C=V(384), O=V(384))),
 'ds_bf16_p640': ('ds_ar', dict(A=V(640), O=V(640))),
 'ds_bf16_p128': ('ds_ar', dict(A=V(128), O=V(128))),
 'ds_attend_norm': ('ds_ar', dict(A=V(512), B=V(512), O=V(512))),
 'ds_route_weights': ('ds_ar', dict(A=V(6), B=V(6), O=V(6))),
 'ds_w_scale': ('ds_ar', dict(A=V(32), O=V(32))),
 'ds_attend_den': ('ds_ar', dict(A=V(1), B=V(1), C=V(1), O=V(1))),
 'ds_q_norm_ss': ('ds_ar', dict(A=V(160, 8), R=V(1))),
 'ds_kv_norm_ss': ('ds_ar', dict(A=V(64, 8), R=V(1))),
 'ds_route_total': ('ds_ar', dict(A=V(6), R=V(1))),
 'ds_attend_max640': ('ds_ar', dict(A=V(640), R=V(1))),
 'ds_attend_exp_sum640': ('ds_ar', dict(A=V(640), B=V(640), O=V(640), R=V(1))),
 'ds_attend_max128': ('ds_ar', dict(A=V(128), R=V(1))),
 'ds_attend_exp_sum128': ('ds_ar', dict(A=V(128), B=V(128), O=V(128), R=V(1))),
 'ds_swiglu': ('ds_ar', dict(A=V(24, 7), B=V(24, 7), C=V(24, 7), O=V(24, 7))),
 'ds_engram_gate': ('ds_ar', dict(A=V(4), B=V(4), O=V(4))),
 'qw_bf16_p': ('qwen', dict(A=V(8192, 8), O=V(8192, 8))),
 'qw_row_scale_res': ('qwen', dict(A=V(4096), B=V(4096), C=V(4096), O=V(4096))),
 'qw_row_scale_gu': ('qwen', dict(A=V(6144), B=V(6144), O=V(6144))),
 'qw_row_scale_qkv': ('qwen', dict(A=V(1536), B=V(1536), O=V(1536))),
 'qw_round_q': ('qwen', dict(A=V(1024), O=V(1024))),
 'qw_pv_normalize': ('qwen', dict(A=V(128, 8), B=V(128, 8), O=V(128, 8))),
 'qw_softmax_max': ('qwen', dict(A=V(8192, 8), R=V(1, 8))),
}
# records measured on a production-sized sub-shape whose class shape is reached by the measured law
LAW = {'qw_softmax_exp_sum_r1': ('qwen', dict(A=V(8192, 8), B=V(1, 8), O=V(8192, 8), R=V(1, 8)), 8),
       'qw_softmax_max_r1': None}
UNLOWERED = {
 ('ds_ar', K(dict(A=V(4), O=V(4)))): 'sfu 6 = sqrt(softplus) (and engram/router SIDE functions): global lane 0 FULL scalar side pipe; '
     'its NumPy golden and side-pipe calendar are not in this bench (cycles null)',
 ('ds_ar', K(dict(A=V(1), O=V(1)))): 'm1 5 (A/imm1) + sfu 2 rsqrt on the FULL lane side pipe (rs records): not lowered here',
 ('ds_ar', K(dict(A=V(1), I=['VM', 1, 1, 'U32'], O=V(1)))): 'indexed gather (I operand, MDESC indexed): needs the gather-index calendar',
 ('ds_ar', K(dict(A=V(64), B=V(64), D=V(64), O=V(64)))): 'rope tail: b_half + c_pair (pair lane operand) addressing not lowered',
 ('ds_ar', K(dict(A=V(64, 32), B=V(64, 32), D=V(64, 32), O=V(64, 32)))): 'rope (index_q): b_half + c_pair not lowered',
 ('qwen', K(dict(A=V(128, 10), B=V(64, 10), D=V(64, 10), O=V(128, 10)))): 'rope: b_half + c_pair not lowered',
}
cen = json.loads(CENSUS.read_text())
frag = {'designs': {}}
GIT = {}


def sim(d, prof):
    lg = d / f'sim_{prof}.log'
    if not lg.exists(): return None, 'no log'
    t = lg.read_text()
    m = re.search(r'^SU_TOP (PASS|FAIL).*$', t, re.M)
    if not m: return None, 'NO VERDICT ' + t[-300:]
    return m.group(1), m.group(0)[:200]


rows = []
for prof in ('mr10', 'mr18'):
    for d in sorted((RES / prof).glob('*/')):
        pj = d / 'programme.json'
        if not pj.exists(): continue
        p = json.loads(pj.read_text())
        v, line = sim(d, prof)
        rows.append((prof, d.name, p, v, line))
by = {(r[0], r[1]): r for r in rows}
for des in ('ds_ar', 'qwen'):
    cl = cen[des]['classes']['SU.VOP']
    ent = dict(law='shape_table', shapes={}, ratio=None, grade='pending', pending=[], where_model_wrong='')
    frag['designs'][des] = {'SU.VOP': ent}
    rat_num = rat_den = 0.0
    meas_model = 0.0
    for rec, (rdes, shp) in MAP.items():
        if rdes != des: continue
        sk = K(shp)
        assert sk in cl['shapes'], (rec, sk)
        c = cl['shapes'][sk]
        r10, r18 = by.get(('mr10', rec)), by.get(('mr18', rec))
        if r10 is None: continue
        p = r10[2]
        cyc = p['cycles_stream_833ps'] if r10[3] == 'PASS' else (p['cycles_stream_833ps'] if r10[3] == 'FAIL' else None)
        note = (f"serial {p['cycles_serial']} edges (x4/3 = 833 ps stream); dispatch {p['dispatch_edge']} -> retire "
                f"{p['retire_edge']} (last LG write + SWD {p['WR']}); {p['issues']} issues / {p['emissions']} emissions on "
                f"{p['lanes_per_quarter']} lanes/quarter, issue->write {p['issue_to_write']}; profile mr10 = die-bound "
                f"pgslice_lg MULTIRATE 10/7 (serial SRD 12 / SWD 10)")
        if r18:
            note += f"; mr18 (18/15 budget: SRD 18 / SWD 16) {r18[2]['cycles_stream_833ps']} ({r18[3]})"
        if p.get('red'):
            note += ('; reduction AS BUILT: 1 lane output / quarter / edge into the reducer (die.v has no pre-tree), '
                     '10 chains + pairwise tree + RF (stree L 32) quarter combine + RF sector drain')
        if p['roles'].get('B') == 'rf':
            note += '; broadcast B from the RF (class-1, producer setup not counted)'
        note += f"; model {c['model_cost']}"
        g = 'PASS' if r10[3] == 'PASS' else 'FAIL'
        ent['shapes'][sk] = dict(cycles=cyc, golden=g if r10[3] else 'NONE', rtl_master='ot_hbm_su_static_top (16 x ot_hbm_su_static_pgslice + 4 x ot_hbm_su_static_qcore + ot_hbm_su_stree_net)',
                                 rtl_source='claude/hd4g-gen2e3-1019@9787e078a', bound_in_die=True,
                                 bench='tools/hbm_static/toksim_su/suvop/{tb_toksim_su_top.sv,prod_compile.py,run_toksim_su.sh} record ' + rec,
                                 job=f"ot-epyc5:/srv/opentallas-scratch/claude/toksim-hbm-su/suvop/vec_mr10/{rec}", verilator='5.050',
                                 notes=note, model_cost=c['model_cost'], n=c['n'], mr18_cycles=(r18[2]['cycles_stream_833ps'] if r18 else None),
                                 mr18_golden=(r18[3] if r18 else None))
        if cyc is not None and g == 'PASS':
            rat_num += c['n'] * cyc; rat_den += c['n'] * c['model_cost']; meas_model += c['n'] * c['model_cost']
    for rec, spec in LAW.items():
        if not spec or spec[0] != des: continue
        r10 = by.get(('mr10', rec)); base = by.get(('mr10', 'qw_softmax_max')); b1 = by.get(('mr10', 'qw_softmax_max_r1'))
        if not (r10 and base and b1): continue
        sk = K(spec[1]); c = cl['shapes'][sk]
        # affine in emissions per row from the two measured softmax.max points (1 row, 8 rows)
        e1, e8 = b1[2]['emissions'], base[2]['emissions']; y1, y8 = b1[2]['cycles_serial'], base[2]['cycles_serial']
        slope = (y8 - y1) / (e8 - e1)
        est = r10[2]['cycles_serial'] + slope * (r10[2]['emissions'] * (spec[2] - 1))
        cyc = round(est * 4 / 3, 2)
        ent['shapes'][sk] = dict(cycles=cyc, golden=r10[3] or 'NONE', rtl_master='ot_hbm_su_static_top', rtl_source='claude/hd4g-gen2e3-1019@9787e078a',
                                 bound_in_die=True, bench='prod_compile.py record ' + rec, job=f"ot-epyc5:.../vec_mr10/{rec}", verilator='5.050',
                                 notes=(f"law affine: measured 1-row record {r10[2]['cycles_serial']} serial edges ({r10[2]['emissions']} "
                                        f"emissions) + {spec[2]-1} rows x {r10[2]['emissions']} emissions x {slope:.4f} edges/emission "
                                        f"(slope from measured softmax.max 1 row {y1} / 8 rows {y8}); the 8-row record needs 1,024 store rows "
                                        f"on the 32 SFU lanes/quarter (> 512) -> split by the compiler; model {c['model_cost']}"),
                                 model_cost=c['model_cost'], n=c['n'], law='affine_emissions')
        if r10[3] == 'PASS':
            rat_num += c['n'] * cyc; rat_den += c['n'] * c['model_cost']; meas_model += c['n'] * c['model_cost']
    for (udes, sk), why in UNLOWERED.items():
        if udes != des: continue
        c = cl['shapes'][sk]
        ent['shapes'][sk] = dict(cycles=None, golden='NONE', rtl_master='ot_hbm_su_static_top', rtl_source='claude/hd4g-gen2e3-1019@9787e078a',
                                 bound_in_die=True, bench=None, job=None, verilator='5.050', notes='NOT MEASURED: ' + why,
                                 model_cost=c['model_cost'], n=c['n'])
    tot = cl['model_sum']
    ent['ratio'] = round(rat_num / rat_den, 4) if rat_den else None
    ent['measured_model_sum'] = round(meas_model, 1)
    ent['covered_pct_of_model_sum'] = round(100 * meas_model / tot, 1)
    ent['grade'] = 'measured-current-d4g' if meas_model else 'pending'
frag['updated_note'] = 'mr10 = die-bound profile used for cycles; mr18 in notes / mr18_cycles'
OUT.write_text(json.dumps(frag, indent=1) + '\n')
for des, e in frag['designs'].items():
    x = e['SU.VOP']; print(des, 'ratio', x['ratio'], 'covered', x['covered_pct_of_model_sum'], '%')
