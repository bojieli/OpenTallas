#!/usr/bin/env python3
"""kv-die 2026-10-09 (OWNER DECISION ~04:00 PT, option 1a): the Qwen3-8B KV die (die generator `qwen_kv`).

One KV die per ROM die.  Long axis N-S; its N edge abuts the r22k ROM die's S edge under spine column M, where the two
UCIe macros face each other; the four HBM3E stacks sit beside its E and W edges (two a side), as they sat beside the
r21c ROM die.  Per side, outward to inward, the r21c HBM band re-placed with the SAME masters and pins
(tools/qwen_kv_die/r21c_band.json, dumped from the r21c generator):

    PHY (ot_hbm3e_phy 833.5 x 12,000.1) | controller (qkd_ctrl / qkd_ctrl_n = qfd_ctrl) | 32 per-PC CDC (qkd_cdc = qfd_cdc) |
    KV landing qkd_land (qfd_kvc successor: CDC core sides -> the stack's row engines, the KV merges, the KVN posted
    write, the embedding strip) | the stack's attention group:
        [ 4 row engines qkd_reng | stack aggregator qkd_astk | 4 row engines ]   (engine long faces abut the
        aggregator; RE-CUT D (results/arch/qwen_kv_die_20261009/recut.json): q in as a 519-b beat broadcast, P.V levels
        1-3 in the engine, one level-3 node a group out in 4,096-b beats -- ot_qwen_nearhbm_row_engine_d ports)

and a centre column: N edge -- UCIe macro (MX: bumps N, FDI S) / qkd_d2d (ot_qkvd_d2d) / qkd_seq (ot_qkvd_kv_seq) /
qkd_embgw (ot_qfd_emb_gw) / qkd_pll (PLL + reset sequencer, forwarded clock to the ROM die); die centre -- qkd_ahub
(ot_qwen_nearhbm_attn_hub_p); S edge -- the host SerDes macro (ot_qfd_serdes_112g_x12_phy) + qkd_host.
Relay stations at <= 430.56 um on every die wire that is not an abutment (same rule as the r21 ROM die).

    python3 tools/qwen_kv_die/kv_die.py plan --out results/arch/qwen_kv_die_20261009/kv_die      (record + DEF/V)
"""
import argparse
import copy
import hashlib
import json
import re
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as F     # noqa: E402  (Inst, Master, lattice, phy_pins, pin_rects, write_netlist)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_strips as KS           # noqa: E402  (v1.2 strip compositions: land / astk RTL bindings + clock entries)

GX, GY, SHAVE = F.GX, F.GY, F.SHAVE
F.MINW_PINS = True               # M6 / M7 face pins at 0.032 (die_kv7 PA DRT-0073: 0.024 is sub-minimum)
up = F.up
TPL_PATH = ROOT / 'tools' / 'qwen_kv_die' / 'r21c_band.json'
MARGIN = 21.6
R = 8                           # row engines a stack (near-HBM gate R = 8: 1,824 cycles at ctx 8192)
# re-cut H (adopted 10-09, recut_h.json): the row engine is 5 hard tiles in a column, bottom -> top head 0, head 1 (both MX),
# control, head 2, head 3; the control tile's two S1b copies leave on its S (heads 0 / 1) and N (heads 2 / 3) faces, every
# head's node beat leaves on its E face into the aggregator.  Frames (variant c, routes qkd_rhead_c / qkd_ectl_c): the head
# 152,960 um2 cells (route qkd_rhead_b floorplan) at 0.52 on 648 wide -- 648 so the far head of a pair (one head tile
# away from the control tile) stays inside the wire reach; the control tile 24,507 um2 synthesized (route qkd_ectl_a), its
# height set by its E face (634 + 425 pins).
HEAD = (648.0, 453.6)
ECTL = (648.0, 129.6)            # E face: si 634 + so 425 pins on M4 at 2-track pitch (101.7 um) + margins
ENG_H = 4 * HEAD[1] + ECTL[1] + 4 * GY
RENG = (HEAD[0], ENG_H)         # the engine column slot
# tile offsets inside an engine column (bottom -> top): head 0, head 1, control, head 2, head 3
TILE_Y = dict(h0=0.0, h1=HEAD[1] + GY, c=2 * (HEAD[1] + GY), h2=2 * (HEAD[1] + GY) + ECTL[1] + GY,
              h3=3 * (HEAD[1] + GY) + ECTL[1] + GY)
ASTK_W = 220.32                  # stack aggregator (re-cut D) MEASURED: 8 exp quads 314 k + Z tree 99 k + P.V tree (levels 4-7) 288 k
                                # + node staging / q broadcast ~73 k um2 cells at 0.50 + score / e memories as SRAM macros (786 k b,
                                # ~0.19 mm2) over the 4-engine height 7,992 um (synth4; was 777.6 ASSUMED)
# v1.2 (split): the landing strip stands one 216-um channel E of the CDC column (+ the 2.4-um CDC overhang of x_land): the
# write-queue controller (172.8 wide) sits in it at the stack middle, so its chains to the write leaves in the CDC column
# stay short (behind a 12-mm landing strip they went round its end: 600-700 um hops, 38 stages); elsewhere it is the relay
# channel of the CDC-column chains (relay spots with their 21.6-um keep-outs); CDC co / cf -> landing <= ~220 um
LAND_CHAN = 2.4 + 216.0
LAND_W = 172.8                  # KV landing column: 8 x 32 crossbar, 8 KV merges, emb strip (ASSUMED; r21c qfd_kvc 96.7)
UCIE = ('ot_qkvd_ucie_x64_phy', 777.6, 777.6)
SERDES = ('ot_qfd_serdes_112g_x12_phy', 2320.056, 1563.57)  # actual native host RXD512 / FDI1043 profile
FRAMES = dict(qkd_ckbump=(43.2, 43.2), qkd_d2d=(777.6, 518.4), qkd_seq=(777.6, 518.4), qkd_embgw=(388.8, 388.8), qkd_pll=(324.0, 324.0),
              qkd_ahub=(648.0, 648.0), qkd_host=(777.6, 518.4))
RELAY_PITCH = 430.56
PIN_REACH = 450.0               # qwen-1010/b: pin-to-pin register hop target (SS reach 504 um)
REACH_TARGET = 470.0            # every register-to-register segment (nearest frame points) <= this (SS reach 504 um)
FIRST_REACH = dict(wencoded=300.0)   # v1.3: first relay of the write-queue controller's group words (ctl_bin f<g>, late launch)
RELAY_TARGET = 320.0            # placement pitch: keeps every segment (nearest frame points) under the 504 um SS reach
GRID = 43.2                     # relay routing grid (um)
CHAN = 129.6                    # routing / relay channel beside every column (um)
STACKS = ('WS', 'WN', 'ES', 'EN')
W = 528
FDI_UCIE = 1 + 1 + 548 + 1 + 548
FDI_SERDES = 1 + 1 + 1043 + 1 + 1043
# re-cut H control tile <-> aggregator: start, T, cyc8, q beat {valid, beat, 512 b}, exp_done, er_data, node credit
ENG_IN = 1 + 14 + 3 + 1 + 6 + 512 + 32 + 64 + 1
# er, sc, lmax, node beat tags {valid, beat, g, gam}, k/v_done, fault (the 4,096-b node data leaves from the head tiles)
ENG_OUT = 1 + 12 + 1 + 12 + 128 + 256 + 2 + 1 + 4 + 1 + 4 + 1 + 1 + 1
HEAD_NB = 1024                  # a head's slice of a node beat (HD 32 / LFB)
T_PAIR = 4 + 1024 + 12 + 1 + 6 + 512   # S1b copy to a head pair: control, row, decision word, q beat
T_E = 16                        # a head's e word
T_RET = 32 + 1 + 1              # a head's scaled score + scale fault + lane fault
ABUT = {'stack_local', 'phy_dfi', 'd2d_fdi', 'hbm_cdc', 'cdc_core'}    # abutted / band buses: no relays
RTL = dict(qkd_ctrl='qfd_ctrl element (rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv + per-PC leaves; '
                    'ot_qfd_emb_pcport KVW 2: KV writes carry the HBM ECC side-band, data = the CDC completion h_cv / h_cdata; '
                    'kc: stream-command word -> ot_async_fifo -> hclk ot_qkvd_kcmd_tap chain -> the 32 ot_qwen_ctrl_pc_head cmd ports)',
           qkd_cdc='rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv ot_qwen_stream4_cdc_pc (route r11a)',
           qkd_land='qfd_kvc successor (landing crossbar) + ot_qkvd_kv_seq KV-merge slices + ot_qfd_emb_strip',
           qkd_ectl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv ot_qwen_nearhbm_ectl_h (re-cut H control tile)',
           qkd_rhead='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv ot_qwen_nearhbm_head_h (re-cut H head tile, hid strap)',
           qkd_astk='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_d.sv ot_qwen_nearhbm_attn_stack_d minus its engines',
           qkd_astk_n='as qkd_astk (N stacks: hub words on the S face)',
           qkd_land_n='as qkd_land (N stacks: pin plan level with the N-stack peers)',
           qkd_ctrl_n='as qkd_ctrl (N stacks: the kc stream-command port on the N face)',
           qkd_ahub='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv ot_qwen_nearhbm_attn_hub_p',
           qkd_seq='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv ot_qkvd_kv_seq',
           qkd_d2d='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv ot_qkvd_kv_end (ot_qkvd_d2d NT 3 / NR 4)',
           qkd_embgw='rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv ot_qfd_emb_gw',
           qkd_host='qfd_io_host successor (ingest stream: hing_qfd) + SerDes adapter ot_qfd_link_adapter',
           qkd_pll='vendor PLL abstract + ot_qwen_sys_rst_seq (ASSUMED frame)')


# die port -> RTL ports of the bound module (strict_ports: every RTL port is in exactly one die port or is classed)
BINDINGS = dict(
    qkd_ectl=dict(module='ot_qwen_nearhbm_ectl_h', file='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv',
                  ports=dict(si=['start_in', 'T_in', 'cyc8_in', 'q_valid_in', 'q_beat_in', 'q_data_in', 'exp_done',
                                 'er_data', 'nb_cr'],
                             so=['er_valid', 'er_addr', 'sc_valid', 'sc_addr', 'sc_data', 'lmax', 'lmax_any', 'nb_valid',
                                 'nb_beat', 'nb_g', 'nb_gam', 'k_done', 'v_done', 'fault'],
                             rq=['req_valid', 'req_v', 'req_g', 'req_t'], rs=['rsp_valid_in', 'rsp_data_in'],
                             t0=['t0_c', 't0_row', 't0_lt', 't0_qv', 't0_qb', 't0_qd'],
                             t1=['t1_c', 't1_row', 't1_lt', 't1_qv', 't1_qb', 't1_qd'],
                             e0=['t0_e'], e2=['t1_e'], s0=['ts0_sc', 'ts0_sf', 'ts0_gf'], s2=['ts1_sc', 'ts1_sf', 'ts1_gf'],
                             ck=['clk'], rst_n=['rst_n']),
                  sliced=dict(e1='e0', e3='e2', s1='s0', s3='s2'),
                  classed={'ev_k_first': 'debug', 'ev_v_first': 'debug'}),
    qkd_rhead=dict(module='ot_qwen_nearhbm_head_h', file='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv',
                   ports=dict(ti=['c_in', 'row_in', 'lt_in', 'q_valid_in', 'q_beat_in', 'q_data_in'], e=['e_in'],
                              s=['sc_d', 'sc_f', 'g_f'], nb=['nb_d'], ck=['clk'], rst_n=['rst_n']),
                   classed={'hid': 'by_design: die-top strap (tie cells), the head index of this tile'}),
    qkd_ahub=dict(module='ot_qwen_nearhbm_attn_hub_p', file='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv',
                  ports=dict(ap_WS=['si_valid', 'si_type', 'si_g', 'si_hh', 'si_k', 'si_any', 'si_data', 'pi_valid',
                                    'pi_g', 'pi_beat', 'pi_data'],
                             am_WS=['mo_valid', 'mo_g', 'mo_hh', 'mo_data'],
                             ao=['out_valid', 'out_g', 'out_beat', 'out_data'], hs=['start'], hf=['fault'],
                             ck=['clk'], rst_n=['rst_n']),
                  sliced=dict(ap_WN='ap_WS', ap_ES='ap_WS', ap_EN='ap_WS', am_WN='am_WS', am_ES='am_WS', am_EN='am_WS'),
                  classed={'ev': 'debug', 'native_reciprocal': 'debug: native-service observation output (unread on the die)',
                           'native_rz_ok': 'debug: native-service observation output (unread on the die)'}),
    qkd_seq=dict(module='ot_qkvd_kv_seq', file='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv',
                 ports=dict(rf=['c_v', 'c_d', 'c_cr'], tf=['u_v', 'u_d', 'u_cr'],
                            aq_WS=['a_start', 'a_T', 'a_layer', 'a_q_valid', 'a_q_beat', 'a_q_data'],
                            ar=['a_out_valid', 'a_out_g', 'a_out_beat', 'a_out_data'], hf=['a_hub_fault'],
                            af_WS=['a_stk_fault'], mf_WS=['m_fault'],
                            kvn_WS=['kvw_v', 'kvw_vg', 'kvw_t', 'kvw_layer', 'kvw_d', 'kvw_cr'], kc_WS=['kc_v', 'kc_d'],
                            gq=['emb_req_v', 'emb_req_d', 'emb_req_cr'], gr=['emb_q_v', 'emb_q_d', 'emb_q_cr'],
                            hc=['hc_v', 'hc_d', 'hc_cr'], tk=['tok_v', 'tok_d', 'tok_cr'], hs=['a_start'],
                            d2df=['d2d_fault', 'd2d_cause'], kst=['fault', 'fault_cause'], ck=['clk'], rst_n=['rst_n']),
                 sliced=dict(aq_WN='aq_WS', aq_ES='aq_WS', aq_EN='aq_WS', af_WN='af_WS', af_ES='af_WS', af_EN='af_WS',
                             mf_WN='mf_WS', mf_ES='mf_WS', mf_EN='mf_WS', kvn_WN='kvn_WS', kvn_ES='kvn_WS',
                             kvn_EN='kvn_WS', kc_WN='kc_WS', kc_ES='kc_WS', kc_EN='kc_WS'),
                 classed={}),
    qkd_d2d=dict(module='ot_qkvd_kv_end', file='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv',
                 ports=dict(rf=['r_v', 'r_d', 'r_cr'], tf=['t_v', 't_d', 't_cr'],
                            fdi=['tx_up', 'tx_v', 'tx_flit', 'rx_v', 'rx_flit'], flt=['fault', 'fault_cause'],
                            ck=['clk'], rst_n=['rst_n']),
                 classed={}),
)
# qwen-split/kvsys 2026-10-14 (owner 06:45 PT: Qwen two-die split, compute die + KV/SYSTEM die): build(split=True) is the
# KV/system die v1 (contract results/arch/qwen_split_1014/CONTRACT_KVSYS.md, link results/arch/qwen_split_1014/LINK.md):
#   - the head slot is the CLOSED hierarchical head cluster ot_qwen_nearhbm_head_hs 734.4 x 855.36 (route qkh_head_hs_ref-q13b);
#     the engine column (4 heads + ectl) grows to 3,551 um and the stack group to 14.3 mm, so each stack band (PHY / ctrl /
#     CDC / landing, 12.1 mm) is centred on a 14.3-mm stack pitch and the die grows N-S (both long edges stay HBM shoreline)
#   - the N-edge centre column ends the die link: ucie (UCIe x64 macro) | qkd_d2d (ot_qkvd_kv_end SPL 1, 777.6 x 518.4 kit
#     qkd_d2d_p2_ref) | qkd_lnk (ot_qkvd_split_kvlink, abutted) and the sequencer qkd_seq (merged-die cluster, 604.8 x 475.2)
#     talks to qkd_lnk on lx / lr (x3 / sd / kvd in, ar / ds / pw out) instead of the old rf / tf words
#   - qkd_embgw = the closed view outline 172.8 x 216; its SU face (EMBQ / EMBD) ends on qkd_lnk (gq / gr)
#   - qkd_ahub = the hard-reciprocal hub kit outline 1175.04 x 760.32 (qkd_ahub_ref-q13b)
SPLIT_HEAD = (734.4, 855.36)
# kvsys contract v1.1 (2026-10-14 PM, die lead): the head is the NATIVE wires-only parent ot_qkh_head_native (Codex decision
# 09:04: 16 closed lane8 + ktree stand; front / 16 stations / score are new hardened leaves; 35 separate child clock entries).
# Its slot is re-cut SHORT so the far head of each pair is one head height + 2.16 from its control tile with the bits
# x-aligned: 492.48 + 2 x 2.16 = 496.8 um <= 500 (no die relay, no latency change).  1080 x 492.48: a 3 x 6 lane_b grid
# (129.6^2, column pitch 172.8, row pitch 151.2, rows from y 54) + the front band (y 0..54, front 648 x 21.6 under the
# control tile's t span) + 16 stations (<= 32.4 x 32.4) in the 43.2 column gaps + ktree (cell + gap = 172.8 >= 151.2) and
# score in the two free cells (top margin 6.48): 0.5319 mm2 for ~0.31 mm2 of leaves.  Die-assigned pins are mirror-legal (horizontal faces M4
# only, vertical faces M5 only, clocks M4 W face), so heads below the control tile are MX and face it with their input
# face again (TP4 orientation rule); the control tile is centred in the wider column.
SPLIT_HEAD_V11 = (1080.0, 492.48)
# per-child clock entries (die ports, each its own CTS sink, delivered at phi - R of that child): die port -> RTL port
# head r2 (d7c8b1909, kvsys-elements 11:39): the lane station is split into stin (front -> lane) and stout (lane -> ktree /
# astk) leaves, each its own root: 51 entries = front, ktree, score, 16 stin, 16 stout, 16 lane8
HEAD_CLK_R2 = (['ck_f', 'ck_k', 'ck_s'] + [f'ck_i{i}' for i in range(16)] + [f'ck_o{i}' for i in range(16)] +
               [f'ck_l{i}' for i in range(16)])
# v1.2: head r4 (Codex, main b5103f681 / plan results/arch/qwen_split_1014/head_native_r4_codex_1014/plan.json): the front
# is four row-quarter leaves and every lane has stin | stk (KP D2) | nb1 | nb2 (NB D2 as two D1 leaves) + its lane8:
# 86 entries = 4 front + ktree + score + 16 x (stin, stk, nb1, nb2, lane); same data ports / cycles as r2 (exact head
# reference PASS 3,515, mutants FAIL).  Die port -> RTL: ck_f<q> -> ck_front[q], ck_k -> ck_kt, ck_s -> ck_score,
# ck_i<l> -> ck_stin[l], ck_t<l> -> ck_stk[l], ck_a<l> -> ck_nb1[l], ck_b<l> -> ck_nb2[l], ck_l<l> -> ck_lane[l]
HEAD_R4_PLAN = 'results/arch/qwen_split_1014/head_native_r4_codex_1014/plan.json'
HEAD_CLK = ([f'ck_f{q}' for q in range(4)] + ['ck_k', 'ck_s'] +
            [f'ck_{t}{i}' for t in 'itabl' for i in range(16)])
HEAD_CLK_CHILD = dict(**{f'ck_f{q}': f'front{q}' for q in range(4)}, ck_k='ktree', ck_s='score',
                      **{f'ck_{t}{i}': f'{c}{i}' if c in ('stin', 'stk', 'lane') else f'{c}_{i}'
                         for t, c in zip('itabl', ('stin', 'stk', 'nb1', 'nb2', 'lane')) for i in range(16)})
ECTL_CLK = ['ck_a', 'ck_b', 'ck_c']
# v1.2: the attention hub is the wires-only composition ot_qkd_ahub_die (kvsys-elements 33048f31a): the CLOSED core
# (qkd_ahub_core hd2) + 13 hardened tiles (4 ot_nhb_zh, ot_qkh_recip_leaf, 4 ot_nhb_pbst, 4 ot_nhb_pvlg), each its own clock
# entry (die port -> RTL ck_core / ck_zh[i] / ck_recip / ck_pbst[i] / ck_pvlg[i]); am[143:0] = 4 registered per-stack copies
AHUB_CLK = ['ck_c'] + [f'ck_z{i}' for i in range(4)] + ['ck_r'] + [f'ck_p{i}' for i in range(4)] + [f'ck_v{i}' for i in range(4)]
SPLIT_FRAMES = dict(qkd_seq=(604.8, 475.2), qkd_lnk=(777.6, 129.6), qkd_embgw=(172.8, 216.0), qkd_ahub=(1175.04, 760.32))
BINDINGS['qkd_lnk'] = dict(module='ot_qkvd_split_kvlink', file='rtl/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv',
    ports=dict(rf=['r_v', 'r_d', 'r_cr'], tf=['t_v', 't_d', 't_cr'],
               # bit order = the sequencer cluster's: r_x3_d = {v, tag, d} (d at bit 0), t_ar_d = {v, d 519}
               lx=['x3_d', 'x3_tag', 'x3_v', 'sd', 'kvd', 'ar_cr'], lr=['ar_d', 'ar_v', 'ds', 'pw', 'x3_cr'],
               gq=['ea_v', 'ea_kind', 'ea_addr', 'ea_cr'], gr=['eq_v', 'eq_d'], d2df=['d2d_fault', 'd2d_cause'], flt=['fault'],
               ck=['clk'], rst_n=['rst_n']),
    classed={})
_BASE = dict(HEAD=HEAD, ECTL=ECTL, ENG_H=ENG_H, RENG=RENG, TILE_Y=dict(TILE_Y), FRAMES=dict(FRAMES))


def _set_geometry(split, reserve_static_memory=False, reserve_native_astk=False):
    """module geometry for the plain KV die (split False) or the split KV/system die (split True)"""
    global HEAD, ENG_H, RENG, TILE_Y, FRAMES, LAND_W, ASTK_W
    if reserve_static_memory and not split:
        raise ValueError('native static memory reservation requires split KV/system die')
    if reserve_native_astk and not split:
        raise ValueError("native ASTK reservation requires split KV/system die")
    ASTK_W = 328.32 if reserve_native_astk else 220.32
    LAND_W = 237.6 if reserve_static_memory else 172.8
    HEAD = SPLIT_HEAD_V11 if split else _BASE['HEAD']
    ENG_H = 4 * HEAD[1] + ECTL[1] + 4 * GY
    RENG = (HEAD[0], ENG_H)
    TILE_Y = dict(h0=0.0, h1=HEAD[1] + GY, c=2 * (HEAD[1] + GY), h2=2 * (HEAD[1] + GY) + ECTL[1] + GY,
                  h3=3 * (HEAD[1] + GY) + ECTL[1] + GY)
    FRAMES = dict(_BASE['FRAMES'], **(SPLIT_FRAMES if split else {}))
    for k_ in _BASE_BINDINGS_LATE:
        _BASE_BINDINGS.setdefault(k_, BINDINGS[k_])
    for k_, v_ in (SPLIT_BINDINGS if split else _BASE_BINDINGS).items():
        BINDINGS[k_] = v_
    if not split:
        for k_ in SPLIT_ONLY_BINDINGS:
            BINDINGS.pop(k_, None)


# split die masters bind to the RTL the split actually instantiates (NO STUBS, owner 08:05 PT): the hierarchical head
# cluster, the merged-die sequencer cluster qkd_seq (native HEADS 1 / Q_FP32 1 profile = its parameters)
_BASE_BINDINGS = {k: BINDINGS[k] for k in ('qkd_rhead', 'qkd_seq', 'qkd_ectl', 'qkd_ahub')}
_BASE_BINDINGS_LATE = ('qkd_kvwq_ctl_bin', 'qkd_kvwq_leaf_s_w129_m')     # defined further down; captured at first _set_geometry call
SPLIT_BINDINGS = dict(
    # v1.1: the native head (wires-only parent of 35 hardened children, each its own clock entry)
    qkd_rhead=dict(module='ot_qkh_head_native_r4', file='rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv',
                   parameters=dict(Q_FP32=1),
                   ports=dict(ti=['c_in', 'row_in', 'lt_in', 'q_valid_in', 'q_beat_in', 'q_data_in'], e=['e_in'],
                              s=['sc_d', 'sc_f', 'g_f'], nb=['nb_d'], ck_f0=['ck_front'], ck_k=['ck_kt'], ck_s=['ck_score'],
                              ck_i0=['ck_stin'], ck_t0=['ck_stk'], ck_a0=['ck_nb1'], ck_b0=['ck_nb2'], ck_l0=['ck_lane'],
                              rst_n=['rst_n']),
                   sliced={**{f'ck_f{q}': 'ck_f0' for q in range(1, 4)},
                           **{f'ck_{t}{i}': f'ck_{t}0' for t in 'itabl' for i in range(1, 16)}},
                   classed={'hid': 'by_design: die-top strap (tie cells), the head index of this tile'}),
    # v1.1: the three native TP8 control leaves A / B / C behind the wires-only qkd_ectl3_s, ck[0..2] = die ck_a / ck_b / ck_c
    # v1.2: the DIRECT-seam parent (Codex 5f3e5767f / 00f42ca01: no B feed-through flops; C launches straight to A over B;
    # exact 3,705 / 4,137 PASS, A/B/C mutants FAIL) = the structural fix of the tp3 views' native-audit FAIL; same ports
    qkd_ectl=dict(module='qkd_ectl3_epoch_direct_s', file='rtl/qwen_sys/split_20261014/qkd_ectl3_epoch_direct_s.sv',
                  ports=dict(si=['si'], so=['so'], t0=['t0'], t1=['t1'], e0=['e0'], e1=['e1'], e2=['e2'], e3=['e3'],
                             s0=['s0'], s1=['s1'], s2=['s2'], s3=['s3'], rq=['rq'], rs=['rs'], ck_a=['ck'], rst_n=['rst_n']),
                  sliced=dict(ck_b='ck_a', ck_c='ck_a'),
                  classed={'cfg': 'by_design: die-top strap {engine 3, stack 2} (tie cells) per slot'}),
    # v1.1: the write-queue controller is the CLOSED strip-form slot qkd_kvwq_ctl_bin (route qkd_kvwq_ctl_bin-sl3-8a9ae6449,
    # 172.8 x 129.6, pin-registered): f0..f3 are the 293-b encoded group words the die carries (v1 bound the old 298-b die
    # form with 5 lane bits tied = the port-bind MISMATCH)
    qkd_kvwq_ctl_bin=dict(module='qkd_kvwq_ctl_bin', file='rtl/physical/ot_qwen_kv_slot_wrappers.sv',
                          ports=dict(kvn=['kvn_d', 'kvn_cr'], f0=['f0'], f1=['f1'], f2=['f2'], f3=['f3'], r0=['r0'],
                                     r1=['r1'], r2=['r2'], r3=['r3'], fault=['fault'], ck=['ck'], rst_n=['rst_n']),
                          classed={'durable': 'by_design (v1.2): the write-retire word {rw_v, rw_id}, unread on the KV/system '
                                              'die (flow control = the kvn credit; no consumer RTL)'}),
    # v1.1: the write leaf is the CLOSED slot qkd_kvwq_leaf_s_w129_m (route qkd_kvwq_leaf_s_w129_m-sl1-4df79ee4f, view with
    # insertion.json); same bit order as ot_qkvd_kv_wq_leaf's split fields
    qkd_kvwq_leaf_s_w129_m=dict(module='qkd_kvwq_leaf_s_w129_m', file='rtl/qwen_sys/kv_die_20261009/qkd_kvwq_leaf_slot.sv',
                                ports=dict(c=['c'], n=['n'], dn=['dn'], dp=['dp'], w=['w'], wr=['wr'], ck=['ck'],
                                           rst_n=['rst_n'], lane=['lane']), classed={}),
    qkd_seq=dict(module='qkd_seq', file='rtl/physical/ot_qwen_kv_centre_slots.sv', parameters=dict(HEADS=1, Q_FP32=1),
                 ports=dict(lx=['r_x3_d', 'r_sd', 'r_kvd', 't_ar_cr'], lr=['t_ar_d', 't_ds', 't_pw', 'r_x3_cr'],
                            **{f'aq_{q}': [f'aq_{q}'] for q in STACKS}, **{f'kvn_{q}': [f'kvn_{q}_d', f'kvn_{q}_cr'] for q in STACKS},
                            **{f'kc_{q}': [f'kc_{q}'] for q in STACKS}, **{f'af_{q}': [f'af_{q}'] for q in STACKS},
                            **{f'mf_{q}': [f'mf_{q}'] for q in STACKS},
                            ar=['ar'], hf=['hf'], hs=['hs'], hc=['hc'], tk=['tk'], kst=['kst'], ck=['ck'], rst_n=['rst_n']),
                 classed={}),
    qkd_ahub=dict(module='ot_qkd_ahub_die', file='rtl/hdc/nearhbm/ot_qkd_ahub_core.sv',
                  ports=dict(ap_WS=['si_valid', 'si_type', 'si_g', 'si_hh', 'si_k', 'si_any', 'si_data', 'pi_valid',
                                    'pi_g', 'pi_beat', 'pi_data'],
                             am_WS=['am'], ao=['out_valid', 'out_g', 'out_beat', 'out_data'], hs=['start'], hf=['fault'],
                             ck_c=['ck_core'], ck_z0=['ck_zh'], ck_r=['ck_recip'], ck_p0=['ck_pbst'], ck_v0=['ck_pvlg'],
                             rst_n=['rst_n']),
                  sliced=dict(ap_WN='ap_WS', ap_ES='ap_WS', ap_EN='ap_WS', am_WN='am_WS', am_ES='am_WS', am_EN='am_WS',
                              **{f'ck_z{i}': 'ck_z0' for i in range(1, 4)}, **{f'ck_p{i}': 'ck_p0' for i in range(1, 4)},
                              **{f'ck_v{i}': 'ck_v0' for i in range(1, 4)}),
                  classed={'ev': 'debug: hub event word (unread on the die)'}))


# v1.2: the strip frames bind the wires-only compositions of their CLOSED leaves (tools/qwen_kv_die/kv_strips.py ->
# rtl/qwen_sys/split_20261014/qkd_strips_s.sv), each leaf its own clock entry
SPLIT_ONLY_BINDINGS = ('qkd_land', 'qkd_land_n', 'qkd_astk', 'qkd_astk_n', 'qkd_embgw', 'qkd_ctrl', 'qkd_ctrl_n')
SPLIT_PHY = 'qkd_hbm3e_phy_pc'
SPLIT_BINDINGS.update(qkd_ctrl=KS.ctrl_binding(rev=True), qkd_ctrl_n=KS.ctrl_binding())   # v1.3: S stacks = reversed chains (kc at the S = outer end)
SPLIT_BINDINGS.update(qkd_land=KS.land_binding(), qkd_land_n=KS.land_binding(), qkd_astk=KS.astk_binding(),
                      qkd_astk_n=KS.astk_binding())
# v1.2: the embedding gateway binds its CLOSED view's RTL (qkd_embgw sl2): the link words gq / gr and the host words hb / est
# match; emf / emr do NOT (gateway {kind 2, seq 4, data 281, v} 288 + cr / 520 + cr vs the landing engine's 530-b
# {cr, pad 5, tag 11, data 512, v}): an RTL interface defect between two closed views (elements: land_emb 'ifw' re-route
# to the gateway's words, 12:40) -> port bind MISMATCH until one side changes
SPLIT_BINDINGS['qkd_embgw'] = dict(
    module='qkd_embgw', file='rtl/physical/ot_qwen_kv_gwhost_slots.sv',
    ports=dict(gq=['r_ea', 't_ecr'], gr=['t_eq'], hb=['hb', 'hb_cr'], est=['est'], ck=['ck'], rst_n=['rst_n'],
               **{f'emf_{q}': [f'emf_{q}', f'emf_{q}_cr'] for q in STACKS},
               **{f'emr_{q}': [f'emr_{q}', f'emr_{q}_cr'] for q in STACKS}), classed={})


# ---- kvsys v1.4 (2026-10-15, die lead r7): REAL HOST / PLL bindings and the 128 die-placed HOST PC slices ----------------
# The HOST frame qkd_host is replaced by the generated root core qkd_host_root_pt (c460799eb, exact hierarchy move of
# qkd_host_root_integrated) and one qkd_host_pc_slice_die level with every CDC / write-leaf pair, in a 129.6-um slice column
# per side between the landing channel and the landing strip (+ a 21.6-um routing cell: +302.4 um die width).  The PLL frame is the allowed analog
# model qkd_pll_analog_model (no digital reset sequencer: every reset is a root output).  Root inputs without a real die
# producer stay UNCONNECTED (port-bind MISMATCH, never tied): host_bind_census.json, owners named there.
HOST_V14 = dict(on=False)
SLICE_W, SLICE_H = 129.6, 345.6
# one 21.6-um routing cell W of the slice column: the write-queue controller (172.8 in the 216-um landing channel) otherwise
# closes the channel at mid-stack and the N stacks' slot-0 slices have no die route to the root (first v1.4 plan)
SLICE_GAP = 21.6
HOST_RT_FILE = 'rtl/qwen_sys/split_20261014/qkd_host_root_pt.sv'
SLICE_DIE_FILE = 'rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv'
# root clock -> PLL family (FIXTURE = tools/qwen_native_host/host_owner.hpp clocks(); INFERRED = no fixture drives it:
# the HOST owner must confirm, recorded in the v1.4 contract)
HOST_CLK_FAMILY = dict(
    **{c: 'core' for c in ('ck_host', 'ck_csr', 'ck_rst', 'ck_ctl', 'ck_prompt', 'ck_rx', 'ck_tx', 'ck_axi', 'ck_ctrl',
                           'ck_hc', 'ck_phy_rx_r', 'ck_phy_tx_w', 'ck_qm_queue', 'ck_qm_ing_w', 'ck_qm_done_r',
                           'ck_qm_core', 'ck_map', 'ck_sum', 'ck_order', 'ck_fence_core', 'ck_guard', 'ck_native')},
    **{c: 'host' for c in ('ck_qm_host', 'ck_qm_ing_r', 'ck_qm_credit', 'ck_qm_done_w', 'ck_fence_host')},
    **{c: 'ingest' for c in ('ck_qm_ingest', 'ck_qm_out', 'ck_qm_bank0', 'ck_qm_bank1')},
    **{c: 'phy' for c in [f'ck_phy{i}' for i in range(8)] + ['ck_pad', 'ck_phy_rx_w', 'ck_phy_tx_r']})
HOST_CLK_INFERRED = dict(
    **{c: 'core' for c in ('ck_program_rx', 'ck_program_loader', 'ck_dispatch', 'ck_retire', 'ck_bootbarrier',
                           'ck_records', 'ck_coordinator_codec', 'ck_coordinator_lifecycle', 'ck_coordinator_post')},
    **{c: 'host' for c in ('ck_peer', 'ck_root_mux')})     # board-link family (1 GHz = the host period; no board PLL output)
HOST_GROUPS = dict(chain_f='chf', chain_c='chc', chain_a='cha', chain_fault_i='chx', slice_ack='sak',
                   slice_boot_done='sbd', slice_boot_ok='sbo', slice_boot_fault='sbf')


def host_rt_binding():
    import re as _re
    txt = _re.sub(r'//[^\n]*', '', (ROOT / HOST_RT_FILE).read_text())
    hdr = txt[txt.index('module qkd_host_root_pt'):]
    hdr = hdr[hdr.index(')(') + 2:hdr.index(');')]
    names = [_re.findall(r'[A-Za-z_][A-Za-z_0-9]*', part.strip())[-1] for part in hdr.split(',') if part.strip()]
    ports, sliced = {}, {}
    for n in names:
        if n in ('ck_phy', 'ck_qm_bank'):
            k_ = 8 if n == 'ck_phy' else 2
            ports[f'{n}0'] = [n]
            sliced.update({f'{n}{i}': f'{n}0' for i in range(1, k_)})
        elif n in HOST_GROUPS:
            g = HOST_GROUPS[n]
            ports[f'{g}0'] = [n]
            sliced.update({f'{g}{i}': f'{g}0' for i in range(1, 4)})
        elif n in ('phy_up', 'phy_rx_v', 'phy_rx_flit', 'phy_tx_v', 'phy_tx_flit', 'hb', 'hb_cr', 'local_tk', 'local_kst'):
            continue
        else:
            ports[n] = [n]
    ports.update(fdi=['phy_up', 'phy_tx_v', 'phy_tx_flit', 'phy_rx_v', 'phy_rx_flit'], hb=['hb', 'hb_cr'],
                 tk=['local_tk'], kst=['local_kst'])
    return dict(module='qkd_host_root_pt', file=HOST_RT_FILE, ports=ports, sliced=sliced,
                parameters=dict(ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1),
                classed={'die_id': 'by_design: package strap (tie cells), role = 2 PKG + DIE, set at package assembly',
                         'por_n': 'by_design: package POR pad (off-chip signal)'})


def slice_die_binding():
    names = ['ck_station', 'ck_static', 'ck_boot', 'ck_boot_test', 'host_rst_n', 'hbm_rst_n', 'lpc', 'bgi', 'bgo', 'fi',
             'fo', 'ci', 'co', 'ai', 'ao', 'fault_i', 'fault_o', 'land_es', 'land_er', 'ctrl_es', 'ctrl_er',
             'ctrl_completion_v', 'ctrl_completion_we', 'ski', 'sdi', 'soi', 'sfi', 'sko', 'sdo', 'soo', 'sfo']
    return dict(module='qkd_host_pc_slice_die', file=SLICE_DIE_FILE, ports={n: [n] for n in names}, classed={})


def pll_model_binding():
    import kv_host_bindings as KHB
    b = KHB.pll_analog_binding()
    b['classed'] = {'refclk': 'by_design: package reference-clock pad (off-chip signal)',
                    'por_n': 'by_design: package POR pad (off-chip signal)'}
    return b


BINDINGS.update(qkd_host_rt=host_rt_binding(), qkd_hslice=slice_die_binding(), qkd_pllm=pll_model_binding())
RTL.update(qkd_host_rt=HOST_RT_FILE, qkd_hslice=SLICE_DIE_FILE)


# not exact-cut yet (frames sized, RTL partition owed): reported, not strict
FRAME_ONLY = dict(qkd_astk='ot_qwen_nearhbm_attn_stack_d minus its engines (re-cut D: q beat broadcast, node staging, '
                           'P.V levels 4-7; recut.json)',
                  qkd_astk_n='as qkd_astk, N-stack pin plan (hub words on the S face)',
                  qkd_land='qfd_kvc crossbar successor + ot_qkvd_kv_merge (rtl/qwen_sys/kv_die_20261009) + ot_qfd_emb_strip',
                  qkd_embgw='ot_qfd_emb_gw + the gateway link side (r21c hub link FIFOs)',
                  qkd_host='qfd_io_host successor (hing_qfd ingest) + ot_qfd_link_adapter', qkd_pll='vendor PLL + '
                  'ot_qwen_sys_rst_seq', qkd_ctrl='qfd_ctrl (r21c element; pcport KVW 2: KV write side-band from the CDC completion; kc: the stream-command '
                  'word from qkd_seq -> async FIFO -> hclk ot_qkvd_kcmd_tap chain -> the 32 per-PC heads)',
                  qkd_ctrl_n='as qkd_ctrl, N-stack pin plan (kc on the N face)',
                  qkd_ckbump='clock / reset bump pair to the ROM die (pad cell, no logic: by design)')


WQ_FILE = 'rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles.sv'
BINDINGS['qkd_kvwq_leaf'] = dict(module='ot_qkvd_kv_wq_leaf', file=WQ_FILE,
    ports=dict(c=['c_v', 'c_d', 'c_sec', 'c_lane', 'c_tag'], n=['n_v', 'n_d', 'n_sec', 'n_lane', 'n_tag'],
               dn=['dn_v', 'dn_bad'], dp=['dp_v', 'dp_bad'], w=['w_v', 'w_sec', 'w_data', 'w_tag'],
               wr=['w_room', 'wd_v', 'wd_tag'], ck=['clk'], rst_n=['rst_n'], lane=['lane']), classed={})
BINDINGS['qkd_kvwq_ctl'] = dict(module='ot_qkvd_kv_wq_ctl', file=WQ_FILE,
    ports=dict(kvn=['kvw_v', 'kvw_vg', 'kvw_t', 'kvw_layer', 'kvw_d', 'kvw_cr'],
               f0=['f_v', 'f_d', 'f_sec', 'f_lane', 'f_tag'], r0=['r_v', 'r_bad'],
               durable=['rw_v', 'rw_id'], fault=['fault'], ck=['clk'], rst_n=['rst_n']),
    sliced=dict(f1='f0', f2='f0', f3='f0', r1='r0', r2='r0', r3='r0'), classed={})
BINDINGS['qkd_cdc_wleaf'] = dict(module='ot_qwen_stream4_cdc_pc', file='rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv',
    ports=dict(ho=['h_cred', 'h_wv', 'h_wsec', 'h_cv', 'h_csec', 'h_cdata', 'h_ctag', 'h_fault'],
               hi=['h_lv', 'h_lsec', 'h_lrow', 'h_ldata', 'h_hand', 'h_wcon', 'h_av', 'h_atag'],
               co=['l_v', 'l_sec', 'l_row', 'l_data', 'l_pop'], wi=['w_v', 'w_sec', 'w_data', 'w_tag'],
               wr=['w_room', 'wd_v', 'wd_tag'], cf=['c_fault'], clk=['clk'], hclk=['hclk'],
               c_arst_n=['c_arst_n'], h_arst_n=['h_arst_n']), classed={})

BINDINGS['qkd_kvwq_ctl_bin'] = copy.deepcopy(BINDINGS['qkd_kvwq_ctl'])
BINDINGS['qkd_kvwq_ctl_bin'].update(module='ot_qkvd_kv_wq_ctl_binary',
    file='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_ctl_binary.sv', parameters=dict(FLANE_BINARY=1))

BINDINGS['qkd_kvwq_leaf_s'] = copy.deepcopy(BINDINGS['qkd_kvwq_leaf'])
BINDINGS['qkd_kvwq_leaf_s_w129'] = copy.deepcopy(BINDINGS['qkd_kvwq_leaf'])
BINDINGS['qkd_kvwq_ctl_bin_h'] = copy.deepcopy(BINDINGS['qkd_kvwq_ctl_bin'])
BINDINGS['qkd_kvwq_ctl_bin_h']['parameters'] = dict(FLANE_BINARY=1, HEAD_PIPE=1)
BINDINGS['qkd_kvwq_leaf_s_w129_m'] = copy.deepcopy(BINDINGS['qkd_kvwq_leaf_s_w129'])

# el1013-qwen-kvstrips 2026-10-13 (coordinator-accepted slot change): the controller strip qkd_ctrl / qkd_ctrl_n is 32
# die slots of ONE hardened master qkd_ctrl_pc (PC k at strip y = 378 k, pc[4:0] strapped) + one qkd_ctrl_kc leaf at the
# N end (strip y = 12,096); the PHY is re-pinned per PC (po / pi face the leaf).  The masters' ports ARE the die buses;
# STRIP_FIELDS gives each bus's fields LSB first (the benches generate their offsets from it).
STRIP_FILE = 'rtl/qwen_sys/kv_die_20261009/qkd_ctrl_strip.sv'
STRIP_FIELDS = dict(
    qkd_ctrl_pc=dict(
        ci=[('h_cred', 3), ('h_wv', 1), ('h_wsec', 24), ('h_cv', 1), ('h_csec', 24), ('h_cdata', 256), ('h_ctag', 9),
            ('h_fault', 1)],                                                   # = qkd_cdc_wleaf ho
        co=[('h_lv', 1), ('h_lsec', 17), ('h_lrow', 8), ('h_ldata', 256), ('h_hand', 1), ('h_wcon', 1), ('h_av', 1),
            ('h_atag', 9)],                                                    # = qkd_cdc_wleaf hi
        es=[('s_v', 1), ('w_d', 256), ('s_row', 19), ('s_col', 5), ('s_bank', 5), ('s_we', 1), ('w_v', 1)],
        er=[('e_v', 1), ('e_data', 256), ('e_ce', 1), ('e_ue', 1), ('s_credit', 1), ('fault_core', 1)],
        po=[('row_v', 1), ('row_op', 3), ('row_bank', 5), ('row_row', 19), ('col_v', 1), ('col_we', 1),
            ('col_bank', 5), ('col_col', 5), ('wd', 288)],
        pi=[('r_v', 1), ('r_d', 288)], ki=[('k_v', 1), ('k_d', 32)], ko=[('k_v', 1), ('k_d', 32)]),
    qkd_ctrl_kc=dict(kc=[('kc_v', 1), ('kc_d', 32)], ko=[('k_v', 1), ('k_d', 32)]))
assert [f for f, _ in STRIP_FIELDS['qkd_ctrl_pc']['ci']] == BINDINGS['qkd_cdc_wleaf']['ports']['ho']
assert [f for f, _ in STRIP_FIELDS['qkd_ctrl_pc']['co']] == BINDINGS['qkd_cdc_wleaf']['ports']['hi']
BINDINGS['qkd_ctrl_pc'] = dict(module='qkd_ctrl_pc', file=STRIP_FILE,
    ports=dict(ci=['ci'], co=['co'], es=['es'], er=['er'], po=['po'], pi=['pi'], ki=['ki'], ko=['ko'], fi=['fi'],
               fo=['fo'], pc=['pc'], pll_hbm=['pll_hbm'], hrst=['hrst'], ck=['ck'], rsi=['rsi']), classed={})
BINDINGS['qkd_ctrl_kc'] = dict(module='qkd_ctrl_kc', file=STRIP_FILE,
    ports=dict(kc=['kc'], ko=['ko'], fi=['fi'], kf=['kf'], pll_hbm=['pll_hbm'], hrst=['hrst'], ck=['ck'],
               rsi=['rsi']), classed={})

# KV landing strip qkd_land / qkd_land_n -> 32 x qkd_land_pc (E half, one a PC slot) + 8 x qkd_land_grp (W half, one a row
# engine beside its four PCs) + 1 x qkd_land_emb (N end).  Strip slot 4 i + q hosts logical PC {q, G(i)} (LAND_GROUP_ORDER:
# i = 0 at the S end; every group then sits beside its engine's rq / rs pins).
LAND_FILE = 'rtl/qwen_sys/kv_die_20261009/qkd_land_strip.sv'
LAND_GROUP_ORDER = (4, 5, 0, 1, 2, 3, 6, 7)
STRIP_FIELDS.update(
    qkd_land_pc=dict(
        li=[('l_v', 1), ('l_sec', 17), ('l_row', 8), ('l_data', 256)], lp=[('l_pop', 1)],          # = qkd_cdc_wleaf co
        gw=[('v', 1), ('layer', 6), ('j', 10), ('data', 256)],
        es=STRIP_FIELDS['qkd_ctrl_pc']['es'], er=STRIP_FIELDS['qkd_ctrl_pc']['er'],
        dni=[('v', 1), ('kind', 1), ('bc', 1), ('pc', 5), ('side', 1), ('s_we', 1), ('w_v', 1), ('s_bank', 5),
             ('s_col', 5), ('s_row', 19), ('w_d', 256), ('tag', 2)],
        upi=[('v', 1), ('side', 1), ('tag', 2), ('e_data', 256), ('e_ce', 1), ('e_ue', 1)]),
    qkd_land_grp=dict(
        rq=[('req_valid', 1), ('req_v', 1), ('req_g', 1), ('req_t', 13)], rs=[('rsp_valid', 1), ('rsp_data', 1024)],
        lt=[('lay_start', 1), ('lay_T', 14), ('lay_idx', 6)],
        kn=[('kvw_v', 1), ('kvw_vg', 2), ('kvw_t', 14), ('kvw_layer', 6), ('kvw_d', 1024)]),
    qkd_land_emb=dict(emf=[('i_v', 1), ('i_d', 523), ('pad', 5), ('o_cr', 1)], emr=[('o_v', 1), ('o_d', 523), ('pad', 5), ('i_cr', 1)]))
assert [f for f, _ in STRIP_FIELDS['qkd_land_pc']['li']] + ['l_pop'] == BINDINGS['qkd_cdc_wleaf']['ports']['co']
assert [f for f, _ in STRIP_FIELDS['qkd_land_grp']['rq']] == BINDINGS['qkd_ectl']['ports']['rq']
BINDINGS['qkd_land_pc'] = dict(module='qkd_land_pc', file=LAND_FILE,
    ports={k: [k] for k in ('li', 'lp', 'cf', 'gw', 'gc', 'es', 'er', 'dni', 'dno', 'upi', 'upo', 'cri', 'cro', 'fi', 'fo',
                            'lpc', 'ck', 'rst_n')}, classed={})
BINDINGS['qkd_land_grp'] = dict(module='qkd_land_grp', file=LAND_FILE,
    ports={k: [k] for k in ('gw0', 'gw1', 'gw2', 'gw3', 'gc0', 'gc1', 'gc2', 'gc3', 'rq', 'rs', 'lt', 'kn', 'fi', 'fo', 'g',
                            's', 'ck', 'rst_n')}, classed={})
BINDINGS['qkd_land_emb'] = dict(module='qkd_land_emb', file=LAND_FILE,
    ports={k: [k] for k in ('emf', 'emr', 'dno', 'upi', 'cri', 'fi', 'gfi', 'mf', 'st', 'ck', 'rst_n')}, classed={})

# el1013-qwen-kvstrips 2026-10-13: the stack aggregator qkd_astk / qkd_astk_n (ot_qwen_nearhbm_attn_stack_h minus its
# engines) -> two 162 um columns of hardened leaves (ASTK_W 324 requested) (rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv; exact bench
# physical/qkd_astk_strip/bench.sh against the golden aggregator; die wiring = rtl/test/qwen_kv_die/
# ot_qwen_nearhbm_attn_stack_k.sv ot_qkd_astk_strip).  Per row (engines 2 r on the W, 2 r + 1 on the E; rows counted from
# the end away from the hub) and column, bottom to top: head 0 A, B; head 1 A, B; ex, ex, ep, ex, ex; head 2 A, B;
# head 3 A, B (A = level-4 tree cell, B = the row's second-level cell); 4 x qkd_astk_zn + qkd_astk_ctl at the hub end.
ASTK_FILE = 'rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv'
ASTK_LEAF = dict(qkd_astk_pv=(162.0, 103.68), qkd_astk_ex=(162.0, 149.04), qkd_astk_ep=(162.0, 345.6), qkd_astk_zn=(86.4, 86.4),
                 qkd_astk_ctl=(324.0, 43.2))
STRIP_FIELDS.update(
    qkd_astk_pv=dict(
        cfg=[('h', 2), ('lvl', 2), ('am', 2), ('bm', 2), ('ym', 2), ('ath', 3), ('bth', 3), ('far', 1), ('tdir', 1)],
        nc=[('v', 1), ('beat', 4), ('g', 1), ('gam', 4)],                    # = qkd_ectl so[421:412]
        li=[('v', 1), ('idx', 4), ('g', 1), ('d', 128)],                     # stream word (lo, each lane of ui / uo / di / do_)
        pi=[('v', 1), ('beat', 5), ('g', 1), ('d', 256)],                    # P.V lane word
        ci=[('start', 1), ('gmax', 5)]),
    qkd_astk_ep=dict(
        qi=[('start', 1), ('T', 14), ('q_valid', 1), ('q_beat', 6), ('q_data', 512), ('kdone', 2), ('m_v', 1), ('m_g', 1),
            ('m_hh', 2), ('m_data', 32)],
        xi=[('fault', 1), ('cnt0', 4), ('cnt1', 4), ('any', 2), ('lmax', 256)],
        zi=[('v', 1), ('tok', 1), ('g', 1), ('k', 4), ('gam', 4), ('sum', 128), ('row', 512)],
        ri=[('v', 1), ('g', 1), ('k', 4), ('gam', 4), ('row', 512)],
        xa=[('v', 1), ('pos', 1), ('s', 32), ('m', 32)] * 4, xe=[('v', 1), ('fault', 1), ('e', 32)] * 4,
        sq=[('engine', 3), ('stack', 2)]),
    qkd_astk_zn=dict(zi=[('v', 1), ('g', 1), ('k', 4), ('slot', 4), ('sum', 128)], zc=[('stack', 2), ('level', 2)],
                     tc=[('start', 1), ('T', 14)]),
    qkd_astk_ctl=dict(
        aq=[('start', 1), ('T', 14), ('layer', 6), ('q_valid', 1), ('q_beat', 6), ('q_data', 512)],
        lt=[('start', 1), ('T', 14), ('layer', 6)], am=[('v', 1), ('g', 1), ('hh', 2), ('data', 32)],
        ap=[('so_valid', 1), ('so_type', 2), ('so_g', 1), ('so_hh', 2), ('so_k', 4), ('so_any', 1), ('so_data', 32),
            ('pv_done', 2), ('pv_valid', 1), ('pv_g', 1), ('pv_beat', 6), ('pv_data', 512)]))
STRIP_FIELDS['qkd_astk_ep']['zo'] = STRIP_FIELDS['qkd_astk_ep']['zi']
STRIP_FIELDS['qkd_astk_ep']['xo'] = STRIP_FIELDS['qkd_astk_ep']['xi']
STRIP_FIELDS['qkd_astk_ctl']['qo'] = STRIP_FIELDS['qkd_astk_ep']['qi']
STRIP_FIELDS['qkd_astk_ctl']['xi'] = STRIP_FIELDS['qkd_astk_ep']['xi']
_ASTK_LANES = ('ui', 'uo', 'di', 'do_', 'pi', 'po', 'ci', 'co', 'kui', 'kuo', 'kdi', 'kdo', 'tui', 'tuo', 'tdi', 'tdo', 'fi', 'fo')
BINDINGS['qkd_astk_pv'] = dict(module='qkd_astk_pv', file=ASTK_FILE,
    ports={k: [k] for k in ('cfg', 'wa', 'wb', 'nc', 'nd', 'nco', 'ndo', 'cra', 'crb', 'li', 'lo', 'lci', 'lco', 'ck', 'rst_n')
           + _ASTK_LANES}, classed={})
BINDINGS['qkd_astk_ex'] = dict(module='qkd_astk_ex', file=ASTK_FILE,
    ports={k: [k] for k in ('xa', 'xe', 'ck', 'rst_n') + _ASTK_LANES}, classed={})
BINDINGS['qkd_astk_ep'] = dict(module='qkd_astk_ep', file=ASTK_FILE,
    ports={k: [k] for k in ('sq', 'so', 'si', 'qi', 'xi', 'xo', 'zi', 'zo', 'ri', 'xa', 'xe', 'cr', 'ck', 'rst_n') + _ASTK_LANES},
    classed={})
BINDINGS['qkd_astk_zn'] = dict(module='qkd_astk_zn', file=ASTK_FILE,
    ports={k: [k] for k in ('zc', 'tc', 'zi', 'zo', 'fi', 'fo', 'ck', 'rst_n')}, classed={})
BINDINGS['qkd_astk_ctl'] = dict(module='qkd_astk_ctl', file=ASTK_FILE,
    ports={k: [k] for k in ('st', 'aq', 'lt', 'am', 'ap', 'af', 'qo', 'xi', 'co', 'px', 'py', 'zi', 'fx', 'fy', 'fz', 'ck', 'rst_n')},
    classed={})
assert sum(w for _, w in STRIP_FIELDS['qkd_astk_ep']['qi']) == 572 and sum(w for _, w in STRIP_FIELDS['qkd_astk_ep']['zi']) == 651
assert sum(w for _, w in STRIP_FIELDS['qkd_astk_ctl']['ap']) == 565 and sum(w for _, w in STRIP_FIELDS['qkd_astk_ctl']['aq']) == 540
assert [f for f, _ in STRIP_FIELDS['qkd_astk_pv']['nc']] == ['v', 'beat', 'g', 'gam']


def astk_cfg(h, lvl=0, am=0, bm=0, ym=0, ath=0, bth=0, far=0, tdir=0):
    """qkd_astk_pv strap word (STRIP_FIELDS order, LSB first)."""
    return h | lvl << 2 | am << 4 | bm << 6 | ym << 8 | ath << 10 | bth << 13 | far << 16 | tdir << 17


def astk_plan(stack=0):
    """The strip's leaf instances in its own frame (y from the end away from the hub; N stacks: the strip is placed MX).
    Rows of (name, master, column, y, straps).  Column x = 0 (W, X cells: kk mod 4 < 2) / 162 (E, Y cells)."""
    out = []
    ph, eh, xh = ASTK_LEAF['qkd_astk_pv'][1], ASTK_LEAF['qkd_astk_ep'][1], ASTK_LEAF['qkd_astk_ex'][1]
    row_h = ENG_H + GY                       # an engine row
    used = 8 * ph + eh + 4 * xh
    assert used <= row_h, (used, row_h)
    gap = (row_h - used) / 12                # the die's relay stations stand in the gaps
    for r in range(4):
        for c in range(2):
            y = r * row_h + gap / 2
            eng = 2 * r + c

            def put(name, master, straps):
                nonlocal y
                out.append((name, master, c, round(y, 3), straps))
                y += ASTK_LEAF[master][1] + gap
            lvl_b, am_b, bm_b, ym_b = ((1, 0, 2, 1), (2, 1, 2, 1), (1, 0, 2, 2), (3, 1, 0, 0))[r]
            ath_b, bth_b = ((0, 2), (0, 4), (4, 6), (0, 0))[r]
            for hp in range(4):
                if hp == 2:
                    put(f'ex_{eng}_0', 'qkd_astk_ex', {}); put(f'ex_{eng}_1', 'qkd_astk_ex', {})
                    put(f'ep_{eng}', 'qkd_astk_ep', dict(sq=stack << 3 | eng))
                    put(f'ex_{eng}_2', 'qkd_astk_ex', {}); put(f'ex_{eng}_3', 'qkd_astk_ex', {})
                put(f'pva_{r}_{hp}_{"xy"[c]}', 'qkd_astk_pv',
                    dict(cfg=astk_cfg(hp, ym=2 if r in (1, 3) else 0, ath=2 * r, bth=2 * r + 1, far=int(hp in (0, 3)))))
                put(f'pvb_{r}_{hp}_{"xy"[c]}', 'qkd_astk_pv', dict(cfg=astk_cfg(hp, lvl_b, am_b, bm_b, ym_b, ath_b, bth_b)))
    top = 4 * row_h                          # the hub end: 237.6 um beyond the four engine rows (slot change request)
    zh = ASTK_LEAF['qkd_astk_zn'][1]
    for z in range(4):
        out.append((f'zn_{z}', 'qkd_astk_zn', z % 2, round(top + zh * (z // 2), 3), dict(zc=z << 2 | stack)))
    out.append(('ctl', 'qkd_astk_ctl', 0, round(top + 2 * zh, 3), dict(st=stack)))
    return out



def _write_tiles(m, add):
    """Opt-in candidate.  Closed ctl/leaf tiles; the explicit OR encoder remains unclosed.

    Preserve the 129.6-um attention-side relay channel.  A separate control/relay
    strip beside the leaves avoids cutting the landing placeholder; its width
    is the first tested width at which this generator routes every candidate bus.
    """
    by = {i.name: i for i in m['insts']}
    for st in STACKS:
        side = st[0]
        for pc in range(32):
            cdc = by[f'cdc_{st}_{pc}']
            cdc.master = 'qkd_cdc_wleaf'
            if m['geo'].get('kv_wq_leaf_s'):
                # The actual CDC LEF is183.72 square, not the old183.048 frame.
                # Shift the column88.56um to fit the lowest leaf inside the die.
                if side == 'E':
                    cdc.x -= 183.72-cdc.w # grow inward, preserve controller-side gap
                if m['geo'].get('split'):
                    # kvs1 real case: the bound qkd_cdc_wleaf view (183.6, its own pin residues) snapped 0.216 um toward the
                    # controller strip, which then snapped onto the PHY: keep 2.16 um of slack on the controller side
                    cdc.x += 2.16 if side == 'W' else -2.16
                cdc.w = cdc.h = 183.72
                cdc.y += 88.56
                lw = 129.6 if m['geo'].get('kv_wq_wide') else 86.4
                x = up(cdc.x + (cdc.w-lw)/2, GX)
                y = cdc.y - 183.6 - GY
                add(f'wleaf_{st}_{pc}', 'qkd_kvwq_leaf_s_w129_m' if m['geo'].get('kv_wq_mirror') else 'qkd_kvwq_leaf_s_w129' if m['geo'].get('kv_wq_wide') else 'qkd_kvwq_leaf_s', x, y, lw, 183.6,
                    'MX' if side == 'W' else 'R180', 'kv_write_leaf', 'strip')
            else:
                x = m['geo']['x_land'] if side == 'W' else m['die']['w'] - m['geo']['x_land'] - 86.4
                add(f'wleaf_{st}_{pc}', 'qkd_kvwq_leaf', x, cdc.y, 86.4-SHAVE, 183.6-SHAVE,
                    'R0' if side == 'W' else 'MY', 'kv_write_leaf', 'strip')
        land = by[f'land_{st}']
        offset = CHAN if m['geo'].get('kv_wq_leaf_s') else 86.4 + GX
        cw, ch = (216.0,648.0) if m['geo'].get('kv_wq_head') else ((172.8, 129.6) if m['geo'].get('split') else (172.8,518.4))
        cm = 'qkd_kvwq_ctl_bin_h' if m['geo'].get('kv_wq_head') else ('qkd_kvwq_ctl_bin' if m['geo'].get('kv_wq_binary') else 'qkd_kvwq_ctl')
        if m['geo'].get('split'):
            offset = 2.4 + 21.6                    # v1.2: in the CDC | landing channel (centred, 21.6 um each side)
        x = m['geo']['x_land'] + offset if side == 'W' else m['die']['w'] - m['geo']['x_land'] - offset - cw
        y = up(land.y + (land.h - ch)/2, GY)
        add(f'wctl_{st}', cm, x, y, cw-SHAVE, ch-SHAVE,
            'R0' if side == 'W' else 'MY', 'kv_write_ctl', 'strip')
        for g in range(0 if m['geo'].get('kv_wq_binary') else 4):
            ex = x if side == 'W' else x + 172.8 - 43.2
            add(f'wenc_{st}_{g}', 'qkd_kvwq_lane_encoder', ex, y - (g+1)*45.36, 43.2-SHAVE, 43.2-SHAVE,
                'R0' if side == 'W' else 'MY', 'kv_write_encoder_unclosed', 'strip')


def _write_buses(m):
    """Split ci[301:0]: write[289:0], room/done[300:290], fault[301].

    co[282:0], including l_pop, stays with the landing.  Four independent
    registered chains a stack visit PCs 8*g+7 .. 8*g N->S; lane straps pc%8.
    The feed encoder implements the exact three OR4 equations of leaves_top.
    """
    buses = []
    for bid, cl, bits, eps in m['buses']:
        if bid.startswith('cdci_'):
            st, pc = bid[5:].rsplit('_', 1)
            buses.extend([(f'ww_{st}_{pc}', 'cdc_core', 290, [(f'wleaf_{st}_{pc}', 'w'), (f'cdc_{st}_{pc}', 'wi')]),
                          (f'wr_{st}_{pc}', 'cdc_core', 11, [(f'cdc_{st}_{pc}', 'wr'), (f'wleaf_{st}_{pc}', 'wr')]),
                          (f'wcf_{st}_{pc}', 'cdc_core', 1, [(f'cdc_{st}_{pc}', 'cf'), (f'land_{st}', f'cf{pc}')])])
                          # v1.2: the landing strip abuts the CDC column again (kvs2 T1b's 620-um cf hop is gone)
        elif bid.startswith('kvn_'):
            st = bid[4:]
            if m['geo'].get('split'):
                # v1.2: the KV write words enter the landing strip (its 8 groups' KV merge fence needs them: kn) and leave
                # it registered on kvo to the write-queue controller (+1 cycle a way on the posted-write path)
                buses.append((bid, cl, bits, [('seq', f'kvn_{st}'), (f'land_{st}', 'kvn')]))
                buses.append((f'kvo_{st}', cl, bits, [(f'land_{st}', 'kvo'), (f'wctl_{st}', 'kvn')]))
            else:
                buses.append((bid, cl, bits, [('seq', f'kvn_{st}'), (f'wctl_{st}', 'kvn')]))
        else:
            buses.append((bid, cl, bits, eps))
    m['buses'] = buses
    m['wq_straps'] = {}
    for st in STACKS:
        ctl = f'wctl_{st}'
        # v1.2 (split): the write-retire word durable has no consumer on the KV/system die (the landing strip's RTL has
        # no such port; the sequencer's kvn credit carries the flow control): unread, not wired to a frame
        if not m['geo'].get('split'):
            buses.append((f'wdurable_{st}', 'spine_local', 23, [(ctl, 'durable'), (f'land_{st}', 'wdurable')]))
        buses.append((f'wfault_{st}', 'spine_local', 1, [(ctl, 'fault'), (f'land_{st}', 'wfault')]))
        for g in range(4):
            enc = f'wenc_{st}_{g}'
            order = range(8) if m['geo'].get('kv_wq_leaf_s') else range(7, -1, -1)
            chain = [f'wleaf_{st}_{8*g+i}' for i in order]
            if m['geo'].get('kv_wq_binary'):
                buses.append((f'wencoded_{st}_{g}', 'spine_local', 293, [(ctl, f'f{g}'), (chain[0], 'c')]))
            else:
                buses += [(f'wfeed_{st}_{g}', 'spine_local', 298, [(ctl, f'f{g}'), (enc, 'a')]),
                          (f'wencoded_{st}_{g}', 'spine_local', 293, [(enc, 'b'), (chain[0], 'c')])]
            buses.append((f'wret_{st}_{g}', 'spine_local', 2, [(chain[0], 'dp'), (ctl, f'r{g}')]))
            for a, b in zip(chain, chain[1:]):
                buses += [(f'wchain_{a}', 'spine_local', 293, [(a, 'n'), (b, 'c')]),
                          (f'wback_{a}', 'spine_local', 2, [(b, 'dp'), (a, 'dn')])]
            buses.append((f'wtail_{st}_{g}', 'constant', 2, [(chain[-1], 'dn')]))
            for pc in range(8*g, 8*g+8):
                leaf = f'wleaf_{st}_{pc}'
                m['wq_straps'][f'wlane_{st}_{pc}'] = pc % 8
                buses.append((f'wlane_{st}_{pc}', 'constant', 3, [(leaf, 'lane')]))
        # qwen-1010/b 2026-10-10: the leaves and the controller join the stack's own core clock trunk and reset (one net
        # per PLL output; a second net on pll_<st> / rso_<st> was a duplicate port binding in die_top_lint)
        for bname, dstport in ((f'clk_core_{st}', 'ck'), (f'rst_core_{st}', 'rst_n')):
            k_ = next(i for i, b in enumerate(buses) if b[0] == bname)
            bid_, cl_, bits_, eps_ = buses[k_]
            buses[k_] = (bid_, cl_, bits_, list(eps_) + [(f'wleaf_{st}_{pc}', dstport) for pc in range(32)] + [(ctl, dstport)])


def strict_ports(M):
    """every RTL port of every bound master is in exactly one die port (or classed debug / by_design) and every die
    port of the master is bound.  -> dict(ok, failures, rows)."""
    import re as _re
    rows, fails = [], []
    for mst, b in BINDINGS.items():
        if mst not in M:
            continue
        # v1.1: the port-bind tool's header parser (a declaration may list several ports: 'output wire [15:0] e0, e1')
        import die_port_bind_kv as _PB
        _, hdr = _PB.header((ROOT / b['file']).read_text(), b['module'])
        rtl = set(hdr)
        bound = {}
        for dp, ps in b['ports'].items():
            for p in ps:
                bound.setdefault(p, []).append(dp)
        die = set(M[mst].order) if mst in M else set()
        for p in sorted(rtl):
            if p in bound or p in b.get('classed', {}):
                continue
            fails.append(f'{mst}: RTL port {p} has no die port')
        for p in sorted(set(bound) - rtl):
            fails.append(f'{mst}: binding names {p}, not an RTL port of {b["module"]}')
        for dp in sorted(die):
            if dp not in b['ports'] and dp not in b.get('sliced', {}):
                fails.append(f'{mst}: die port {dp} not bound to RTL')
        for dp in sorted(set(b['ports']) - die):
            fails.append(f'{mst}: bound die port {dp} absent from the abstract (no die net)')
        rows.append(dict(master=mst, module=b['module'], rtl_ports=len(rtl), die_ports=len(die),
                         classed=b.get('classed', {})))
    return dict(ok=not fails, failures=fails, rows=rows, frame_only=FRAME_ONLY)


def tpl():
    return json.loads(TPL_PATH.read_text())


def _band(T, side, Wk):
    """r21c band instances of one side, re-placed: (name, master, x, y, w, h, orient, kind, domain)."""
    I = T['insts']
    out = []
    ctrl_s, ctrl_n = I[f'ctrl_{side}S'], I[f'ctrl_{side}N']
    dy = {'S': MARGIN - ctrl_s['y'], 'N': MARGIN + ctrl_s['h'] + GY - ctrl_n['y']}
    xs = 25815.456 - Wk                                  # the r21c die width; the E band keeps its distance to E
    for n, d in I.items():
        if not (n.split('_')[1][0] == side and len(n.split('_')[1]) == 2 or n.split('_')[1] == side + 'S'
                or n.split('_')[1] == side + 'N'):
            continue
        half = n.split('_')[1][1]
        if d['kind'] == 'link_fifo':
            continue
        x = d['x'] if side == 'W' else d['x'] - xs
        master = dict(qfd_ctrl='qkd_ctrl_n' if half == 'N' else 'qkd_ctrl', qfd_cdc='qkd_cdc').get(d['master'], d['master'])
        out.append((n, master, x, d['y'] + dy[half], d['w'], d['h'], d['orient'], d['kind'], d['domain']))
    return out, dy


_PIN_HINT = {}


def build(r=R, kv_wq_leaves=False, kv_wq_binary=False, kv_wq_leaf_s=False, kv_wq_head=False, kv_wq_wide=False, kv_wq_mirror=False, split=False, reserve_static_memory=False, reserve_native_astk=False, host_v14=None):
    """qwen-1010/b 2026-10-10: two passes -- the second plans every relay chain from the pins the first pass drew (a
    shared master's pin is the one its first instance's peers set), so each hop is measured pin to pin on the die."""
    kw = dict(r=r, kv_wq_leaves=kv_wq_leaves, kv_wq_binary=kv_wq_binary, kv_wq_leaf_s=kv_wq_leaf_s, kv_wq_head=kv_wq_head,
              kv_wq_wide=kv_wq_wide, kv_wq_mirror=kv_wq_mirror, split=split)
    if host_v14 is not None:
        HOST_V14['on'] = bool(host_v14)          # v1.4 (die_top_lint --variant ...,host_v14); None keeps the CLI setting
    _set_geometry(split, reserve_static_memory=reserve_static_memory, reserve_native_astk=reserve_native_astk)
    _PIN_HINT.clear()
    m = _build(**kw)
    best = None
    for _ in range(3):                      # re-plan from the drawn pins; keep the pass with the fewest pin-hop violations
        M = masters(m, 1)
        nv = pin_reach(m, M)['violations']
        if best is None or nv < best[0]:
            best = (nv, m)
        if nv == 0:
            break
        by = {i.name: i for i in m['insts']}
        _PIN_HINT.clear()
        for bid, cl, bits, eps in m['buses']:
            for inst, port in eps:
                it_ = by[inst]
                if not it_.master.startswith('qkd_rly') and it_.master in M and port.lstrip('*') in M[it_.master].ports:
                    try:
                        _PIN_HINT[(inst, port.lstrip('*'))] = pin_xy(it_, M[it_.master], port.lstrip('*'))
                    except (TypeError, KeyError):
                        pass
        try:
            m = _build(**kw)
        except ValueError as e_:
            # v1.1: a pin-hinted re-plan pass can corner a relay chain (af_WN at the astk top, head 492.48): keep the best
            # earlier pass (its drawn pins and relay chains are consistent) and record why the re-plan stopped
            best[1].setdefault('geo', {})['replan_stopped'] = str(e_)
            break
    else:
        M = masters(m, 1)
        nv = pin_reach(m, M)['violations']
        if nv < best[0]:
            best = (nv, m)
    _PIN_HINT.clear()
    if split and best[0]:
        import kv_pin_repair
        repaired = kv_pin_repair.repair(sys.modules[__name__], best[1])
        failures = pin_reach(repaired, masters(repaired, 1))
        if failures['violations']:
            raise ValueError(f"split KV die has {failures['violations']} unrepaired pin hops: {failures['worst'][:3]}")
        return repaired
    return best[1]


def _build(r=R, kv_wq_leaves=False, kv_wq_binary=False, kv_wq_leaf_s=False, kv_wq_head=False, kv_wq_wide=False, kv_wq_mirror=False, split=False):
    kv_wq_wide = kv_wq_wide or kv_wq_mirror
    kv_wq_leaf_s = kv_wq_leaf_s or kv_wq_head or kv_wq_wide
    kv_wq_binary = kv_wq_binary or kv_wq_leaf_s
    kv_wq_leaves = kv_wq_leaves or kv_wq_binary
    T = tpl()
    I = T['insts']
    stack_h = I['ctrl_WS']['h']
    edge_chan = CHAN if kv_wq_leaf_s else 0.0
    # split: the engine group (4 engine columns of 4 heads + ectl) is taller than the 12.1-mm band: stack pitch sp, the band
    # centred on it (band_shift per half)
    gh_ = 4 * RENG[1] + 3 * GY
    # 2 x CHAN of relay channel above and below each group: the S | N groups leave a 518-um channel between them (the
    # col-1 engines' KV rows krq / krs and the centre words cross the W / E stack walls there)
    # every shift is a multiple of 43.2 um (= 900 / 675 / 540 tracks of M4-5 / M6-7 / M8-9 and 160 rows): a shifted band
    # keeps the legal origin residues of its hard macros (kvs1 real case: phy_WN MY had no legal origin at a GY shift)
    LAT = 43.2
    sp = (stack_h + up(max(0.0, gh_ + 4 * CHAN - stack_h), LAT)) if split else stack_h
    band_shift = {'S': up((sp - stack_h) / 2, LAT), 'N': up((sp - stack_h) / 2, LAT) + (sp - stack_h)}
    # split: the S engine groups reach down to the die edge, where the host SerDes PHY (2,400 wide, wider than the centre
    # column) sits: lift everything above it by d0
    d0 = up(max(0.0, SERDES[2] + GY + 2 * CHAN - (edge_chan + (sp - gh_) / 2)), LAT) if split else 0.0
    band_shift = {k: v + d0 for k, v in band_shift.items()}
    Hk = up(2 * (MARGIN+edge_chan) + 2 * sp + GY + d0, GY)
    # x layout (W half; E mirrors)
    x_land = I['cdc_WS_0']['x'] + I['cdc_WS_0']['w'] + GX
    leaf_shift = ((518.4 if kv_wq_head else 432.0) + GX if kv_wq_leaf_s else 518.4 + GX) if kv_wq_leaves else 0.0
    x_grp = up(x_land + leaf_shift + LAND_W + CHAN, GX)
    slice_w = SLICE_W + SLICE_GAP if (split and HOST_V14['on']) else 0.0     # v1.4: the HOST slice column (CDC column | landing channel)
    x_grp += slice_w
    grp_w = 2 * RENG[0] + ASTK_W + 2 * GX
    centre_w = max(UCIE[1], FRAMES["qkd_ahub"][0]) + 4 * CHAN   # re-cut H engines are 1,953 um: the centre relay channel needs 2 x 259 (was 2 x 130)
    if split:
        centre_w = max(UCIE[1], FRAMES['qkd_ahub'][0], FRAMES['qkd_d2d'][0]) + 4 * CHAN
    Wk = up(2 * (x_grp + grp_w) + centre_w, 2 * GX)
    m = dict(die=dict(w=Wk, h=Hk), insts=[], buses=[], regions=[], geo={})
    ins = m['insts']

    def add(name, master, x, y, w, h, orient='R0', kind='', region='', domain='stream_1p2'):
        it = F.Inst(name, master, round(x, 4), round(y, 4), w, h, orient, kind=kind, region=region, domain=domain)
        ins.append(it)
        return it
    band_dy = {}
    for side in ('W', 'E'):
        rows, dy = _band(T, side, Wk)
        band_dy[side] = {half:offset+edge_chan for half,offset in dy.items()}
        for n, mst, x, y, w, h, o, k, dom in rows:
            half = 'N' if y + h / 2 > MARGIN + stack_h + GY / 2 else 'S'
            add(n, mst, x, y+edge_chan+band_shift[half], w, h, o, k, 'phy' if k == 'phy' else ('ctrl' if k == 'ctrl' else 'strip'), dom)
    if split:
        for it_ in ins:
            if it_.master == 'ot_hbm3e_phy':
                it_.master = SPLIT_PHY     # v1.2: the PHY-only abstract with per-PC DFI words (no controller inside)
    ystack = {'S': MARGIN+edge_chan+band_shift['S'], 'N': MARGIN+edge_chan + stack_h + GY+band_shift['N']}
    xc = Wk / 2
    for st in STACKS:
        side, half = st[0], st[1]
        y0 = ystack[half]
        lx = x_land + leaf_shift if side == 'W' else Wk - x_land - leaf_shift - LAND_W
        if split:
            # v1.2: the landing strip abuts the CDC column (CDC co / cf and the controller strip's es / er are one hop of
            # <= 200 um; kvs2 T1 was a 450-620 um CDC -> landing hop); the write-queue controller moves beyond it
            lx = x_land + slice_w + LAND_CHAN if side == 'W' else Wk - x_land - slice_w - LAND_CHAN - LAND_W
        add(f'land_{st}', 'qkd_land_n' if st[1] == 'N' else 'qkd_land', lx, y0, LAND_W - SHAVE, stack_h - SHAVE, 'MY' if side == 'W' else 'R0',
            'land', 'strip')
        gx = x_grp if side == 'W' else Wk - x_grp - grp_w
        gh = 4 * RENG[1] + 3 * GY
        gy = up(y0 + (stack_h - gh) / 2, GY)
        grp_y = locals().setdefault('grp_y', {})
        grp_y[st] = (gy, gy + gh)
        # qwen-1010/b 2026-10-10 (KV11 die STA: land -> ectl rs hops of ~3 mm between pins): every stack group is the
        # MIRROR of the WS group about the die's vertical axis (E stacks: aggregator MY, engines 0-3 in the column next
        # to the landing on both sides), so a shared master's pin is level with the same peer in every stack; the N
        # stacks' aggregator is its own master qkd_astk_n (hub words ap / am on the S face, toward the hub)
        add(f'astk_{st}', 'qkd_astk_n' if st[1] == 'N' else 'qkd_astk', gx + RENG[0] + GX, gy, ASTK_W - SHAVE,
            gh + (237.6 if ASTK_W > 324 else 0.0) - SHAVE,
            'MY' if side == 'E' else 'R0', 'attn_stack', 'attn')
        for e in range(r):
            col = (e // 4) if side == 'W' else 1 - e // 4      # physical column: 0 = the landing side on the W stacks
            ex = gx if col == 0 else gx + RENG[0] + ASTK_W + 2 * GX
            ey = gy + (e % 4) * (RENG[1] + GY)
            o_up, o_dn = ('R0', 'MX') if col == 0 else ('MY', 'R180')
            # split (kvs1 real case: 'qkd_rhead MX y has no legal origin'): the closed head_hs view has horizontal pins on
            # M4 AND M6, which no y-mirrored origin can put on both track grids -> v1 places every head unflipped in y
            # (R0 / MY); the heads below the control tile then face it with their N (output) face: element-queue item
            # (MY is illegal too: its vertical pins sit on M3 and M5): every split head is R0, so the col-1 heads' nb (E face)
            # faces away from the aggregator
            # v1.1: the native head frame's die-assigned pins are mirror-legal -> the TP4 orientations again
            hd_dn, hd_up = (o_dn, o_up)
            exo = up((HEAD[0] - ECTL[0]) / 2, GX) if split else 0.0     # control tile centred in the wider column
            for h in range(4):
                add(f'head_{st}_{e}_{h}', 'qkd_rhead', ex, ey + TILE_Y[f'h{h}'], HEAD[0] - SHAVE, HEAD[1] - SHAVE,
                    hd_dn if h < 2 else hd_up, 'row_engine', 'attn')
            add(f'ectl_{st}_{e}', 'qkd_ectl', ex + exo, ey + TILE_Y['c'], ECTL[0] - SHAVE, ECTL[1] - SHAVE,
                o_up, 'row_engine', 'attn')
    # centre column: N edge stack, hub, S edge host
    uy = Hk - MARGIN - UCIE[2]
    add('ucie_rom', UCIE[0], xc - UCIE[1] / 2, uy, UCIE[1] - SHAVE, UCIE[2] - SHAVE, 'MX', 'phy_d2d', 'io')
    dw, dh = FRAMES['qkd_d2d']
    add('d2d_kv', 'qkd_d2d', xc - dw / 2, up(uy - GY - dh, GY), dw - SHAVE, dh - SHAVE, 'R0', 'd2d', 'io')
    sw, sh = FRAMES['qkd_seq']
    sy = up(uy - 2 * GY - dh - sh, GY)
    if split:
        # qkd_lnk abuts the KV end (its rf / tf faces = the KV end's r / t faces); the sequencer below it
        lw_, lh_ = FRAMES['qkd_lnk']
        ly = up(uy - GY - dh, GY) - GY - lh_
        add('lnk', 'qkd_lnk', xc - lw_ / 2, up(ly - GY, GY), lw_ - SHAVE, lh_ - SHAVE, 'R0', 'd2d', 'io')
        sy = up(ly - 2 * GY - sh - 4 * CHAN, GY)
    add('seq', 'qkd_seq', xc - sw / 2, sy, sw - SHAVE, sh - SHAVE, 'R0', 'seq', 'ctl')
    gw_, gh_ = FRAMES['qkd_embgw']
    add('embgw', 'qkd_embgw', xc - gw_ / 2, up(sy - GY - gh_, GY), gw_ - SHAVE, gh_ - SHAVE, 'R0', 'embgw', 'ctl')
    cw_, ch_ = FRAMES['qkd_ckbump']
    add('ckb_kv', 'qkd_ckbump', xc - UCIE[1] / 2 - cw_ - 10 * GX, Hk - MARGIN - ch_, cw_ - SHAVE, ch_ - SHAVE, 'R0', 'bump', 'io')
    pw, ph = FRAMES['qkd_pll']
    add('pll', 'qkd_pllm' if slice_w else 'qkd_pll', xc + UCIE[1] / 2 + GX * 10, Hk - MARGIN - ph, pw - SHAVE, ph - SHAVE, 'R0', 'pll', 'io')
    hw, hh = FRAMES['qkd_ahub']
    add('ahub', 'qkd_ahub', xc - hw / 2, up(Hk / 2 - hh / 2, GY), hw - SHAVE, hh - SHAVE, 'R0', 'attn_hub', 'attn')
    add('serdes_host', SERDES[0], xc - SERDES[1] / 2, MARGIN, SERDES[1] - SHAVE, SERDES[2] - SHAVE, 'R0', 'phy_host',
        'io', 'link_serdes')
    tw, th = FRAMES['qkd_host']
    add('host', 'qkd_host_rt' if slice_w else 'qkd_host', xc - tw / 2, MARGIN + SERDES[2] + GY, tw - SHAVE, th - SHAVE, 'R0', 'host', 'io')
    # v1.2 candidate lanes are OFF by default (kvs2 T2 try: window fine H 1.37 -> 1.25, coarse 1.32 -> 1.17 H but 0.80 -> 1.10 V,
    # lx 1 -> 2 stages, one re-plan reach miss): OT_KV_LANES=1 turns them on for the next revision's work
    m['geo'] = dict(grp_y=grp_y, split=split, land_width_um=LAND_W, static_memory_reservation=LAND_W > 172.8, lanes=bool(split and __import__('os').environ.get('OT_KV_LANES', '2') in ('1', '2')), stack_pitch=sp, band_shift=band_shift, x_land=x_land, x_grp=x_grp, grp_w=grp_w, centre_w=centre_w, stack_h=stack_h, band_dy=band_dy,
                    ystack=ystack, slice_w=slice_w, host_v14=bool(slice_w), r=r, kv_wq_leaves=kv_wq_leaves, kv_wq_binary=kv_wq_binary, kv_wq_leaf_s=kv_wq_leaf_s, leaf_shift=leaf_shift, edge_channel=edge_chan, kv_wq_head=kv_wq_head, kv_wq_wide=kv_wq_wide, kv_wq_mirror=kv_wq_mirror)
    if kv_wq_leaves:
        _write_tiles(m, add)
    if slice_w:
        _host_slices(m, add)
    _buses(m, T, r)
    if kv_wq_leaves:
        _write_buses(m)
    if slice_w:
        _host_v14_buses(m)
    _relays(m)
    m['regions'] = _regions(m)
    m['die']['mm2'] = round(Wk * Hk / 1e6, 3)
    return m


def _buses(m, T, r):
    B = m['buses']
    names = {i.name for i in m['insts']}
    # r21c band buses (dfi, PHY <-> controller <-> CDC, CDC core sides <-> landing, HBM clocks / resets), renamed
    for bid, cl, bits, eps in T['buses']:
        ne = [(('land_' + i.split('_')[1]) if i.startswith('lfifo_') else i, p) for i, p in eps]
        if m['geo'].get('split') and cl == 'phy_dfi':
            continue          # v1.2: per-PC DFI words (below) between the controller strip's leaves and the PHY abstract
        if all(i in names for i, _ in ne):
            B.append((bid, cl, bits, ne))
    add = B.append
    cdcs = {st: [i.name for i in m['insts'] if i.name.startswith(f'cdc_{st}_')] for st in STACKS}
    # clocks (PLL core trunks a stack group + the centre) and resets
    for st in STACKS:
        sp_ = m['geo'].get('split')
        grp = ([(f'land_{st}', c_) for c_ in KS.LAND_CLK] + [(f'astk_{st}', c_) for c_ in KS.ASTK_CLK] if sp_ else
               [(f'land_{st}', 'ck'), (f'astk_{st}', 'ck')]) + \
              [(f'ectl_{st}_{e}', c_) for e in range(r) for c_ in (ECTL_CLK if sp_ else ['ck'])] + \
              [(f'head_{st}_{e}_{h}', c_) for e in range(r) for h in range(4) for c_ in (HEAD_CLK if sp_ else ['ck'])] + \
              [(c, 'clk') for c in cdcs[st]]
        add((f'clk_core_{st}', 'clock_trunk', 1, [('pll', f'pll_{st}')] + grp +
             [(f'ctrl_{st}', 'ck')]))   # qwen-1010/b: the kc stream-command FIFO's write side (reset: rsi, below)
        add((f'rst_core_{st}', 'reset', 1, [('pll', f'rso_{st}'), (f'ctrl_{st}', 'rsi')] +
             [(n, 'rst_n') for n in dict.fromkeys(n for n, _ in grp) if not n.startswith('cdc_')]))   # the CDC core resets come from land.crst (r21c rst_kv)
    cen = ['d2d_kv', 'seq', 'embgw', 'ahub', 'host'] + (['lnk'] if m['geo'].get('split') else [])
    add(('clk_core_c', 'clock_trunk', 1, [('pll', 'pll_c')] +
         [(n, c_) for n in cen for c_ in (AHUB_CLK if (n == 'ahub' and m['geo'].get('split')) else ['ck'])] +
         [('ucie_rom', 'clk'), ('serdes_host', 'clk')]))
    add(('rst_core_c', 'reset', 1, [('pll', 'rso_c')] + [(n, 'rst_n') for n in cen] +
         [('ucie_rom', 'rst_n'), ('serdes_host', 'rst_n')]))
    add(('pll_fwd', 'clock_trunk', 1, [('pll', 'pll_fwd'), ('ckb_kv', 'pll_ck')]))       # to the clock bump pair
    add(('rst_fwd', 'reset', 1, [('pll', 'rso_fwd'), ('ckb_kv', 'rs')]))
    # the link
    add(('d2d_fdi', 'd2d_fdi', FDI_UCIE, [('d2d_kv', 'fdi'), ('ucie_rom', 'fdi')]))
    split = m['geo'].get('split')
    lend = 'lnk' if split else 'seq'
    add(('d2d_dn', 'd2d_face', 4 * (W + 1) + 4, [('d2d_kv', 'rf'), (lend, 'rf')]))       # CTL Q KVN EMBQ + credits back
    add(('d2d_up', 'd2d_face', 3 * (W + 1) + 3, [(lend, 'tf'), ('d2d_kv', 'tf')]))       # RES EMBD HCTL/SCTL + credits back
    if split:
        # LINK.md: the bridge <-> sequencer ROM-side faces (x3 {v, tag 11, d 512}, sd 56, kvd 44, ar credit) and back (ar
        # {v, 519}, ds 187, pw 75, x3 credit)
        add(('lx', 'spine_local', 1 + 11 + 512 + 56 + 44 + 1, [('lnk', 'lx'), ('seq', 'lx')]))
        add(('lr', 'spine_local', 1 + 519 + 187 + 75 + 1, [('seq', 'lr'), ('lnk', 'lr')]))
    # attention
    for st in STACKS:
        add((f'aq_{st}', 'spine_local', 1 + 14 + 6 + 1 + 6 + 512, [('seq', f'aq_{st}'), (f'astk_{st}', 'aq')]))
        add((f'lt_{st}', 'spine_local', 1 + 14 + 6, [(f'astk_{st}', 'lt'), (f'land_{st}', 'lt')]))   # layer start / T / index -> the KV merge fence
        add((f'ap_{st}', 'spine_local', 42 + 521, [(f'astk_{st}', 'ap'), ('ahub', f'ap_{st}')]))
        add((f'am_{st}', 'spine_local', 36, [('ahub', f'am_{st}'), (f'astk_{st}', 'am')]))
        for e in range(r):
            c_ = f'ectl_{st}_{e}'
            add((f'eq_{st}_{e}', 'stack_local', ENG_IN, [(f'astk_{st}', f'e{e}o'), (c_, 'si')]))
            add((f'el_{st}_{e}', 'stack_local', ENG_OUT, [(c_, 'so'), (f'astk_{st}', f'e{e}i')]))
            for pr in range(2):           # S1b copy -> the pair's two heads (one net, two loads)
                add((f'tp_{st}_{e}_{pr}', 'stack_local', T_PAIR, [(c_, f't{pr}')] +
                     [(f'head_{st}_{e}_{h}', 'ti') for h in (2 * pr, 2 * pr + 1)]))
            for h in range(4):
                hd_ = f'head_{st}_{e}_{h}'
                add((f'te_{st}_{e}_{h}', 'stack_local', T_E, [(c_, f'e{h}'), (hd_, 'e')]))
                add((f'ts_{st}_{e}_{h}', 'stack_local', T_RET, [(hd_, 's'), (c_, f's{h}')]))
                add((f'nb_{st}_{e}_{h}', 'stack_local', HEAD_NB, [(hd_, 'nb'), (f'astk_{st}', f'f{e}{h}')]))
            add((f'krq_{st}_{e}', 'spine_local', KS.W_RQ if split else 16, [(c_, 'rq'), (f'land_{st}', f'rq{e}')]))
            add((f'krs_{st}_{e}', 'spine_local', 1 + 1024, [(f'land_{st}', f'rs{e}'), (c_, 'rs')]))
        add((f'kvn_{st}', 'kvn', 1024 + 2 + 14 + 6 + 1 + 1, [('seq', f'kvn_{st}'), (f'land_{st}', 'kvn')]))
        # qwen-1010/b 2026-10-11: stream-command net -- the descriptor issuer in qkd_seq (ot_qkvd_kv_desc, KDESC 1) posts
        # DESC / GO words ~320 hclk ahead of each layer's go; one registered copy per stack runs on relays (core clock) to
        # the stack's controller element, whose W-face kc port enters the async FIFO and the hclk tap chain to the 32
        # per-PC heads (ot_qkvd_kcmd_tap).  No ready: the issuer bounds its outstanding layers.
        add((f'kc_{st}', 'kv_oneway', 1 + 32, [('seq', f'kc_{st}'), (f'ctrl_{st}', 'kc')]))
        add((f'emf_{st}', 'kvn', KS.W_EMF if split else W + 2, [('embgw', f'emf_{st}'), (f'land_{st}', 'emf')]))
        add((f'emr_{st}', 'kvn', KS.W_EMR if split else W + 2, [(f'land_{st}', 'emr'), ('embgw', f'emr_{st}')]))
        if not m['geo'].get('split'):
            add((f'ing_{st}', 'kvn', W + 2, [('host', f'ing_{st}'), (f'land_{st}', 'ing')]))
        else:
            # v1.2: the landing strip <-> controller strip words (per PC: the embedding engine's static command es and
            # its return er, across the CDC column = one abutted hop) and the controller strip's fault into the
            # landing's PC fault chain (kvs RTL: tools/qwen_kv_die/kv_strips.py).  'ing' (host -> landing) is gone:
            # no RTL on either side; the host's embedding words reach the gateway on hb (qkd_embgw RTL)
            for k_ in range(32):
                add((f'les_{st}_{k_}', 'stack_local', 288, [(f'land_{st}', f'es{k_}'), (f'ctrl_{st}', f'es{k_}')]))
                add((f'ler_{st}_{k_}', 'stack_local', 261, [(f'ctrl_{st}', f'er{k_}'), (f'land_{st}', f'er{k_}')]))
            # v1.3: S stacks abut at the S ends (kc leaf <-> land pc0); N stacks run the kc leaf's fault (strip N end) to
            # the landing's pc0 (S end) on relays (a fault level: latency is not a protocol term)
            add((f'lkf_{st}', 'stack_local' if st.endswith('S') else 'kv_oneway', 1,
                 [(f'ctrl_{st}', 'kf'), (f'land_{st}', 'kf')]))
    add(('ares', 'spine_local', 1 + 1 + 6 + 512, [('ahub', 'ao'), ('seq', 'ar')]))
    add(('hs', 'spine_local', 1, [('seq', 'hs'), ('ahub', 'hs')]))                  # layer start to the hub
    add(('d2df', 'spine_local', 6, [('d2d_kv', 'flt'), (lend, 'd2df')]))            # link-end fault + cause
    add(('kst', 'spine_local', 10, [('seq', 'kst'), ('host', 'kst')]))               # KV-die status to the host
    if split:
        # v1.2: the host's embedding words to the gateway (qkd_embgw hb 283 + hb_cr back) and its status word est
        add(('hb', 'kvn', 283 + 1, [('host', 'hb'), ('embgw', 'hb')]))
        add(('est', 'spine_local', 13, [('embgw', 'est'), ('host', 'est')]))
        # v1.2: the controller strip is 32 qkd_ctrl_pc + qkd_ctrl_kc (CLOSED leaves): every leaf its own core and HBM
        # clock entry; the HBM clock / reset are driven by the PLL / reset-sequencer frame (r21c's controller element
        # held the HBM PLL: the leaves only take pll_hbm / hrst); the PHY abstract qkd_hbm3e_phy_pc takes each PC's DFI
        # words po / pi (the controller is our RTL, not inside the PHY model)
        for st in STACKS:
            ctl_ = f'ctrl_{st}'
            for i_, (bid_, cl_, bits_, eps_) in enumerate(B):
                if (ctl_, 'ck') in eps_:
                    eps_ = [e for e in eps_ if e != (ctl_, 'ck')] + [(ctl_, c_) for c_ in KS.CTRL_CLK]
                if bid_ == f'clk_hbm_{st}':
                    eps_ = [('pll', f'pll_hbm_{st}')] + [e for e in eps_ if e != (ctl_, 'pll_hbm')] + \
                           [(ctl_, c_) for c_ in KS.CTRL_HCLK]
                if bid_ == f'rst_hbm_{st}':
                    eps_ = [('pll', f'rso_hbm_{st}')] + list(eps_)
                B[i_] = (bid_, cl_, bits_, eps_)
            for k_ in range(32):
                add((f'dpo_{st}_{k_}', 'phy_dfi', KS.W_PO, [(ctl_, f'po{k_}'), (f'phy_{st}', f'po{k_}')]))
                add((f'dpi_{st}_{k_}', 'phy_dfi', KS.W_PI, [(f'phy_{st}', f'pi{k_}'), (ctl_, f'pi{k_}')]))
        # v1.2: the CDC core-side resets come from the stack's core reset tree (the landing strip's leaves have no
        # crst output: r21c's land.crst was a frame port)
        for st in STACKS:
            kk = next(i for i, b in enumerate(B) if b[0] == f'rst_kv_{st}')
            cdc_eps = [e for e in B[kk][3] if e[0].startswith('cdc_')]
            del B[kk]
            kc_ = next(i for i, b in enumerate(B) if b[0] == f'rst_core_{st}')
            B[kc_] = (B[kc_][0], B[kc_][1], B[kc_][2], list(B[kc_][3]) + cdc_eps)
    add(('hf', 'spine_local', 1, [('ahub', 'hf'), ('seq', 'hf')]))                  # hub fault
    for st in STACKS:
        add((f'af_{st}', 'spine_local', 1, [(f'astk_{st}', 'af'), ('seq', f'af_{st}')]))
        add((f'mf_{st}', 'spine_local', 1, [(f'land_{st}', 'mf'), ('seq', f'mf_{st}')]))
    if split:   # EMBQ / EMBD: the SU's embedding face crosses the link and ends on the gateway (LINK.md classes 3 / 5)
        add(('gq', 'kvn', 1 + 1 + 24 + 1, [('lnk', 'gq'), ('embgw', 'gq')]))
        add(('gr', 'kv_oneway', 1 + 512, [('embgw', 'gr'), ('lnk', 'gr')]))
        add(('lflt', 'spine_local', 1, [('lnk', 'flt'), ('host', 'lflt')]))          # link + bridge fault -> host status (LINK.md open item 1)
    else:
        add(('gq', 'kvn', W + 2, [('seq', 'gq'), ('embgw', 'gq')]))
        add(('gr', 'kvn', W + 2, [('embgw', 'gr'), ('seq', 'gr')]))
    add(('hc', 'kv_oneway' if split else 'kvn', 182 if split else W + 2, [('host', 'hc'), ('seq', 'hc')]))
    add(('tk', 'kv_oneway' if split else 'kvn', 93 if split else W + 2, [('seq', 'tk'), ('host', 'tk')]))
    add(('host_fdi', 'd2d_fdi', FDI_SERDES, [('host', 'fdi'), ('serdes_host', 'fdi')]))


def _host_slices(m, add):
    """v1.4: one qkd_host_pc_slice_die per PC in the slice column, level with its CDC / write-leaf pair (W: R0, E: MY)."""
    by = {i.name: i for i in m['insts']}
    Wd, xl = m['die']['w'], m['geo']['x_land']
    # the slice column sits between the landing channel and the landing strip (the channel keeps the write-leaf chain and
    # the write-queue controller): slice -> landing abuts, slice -> controller strip crosses CDC column + channel (~402 um,
    # the v1.3 landing -> controller es / er hop), CDC -> landing words cross 129.6 um more (cdc_core hop ~350 um)
    xw = math.floor(round((xl + LAND_CHAN + SLICE_GAP) / GX, 6)) * GX     # snapped DOWN: never into the landing strip
    for st in STACKS:
        for k in range(32):
            c_, w_ = by[f'cdc_{st}_{k}'], by[f'wleaf_{st}_{k}']
            y0, y1 = min(c_.y, w_.y), max(c_.y + c_.h, w_.y + w_.h)
            y = up(y0 + (y1 - y0 - SLICE_H) / 2, GY)
            x = xw if st[0] == 'W' else Wd - xw - (SLICE_W - SHAVE)
            add(f'hsl_{st}_{k}', 'qkd_hslice', x, y, SLICE_W - SHAVE, SLICE_H - SHAVE, 'R0' if st[0] == 'W' else 'MY',
                'host_slice', 'strip')


def host_lpc(k):
    """logical PC of landing strip slot k (kv_strips: slot 4 i + q hosts lpc 8 q + G(i))"""
    return 8 * (k % 4) + LAND_GROUP_ORDER[k // 4]


def _host_v14_buses(m):
    """v1.4: the HOST root core / slices / PLL-model / reset wiring (see HOST_V14 above).  Root resets replace the frame
    PLL's rso_* outputs (the analog model has none); the landing <-> controller es / er words pass through the slices."""
    B = m['buses']
    names = {i.name for i in m['insts']}
    die_l, hbm_l, link_l = [], [], []
    link_inst = {'ucie_rom', 'serdes_host', 'd2d_kv', 'lnk'}
    keep = []
    for bid, cl, bits, eps in B:
        if bid.startswith(('les_', 'ler_')) or bid == 'lflt':
            continue                                  # re-made through the slices / lnk.flt -> typed transport-fault collector (owed)
        eps = [e for e in eps if not (e[0] == 'host' and e[1] in ('ck', 'rst_n'))]
        if eps and eps[0][0] == 'pll' and eps[0][1].startswith('rso'):
            loads = eps[1:]
            if eps[0][1].startswith('rso_hbm'):
                hbm_l += loads
            else:
                die_l += [e for e in loads if e[0] not in link_inst]
                link_l += [e for e in loads if e[0] in link_inst]
            continue
        if bid.startswith('lkf_'):
            cl = 'kv_oneway'          # the landing moved 151.2 um away: the controller fault level kf rides relays (553 um)
        keep.append((bid, cl, bits, eps))
    B[:] = keep
    add = B.append
    ties = m.setdefault('host_ties', {})
    sl = lambda st, k: f'hsl_{st}_{k}'  # noqa: E731
    slices = [sl(st, k) for st in STACKS for k in range(32)]
    add(('rst_die', 'reset', 1, [('host', 'die_rst_n')] + list(dict.fromkeys(die_l))))
    add(('rst_hbm', 'reset', 1, [('host', 'hbm_rst_n')] + list(dict.fromkeys(hbm_l)) + [(s, 'hbm_rst_n') for s in slices]))
    add(('rst_link', 'reset', 1, [('host', 'link_rst_n')] + list(dict.fromkeys(link_l))))
    add(('rst_host', 'reset', 1, [('host', 'host_rst_n')] + [(s, 'host_rst_n') for s in slices]))
    add(('hboot', 'reset', 1, [('host', 'boot_go')] + [(sl(st, 0), 'bgi') for st in STACKS]))
    add(('pll_lock', 'spine_local', 1, [('pll', 'locked'), ('host', 'pll_locked')]))
    fam = dict(HOST_CLK_FAMILY, **HOST_CLK_INFERRED)
    for i_, (bid, cl, bits, eps) in enumerate(B):
        if bid == 'clk_core_c':
            B[i_] = (bid, cl, bits, eps + [('host', c) for c, f in sorted(fam.items()) if f == 'core'])
        for st in STACKS:
            if bid == f'clk_core_{st}':
                B[i_] = (bid, cl, bits, list(B[i_][3]) + [(sl(st, k), c) for k in range(32)
                                                          for c in ('ck_station', 'ck_static', 'ck_boot', 'ck_boot_test')])
    for f_ in ('host', 'ingest', 'phy'):
        add((f'clk_{f_}', 'clock_trunk', 1, [('pll', f'pll_{f_}')] + [('host', c) for c, f in sorted(fam.items()) if f == f_]))
    for si, st in enumerate(STACKS):
        for k in range(32):
            s = sl(st, k)
            add((f'les_{st}_{k}', 'stack_local', 288, [(f'land_{st}', f'es{k}'), (s, 'land_es')]))
            add((f'hes_{st}_{k}', 'stack_local', 288, [(s, 'ctrl_es'), (f'ctrl_{st}', f'es{k}')]))
            add((f'ler_{st}_{k}', 'stack_local', 261, [(f'ctrl_{st}', f'er{k}'), (s, 'ctrl_er')]))
            add((f'hler_{st}_{k}', 'stack_local', 261, [(s, 'land_er'), (f'land_{st}', f'er{k}')]))
            add((f'hlpc_{st}_{k}', 'constant', 5, [(s, 'lpc')]))
            ties[f'hlpc_{st}_{k}'] = (5, host_lpc(k))
            if k < 31:
                n_ = sl(st, k + 1)
                add((f'hf_{st}_{k}', 'stack_local', 291, [(s, 'fo'), (n_, 'fi')]))
                add((f'hbg_{st}_{k}', 'stack_local', 1, [(s, 'bgo'), (n_, 'bgi')]))
                for o, i in (('co', 'ci'), ('ao', 'ai'), ('fault_o', 'fault_i'), ('sko', 'ski'), ('sdo', 'sdi'),
                             ('soo', 'soi'), ('sfo', 'sfi')):
                    add((f'h{o}_{st}_{k}', 'stack_local', 1 if o == 'fault_o' else 32, [(n_, o), (s, i)]))
            else:
                for i, w_ in (('ci', 32), ('ai', 32), ('fault_i', 1), ('ski', 32), ('sdi', 32), ('soi', 32), ('sfi', 32)):
                    add((f'ht{i}_{st}', 'constant', w_, [(s, i)]))          # chain terminator (source parent assigns 0)
                    ties[f'ht{i}_{st}'] = (w_, 0)
        s0 = sl(st, 0)
        add((f'hchf_{st}', 'kv_oneway', 291, [('host', f'chf{si}'), (s0, 'fi')]))
        for o, rp, w_ in (('co', 'chc', 32), ('ao', 'cha', 32), ('fault_o', 'chx', 1), ('sko', 'sak', 32), ('sdo', 'sbd', 32),
                          ('soo', 'sbo', 32), ('sfo', 'sbf', 32)):
            add((f'h{rp}_{st}', 'kv_oneway', w_, [(s0, o), ('host', f'{rp}{si}')]))


def _centre(it, port=None):
    return it.x + it.w / 2, it.y + it.h / 2


def _relays(m):
    """Registered relay stations every <= RELAY_PITCH on every non-abutted point-to-point bus.  The path is a shortest
    route on a GRID-um grid that avoids every block frame except the two endpoints (BFS from the driver's nearest edge
    point to the load's), so a word between the centre column and a landing column runs through the free rows above /
    below the attention groups and the channels beside them; relays sit on the path at <= RELAY_PITCH (a free spot
    within two grid cells).  Clock / reset trees (CTS / reset tree) and multi-endpoint buses are not relayed."""
    from collections import deque
    by = {i.name: i for i in m['insts']}
    Wd, Hd = m['die']['w'], m['die']['h']
    # The south-face leaf fits inside the CDC-column gap.  A43.2um occupancy
    # cell falsely merges that gap with the adjacent control tile; half-grid
    # routing represents its actual free channels without moving a pin.
    G = GRID/2 if m['geo'].get('kv_wq_leaf_s') else GRID
    nx, ny = int(Wd // G) + 1, int(Hd // G) + 1
    owner = {}
    for it in m['insts']:
        for gx in range(int(it.x // G), int((it.x + it.w) // G) + 1):
            for gy in range(int(it.y // G), int((it.y + it.h) // G) + 1):
                owner.setdefault((gx, gy), set()).add(it.name)
    occ = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]
    rocc = {}
    SP = dict(on=False)        # v1.1: set for a chain's retry: route around cells other chains' relays hold

    def free(x, y, w, h, gap=4.32, bgap=21.6):
        # keep-outs: 4.32 um to other relays, 21.6 um to block frames (the die placer snaps every origin to its
        # master's legal track / row lattice: a 16 k-pin row engine moved 15.1 um, so a relay must not hug a block)
        if x - gap < 0 or y - gap < 0 or x + w + gap > Wd or y + h + gap > Hd:
            return False
        for gx in range(int((x - bgap) // G) - 1, int((x + w + bgap) // G) + 2):
            for gy in range(int((y - bgap) // G) - 1, int((y + h + bgap) // G) + 2):
                for q in rocc.get((gx, gy), ()):
                    if q[0] < x + w + gap and x - gap < q[2] and q[1] < y + h + gap and y - gap < q[3]:
                        return False
                for n in owner.get((gx, gy), ()):
                    it = by[n]
                    if it.x < x + w + bgap and x - bgap < it.x + it.w and it.y < y + h + bgap and y - bgap < it.y + it.h:
                        return False
        return True

    def ring(it):
        """free grid cells touching the frame from outside (where its pins meet the die routing)."""
        x0, y0 = int(it.x // G) - 1, int(it.y // G) - 1
        x1, y1 = int((it.x + it.w) // G) + 1, int((it.y + it.h) // G) + 1
        cells = [(x, y) for x in range(x0, x1 + 1) for y in (y0, y1)] + \
                [(x, y) for y in range(y0 + 1, y1) for x in (x0, x1)]
        return [c for c in cells if 0 <= c[0] < nx and 0 <= c[1] < ny and not owner.get(c)]

    def near_pin(cells, inst, port):
        # qwen-1010/b: with a drawn pin (second pass), the chain leaves / enters at the ring cells nearest that pin
        pt = _PIN_HINT.get((inst, port.lstrip('*')))
        if pt is None or not cells:
            return cells
        dist = lambda c: abs((c[0] + 0.5) * G - pt[0]) + abs((c[1] + 0.5) * G - pt[1])  # noqa: E731
        d0 = min(dist(c) for c in cells)
        return [c for c in cells if dist(c) <= d0 + 2 * G]

    def route(a, b, pa='', pb=''):
        try:
            return route_(a, b, near_pin(ring(by[a]), a, pa), set(near_pin(ring(by[b]), b, pb)))
        except ValueError:
            return route_(a, b, ring(by[a]), set(ring(by[b])))      # pin cells enclosed: any free ring cell

    def route_via(a, b, pa, pb, lane_y):
        """v1.2: an N-half KV-row chain (kvn / krs / krq / kc / emf / emr / ing) runs through its own lane row of the free
        band above the N engine groups instead of every chain hugging the group edge (kvs2 T2: one corridor at the N
        group top, GRT detours, kvn / emf / krs relay hops TT -155 / -108 / -90 ps)"""
        xa = by[a].x + by[a].w / 2
        xb = by[b].x + by[b].w / 2
        wy = int(lane_y // G)
        w_ = None
        for dx_ in range(0, 400):
            for sgn in (1, -1):
                wx = int(((xa + xb) / 2) // G) + sgn * dx_
                if 0 <= wx < nx and 0 <= wy < ny and not owner.get((wx, wy)) and (wx, wy) not in rocc:
                    w_ = (wx, wy)
                    break
            if w_:
                break
        if w_ is None:
            raise ValueError('no lane cell')
        p1 = route_(a, f'lane{lane_y}', near_pin(ring(by[a]), a, pa), {w_})
        p2 = route_(f'lane{lane_y}', b, [w_], set(near_pin(ring(by[b]), b, pb)))
        return p1 + p2[1:]

    def route_(a, b, src, dst):
        if not src or not dst:
            raise ValueError(f'kv die: {a} or {b} has no free cell around it')
        prev = {c: None for c in src}
        dq = deque(src)
        hit = None
        while dq:
            c = dq.popleft()
            if c in dst:
                hit = c
                break
            for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (c[0] + d[0], c[1] + d[1])
                # v1.1 (split): on a chain's retry it does not run through cells another chain's relays already hold, so
                # it leaves the corridor where the relay spots ran out (head 492.48: af_WN / aq_WS at the N group top)
                # v1.2: never along the die-edge cell ring (no relay fits there: kc_ES ran 24 mm up and down the E edge
                # past the PHY to the controller strip's N-end PHY gap once the landing strip closed its old channel)
                if q not in prev and 1 <= q[0] < nx - 1 and 1 <= q[1] < ny - 1 and not owner.get(q) and \
                        not (SP['on'] and q in rocc):
                    prev[q] = c
                    dq.append(q)
        if hit is None:
            raise ValueError(f'kv die: no route {a} -> {b}')
        path, c = [], hit
        while c is not None:
            path.append(((c[0] + 0.5) * G, (c[1] + 0.5) * G))
            c = prev[c]
        return path[::-1]
    nb, stages, lengths = [], {}, {}
    rly_ends = {}                                  # relay inst -> (driver inst, load inst) of the bus it stages
    order_ = list(m['buses'])
    if m['geo'].get('split'):
        # the link bridge <-> sequencer words (lx / lr = the measured link cost's K_ST) take their relay spots first, so
        # other chains' relays never push them from one stage to two
        order_.sort(key=lambda b_: b_[0] not in ('lx', 'lr'))
    for bid, cl, bits, eps in order_:
        if cl in ABUT or cl in ('clock_trunk', 'reset', 'constant') or len(eps) != 2:
            nb.append((bid, cl, bits, eps))
            stages[bid] = 0
            continue
        (a, pa), (b, pb) = eps
        path = None
        lane = _kv_lane(m, bid) if m['geo'].get('lanes') else None
        if lane is not None:
            try:
                path = route_via(a, b, pa, pb, lane)
            except ValueError:
                path = None
        if path is None:
            path = route(a, b, pa, pb)
        L = (len(path) + 1) * G            # + the cell from each frame edge to the ring
        lengths[bid] = round(L, 1)
        span = bits * 0.048 + 4.0
        fw, fh = (52.68, 30.24) if bits <= 512 else (52.68, up(span, GY))
        mst = f'qkd_rly_{bits}'

        def near_d(r0, r1):
            # nearest-point Manhattan distance between two rectangles (x0, y0, x1, y1)
            dx_ = max(0.0, r0[0] - r1[2], r1[0] - r0[2])
            dy_ = max(0.0, r0[1] - r1[3], r1[1] - r0[3])
            return dx_ + dy_
        rect = lambda it: (it.x, it.y, it.x + it.w, it.y + it.h)  # noqa: E731
        # qwen-1010/b 2026-10-10: hops are measured PIN TO PIN (relay in-pin a on its W face, out-pin b on its E face;
        # an engine control tile's rq / rs on its fixed face; any other end = its frame, whose word is drawn level with
        # this peer by _land_level_pins) -- the frame-to-frame measure let 600-700 um pin hops through
        def fixed_pin(inst, port):
            if (inst, port.lstrip('*')) in _PIN_HINT:
                return _PIN_HINT[(inst, port.lstrip('*'))]
            it_ = by[inst]
            if it_.master == 'qkd_ectl' and port.lstrip('*') in ('rq', 'rs'):
                x_ = it_.x + (it_.w if it_.orient in ('MY', 'R180') else 0.0)
                return (x_, it_.y + it_.h / 2)
            return None

        def d_ep(pt, inst, port):
            fp = fixed_pin(inst, port)
            if fp is not None:
                return abs(pt[0] - fp[0]) + abs(pt[1] - fp[1])
            it_ = by[inst]
            return near_d((pt[0], pt[1], pt[0], pt[1]), rect(it_))
        prev_pt, prev_ep, k, idx0 = None, (a, pa), 0, 0
        offs = [(0, 0)] + [(i * G, j * G) for r_ in (range(1,7) if m['geo'].get('kv_wq_leaf_s') else (1,2,3)) for i in range(-r_, r_ + 1) for j in range(-r_, r_ + 1)
                           if max(abs(i), abs(j)) == r_]

        def remaining():
            if prev_pt is None:
                fa, fb = fixed_pin(a, pa), fixed_pin(b, pb)
                if fa is not None:
                    return d_ep(fa, b, pb)
                if fb is not None:
                    return d_ep(fb, a, pa)
                return near_d(rect(by[a]), rect(by[b]))
            return d_ep(prev_pt, b, pb)
        st_ = dict(prev_pt=None, prev_ep=(a, pa), k=0, idx0=0, path=path)
        offs_wide = [(0, 0)] + [(i * G, j * G) for r_ in range(1, 11) for i in range(-r_, r_ + 1) for j in range(-r_, r_ + 1)
                                if max(abs(i), abs(j)) == r_]
        mark = (len(nb), len(m['insts']))
        cells_added = []

        def remaining_():
            if st_['prev_pt'] is None:
                fa, fb = fixed_pin(a, pa), fixed_pin(b, pb)
                if fa is not None:
                    return d_ep(fa, b, pb)
                if fb is not None:
                    return d_ep(fb, a, pa)
                return near_d(rect(by[a]), rect(by[b]))
            return d_ep(st_['prev_pt'], b, pb)

        def reach_():
            # v1.3 (kvs5L TT -17.19: CLOSED ctl_bin launches f<g> late, 413 um to its first relay): a bus whose driver is a
            # closed view with a late launch takes its FIRST relay within FIRST_REACH of that pin; later hops keep PIN_REACH
            if st_['prev_pt'] is None:
                return FIRST_REACH.get(bid.rsplit('_', 2)[0], PIN_REACH)
            return PIN_REACH

        def chain_():
            path_ = st_['path']
            while remaining_() > reach_():
                got = None
                prev_pt_, idx0_ = st_['prev_pt'], st_['idx0']
                rch = reach_()
                # the farthest path point (from the previous chain point) with a free spot within reach
                for idx in range(min(len(path_) - 1, idx0_ + int(rch // G) + 2), idx0_, -1):
                    px, py = path_[idx]
                    for dx_, dy_ in (offs_wide if st_.get('wide') else offs):
                        qx, qy = up(px + dx_ - fw / 2, GX), up(py + dy_ - fh / 2, GY)
                        pin_a = (qx, qy + fh / 2)
                        dd = d_ep(pin_a, a, pa) if prev_pt_ is None else abs(pin_a[0] - prev_pt_[0]) + abs(pin_a[1] - prev_pt_[1])
                        if dd <= rch and free(qx, qy, fw, fh):
                            got = (qx, qy, idx)
                            break
                    if got:
                        break
                if got is None:
                    raise ValueError(f'kv die relays: no spot for {bid} stage {st_["k"]} after path index {idx0_}')
                nm = f'rly_{bid}_{st_["k"]}'
                it = F.Inst(nm, mst, got[0], got[1], fw - SHAVE, fh - SHAVE, 'R0', kind='relay', region='relay')
                m['insts'].append(it)
                rly_ends[nm] = (a, b)
                for gx in range(int(it.x // G), int((it.x + fw) // G) + 1):
                    for gy in range(int(it.y // G), int((it.y + fh) // G) + 1):
                        r_ = (it.x, it.y, it.x + fw, it.y + fh)
                        rocc.setdefault((gx, gy), []).append(r_)
                        cells_added.append(((gx, gy), r_))
                nb.append((f'{bid}__r{st_["k"]}' if st_['k'] else bid, cl, bits, [st_['prev_ep'], (nm, 'a')]))
                st_.update(prev_ep=(nm, 'b'), prev_pt=(it.x + it.w, it.y + it.h / 2), idx0=got[2], k=st_['k'] + 1)

        def rollback_():
            for it_ in m['insts'][mark[1]:]:
                rly_ends.pop(it_.name, None)
            del m['insts'][mark[1]:]
            del nb[mark[0]:]
            for cell, r_ in cells_added:
                rocc[cell].remove(r_)
            cells_added.clear()
            st_.update(prev_pt=None, prev_ep=(a, pa), k=0, idx0=0)
        for attempt in (0, 1):
            try:
                chain_()
                break
            except ValueError:
                if attempt or not m['geo'].get('split'):
                    raise
                # v1.1 (split): the chain ran out of relay spots in a corridor other chains fill: re-route it around
                # every cell those chains' relays hold and place it again
                rollback_()
                st_['wide'] = True        # and look for a relay spot up to 10 grid cells off the path (was 6)
                SP['on'] = True
                try:
                    st_['path'] = route(a, b, pa, pb)
                finally:
                    SP['on'] = False
        n = st_['k']
        stages[bid] = n
        if n == 0:
            nb.append((bid, cl, bits, eps))
            continue
        nb.append((f'{bid}__r{n}', cl, bits, [st_['prev_ep'], (b, pb)]))
    # el1011-q-kvd 2026-10-12 (region-DRT pilot, results/physical/die_region_drt_1012/README.md): a relay is a register
    # stage on the core clock, but its ck was on no bus, so the auto-pin pass never drew it -> qkd_rly_* LEF/odb masters
    # had only a/b, the element lib (pins from the LEF) carried no arcs, and the die STA could not time a single relay hop.
    # Each relay now joins the core clock trunk of the instance that drives its bus (else its load's, else the centre).
    trunk = {}
    for i, (bid_, cl_, _b, eps_) in enumerate(nb):
        if cl_ == 'clock_trunk' and bid_.startswith('clk_core_'):
            for inst_, _p in eps_[1:]:
                trunk.setdefault(inst_, i)
    adds = {}
    for nm_, (drv, rcv) in rly_ends.items():
        i = trunk.get(drv, trunk.get(rcv, next(j for j, e in enumerate(nb) if e[0] == 'clk_core_c')))
        adds.setdefault(i, []).append((nm_, 'ck'))
    for i, extra in adds.items():
        bid_, cl_, bits_, eps_ = nb[i]
        nb[i] = (bid_, cl_, bits_, list(eps_) + extra)
    m['buses'] = nb
    m['relay_stages'] = stages
    m['route_um'] = lengths


_LANES = {}


def _kv_lane(m, bid):
    """v1.2 lane row (y um) of an N-half KV-row chain of the split die, or None.  Lanes start 64.8 um above the N engine
    groups and step 64.8 um up to two channels below the die edge; the chains are dealt round-robin over them.  The S
    half keeps the shortest paths (its chains leave the centre column between the groups); aq / lt / lx / lr too."""
    # v1.2: OT_KV_LANES=2 lanes only the sequencer-centred chains (kvn / kc / emf / emr): kvs3L's krq / krs lanes cost up to
    # +18 / +16 relay stages on the engine <-> landing KV rows (relay_depth_changes.json), which are local words
    import os as _os
    # v1.2 DEFAULT (kvs5L vs kvs5: TT relay->relay 0 violators / +14.8 vs 59 / -66.7, no depth change): '2'; '0' = off
    rx_ = r'(kvn|kc|emf|emr)_(WN|EN)(?:_|$)' if _os.environ.get('OT_KV_LANES', '2') == '2' else \
        r'(kvn|krs|krq|kc|emf|emr|ing)_(WN|EN)(?:_|$)'
    mt = re.match(rx_, bid)
    g = m['geo'].get('grp_y', {})
    if not mt or not g:
        return None
    y0 = max(v[1] for k, v in g.items() if k[1] == 'N') + 64.8
    n = max(1, int((m['die']['h'] - 2 * CHAN - y0) // 64.8))
    key = id(m)
    j = _LANES.get(key, 0)
    _LANES[key] = j + 1
    return y0 + (j % n) * 64.8


def _regions(m):
    regs = []
    for it in m['insts']:
        if it.kind in ('phy', 'ctrl', 'land', 'phy_d2d', 'phy_host'):
            regs.append(dict(name=f'r_{it.name}', kind=it.kind, rect=[it.x, it.y, it.x + it.w, it.y + it.h]))
    return regs


# ------------------------------------------------------------------------------------------------ masters
def masters(m, k=1, port_bits=None):
    T = tpl()
    by = {i.name: i for i in m['insts']}
    used = {}
    for bid, cl, bits, eps in m['buses']:
        for inst, port in eps:
            used.setdefault(by[inst].master, {})[port.lstrip('*')] = max(bits, used.get(by[inst].master, {}).get(port.lstrip('*'), 0))
    if m['geo'].get('kv_wq_binary') and not m['geo'].get('split'):
        # Physical eight-bit lane port survives; only its low3 pins enter the bus.
        for g in range(4):
            used['qkd_kvwq_ctl_bin_h' if m['geo'].get('kv_wq_head') else 'qkd_kvwq_ctl_bin'][f'f{g}'] = 298
    M = {}
    tmap = dict(qkd_ctrl='qfd_ctrl', qkd_ctrl_n='qfd_ctrl', qkd_cdc='qfd_cdc', qkd_land='qfd_kvc', qkd_land_n='qfd_kvc')
    if m['geo'].get('kv_wq_leaves'):
        tmap['qkd_cdc_wleaf'] = 'qfd_cdc'     # ot_hbm3e_phy: the real LEF (k = 1)
    for name, src in tmap.items():
        t = T['masters'][src]
        if name in ('qkd_land', 'qkd_land_n'):
            mm = F.Master(name, LAND_W - SHAVE, m['geo']['stack_h'] - SHAVE, 7, 'KV landing (qfd_kvc successor)')
            land = by['land_WN' if name == 'qkd_land_n' else 'land_WS']
            for p in t['order']:
                if p in used.get(name, {}):
                    sp = list(t['ports'][p])
                    mt = __import__('re').fullmatch(r'c(\d+)([io])', p)
                    if mt and sp[0] == 'face':
                        cdc = by[f'cdc_{land.name[5:]}_{mt.group(1)}']   # this landing's own CDC column
                        sp[4] = cdc.y + cdc.h / 2 - land.y + (40.0 if mt.group(2) == 'i' else -40.0)
                    if sp[0] == 'face' and sp[1] * 0.096 + 4.0 < (mm.w if sp[2] in 'NS' else mm.h):
                        sp[5] = 2          # 2-track pitch where the face has room (emf[221] DRT-0073 at 1 track)
                    mm.ports[p] = tuple(sp)
                    mm.order.append(p)
        else:
            w, h = (183.72,183.72) if name == 'qkd_cdc_wleaf' and m['geo'].get('kv_wq_leaf_s') else (t['w'],t['h'])
            mm = F.Master(name, w, h, t['obs_top'], t['note'])
            for p in (dict.fromkeys(t['order']) if name == 'qkd_cdc_wleaf' else t['order']):
                if m['geo'].get('split') and name in ('qkd_ctrl', 'qkd_ctrl_n') and p not in used.get(name, {}):
                    continue      # v1.2: the strip composition has no r21c 'phy' bundle / 'ck' / 'pll_hbm' frame ports
                if name == 'qkd_cdc_wleaf' and p == 'ci':
                    sp = t['ports'][p]
                    for pn, lo, width in [('wi', 0, 290), ('wr', 290, 11), ('cf', 301, 1)]:
                        part = list(sp)
                        part[1] = width
                        # Pin centres retain the original 302-bit ci order and pitch.
                        part[4] = sp[4] + (lo + (width-1)/2 - (302-1)/2)*0.048*sp[5]
                        mm.ports[pn] = tuple(part)
                        mm.order.append(pn)
                else:
                    mm.ports[p] = tuple(t['ports'][p])
                    mm.order.append(p)
            if name in ('qkd_ctrl', 'qkd_ctrl_n') and 'kc' in used.get(name, {}):
                # the stream-command word enters the controller column's OUTER end (S face on the S stacks, N face on
                # the N stacks = qkd_ctrl_n, the only difference between the two masters): the W face abuts the CDC
                # column, the E face the PHY and the inner end the other band, so the outer edge channel is the one
                # face a relay chain reaches
                mm.ports['kc'] = ('face', 33, 'N' if name == 'qkd_ctrl_n' else 'S', 'M5', round(t['w'] / 2, 4), 1)
                mm.order.append('kc')
        M[name] = mm
    sizes = {i.master: (i.w, i.h) for i in m['insts']}
    for mst, (w, h) in sizes.items():
        if mst == 'ot_hbm3e_phy' and k == 1:
            continue
        if mst in (UCIE[0], SERDES[0]):
            mm = F.Master(mst, w, h, 5, 'licensed PHY abstract (real LEF)')
            for p_, bits_ in sorted(used.get(mst, {}).items()):
                mm.face(p_, bits_, 'N', 'M5', w / 2 if p_ == 'fdi' else 6.0 + 2.0 * len(mm.order), 1)
            M[mst] = mm
            continue
        if mst == SPLIT_PHY:
            # v1.2: HBM3E PHY-only abstract (analog model; its digital layer = qkd_ctrl_pc): outline and M1-M4 blockage of
            # the v2_ew PHY abstract, per-PC DFI words on the controller face (pins: _strip_face_pins)
            M[mst] = F.Master(mst, w, h, 4, 'HBM3E PHY abstract, PHY only: per-PC DFI po (in) / pi (out) on the controller face')
            continue
        if mst not in M:
            M[mst] = F.Master(mst, w, h, 7 if not mst.startswith('qkd_rly') else 3, RTL.get(mst, mst))
    # auto pins: every used port not yet on its master goes to the face nearest its peer, spread along the face
    peer = {}
    for bid, cl, bits, eps in m['buses']:
        if len(eps) == 2:
            for (i0, p0), (i1, p1) in ((eps[0], eps[1]), (eps[1], eps[0])):
                peer.setdefault((by[i0].master, p0.lstrip('*')), []).append(by[i1])
    face_load = {}
    for mst, ports in sorted(used.items()):
        if mst not in M:
            continue
        mm = M[mst]
        inst0 = next(i for i in m['insts'] if i.master == mst)
        for p, bits in sorted(ports.items()):
            if p in mm.ports:
                continue
            if mst == 'qkd_rhead' and p in ('ck', 'rst_n'):
                # the MX head's clock / reset are W-face M4 pins (as its route, cfg qkd_rhead_c): with M8 area pins
                # the mirrored origin needs H = 12 mod 30 nm, which no 2.16-um frame - 0.024 meets (die_kv9: 'site grid
                # never meets the legal residues mod 240'); M4 alone needs H = 0 mod 6 nm (453.576 is)
                mm.face(p, 1, 'W', 'M4', mm.h / 2 + (8.0 if p == 'ck' else -8.0), 1)
                continue
            if mst in ('qkd_kvwq_leaf_s_w129', 'qkd_kvwq_leaf_s_w129_m') and p in ('ck', 'rst_n'):
                # qwen-1010/b 2026-10-11 (die_kv15 real case: 'leaf_s_w129_m MX y: site grid never meets the legal residues
                # mod 240' with M8 area pins): the closed leaf's clock / reset are E-face M4 pins at y 86-97 (its route
                # cfg), so the MX origin only meets the M4 / M5 grids, as the rhead's W-face M4 clock does
                mm.face(p, 1, 'E', 'M4', 88.0 if p == 'ck' else 95.0, 1)
                continue
            if bits == 1 and (p in ('ck', 'clk', 'rst_n', 'rsi', 'c_arst_n', 'rs') or p.startswith(('pll', 'rso'))):
                j = len([q for q in mm.order if mm.ports[q][0] == 'area'])
                mm.area(p, 1, min(mm.w - 1.0, max(1.0, mm.w / 2 + ((j % 12) - 6) * 1.6)),
                        min(mm.h - 1.0, max(1.0, mm.h / 2 + (j // 12 - 5) * 1.6)), 1)
                continue
            if mst.startswith('qkd_rly'):
                mm.face(p, bits, 'W' if p == 'a' else 'E', 'M4', mm.h / 2, 1)   # wide relays: frame height = the word
                continue
            pe = peer.get((mst, p), [inst0])[0]
            dxp, dyp = pe.x + pe.w / 2 - (inst0.x + inst0.w / 2), pe.y + pe.h / 2 - (inst0.y + inst0.h / 2)
            if inst0.orient in ('MY', 'R180'):
                dxp = -dxp
            if inst0.orient in ('MX', 'R180'):
                dyp = -dyp
            face = ('E' if dxp > 0 else 'W') if abs(dxp) >= abs(dyp) else ('N' if dyp > 0 else 'S')
            if mst in ('qkd_kvwq_leaf_s','qkd_kvwq_leaf_s_w129','qkd_kvwq_leaf_s_w129_m'):
                # MX places the S write face against the CDC S face, with the
                # chain direction S->N after the flip (PC0..7).
                face = dict(c='N', n='S', dn='S', dp='N', w='S', wr='S', lane='E').get(p, 'E')
            if mst == 'qkd_ectl':
                # the tile column: si / so to the aggregator (E), the pair-0 copy / returns S, pair-1 N, KV rows W
                face = {'si': 'E', 'so': 'E', 't0': 'S', 'e0': 'S', 'e1': 'S', 's0': 'S', 's1': 'S',
                        't1': 'N', 'e2': 'N', 'e3': 'N', 's2': 'N', 's3': 'N'}.get(p, 'W')
            if mst == 'qkd_rhead':
                face = 'E' if p == 'nb' else 'S'  # the S face faces the control tile (heads 0 / 1 are MX)
            if mst in ('qkd_land', 'qkd_land_n') and face in 'NS':
                # the landing is a 172.8 um x 12 mm column: its short faces cannot hold its words (die_kv7: 3,186
                # overlapping pin shapes, PA DRT-0073); every word leaves on the long face toward its peer
                face = 'E' if dxp > 0 else 'W'
            if mst in ('qkd_astk', 'qkd_astk_n') and p[0] in 'ef' and p[1].isdigit():
                face = 'W' if int(p[1]) < 4 else 'E'
            layer = 'M4' if face in ('E', 'W') else 'M5'
            # the control tile's horizontal pins all on M4: with M4 + M6 its legal origins sit on an 8.64-um lattice
            # (lcm 48 / 64 / 270 nm) that the 2.16-um tile gaps cannot absorb (die_kv10: no legal origin for ectl_WS_3)
            # the head tile is placed MX / R180 below the control tile: a mirrored master's horizontal pins must be
            # mirror-legal on every layer at once (origin = 2 off - H mod pitch per layer).  M4 (off 12 / 48) and M8 (116 /
            # 80) agree mod 16, M6 (16 / 64) agrees with neither (die_kv8: 'qkd_rhead MX y has no legal origin') -> the
            # head's node beat on M4, its clock / reset area pins on M8, nothing on M6 (the astk faces it on M4)
            L = mm.h if face in ('E', 'W') else mm.w
            fl = face_load.setdefault((mst, face), [])
            # re-cut D faces are narrow enough for 2-track pitch (1-track first bits had no access point next to the
            # die PDN, DRT-0073 on astk e0i[0] / reng so[0])
            mm.face(p, bits, face, layer, 0.0, 2 if (mst in ('qkd_ectl', 'qkd_rhead', 'qkd_astk', 'qkd_astk_n') or (mst in ('qkd_land', 'qkd_land_n') and face in 'NS')) else 1)
            fl.append(p)
        # spread the face pins of each face evenly (centres)
        for face in ('N', 'S', 'E', 'W'):
            fl = face_load.get((mst, face), [])
            if not fl:
                continue
            L = mm.h if face in ('E', 'W') else mm.w
            tot = sum(mm.ports[p][1] for p in fl)
            pos = 2.0
            for p in fl:
                span = (L - 4.0) * mm.ports[p][1] / tot
                sp = list(mm.ports[p])
                sp[4] = pos + span / 2
                if mst in ('qkd_astk', 'qkd_astk_n') and p[0] in 'ef' and p[1].isdigit():
                    e = int(p[1])
                    t_ = 'c' if p[0] == 'e' else f'h{p[2]}'
                    sp[4] = (e % 4) * (RENG[1] + GY) + TILE_Y[t_] + (ECTL[1] if t_ == 'c' else HEAD[1]) / 2   # level with its tile
                    if t_ == 'c':            # facing the control tile's si (below) / so (above)
                        sp[4] += (1 if p[-1] == 'i' else -1) * (ECTL[1] - 4.0) * (425 if p[-1] == 'o' else 634) / (2 * 1059)
                if mst == 'qkd_ectl' and p in ('si', 'so'):
                    # one face, one layer: si below so, each centred on its share of the face
                    sp[4] = ECTL[1] / 2 + (-1 if p == 'si' else 1) * (ECTL[1] - 4.0) * (425 if p == 'si' else 634) / (2 * 1059)
                mm.ports[p] = tuple(sp)
                pos += span
        if m['geo'].get('split'):
            _strip_face_pins(mst, mm)
        if mst == 'qkd_hslice':
            _slice_pins(m, mm)
        if mst in LEVEL_PIN_MASTERS:
            _land_level_pins(m, mm, inst0, face_load, by)
    if m['geo'].get('split'):
        _split_pins(M, m)
    for mst in list(M):
        if mst not in used and mst not in sizes:
            M.pop(mst)
    for name, ports in m.get('assigned_ports', {}).items():
        if name in M:
            M[name].ports.update({p: tuple(v) for p, v in ports.items() if p in M[name].ports})
    return M


# kvsys v1.1: die-assigned pins of the native head frame and the three-leaf control frame (top-down, owner 10-13).
# t0 / t1 (S1b copy to a head pair, 1,559 b) leave the control tile on M5 at 6-track pitch over x 8.5..457.5 of its S / N
# face; every head's ti lands on its control-facing face at the SAME x (the control tile is centred in the column, offset
# EXO), so a far head's bits run straight over its near neighbour on M9 (one head height + gap, <= 504 um, no relay).
ECTL_T_CX = 233.0
ECTL_E_X = (470.0, 471.6)          # e0 / e1 (S face) and e2 / e3 (N face): a pair's two e words side by side
ECTL_S_X = (490.0, 493.4)          # s0 / s1, s2 / s3
ECTL_CK_X = (127.44, 382.32, 578.88)   # leaf A / B / C centres (254.88 | 254.88 | 138.24 x 129.6)


def _split_pins(M, m=None):
    if 'qkd_ectl' in M:
        mm = M['qkd_ectl']
        exo = up((HEAD[0] - ECTL[0]) / 2, GX)
        for f, (tp, es) in (('S', ('t0', (('e0', 'e1'), ('s0', 's1')))), ('N', ('t1', (('e2', 'e3'), ('s2', 's3'))))):
            if tp in mm.ports:
                mm.ports[tp] = ('face', mm.ports[tp][1], f, 'M5', ECTL_T_CX, 6)
            for pair, xs in zip(es, (ECTL_E_X, ECTL_S_X)):
                for p_, x_ in zip(pair, xs):
                    if p_ in mm.ports:
                        mm.ports[p_] = ('face', mm.ports[p_][1], f, 'M5', x_, 2)
        for c_, x_ in zip(ECTL_CK_X, ECTL_CLK):
            if x_ in mm.ports:
                mm.ports[x_] = ('area', 1, c_, ECTL[1] / 2, 1)
        if 'rst_n' in mm.ports:
            mm.ports['rst_n'] = ('area', 1, ECTL[0] / 2, ECTL[1] / 2 + 8.0, 1)
        if 'qkd_rhead' in M:
            hm = M['qkd_rhead']
            for p_, x_, pt_ in (('ti', exo + ECTL_T_CX, 6), ('e', exo + sum(ECTL_E_X) / 2, 2), ('s', exo + sum(ECTL_S_X) / 2, 2)):
                if p_ in hm.ports:
                    hm.ports[p_] = ('face', hm.ports[p_][1], 'S', 'M5', x_, pt_)
            if 'nb' in hm.ports:
                hm.ports['nb'] = ('face', hm.ports['nb'][1], 'E', 'M4', HEAD[1] / 2, 2)
            # v1.2 (head r4): the 86 clock entries (+ reset) are W-face M4 pins (an M8 area pin breaks the MX head's
            # mirror-legal origin: kvs4 real case 'qkd_rhead MX y: site grid never meets the legal residues mod 240'),
            # each level with the centre of the child it clocks (Codex r4 plan, canonical R0 = control face S), de-
            # overlapped at >= 1.2 um; one CTS sink per child, delivered at phi - R of that child
            ch = json.loads((ROOT / HEAD_R4_PLAN).read_text())['children']
            want = sorted((ch[HEAD_CLK_CHILD[p_]][1] + ch[HEAD_CLK_CHILD[p_]][3] / 2, p_) for p_ in HEAD_CLK if p_ in hm.ports)
            ys_, last = {}, 2.0 - 1.2
            for y_, p_ in want:
                last = max(y_, last + 1.2)
                ys_[p_] = last
            top = HEAD[1] - 12.0
            if ys_ and max(ys_.values()) > top:          # pack downward from the top when the run overflows the face
                for p_ in sorted(ys_, key=ys_.get, reverse=True):
                    ys_[p_] = min(ys_[p_], top)
                    top = ys_[p_] - 1.2
            for p_, y_ in ys_.items():
                hm.ports[p_] = ('face', 1, 'W', 'M4', round(y_, 3), 1)
            if 'rst_n' in hm.ports:
                hm.ports['rst_n'] = ('face', 1, 'W', 'M4', 440.0, 1)
    # v1.2: the strip compositions' leaf clock entries = area pins at each leaf (land: PC leaf k beside its CDC on the E
    # half, group i at the middle of its four PCs on the W half, the embedding engine at the N end; astk: astk_plan)
    for mn in ('qkd_land', 'qkd_land_n'):
        if mn in M:
            hm = M[mn]
            pos = {**{f'ck_p{k}': (hm.w * 0.75, STRIP_PC_PITCH * k + 190.08 + 86.4) for k in range(32)},
                   **{f'ck_g{i}': (hm.w * 0.25, STRIP_PC_PITCH * (4 * i + 2)) for i in range(8)},
                   'ck_e': (hm.w / 2, hm.h - 40.0), 'ck_r': (hm.w / 2, STRIP_PC_PITCH * 16 + 120.0)}
            for p_, (x_, y_) in pos.items():
                if p_ in hm.ports:
                    hm.ports[p_] = ('area', 1, round(x_, 3), round(y_, 3), 1)
    for mn in ('qkd_ctrl', 'qkd_ctrl_n'):
        if mn in M:
            hm = M[mn]
            pos = {**{f'ck_p{k}': (hm.w / 2 - 20.0, STRIP_PC_PITCH * k + 190.08 + 86.4) for k in range(32)},
                   **{f'hk_p{k}': (hm.w / 2 + 20.0, STRIP_PC_PITCH * k + 190.08 + 86.4) for k in range(32)},
                   'ck_k': (hm.w / 2 - 10.0, 12096.0 + 21.6), 'hk_k': (hm.w / 2 + 10.0, 12096.0 + 21.6)}
            for p_, (x_, y_) in pos.items():
                if p_ in hm.ports:
                    hm.ports[p_] = ('area', 1, round(x_, 3), round(min(y_, hm.h - 2.0), 3), 1)
    for mn in ('qkd_astk', 'qkd_astk_n'):
        if mn in M:
            hm = M[mn]
            pos = {}
            for name, mst_, col, y_, _ in astk_plan():
                h_ = ASTK_LEAF[mst_][1]
                x_ = hm.w * (0.25 if col == 0 else 0.75)
                if mst_ == 'qkd_astk_pv':
                    r_, hp_, c_ = int(name[4]), int(name[6]), 'xy'.index(name[8])
                    key = f'ck_v{16 * r_ + 8 * c_ + 2 * hp_ + (name[2] == "b")}'
                elif mst_ == 'qkd_astk_ex':
                    e_, j_ = map(int, name[3:].split('_'))
                    key = f'ck_x{4 * e_ + j_}'
                elif mst_ == 'qkd_astk_ep':
                    key = f'ck_e{int(name[3:])}'
                elif mst_ == 'qkd_astk_zn':
                    key = f'ck_z{int(name[3:])}'
                else:
                    key = 'ck_c'
                pos[key] = (x_, min(hm.h - 2.0, y_ + h_ / 2))
            pos['ck_r'] = (hm.w / 2, hm.h / 2 + 3.2)
            for p_, (x_, y_) in pos.items():
                if p_ in hm.ports:
                    hm.ports[p_] = ('area', 1, round(x_, 3), round(y_, 3), 1)
    # v1.2: the hub composition's 14 clock entries = area pins in one row across the slot (one CTS sink each; the
    # elements' child sub-slot plan moves each to its child's clock pin)
    if 'qkd_ahub' in M:
        hm = M['qkd_ahub']
        for j_, p_ in enumerate(AHUB_CLK):
            if p_ in hm.ports:
                hm.ports[p_] = ('area', 1, round(hm.w * (j_ + 1) / (len(AHUB_CLK) + 1), 3), hm.h / 2, 1)
    # the link bridge abuts the KV end: its rf / tf faces take the KV end's bit positions (v1 drew them ~220 um apart:
    # the 1.47 fine window of the d2d | lnk face); lx / lr leave its S face over the sequencer's lx / lr pins
    if m is not None and 'qkd_lnk' in M and 'qkd_d2d' in M:
        by = {i.name: i for i in m['insts']}
        ln, dd = M['qkd_lnk'], M['qkd_d2d']
        il, idd = by.get('lnk'), by.get('d2d_kv')
        for p_ in ('rf', 'tf'):
            if p_ in ln.ports and p_ in dd.ports and il is not None and idd is not None:
                sp = dd.ports[p_]
                ln.ports[p_] = ('face', ln.ports[p_][1], 'N', sp[3], sp[4] + idd.x - il.x, sp[5])
        sq = M.get('qkd_seq')
        isq = by.get('seq')
        if sq is not None and isq is not None and il is not None:
            # v1.2: the sequencer's link words leave its N face straight under the bridge (lr at x 250, lx at x 380, M5),
            # so the 522-um gap takes exactly one relay each way (K_ST 1 of the measured link cost) whatever the other
            # chains do (with level pins lx drifted to the W face and took 2 stages)
            for p_, x_ in (('lr', 250.0), ('lx', 380.0)):
                if p_ in sq.ports:
                    sq.ports[p_] = ('face', sq.ports[p_][1], 'N', 'M5', x_, 1)
            for p_ in ('lx', 'lr'):
                if p_ in ln.ports and p_ in sq.ports and sq.ports[p_][0] == 'face' and sq.ports[p_][2] == 'N':
                    ln.ports[p_] = ('face', ln.ports[p_][1], 'S', 'M5', sq.ports[p_][4] + isq.x - il.x, sq.ports[p_][5])


def real_pin_bindings(m):
    """Read actual LEF shapes, mapped per RTL bit. Missing views stay explicit.

    The CDC geometry view is historical evidence only; importing its pins does
    not assert that an appropriate die-context timing model exists.
    """
    if not m['geo'].get('kv_wq_leaf_s'):
        return {}, {}
    import re
    import die_top_lint as DTL
    paths = dict(qkd_cdc_wleaf='physical/qwen_die_masters/views/qfd_cdc_eco_h1/qfd_cdc.lef',
                 qkd_kvwq_leaf_s='physical/qwen_die_masters/views/qkd_kvwq_leaf_s/qkd_kvwq_leaf_s.lef',
                 qkd_kvwq_ctl_bin='physical/qwen_die_masters/views/qkd_kvwq_ctl_bin_a/qkd_kvwq_ctl_bin_a.lef')
    if m['geo'].get('kv_wq_head'):
        paths['qkd_kvwq_ctl_bin_h'] = 'physical/qwen_die_masters/views/qkd_kvwq_ctl_bin_h/qkd_kvwq_ctl_bin_h.lef'
        del paths['qkd_kvwq_ctl_bin']
    if m['geo'].get('kv_wq_wide'):
        paths['qkd_kvwq_leaf_s_w129'] = 'physical/qwen_die_masters/views/qkd_kvwq_leaf_s_w129/qkd_kvwq_leaf_s_w129.lef'
        del paths['qkd_kvwq_leaf_s']
    if m['geo'].get('kv_wq_mirror'):
        paths = {('qkd_kvwq_leaf_s_w129_m' if k=='qkd_kvwq_leaf_s_w129' else k):v.replace('qkd_kvwq_leaf_s_w129/','qkd_kvwq_leaf_s_w129_m/').replace('qkd_kvwq_leaf_s_w129.lef','qkd_kvwq_leaf_s_w129_m.lef') for k,v in paths.items()}
    if m['geo'].get('split'):
        paths.pop('qkd_kvwq_ctl_bin', None)     # v1.1: the sl3 strip-form view, bound by bind_views (not this old-form import)
        paths['qkd_kvwq_leaf_s_w129_m'] = ('physical/ref_tile/qkd_kvwq_leaf_s_w129_m/views/qkd_kvwq_leaf_s_w129_m/'
                                          'qkd_kvwq_leaf_s_w129_m.lef')
    rows, status = {}, {}
    for mst, rel in paths.items():
        path = ROOT/rel
        if not path.exists():
            status[mst] = dict(path=rel, ready=False, reason='own routed view not yet present')
            continue
        text = path.read_text()
        size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text)
        raw = {}
        for pin in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1\s', text, re.S):
            shapes = []
            for layer, a,b,c,d in re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*;', pin[2]):
                shapes.append((layer, tuple(map(float, (a,b,c,d)))))
            raw[pin[1]] = shapes
        binding = BINDINGS[mst]
        ports = DTL.parse_module(binding['file'], binding['module'], dict(TAGW=9,HD=128,QD=4,FLANE_BINARY=1))['ports']
        def expand(names):
            out = []
            for name in names:
                width = ports[name][1]
                out += [name] if width == 1 else [f'{name}[{i}]' for i in range(width)]
            return out
        groups = {dp:expand(names) for dp,names in binding['ports'].items()}
        if mst in ('qkd_kvwq_ctl_bin','qkd_kvwq_ctl_bin_h'):
            for g in range(4):
                groups[f'f{g}'] = [f'f_v[{g}]'] + [f'f_d[{256*g+i}]' for i in range(256)] + \
                    [f'f_sec[{24*g+i}]' for i in range(24)] + [f'f_lane[{8*g+i}]' for i in range(8)] + \
                    [f'f_tag[{9*g+i}]' for i in range(9)]
                groups[f'r{g}'] = [f'r_v[{g}]', f'r_bad[{g}]']
        mapped = []
        for dp, names in groups.items():
            for i, name in enumerate(names):
                if name not in raw:
                    raise ValueError(f'{mst}: actual LEF missing RTL pin {name}')
                mapped += [(f'{dp}[{i}]', layer, rect, name) for layer, rect in raw[name]]
        status[mst] = dict(path=rel, ready=True, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           size_um=list(map(float,size.groups())), named_pins=len(raw), mapped_shapes=len(mapped),
                           timing_gate='not implied by pin import')
        rows[mst] = mapped
    return rows, status


def cdc_write_pin_reach(m, rows):
    """Per-bit physical Manhattan distance, with the actual instance mirrors."""
    if 'qkd_cdc_wleaf' not in rows or not any(k in rows for k in ('qkd_kvwq_leaf_s','qkd_kvwq_leaf_s_w129','qkd_kvwq_leaf_s_w129_m')):
        return dict(ready=False, reason='actual CDC and south-face leaf pins both required')
    by = {i.name:i for i in m['insts']}
    def locations(it, port):
        out = {}
        for pin, layer, rect, rtl in rows[it.master]:
            if not pin.startswith(port+'['):
                continue
            x=(rect[0]+rect[2])/2; y=(rect[1]+rect[3])/2
            if it.orient in ('MY','R180'): x=it.w-x
            if it.orient in ('MX','R180'): y=it.h-y
            out.setdefault(pin,[]).append((it.x+x,it.y+y))
        return out
    distances=[]
    for st in STACKS:
        for pc in range(32):
            leaf=by[f'wleaf_{st}_{pc}']; cdc=by[f'cdc_{st}_{pc}']
            for lp,cp,width in [('w','wi',290),('wr','wr',11)]:
                a=locations(leaf,lp); b=locations(cdc,cp)
                for bit in range(width):
                    near=min(abs(x-u)+abs(y-v) for x,y in a[f'{lp}[{bit}]'] for u,v in b[f'{cp}[{bit}]'])
                    distances.append(dict(stack=st,pc=pc,port=lp,bit=bit,um=round(near,3)))
    worst=max(distances,key=lambda x:x['um'])
    return dict(ready=True, bits=len(distances), worst=worst, max_um=worst['um'],
                over_100um=sum(x['um']>100 for x in distances), over_SS_504um=sum(x['um']>504 for x in distances))


LEVEL_PIN_MASTERS = ('qkd_land', 'qkd_land_n', 'qkd_astk', 'qkd_astk_n', 'qkd_seq', 'qkd_ahub', 'qkd_embgw', 'qkd_host',
                     'qkd_d2d')


STRIP_ES_Y, STRIP_ER_Y, STRIP_KF_Y, STRIP_PC_PITCH = 60.0, 240.0, 21.6, 378.0
PHY_STRIP_DY = 71.28           # the PHY band starts 71.28 um above its controller strip's end (r21c band)


def _strip_face_pins(mst, mm):
    """v1.2: the landing <-> controller strip words of PC k (es<k> / er<k>) leave both strips level with PC k (local y
    378 k + 60 / + 240, clear of the CDC words c<k>i / c<k>o) on the faces that face each other across the CDC column;
    the controller strip's fault kf at y 6,150"""
    if mst not in ('qkd_land', 'qkd_land_n', 'qkd_ctrl', 'qkd_ctrl_n', SPLIT_PHY):
        return
    for p, sp in list(mm.ports.items()):
        mt = re.fullmatch(r'(po|pi)(\d+)', p)
        if sp[0] == 'face' and mt:
            y = STRIP_PC_PITCH * int(mt.group(2)) + (200.0 if mt.group(1) == 'po' else 236.0)
            if mst == SPLIT_PHY:
                mm.ports[p] = ('face', sp[1], 'W', 'M4', y - PHY_STRIP_DY, 1)
            else:
                mm.ports[p] = ('face', sp[1], 'E', 'M4', y, 1)
    if mst == SPLIT_PHY:
        return
    for p, sp in list(mm.ports.items()):
        if sp[0] != 'face':
            continue
        mt = re.fullmatch(r'(es|er)(\d+)', p)
        if mt:
            y = STRIP_PC_PITCH * int(mt.group(2)) + (STRIP_ES_Y if mt.group(1) == 'es' else STRIP_ER_Y)
        elif p == 'kf':
            # v1.3 (die-placed controller leaves): kf leaves the controller strip at its kc leaf = the strip's OUTER end
            # (S stacks: qkd_ctrl_strip_sr, kc leaf at the S end; N stacks: kc leaf at the N end) and enters the landing
            # strip's PC fault chain at pc0 = its S end; a mid-strip pin (v1.2 y 6,150) became a 6-mm unrelayed wire
            if mst == 'qkd_ctrl_n':
                mm.ports[p] = ('face', sp[1], 'N', 'M5', round(mm.w / 2 + 21.6, 4), 1)
                continue
            y = STRIP_KF_Y
        else:
            continue
        mm.ports[p] = ('face', sp[1], 'E' if mst.startswith('qkd_land') else 'W', 'M4', y, 1)


def _slice_pins(m, mm):
    """v1.4: HOST slice pins.  es / er words level with the strips' es<k> / er<k> (local 378 k + 60 / + 240): controller
    side on the W face (R0 W stacks; MY puts it on the E side toward the E controller strip), landing side on the E face;
    the stack chains run N-S through the 32.4-um slot gaps (S face: toward slot k-1 = the root end); clocks / resets /
    straps are area pins."""
    by = {i.name: i for i in m['insts']}
    off = by['hsl_WS_0'].y - by['land_WS'].y
    w = {p: sp[1] for p, sp in mm.ports.items()}
    mm.ports.clear()
    mm.order.clear()
    lvl = dict(ctrl_es=('W', STRIP_ES_Y), land_es=('E', STRIP_ES_Y), ctrl_er=('W', STRIP_ER_Y), land_er=('E', STRIP_ER_Y))
    south = ['fi', 'co', 'ao', 'fault_o', 'sko', 'sdo', 'soo', 'sfo', 'bgi']
    north = ['fo', 'ci', 'ai', 'fault_i', 'ski', 'sdi', 'soi', 'sfi', 'bgo']
    for p, (face, y) in lvl.items():
        if p in w:
            mm.face(p, w[p], face, 'M4', round(y - off, 3), 2)
    for face, lst in (('S', south), ('N', north)):
        lst = [p for p in lst if p in w]
        span = [w[p] * 0.048 * 2 for p in lst]
        pos = (mm.w - sum(span) - 2.0 * (len(lst) - 1)) / 2
        for p, s_ in zip(lst, span):
            mm.face(p, w[p], face, 'M5', round(pos + s_ / 2, 3), 2)
            pos += s_ + 2.0
    rest = [p for p in w if p not in mm.ports]
    for j, p in enumerate(sorted(rest)):
        if w[p] == 1:
            mm.area(p, 1, round(mm.w / 2 + ((j % 8) - 4) * 3.2, 3), round(mm.h / 2 + (j // 8 - 1) * 3.2, 3), 1)
        else:
            mm.face(p, w[p], 'W', 'M4', round(mm.h / 2, 3), 2)          # lpc strap (5 b), mid W face between es / er


def _land_level_pins(m, mm, inst0, face_load, by):
    """qwen-1010/b 2026-10-10 (KV11 die STA TT -38.6 ns: land_ES/rs4 -> ectl_ES_4/rs, a 'neighbour' hop whose landing pin
    sat ~mm away along the 12-mm landing face).  Every word of a placeholder master (LEVEL_PIN_MASTERS) that is not a
    fixed-position port (CDC column ports, the aggregator's tile-level e / f ports) is drawn LEVEL WITH ITS OWN PEER
    (the tile, or the first relay of its chain) on the face that faces it, then de-overlapped against the fixed ports
    and each other (nearest free slot).  The pin-to-pin hop is then the frame gap the relay planner measured."""
    own = {}
    for bid, cl, bits, eps in m['buses']:
        if len(eps) == 2:
            for (i0, p0), (i1, p1) in ((eps[0], eps[1]), (eps[1], eps[0])):
                if i0 == inst0.name:
                    own[p0.lstrip('*')] = by[i1]
    pitch_um = 0.048
    fixed_rx = re.compile(r'^(c\d+[io]|[ef]\d.*|es\d+|er\d+|kf)$')
    for face in ('E', 'W', 'N', 'S'):
        L = mm.h if face in 'EW' else mm.w
        fl = face_load.get((mm.name, face), [])
        fixed, mov = [], []
        for p, sp in mm.ports.items():
            if sp[0] != 'face' or sp[2] != face:
                continue
            span = sp[1] * pitch_um * sp[5]
            (mov if (p in fl and p in own and not fixed_rx.match(p)) else fixed).append((p, span))
        occ = [(mm.ports[p][4] - sp_ / 2 - 1.0, mm.ports[p][4] + sp_ / 2 + 1.0) for p, sp_ in fixed]
        want = []
        for p, span in mov:
            pe = own[p]
            if face in 'EW':
                c = pe.y + pe.h / 2 - inst0.y
                if inst0.orient in ('MX', 'R180'):
                    c = inst0.h - c
            else:
                c = pe.x + pe.w / 2 - inst0.x
                if inst0.orient in ('MY', 'R180'):
                    c = inst0.w - c
            want.append((min(max(c, span / 2 + 2.0), L - span / 2 - 2.0), p, span))
        for y, p, span in sorted(want):
            for k in range(0, 80000):
                for cand in ((y + 0.5 * k, y - 0.5 * k) if k else (y,)):
                    lo, hi = cand - span / 2 - 1.0, cand + span / 2 + 1.0
                    if lo < 1.0 or hi > L - 1.0:
                        continue
                    if all(hi <= a or lo >= b for a, b in occ):
                        sp = list(mm.ports[p])
                        sp[4] = cand
                        mm.ports[p] = tuple(sp)
                        occ.append((lo, hi))
                        break
                else:
                    continue
                break
            else:
                raise ValueError(f'kv die: no {mm.name} face {face} slot for {p}')


def pin_xy(it, mm, port):
    """qwen-1010/b: absolute centre of a face / area port of instance it (master mm), with the orientation applied."""
    sp = mm.ports[port]
    if sp[0] == 'face':
        f, c = sp[2], sp[4]
        x, y = {'E': (it.w, c), 'W': (0.0, c), 'N': (c, it.h), 'S': (c, 0.0)}[f]
    else:
        x, y = sp[2], sp[3]
    if it.orient in ('MY', 'R180'):
        x = it.w - x
    if it.orient in ('MX', 'R180'):
        y = it.h - y
    return it.x + x, it.y + y


def pin_reach(m, M, reach=500.0, skip=('clock_trunk', 'reset', 'constant')):
    """qwen-1010/b 2026-10-10: the pin-to-pin register hops of every point-to-point die bus (Manhattan between the two
    drawn pins; the frame-to-frame margin lint cannot see a pin on a far face or far along a long face)."""
    by = {i.name: i for i in m['insts']}
    bad, n = [], 0
    for bid, cl, bits, eps in m['buses']:
        if cl in skip or len(eps) != 2 or cl in ABUT:
            continue
        (a, pa), (b, pb) = eps
        ia, ib = by[a], by[b]
        if ia.master not in M or ib.master not in M or pa.lstrip('*') not in M[ia.master].ports or pb.lstrip('*') not in M[ib.master].ports:
            continue
        n += 1
        try:
            xa, ya = pin_xy(ia, M[ia.master], pa.lstrip('*'))
            xb, yb = pin_xy(ib, M[ib.master], pb.lstrip('*'))
        except (TypeError, KeyError):
            continue
        d = abs(xa - xb) + abs(ya - yb)
        if d > reach:
            bad.append(dict(bus=bid, cls=cl, bits=bits, um=round(d, 1), a=f'{a}.{pa}', b=f'{b}.{pb}'))
    bad.sort(key=lambda r: -r['um'])
    return dict(hops=n, reach_um=reach, violations=len(bad), worst=bad[:40])


def stack_local_reach(m, M, reach=500.0):
    """v1.1: the abutted / stack-local buses the relay planner never relays (ectl <-> heads tp / te / ts, heads -> astk nb,
    astk <-> ectl eq / el): driver pin centre -> every load pin centre (spans are bit-aligned, so the centre distance is the
    bit distance).  v1 had 192 far-head hops 505-963 um here."""
    by = {i.name: i for i in m['insts']}
    bad, n, worst = [], 0, 0.0
    for bid, cl, bits, eps in m['buses']:
        if cl != 'stack_local' or len(eps) < 2:
            continue
        try:
            a = pin_xy(by[eps[0][0]], M[by[eps[0][0]].master], eps[0][1].lstrip('*'))
        except (KeyError, TypeError):
            continue
        for inst, port in eps[1:]:
            try:
                b = pin_xy(by[inst], M[by[inst].master], port.lstrip('*'))
            except (KeyError, TypeError):
                continue
            n += 1
            d = abs(a[0] - b[0]) + abs(a[1] - b[1])
            worst = max(worst, d)
            if d > reach:
                bad.append(dict(bus=bid, bits=bits, um=round(d, 1), a=f'{eps[0][0]}.{eps[0][1]}', b=f'{inst}.{port}'))
    bad.sort(key=lambda r: -r['um'])
    return dict(hops=n, reach_um=reach, violations=len(bad), max_um=round(worst, 1), worst=bad[:20])


_BASE_PORT_WIDTHS = F.port_widths


def port_widths(m, k=1):
    widths = _BASE_PORT_WIDTHS(m, k)
    if m['geo'].get('kv_wq_binary') and not m['geo'].get('split'):
        if k != 1:
            raise ValueError('binary ctl requires full-width pin mapping')
        for g in range(4):
            widths[('qkd_kvwq_ctl_bin_h' if m['geo'].get('kv_wq_head') else 'qkd_kvwq_ctl_bin', f'f{g}')] = 298
    return widths


def write_netlist(m, k, path, top='qkd_die'):
    F.write_netlist(m, k, path, top=top)
    if m.get('host_ties'):
        # v1.4: per-slice logical-PC straps and the stack chain terminators (the source parent's constants), as tie cells
        p_ = Path(path)
        tx = p_.read_text()
        tx = tx.replace('endmodule', '\n'.join(f"  assign n_{b} = {w}'d{v};" for b, (w, v) in m['host_ties'].items()) +
                        '\nendmodule', 1)
        p_.write_text(tx)
    if not m['geo'].get('kv_wq_leaves'):
        return
    if k != 1:
        raise ValueError('per-PC leaves require full-width nets (k=1)')
    # These constants are die-top straps, not muxes or a second CDC writer.
    p = Path(path)
    txt = p.read_text()
    if m['geo'].get('kv_wq_binary'):
        unused = []
        for st in STACKS:
            for g in range(4):
                net = f'n_wencoded_{st}_{g}'
                u = f'ctl_lane_high5_unused_{st}_{g}'
                unused.append(f'  wire [4:0] {u};')
                before = f'.f{g}({net})'
                after = f'.f{g}({{{net}[292:284], {u}, {net}[283:0]}})'
                if before not in txt:
                    raise ValueError(f'binary ctl group port missing: {st}/{g}')
                txt = txt.replace(before, after, 1)
        txt = txt.replace(f'module {top} ();', f'module {top} ();\n' + '\n'.join(unused), 1)
    ties = [f"  assign n_{bid} = 3'd{lane};" for bid, lane in m['wq_straps'].items()]
    ties += [f"  assign n_wtail_{st}_{g} = 2'b00;" for st in STACKS for g in range(4)]
    txt = txt.replace('endmodule', '\n'.join(ties) + '\nendmodule', 1)
    p.write_text(txt)
    # Explicit nine OR2-equivalent gates a group; no silent 8-bit/3-bit rename.
    # This module is functional composition RTL only.  The die physical abstract
    # remains UNQUALIFIED until this encoder closes at SS/FF in context.
    if m['geo'].get('kv_wq_binary'):
        return
    p.with_name('kv_wq_lane_encoder.sv').write_text("""module qkd_kvwq_lane_encoder(input wire [297:0] a, output wire [292:0] b);
  wire [7:0] oh = a[288:281];
  wire [2:0] lane = {oh[4]|oh[5]|oh[6]|oh[7], oh[2]|oh[3]|oh[6]|oh[7], oh[1]|oh[3]|oh[5]|oh[7]};
  assign b = {a[297:289], lane, a[280:0]};
endmodule
""")


def record(m):
    by_m = {}
    for i in m['insts']:
        r = by_m.setdefault(i.master, dict(n=0, mm2=0.0))
        r['n'] += 1
        r['mm2'] += i.w * i.h / 1e6
    inst_mm2 = sum(r['mm2'] for r in by_m.values())
    die = m['die']
    st = m['relay_stages']
    return dict(schema='opentallas.qwen-kv-die.plan.v1', generator='tools/qwen_kv_die/kv_die.py',
                generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                template=dict(path=str(TPL_PATH.relative_to(ROOT)), sha256=hashlib.sha256(TPL_PATH.read_bytes()).hexdigest()),
                die_um=[die['w'], die['h']], die_mm2=die['mm2'], instances=len(m['insts']), buses=len(m['buses']),
                instance_mm2=round(inst_mm2, 3), fill=round(inst_mm2 / die['mm2'], 4),
                static_memory_reservation=dict(enabled=m['geo'].get('static_memory_reservation',False),
                    land_width_um=LAND_W, status='PLAN_ONLY_ACTUAL_ADAPTER_BINDING_REQUIRED' if m['geo'].get('static_memory_reservation') else 'LEGACY_LANDING_PROFILE'),
                native_astk_reservation=dict(enabled=ASTK_W>324, parent_width_um=ASTK_W,
                    status='PLAN_ONLY_SELECTED_PROFILE_BINDING_REQUIRED' if ASTK_W>324 else 'LEGACY_FRAME'),
                masters={k_: dict(n=v_['n'], mm2=round(v_['mm2'], 4)) for k_, v_ in sorted(by_m.items())},
                ucie=dict(macro=UCIE[0], mm2=round(UCIE[1] * UCIE[2] / 1e6, 4), edge_um=UCIE[1], edge='N (abuts the '
                          'ROM die S edge under spine column M)'),
                relay_stages={k_: v_ for k_, v_ in sorted(st.items()) if v_},
                critical_stages=dict(
                    d2d_to_seq=st.get('d2d_dn', 0), seq_to_astk={s: st.get(f'aq_{s}', 0) for s in STACKS},
                    astk_to_hub={s: st.get(f'ap_{s}', 0) for s in STACKS}, hub_to_astk={s: st.get(f'am_{s}', 0) for s in STACKS},
                    hub_to_seq=st.get('ares', 0), seq_to_d2d=st.get('d2d_up', 0),
                    seq_to_land={s: st.get(f'kvn_{s}', 0) for s in STACKS},
                    gw_to_land={s: st.get(f'emf_{s}', 0) for s in STACKS}, land_to_gw={s: st.get(f'emr_{s}', 0) for s in STACKS},
                    seq_to_gw=st.get('gq', 0), gw_to_seq=st.get('gr', 0)),
                assumed=dict(row_engine_frame=f're-cut H: 4 x qkd_rhead {HEAD[0]} x {HEAD[1]} + qkd_ectl {ECTL[0]} x {ECTL[1]} '
                                              f'(measured cells: head 152,960 um2 placed, control 24,507 um2 synthesized; '
                                              f'routes qkd_rhead_c / qkd_ectl_c)',
                             astk_w=ASTK_W, land_w=LAND_W, frames=FRAMES,
                             note='frames without a routed element are sized from synthesis or stated as ASSUMED'))


def check(m):
    ins = m['insts']
    ev = sorted(ins, key=lambda i: i.x)
    act, bad = [], []
    for i in ev:
        act = [a for a in act if a.x + a.w > i.x + 1e-3]
        for a in act:
            if min(a.y + a.h, i.y + i.h) - max(a.y, i.y) > 1e-3 and min(a.x + a.w, i.x + i.w) - max(a.x, i.x) > 1e-3:
                bad.append((a.name, i.name))
        act.append(i)
    out = [i.name for i in ins if i.x < -1e-3 or i.y < -1e-3 or i.x + i.w > m['die']['w'] + 1e-3
           or i.y + i.h > m['die']['h'] + 1e-3]
    return dict(overlaps=len(bad), overlap_examples=bad[:10], outside=len(out), outside_examples=out[:10])


def case(m, work):
    """the die-level case of the r21 Qwen chain (tools/qwen_rom_fulldie.case_real: elements.lef from these masters,
    phy_ew.lef, die.v, place.tcl, run.tcl legality / on-track / pin access, run_pa.tcl PDN), written by the base
    generator's writer with this die's masters and port widths."""
    if m['geo'].get('static_memory_reservation'):
        raise ValueError('static memory shape reservation is plan-only until actual adapter ports/relays replace old landing binding')
    # qwen-1010/b 2026-10-11: the mirror leaf plan is the ADOPTED write queue (ctl_bin + leaf_s_w129(_m) closed, bound
    # in superseded_elements.json); the other leaf candidates stay plan-only
    if m['geo'].get('kv_wq_leaves') and not m['geo'].get('kv_wq_mirror'):
        raise ValueError('per-PC leaf candidate is plan-only until encoder/pin/context gates pass')
    saved = F.masters, F.port_widths
    F.masters, F.port_widths = masters, port_widths
    try:
        man = F.case_real(m, work)
    finally:
        F.masters, F.port_widths = saved
    run = (work / 'run.tcl').read_text()
    (work / 'run_pdn.tcl').write_text((work / 'run_pa.tcl').read_text())
    # the HBM PHY macros' own M4 power rails (the KV die's four PHY bands): a macro grid that straps them to M8 / M9,
    # so the PG check sees them connected (die_kv2..4: 1,000 PSM-0038 unconnected M4 shapes over x 20.8 - 853.3 um).
    # qwen-1010/b 2026-10-10: M4 and M8 are both horizontal, so an M4 -> M8 connect only forms where a strap happens to
    # overlay a rail of its own net (die_kv11: VDD PASS by that coincidence, every VSS rail open, PSM-0069).  The grid now
    # crosses the rails with vertical M5 straps (M5 is free over the PHY: OBS M1-M4 only), M4 -> M5 at every crossing,
    # M5 -> M8 stacked onto the CORE grid's M8 (which runs over the PHY).  The grid's own M8 / M9 copy is gone: with it
    # VSS still failed (die_kv12 PSM-0069); without it VSS passes (pgb test on the die_kv11 floorplan).
    (work / 'pdn.tcl').write_text((work / 'pdn.tcl').read_text() + '''
set phy_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { if {[string match ot_hbm3e_phy* [$c getName]]} { lappend phy_cells [$c getName] } } }
if {[llength $phy_cells]} {
  define_pdn_grid -macro -cells $phy_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {phy}
  add_pdn_stripe -grid {phy} -layer {M5} -width {0.12} -pitch {10.88} -offset {1.0}
  add_pdn_connect -grid {phy} -layers {M4 M5}
  add_pdn_connect -grid {phy} -layers {M5 M8}
}
# kv-die it2 (die_iter_1012): bound real element views (exact LEFs) carry their PG pins as full-length horizontal M6
# stripes (layer contract: leaf PG on M6, parent straps one layer up).  M6 and the die's M8 are both horizontal, so the
# die grid never reaches them (it1 die_kvi1: all 132 bound views PSM-0039 unconnected, PSM-0069).  Vertical M7 straps
# over every block master whose VDD pin is on M6: M6 -> M7 at each crossing, M7 -> M8 onto the core grid.
set hv6_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock]} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M6"} { lappend hv6_cells [$c getName] } } }
} }
set hv6_cells [lsort -unique $hv6_cells]
puts "OT_HV6 masters [llength $hv6_cells]: $hv6_cells"
if {[llength $hv6_cells]} {
  define_pdn_grid -macro -cells $hv6_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv6}
  add_pdn_stripe -grid {hv6} -layer {M7} -width {0.288} -pitch {10.88} -offset {2.0}
  add_pdn_connect -grid {hv6} -layers {M6 M7}
  add_pdn_connect -grid {hv6} -layers {M7 M8}
}
# qwen-split kvs1 (PSM-0039 on all 128 head_hs): cluster views whose PG pins are VERTICAL M7 stripes (no M6 PG) only need the
# M7 -> M8 connect onto the core grid (the core M8 straps cross their M7 stripes)
set hv7_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock] || [lsearch -exact $hv6_cells [$c getName]] >= 0} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M7"} { lappend hv7_cells [$c getName] } } }
} }
set hv7_cells [lsort -unique $hv7_cells]
puts "OT_HV7 masters [llength $hv7_cells]: $hv7_cells"
if {[llength $hv7_cells]} {
  define_pdn_grid -macro -cells $hv7_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv7}
  add_pdn_connect -grid {hv7} -layers {M7 M8}
}
# qwen-split kvsys v1.1 (kvs1 PSM-0039 on all 128 qkd_cdc_wleaf; the sl1 write leaf too): M5-capped leaf views whose PG pins
# are VERTICAL M5 stripes (no M6 / M7 PG): the core grid's horizontal M8 straps cross them -> a stacked M5 -> M8 connect
# (M6 / M7 are free over an M5-capped leaf)
set hv5_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] {
  if {![$c isBlock] || [lsearch -exact $hv6_cells [$c getName]] >= 0 || [lsearch -exact $hv7_cells [$c getName]] >= 0} { continue }
  if {[string match ot_hbm3e_phy* [$c getName]]} { continue }
  set t [$c findMTerm VDD]
  if {$t eq "NULL"} { continue }
  foreach mp [$t getMPins] { foreach b [$mp getGeometry] {
    if {[$b getTechLayer] ne "NULL" && [[$b getTechLayer] getName] eq "M5"} { lappend hv5_cells [$c getName] } } }
} }
set hv5_cells [lsort -unique $hv5_cells]
puts "OT_HV5 masters [llength $hv5_cells]: $hv5_cells"
if {[llength $hv5_cells]} {
  define_pdn_grid -macro -cells $hv5_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {hv5}
  add_pdn_connect -grid {hv5} -layers {M5 M8}
}
''')
    man.update(die='qwen_kv', die_um=[m['die']['w'], m['die']['h']], generator='tools/qwen_kv_die/kv_die.py')
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['plan', 'case'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--r', type=int, default=R)
    ap.add_argument('--kv-wq-leaves', action='store_true', help='candidate per-PC write leaves; encoder closure still owed')
    ap.add_argument('--kv-wq-leaf-s', action='store_true', help='plan-only south-face leaf plus binary ctl candidate')
    ap.add_argument('--kv-wq-binary', action='store_true', help='plan-only binary ctl candidate; needs its own routed closure')
    ap.add_argument('--kv-wq-head', action='store_true', help='candidate 216x648 binary ctl with one head capture edge')
    ap.add_argument('--kv-wq-wide', action='store_true', help='candidate 129.6um south-face leaf')
    ap.add_argument('--kv-wq-mirror', action='store_true', help='candidate single-layer mirror-legal wide leaf; head capture remains opt-in')
    ap.add_argument('--reserve-static-memory', action='store_true', help='plan-only native151.2umPC SRAM column plus86.4um row-control column; actual adapter binding still required')
    ap.add_argument('--reserve-native-astk', action='store_true', help='plan-only328.32um parent for actual two162um ASTK columns; selected static/native views remain required')
    ap.add_argument('--split', action='store_true', help='qwen-split 2026-10-14: the KV/SYSTEM die of the two-die split (CONTRACT_KVSYS.md)')
    ap.add_argument('--host-v14', action='store_true', help='kvsys v1.4: real HOST root core + 128 die-placed PC slices + PLL model')
    a = ap.parse_args(argv)
    if a.host_v14:
        if not a.split:
            ap.error('--host-v14 needs --split')
        HOST_V14['on'] = True
    a.kv_wq_wide = a.kv_wq_wide or a.kv_wq_mirror
    a.kv_wq_leaf_s = a.kv_wq_leaf_s or a.kv_wq_head or a.kv_wq_wide
    a.kv_wq_binary = a.kv_wq_binary or a.kv_wq_leaf_s
    a.kv_wq_leaves = a.kv_wq_leaves or a.kv_wq_binary
    if a.mode == 'case' and a.reserve_native_astk:
        ap.error('native ASTK envelope reservation is plan-only until selected profile/clock/pin binding closes')
    if a.mode == 'case' and a.kv_wq_leaves and not a.kv_wq_mirror:
        ap.error('per-PC leaf candidate is plan-only: encoder and closed-view pin/context gates remain open')
    m = build(a.r, kv_wq_leaves=a.kv_wq_leaves, kv_wq_binary=a.kv_wq_binary, kv_wq_leaf_s=a.kv_wq_leaf_s, kv_wq_head=a.kv_wq_head, kv_wq_wide=a.kv_wq_wide, kv_wq_mirror=a.kv_wq_mirror, split=a.split, reserve_static_memory=a.reserve_static_memory, reserve_native_astk=a.reserve_native_astk)
    if a.mode == 'case':
        m['buses'] = [(bid, cls, bits, eps) for bid, cls, bits, eps in m['buses']]
        print(json.dumps(case(m, a.out)))
        return 0
    rec = record(m)
    rec['legality'] = check(m)
    M = masters(m, 1)
    rec['masters_abstract'] = {n: dict(w=round(mm.w, 3), h=round(mm.h, 3), ports=len(mm.order)) for n, mm in M.items()}
    rec['strict_ports'] = strict_ports(M)
    rec['pin_reach'] = pin_reach(m, M)   # qwen-1010/b: pin-to-pin register hops (SS reach 504 um)
    rec['stack_local_reach'] = stack_local_reach(m, M)
    real_rows, real_status = real_pin_bindings(m)
    if a.kv_wq_leaf_s:
        rec['actual_pin_views'] = real_status
        rec['cdc_write_pin_reach'] = cdc_write_pin_reach(m, real_rows)
    if a.kv_wq_leaves:
        rec['kv_wq_candidate'] = dict(adopted=False, leaves=128, control_tiles=4, encoder_tiles=0 if a.kv_wq_binary else 16,
            encoder='binary low3/high5zero inside successor ctl' if a.kv_wq_binary else '3 OR4 per group; matches ot_qkvd_kv_wq_leaves exactly',
            gate='BLOCKED_BINARY_CTL_PHYSICAL_CLOSURE' if a.kv_wq_binary else 'BLOCKED_ENCODER_PHYSICAL_CLOSURE', chain_order='PC 8*g through 8*g+7 S-to-N' if a.kv_wq_leaf_s else 'PC 8*g+7 through 8*g N-to-S, lane strap PC%8',
            cdc_ci_slices=dict(wi=[0,290], wr=[290,11], cf=[301,1]),
            controller_head_cycles=1 if a.kv_wq_head else 0, chain_hop_cycles=dict(feed=2, done=1), relay_cycles=m['relay_stages'],
            controller_group_slices={g: dict(f_v=[g,1], f_d=[256*g,256], f_sec=[24*g,24],
                                             f_lane=[8*g,8], f_tag=[9*g,9], r_v=[g,1], r_bad=[g,1]) for g in range(4)},
            physical_gate='closed leaf/ctl pin shapes must replace candidate abstracts; optionB TT>=0 FF>=0 DRC0 with SS reach sensitivity',
            encoder_sizing=dict(or4_per_group=0 if a.kv_wq_binary else 3, or2_equivalent_total=0 if a.kv_wq_binary else 144,
                                reserved_frame_mm2=0 if a.kv_wq_binary else round(16*43.2*43.2/1e6,6), measured_cell_area=None))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'plan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    if real_rows:
        (a.out/'actual_pin_bindings.json').write_text(json.dumps(real_rows,indent=1)+'\n')
    (a.out / 'insts.json').write_text(json.dumps([i.d() for i in m['insts']]) + '\n')
    write_netlist(m, 1, a.out / 'kv_die.v', top='qkd_die')
    print(json.dumps({k_: rec[k_] for k_ in ('die_um', 'die_mm2', 'instances', 'fill', 'legality')}))
    return 0 if not rec['legality']['overlaps'] and not rec['legality']['outside'] else 1


if __name__ == '__main__':
    sys.exit(main())
