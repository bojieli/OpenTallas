#!/usr/bin/env python3
"""MU-S81-2/DIE (10-19, port of MU-S81/DIE 908a67c18 onto the next S81 GEN base claude/s81-pilot-next-1019 198cf1c56):
multi-user bind tables of the p4l die, derived from bind_table_p4l3.json (unchanged, the single-user default:
ot_pdie_serdes_col stand-ins, CH_BOARD 700 coll lane RTL).  Plans (tools/s81_dv/dv_plan.py --layout p4 --p4l --tier-w 276
--lanes 4 --p4h-drop 6 --frame-w 1436.832 --mu N --lk-slots results/arch/s81_dv_1016/p4l_lkcol/plan.json):
  --mu 0 -> p4l_lkcol/plan.json byte-identical;  --mu 1 -> p4l_lkcol_mu;  --mu 2 -> p4l_lkcol_mab.
  bind_table_p4l3_mu.json   MU_EN die (every multi-user die; the 51 non-duplicated stage groups): seqhost
                            dsdv_seq_host_mux = seq_host + CLOSED dsdv_mu_hslot (NSLOT 47) + NEW leaf dsdv_mu_hwin (end-slice
                            windows; boot words = host CSR 0x15 / 0x16 from f_host); end slices on lep_mu_a (copy A only)
                            except s_7N (host plane: lep_mu HOST_EN 1, owed top / kit); every MU cluster has the CLOSED
                            dsdv_mu_land leaf
  bind_table_p4l3_mab.json  + copy-A/B rank-die variant (pre/post-group dies of the 8 duplicated groups): s_0S
                            dsdv_slice_lepw_mab (lep_mu_ab, 2nd lane pair tx2/tx3/rx2/rx3 -> lk_WS2 / lk_WS3, copy-B relay
                            plan results/arch/mu_s81_1018/copyb_relay_plan.json if_slot_3596)
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
LEAF = {'a': 'ot_s81sl_lep_mu_a (copy-A endpoint; kit s81sl_lepmua, gate pending -> view owed)',
        'ab': 'ot_s81sl_lep_mu_ab (copy-A/B endpoint; kit s81sl_lepmu, gate pending -> view owed)',
        'h': 'ot_s81sl_lep_mu HOST_EN 1 AB_EN 0 (host-plane MU endpoint of s_7N: parameter-free top + kit OWED)'}


# MU-DIE-S81/PO2 (10-19): the closed view each landing master binds (closure-record commit + kit) and its reset landing.
# po2 views (PO-SUBMIT, kit reset_landing 2 stages) carry landing_reset_stages 2; old views (l1 / g3a / p3) carry no key.
# dv_bind's strict landing reset check derives RL from each view's source kit and FAILS any disagreement.
LAND_VIEWS = {   # master: (record branch, commit, RL)
    'dsfd_dvland_276': ('codex/closure-record-s81dv_land_276-po2-df5c2d585', '4e4a509e266ac84a0ac9f77552936342956f7b21', 2),
    'dsfd_dvland_276l': ('codex/closure-record-s81dv_land_276l-po2-df5c2d585', 'c1f2495df9e5c32462adc0d2a2c0c66d0af76562', 2),
    'dsfd_dvland_70': ('codex/closure-record-s81dv_land_70-po2-df5c2d585', 'e676a75d23d7f728746c3d225dc54c58eab9f00a', 2),
    'dsfd_dvland_562': ('codex/closure-record-s81dv_land_562-po2-df5c2d585', '23d9cbb8cfecf6303a8b3afe1e51d5127640faa6', 2),
    'dsfd_dvland_512': ('codex/closure-record-s81dv_land_512-po2-df5c2d585', '306a99997b1bfc28ebc33ea7948003a6a62e1860', 2),
    'dsfd_dvland_682': ('codex/closure-record-s81dv_land_682-l1-1da4d6aae', 'ff575a79ee8ef4f584b625c7b1dfd732aec483ce', 0),
    'dsfd_dvland_pvrd': ('codex/closure-record-s81dv_land_pvrd-p3-b15a4ddad', '3b83f2255f8e17caa8eb4ff7e6354214440b817b', 0),
}


def lane_add(rule, lane, entries):
    rule['lanes'][lane]['split'] += entries


def build(ab):
    T = copy.deepcopy(T0)
    M = T['masters']; W = T['rtl_widths']
    # ---- seqhost
    q = copy.deepcopy(M['dsdv_seq_host']); q['module'] = 'dsdv_seq_host_mux'; q.pop('ref', None)
    q['view'] = None
    q['view_note'] = ('cluster not hardened; sh_vc CLOSED, dsdv_mu_hslot CLOSED (NSLOT 47, child_views); MU-S81-2/DIE: '
                      'dsdv_seq_host_mu NSLOT 47 + dsdv_mu_hwin (NEV 8, NEP 4, NRT 2; kit owed)')
    lane_add(q['ports']['ht.o'], 0, [['mu_c_7n', 0, 131, 34], ['mu_rc_7n', 0, 165, 11]])
    lane_add(q['ports']['hf.i'], 2, [['mu_rt_7n', 0, 20, 32]])
    for e in ('0N', '0S', '7S'):
        q['ports'][f'mu{e}.o'] = {'lanes': [{'split': [[f'mu_c_{e.lower()}', 0, 0, 34], [f'mu_rc_{e.lower()}', 0, 34, 11]]}]}
    q['ports']['rt0N.i'] = {'land': True, 'lanes': [{'split': [['mu_rt_0n', 0, 0, 32]]}]}
    q['port_note'] = q.get('port_note', '') + '; MU: mu_c/mu_rc to s_7N in ht spare bits, s_0N/0S/7S on mu_* lanes; mu_rt from s_7N in hf_l2 spare bits, s_0N on rt_0N'
    M['dsdv_seq_host_mux'] = q
    w = dict(W['dsdv_seq_host'])
    w.update(t_mf=4, **{f'mu_c_{e}': 34 for e in ('7n', '7s', '0n', '0s')}, **{f'mu_rc_{e}': 11 for e in ('7n', '7s', '0n', '0s')},
             mu_rt_7n=32, mu_rt_0n=32)
    W['dsdv_seq_host_mux'] = w

    # ---- end slices
    def slice_master(src, new, module, rt, leaf, extra=None):
        m = copy.deepcopy(M[src]); m['module'] = module
        m['view_note'] = f'cluster not hardened; MU-S81-2/DIE: leaf {LEAF[leaf]} + dsdv_mu_land CLOSED (child_views), lane tiles dsfd_coll_lane_w/e'
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
        w.pop('tf', None)        # BIND/mu4: MU masters have no tf / tfb (tf-less lane tiles dsfd_coll_lane_*_ntf)
        if extra:
            w.update(tx2=512, tx3=512, rx2=514, rx3=514)
        W[module] = w
    slice_master('dsdv_slice_lepe', 'dsdv_slice_lepe_mu', 'ot_s81sl_slice_lepe_mu', True, 'h')
    slice_master('dsdv_slice_lepe_nh', 'dsdv_slice_lepe_nh_mus', 'ot_s81sl_slice_lepe_nh_mus', False, 'a')
    slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mu', 'ot_s81sl_slice_lepw_mu', True, 'a')
    if ab:
        ex = {'tx2.o': {'port': 'tx2', 'lane': 512}, 'rx2.i': {'lanes': [{'split': [['rx2', 0, 0, 514]]}], 'land': True},
              'tx3.o': {'port': 'tx3', 'lane': 512}, 'rx3.i': {'lanes': [{'split': [['rx3', 0, 0, 514]]}], 'land': True}}
        slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mab', 'ot_s81sl_slice_lepw_mab', False, 'ab', ex)
    else:
        slice_master('dsdv_slice_lepw', 'dsdv_slice_lepw_mus', 'ot_s81sl_slice_lepw_mus', False, 'a')
    # All endpoint faults are sticky RTL outputs; do not leave MU protocol faults unobservable.
    T['endpoint_fault_masters'] = ['dsdv_slice_lepe_mu', 'dsdv_slice_lepe_nh_mus',
                                   'dsdv_slice_lepw_mu', 'dsdv_slice_lepw_mab' if ab else 'dsdv_slice_lepw_mus']
    # S81-DIECHAIN 10-19: every other block's sticky fault output joins the die status boundary (block_fault vector, one bit
    # per instance whose RTL module has a `fault` output: plain slices, bk collector/selector, G-unit, svc_rs ENTRY slices)
    T['status_fault_masters'] = ['dsdv_slice', 'dsfd_bk_collector', 'dsfd_bk_selector', 'dsdv_gunit', 'dsdv_svc_rs']
    # seq_host MU table faults (hslot + hwin fold, dsdv_mu_hwin.sv t_mf[3:0]) leave as die status pins (strict OUTPUT_OPEN before)
    T['masters']['dsdv_seq_host_mux'].setdefault('top_ports', []).append({'port': 't_mf', 'dir': 'output', 'bits': 4})
    # BIND/mu4 10-19: chain-end frames (strict OUTPUT_OPEN xo / xok on 64 frames): every col_h9 / col_h10 instance with no
    # plan xo link binds the generated chain-end variant <module>_nx (tools/s81_dv/frame_l4.py: xo / xok and their four
    # relays removed at the source; frame_bench NX=1).  col_h9_MX (the L02 -> L03 forward) is unchanged.
    for mk in ('col_h9', 'col_h10'):
        mod = T['masters'][mk]['module']
        T['masters'][mk]['chain_end'] = {'plan_port': 'xo', 'dir': 'o', 'module': mod + '_nx'}
        W[mod + '_nx'] = {k: v for k, v in W[mod].items() if k not in ('xo', 'xok')}
    # BIND/mu4 10-19: the S81 HBM macro is the K-only variant ot_hbm3e_phy_v41x_aw30_e8p5_k (no W port, no model counter
    # ports: strict OUTPUT_OPEN w_* / wr_* / w_oor / refreshes / w_reads and the W pads removed at the source; abstract by
    # tools/s81_dv/phy_k_variant.py, model rtl/dsrom_sys/s81_link/ot_hbm3e_phy_v41x_aw30_e8p5_k.sv, HBM gate PHY_K=1);
    # its sticky k_oor leaves as the die status pin phy_hbm_k_oor.
    ph = T['masters']['ot_hbm3e_phy_v41x_aw30_e8p5']
    ph['module'] = 'ot_hbm3e_phy_v41x_aw30_e8p5_k'
    ph['mode_unused'] = [u for u in ph.get('mode_unused', []) if not (u['port'].startswith('w_') or u['port'].startswith('wr_'))]
    ph['top_ports'] = [{'port': 'k_oor', 'dir': 'output', 'bits': 1}]
    ph['port_note'] = ('k_*/kr_* = abutted faces of the 16 dsfd_ctrl_rg2 (2 PCs each); BIND/mu4: K-only macro (no W port / '
                       'counters), k_oor -> die status pin phy_hbm_k_oor')
    W['ot_hbm3e_phy_v41x_aw30_e8p5_k'] = {k: v for k, v in W['ot_hbm3e_phy_v41x_aw30_e8p5'].items()
                                          if not (k.startswith('w_') or k.startswith('wr_') or k in ('refreshes',))}
    T['spare_out_rules'] = True          # tools/s81_dv/dv_spare_out.py (svc_rs role faces, lane quantisation, clock taps)
    T['rtl_files'] = T['rtl_files'] + ['physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']   # dsdv_mu_land SRAM 1
    cv = T['child_views']
    cv['dsdv_mu_hslot'] = dict(view='dsdv_mu_hslot-28a8118d5 (CLOSED TT +70.22 / FF +27.30, DRC 0; native PASS L 124.5 / C 88.3 / sp 10.7/11.0; main ccf787d45, audit 7aa582c7a)',
                               parent='dsdv_seq_host_mux -> dsdv_seq_host_mu (u_hs, NSLOT 47 MUT 0; source byte-identical to the view)')
    cv['dsdv_mu_land'] = dict(view='dsdv_mu_land-dsdv_mu_land-263e13fc3 (CLOSED TT +68.25 / FF +24.02, DRC 0; native PASS L 104.8 / C 79.1 / sp 32.6/27.2; main 9b80ceb82, audit be45f0660)',
                              parent='ot_s81sl_slice_lep_mux (u_land, W 1104 NB 80 NS 1 SRAM 1) in every MU end slice')
    ow = T['child_views_owed']
    ow['ot_s81sl_lep_mu_a'] = 'kit s81sl_lepmua (d53b41629) --cts gate pending: collect / review / submit (MU-S81b)'
    if ab:
        ow['ot_s81sl_lep_mu_ab'] = 'kit s81sl_lepmu --cts gate pending: collect / review / submit (MU-S81/KIT)'
    ow['ot_s81sl_lep_mu(HOST_EN1,AB_EN0)'] = 's_7N host-plane MU endpoint: parameter-free top + kit OWED (MU-S81b item 3)'
    ow['dsdv_mu_hwin'] = 'NEW leaf (end-slice windows + RX tag check, MU-S81-2/DIE): kit owed'
    T['plan'] = 'S81-DV p4l ' + ('copy-A/B rank die (results/arch/s81_dv_1016/p4l_lkcol_mab/plan.json)' if ab else
                                 'multi-user (results/arch/s81_dv_1016/p4l_lkcol_mu/plan.json)')
    T['note'] = T['note'] + '; MU-S81-2/DIE 10-19: ' + ('MU_EN + AB_EN (s_0S)' if ab else 'MU_EN') + ' variant (bind/mk_table_p4l3_mu.py)'
    T['land_plan_note_mu'] = ('MU lanes (mu_*, rt_0N' + (', lt/lr_lk_WS2/3' if ab else '') + ') are not in landing/p4l3/land_plan.json: '
                              'landing K 1 default until the die lead re-runs dv_land_pilot on the MU plan')
    T['land_views'] = {m: dict(ref=r, commit=c, kit=f"physical/ref_tile/s81dv_land_{m[len('dsfd_dvland_'):]}",
                               job=r.split('closure-record-', 1)[1]) for m, (r, c, _) in LAND_VIEWS.items()}
    T['landing_reset_stages'] = {m: rl for m, (_, _, rl) in LAND_VIEWS.items() if rl}
    band_b_513(T)
    return T


# BIND mu4 (10-19): the C3 band port B is 513 b = {pk[511:0], valid} at the source (ot_s81sl_xr BW 513; a B send with
# pairs > 2 is a sticky xr fault, refused by dv_layer_compile.send_cfg).  bo maps contiguously onto the two q lanes:
# bo[275:0] -> lane 0 bits 0..275, bo[512:276] -> lane 1 bits 0..236 (lane 1 bits 237..275 stay the lane-quantisation pad).
BO_W = 513
Q_O_513 = {'hb': 1, 'lanes': [{'split': [['bo', 0, 0, 276]]}, {'split': [['bo', 276, 0, BO_W - 276]]}]}


def band_b_513(T):
    for m in T['masters'].values():
        if 'q.o' in m.get('ports', {}):
            m['ports']['q.o'] = copy.deepcopy(Q_O_513)
    for w in T['rtl_widths'].values():
        if 'bo' in w:
            w['bo'] = BO_W


for ab, nm in ((False, 'bind_table_p4l3_mu.json'), (True, 'bind_table_p4l3_mab.json')):
    (B / nm).write_text(json.dumps(build(ab), indent=1) + '\n')
    print('wrote', nm)
