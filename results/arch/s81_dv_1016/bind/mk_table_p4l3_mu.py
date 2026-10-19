#!/usr/bin/env python3
"""MU-S81/DIE (10-19): multi-user bind tables of the p4l die, derived from bind_table_p4l3.json (unchanged, the
single-user default).  Plan: tools/s81_dv/dv_plan.py --layout p4 --p4l --tier-w 276 --lanes 4 --p4h-drop 6
--frame-w 1436.832 --mu 1 (-> p4l_mu) / --mu 2 (-> p4l_mab); --mu 0 reproduces p4l/plan.json byte-identically.
  bind_table_p4l3_mu.json   MU_EN die (every multi-user die): seqhost dsdv_seq_host_mux (dsdv_seq_host + slot table +
                            end-slice windows; boot config = host CSR 0x15 from f_host), end slices _mu / _mus masters
  bind_table_p4l3_mab.json  + copy-A/B rank-die variant (64 pre/post-group rank dies): s_0N dsdv_slice_lepw_mab
                            (AB_EN 1, 2nd lane pair tx2/tx3/rx2/rx3 -> 2 more ot_pdie_serdes lk_WN2 / lk_WN3)
Wiring (split = [port, port bit, lane bit, width]):
  s_7N   mu_c 34 + mu_rc 11 in ht_7N bits 131..175 (seqhost ht.o -> slice ht.i), mu_rt 32 in hf_7N_l2 bits 20..51
  s_0N   lanes mu_0N (seqhost mu0N.o -> slice mu.i, landed) / rt_0N (slice rt.o -> seqhost rt0N.i, landed)
  s_0S / s_7S   lanes mu_0S / mu_7S (seqhost mu0S.o / mu7S.o -> slice mu.i, landed); S-tier mu_rt not returned
"""
import copy, json
from pathlib import Path
B = Path(__file__).resolve().parent
T0 = json.load(open(B / 'bind_table_p4l3.json'))
MU_IN = {'land': True, 'lanes': [{'split': [['mu_c', 0, 0, 34], ['mu_rc', 0, 34, 11]]}]}
RT_OUT = {'lanes': [{'split': [['mu_rt', 0, 0, 32]]}]}


def lane_add(rule, lane, entries):
    rule['lanes'][lane]['split'] += entries


def build(ab):
    T = copy.deepcopy(T0)
    M = T['masters']; W = T['rtl_widths']
    # ---- seqhost
    q = copy.deepcopy(M['dsdv_seq_host']); q['module'] = 'dsdv_seq_host_mux'; q.pop('ref', None)
    q['view'] = None; q['view_note'] = 'MU-S81/DIE: dsdv_seq_host_mu NSLOT 47 NEV 8 (worktree RTL; unit not hardened, hslot leaf kit owed MU-S81/KIT)'
    lane_add(q['ports']['ht.o'], 0, [['mu_c_7n', 0, 131, 34], ['mu_rc_7n', 0, 165, 11]])
    lane_add(q['ports']['hf.i'], 2, [['mu_rt_7n', 0, 20, 32]])
    for e in ('0N', '0S', '7S'):
        q['ports'][f'mu{e}.o'] = {'lanes': [{'split': [[f'mu_c_{e.lower()}', 0, 0, 34], [f'mu_rc_{e.lower()}', 0, 34, 11]]}]}
    q['ports']['rt0N.i'] = {'land': True, 'lanes': [{'split': [['mu_rt_0n', 0, 0, 32]]}]}
    q['port_note'] = q.get('port_note', '') + '; MU-S81/DIE: mu_c/mu_rc to s_7N in ht spare bits, s_0N/0S/7S on mu_* lanes; mu_rt from s_7N in hf_l2 spare bits, s_0N on rt_0N'
    M['dsdv_seq_host_mux'] = q
    w = dict(W['dsdv_seq_host']); w.pop('f_mc', None)
    w.update(t_mf=4, **{f'mu_c_{e}': 34 for e in ('7n', '7s', '0n', '0s')}, **{f'mu_rc_{e}': 11 for e in ('7n', '7s', '0n', '0s')},
             mu_rt_7n=32, mu_rt_0n=32)
    W['dsdv_seq_host_mux'] = w
    # ---- end slices
    def slice_master(src, new, module, rt, extra=None):
        m = copy.deepcopy(M[src]); m['module'] = module
        m['view_note'] = m['view_note'] + '; MU-S81/DIE: MU_EN 1 (leaf ot_s81sl_lep_mu + dsdv_mu_land, kits owed MU-S81/KIT)'
        if src == 'dsdv_slice_lepe':
            lane_add(m['ports']['ht.i'], 0, [['mu_c', 0, 131, 34], ['mu_rc', 0, 165, 11]])
            lane_add(m['ports']['hf.o'], 2, [['mu_rt', 0, 20, 32]])
        else:
            m['ports']['mu.i'] = copy.deepcopy(MU_IN)
            if rt:
                m['ports']['rt.o'] = copy.deepcopy(RT_OUT)
        if extra:
            m['ports'].update(extra)
        M[new] = m
        w = dict(W.get(M[src]['module'], {}))
        w.update(mu_c=34, mu_rc=11, **({'mu_rt': 32} if rt else {}))
        if extra:
            w.update(tx2=512, tx3=512, rx2=514, rx3=514, tfb=2)
        if w:
            W[module] = w
    slice_master('dsdv_slice_lepe', 'dsdv_slice_lepe_mu', 'ot_s81sl_slice_lepe_mu', True)
    slice_master('dsdv_slice_lepe_nh', 'dsdv_slice_lepe_nh_mus', 'ot_s81sl_slice_lepe_nh_mus', False)
    slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mus', 'ot_s81sl_slice_lepw_mus', False)
    if ab:
        ex = {'tx2.o': {'port': 'tx2', 'lane': 512}, 'rx2.i': {'lanes': [{'split': [['rx2', 0, 0, 514]]}], 'land': True},
              'tx3.o': {'port': 'tx3', 'lane': 512}, 'rx3.i': {'lanes': [{'split': [['rx3', 0, 0, 514]]}], 'land': True}}
        slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mab', 'ot_s81sl_slice_lepw_mab', True, ex)
    else:
        slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mu', 'ot_s81sl_slice_lepw_mu', True)
    T['rtl_files'] = T['rtl_files'] + ['physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']   # dsdv_mu_land SRAM 1
    T['plan'] = 'S81-DV p4l ' + ('copy-A/B rank die (results/arch/s81_dv_1016/p4l_mab/plan.json)' if ab else
                                 'multi-user (results/arch/s81_dv_1016/p4l_mu/plan.json)')
    T['note'] = T['note'] + '; MU-S81/DIE 10-19: ' + ('MU_EN + AB_EN' if ab else 'MU_EN') + ' variant (bind/mk_table_p4l3_mu.py)'
    T['land_plan_note_mu'] = 'MU lanes (mu_*, rt_0N, lt/lr_lk_WN2/3) are not in landing/p4l3/land_plan.json: landing K 1 default until the die lead re-runs dv_land_pilot on the MU plan'
    return T


for ab, nm in ((False, 'bind_table_p4l3_mu.json'), (True, 'bind_table_p4l3_mab.json')):
    (B / nm).write_text(json.dumps(build(ab), indent=1) + '\n')
    print('wrote', nm)
