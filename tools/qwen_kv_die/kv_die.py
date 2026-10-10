#!/usr/bin/env python3
"""kv-die 2026-10-09 (OWNER DECISION ~04:00 PT, option 1a): the Qwen3-8B KV die (die generator `qwen_kv`).

One KV die per ROM die.  Long axis N-S; its N edge abuts the r22k ROM die's S edge under spine column M, where the two
UCIe macros face each other; the four HBM3E stacks sit beside its E and W edges (two a side), as they sat beside the
r21c ROM die.  Per side, outward to inward, the r21c HBM band re-placed with the SAME masters and pins
(tools/qwen_kv_die/r21c_band.json, dumped from the r21c generator):

    PHY (ot_hbm3e_phy 833.5 x 12,000.1) | controller (qkd_ctrl = qfd_ctrl) | 32 per-PC CDC (qkd_cdc = qfd_cdc) |
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
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_rom_fulldie as F     # noqa: E402  (Inst, Master, lattice, phy_pins, pin_rects, write_netlist)

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
LAND_W = 172.8                  # KV landing column: 8 x 32 crossbar, 8 KV merges, emb strip (ASSUMED; r21c qfd_kvc 96.7)
UCIE = ('ot_qkvd_ucie_x64_phy', 777.6, 777.6)
SERDES = ('ot_qfd_serdes_112g_x12_phy', 2400.0, 1512.0)
FRAMES = dict(qkd_ckbump=(43.2, 43.2), qkd_d2d=(777.6, 518.4), qkd_seq=(777.6, 518.4), qkd_embgw=(388.8, 388.8), qkd_pll=(324.0, 324.0),
              qkd_ahub=(648.0, 648.0), qkd_host=(777.6, 518.4))
RELAY_PITCH = 430.56
REACH_TARGET = 470.0            # every register-to-register segment (nearest frame points) <= this (SS reach 504 um)
RELAY_TARGET = 320.0            # placement pitch: keeps every segment (nearest frame points) under the 504 um SS reach
GRID = 43.2                     # relay routing grid (um)
CHAN = 129.6                    # routing / relay channel beside every column (um)
STACKS = ('WS', 'WN', 'ES', 'EN')
W = 528
FDI_UCIE = 1 + 1 + 548 + 1 + 548
FDI_SERDES = 1 + 1 + 1041 + 1 + 1041
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
                    'ot_qfd_emb_pcport KVW 2: KV writes carry the HBM ECC side-band, data = the CDC completion h_cv / h_cdata)',
           qkd_cdc='rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv ot_qwen_stream4_cdc_pc (route r11a)',
           qkd_land='qfd_kvc successor (landing crossbar) + ot_qkvd_kv_seq KV-merge slices + ot_qfd_emb_strip',
           qkd_ectl='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv ot_qwen_nearhbm_ectl_h (re-cut H control tile)',
           qkd_rhead='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv ot_qwen_nearhbm_head_h (re-cut H head tile, hid strap)',
           qkd_astk='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_d.sv ot_qwen_nearhbm_attn_stack_d minus its engines',
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
                  classed={'ev': 'debug'}),
    qkd_seq=dict(module='ot_qkvd_kv_seq', file='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv',
                 ports=dict(rf=['c_v', 'c_d', 'c_cr'], tf=['u_v', 'u_d', 'u_cr'],
                            aq_WS=['a_start', 'a_T', 'a_layer', 'a_q_valid', 'a_q_beat', 'a_q_data'],
                            ar=['a_out_valid', 'a_out_g', 'a_out_beat', 'a_out_data'], hf=['a_hub_fault'],
                            af_WS=['a_stk_fault'], mf_WS=['m_fault'],
                            kvn_WS=['kvw_v', 'kvw_vg', 'kvw_t', 'kvw_layer', 'kvw_d', 'kvw_cr'],
                            gq=['emb_req_v', 'emb_req_d', 'emb_req_cr'], gr=['emb_q_v', 'emb_q_d', 'emb_q_cr'],
                            hc=['hc_v', 'hc_d', 'hc_cr'], tk=['tok_v', 'tok_d', 'tok_cr'], hs=['a_start'],
                            d2df=['d2d_fault', 'd2d_cause'], kst=['fault', 'fault_cause'], ck=['clk'], rst_n=['rst_n']),
                 sliced=dict(aq_WN='aq_WS', aq_ES='aq_WS', aq_EN='aq_WS', af_WN='af_WS', af_ES='af_WS', af_EN='af_WS',
                             mf_WN='mf_WS', mf_ES='mf_WS', mf_EN='mf_WS', kvn_WN='kvn_WS', kvn_ES='kvn_WS',
                             kvn_EN='kvn_WS'),
                 classed={}),
    qkd_d2d=dict(module='ot_qkvd_kv_end', file='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv',
                 ports=dict(rf=['r_v', 'r_d', 'r_cr'], tf=['t_v', 't_d', 't_cr'],
                            fdi=['tx_up', 'tx_v', 'tx_flit', 'rx_v', 'rx_flit'], flt=['fault', 'fault_cause'],
                            ck=['clk'], rst_n=['rst_n']),
                 classed={}),
)
# not exact-cut yet (frames sized, RTL partition owed): reported, not strict
FRAME_ONLY = dict(qkd_astk='ot_qwen_nearhbm_attn_stack_d minus its engines (re-cut D: q beat broadcast, node staging, '
                           'P.V levels 4-7; recut.json)',
                  qkd_land='qfd_kvc crossbar successor + ot_qkvd_kv_merge (rtl/qwen_sys/kv_die_20261009) + ot_qfd_emb_strip',
                  qkd_embgw='ot_qfd_emb_gw + the gateway link side (r21c hub link FIFOs)',
                  qkd_host='qfd_io_host successor (hing_qfd ingest) + ot_qfd_link_adapter', qkd_pll='vendor PLL + '
                  'ot_qwen_sys_rst_seq', qkd_ctrl='qfd_ctrl (r21c element; pcport KVW 2: KV write side-band from the CDC completion, no new die port)',
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
            x = m['geo']['x_land'] if side == 'W' else m['die']['w'] - m['geo']['x_land'] - 86.4
            add(f'wleaf_{st}_{pc}', 'qkd_kvwq_leaf', x, cdc.y, 86.4-SHAVE, 183.6-SHAVE,
                'R0' if side == 'W' else 'MY', 'kv_write_leaf', 'strip')
        land = by[f'land_{st}']
        x = m['geo']['x_land'] + 86.4 + GX if side == 'W' else m['die']['w'] - m['geo']['x_land'] - 86.4 - GX - 172.8
        y = up(land.y + (land.h - 518.4)/2, GY)
        add(f'wctl_{st}', 'qkd_kvwq_ctl', x, y, 172.8-SHAVE, 518.4-SHAVE,
            'R0' if side == 'W' else 'MY', 'kv_write_ctl', 'strip')
        for g in range(4):
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
        elif bid.startswith('kvn_'):
            st = bid[4:]
            buses.append((bid, cl, bits, [('seq', f'kvn_{st}'), (f'wctl_{st}', 'kvn')]))
        else:
            buses.append((bid, cl, bits, eps))
    m['buses'] = buses
    m['wq_straps'] = {}
    for st in STACKS:
        ctl = f'wctl_{st}'
        buses += [(f'wdurable_{st}', 'spine_local', 23, [(ctl, 'durable'), (f'land_{st}', 'wdurable')]),
                  (f'wfault_{st}', 'spine_local', 1, [(ctl, 'fault'), (f'land_{st}', 'wfault')])]
        for g in range(4):
            enc = f'wenc_{st}_{g}'
            chain = [f'wleaf_{st}_{8*g+i}' for i in range(7, -1, -1)]
            buses += [(f'wfeed_{st}_{g}', 'spine_local', 298, [(ctl, f'f{g}'), (enc, 'a')]),
                      (f'wencoded_{st}_{g}', 'spine_local', 293, [(enc, 'b'), (chain[0], 'c')]),
                      (f'wret_{st}_{g}', 'spine_local', 2, [(chain[0], 'dp'), (ctl, f'r{g}')])]
            for a, b in zip(chain, chain[1:]):
                buses += [(f'wchain_{a}', 'spine_local', 293, [(a, 'n'), (b, 'c')]),
                          (f'wback_{a}', 'spine_local', 2, [(b, 'dp'), (a, 'dn')])]
            buses.append((f'wtail_{st}_{g}', 'constant', 2, [(chain[-1], 'dn')]))
            for pc in range(8*g, 8*g+8):
                leaf = f'wleaf_{st}_{pc}'
                m['wq_straps'][f'wlane_{st}_{pc}'] = pc % 8
                buses.append((f'wlane_{st}_{pc}', 'constant', 3, [(leaf, 'lane')]))
        for kind, srcport, dstport in [('clock_trunk', f'pll_{st}', 'ck'), ('reset', f'rso_{st}', 'rst_n')]:
            buses.append((f'wq_{kind}_{st}', kind, 1, [('pll', srcport)] +
                          [(f'wleaf_{st}_{pc}', dstport) for pc in range(32)] + [(ctl, dstport)]))


def strict_ports(M):
    """every RTL port of every bound master is in exactly one die port (or classed debug / by_design) and every die
    port of the master is bound.  -> dict(ok, failures, rows)."""
    import re as _re
    rows, fails = [], []
    for mst, b in BINDINGS.items():
        if mst not in M:
            continue
        txt = _re.sub(r'//[^\n]*', '', (ROOT / b['file']).read_text())
        mm = _re.search(r'module\s+' + b['module'] + r'\b.*?\);', txt, _re.S)
        rtl = set(_re.findall(r'(?:input|output)\s+(?:wire|reg)?\s*(?:\[[^\]]*\])?\s*(\w+)', mm.group(0)))
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
        master = dict(qfd_ctrl='qkd_ctrl', qfd_cdc='qkd_cdc').get(d['master'], d['master'])
        out.append((n, master, x, d['y'] + dy[half], d['w'], d['h'], d['orient'], d['kind'], d['domain']))
    return out, dy


def build(r=R, kv_wq_leaves=False):
    T = tpl()
    I = T['insts']
    stack_h = I['ctrl_WS']['h']
    Hk = up(2 * MARGIN + 2 * stack_h + GY, GY)
    # x layout (W half; E mirrors)
    x_land = I['cdc_WS_0']['x'] + I['cdc_WS_0']['w'] + GX
    leaf_shift = 518.4 + GX if kv_wq_leaves else 0.0
    x_grp = up(x_land + leaf_shift + LAND_W + CHAN, GX)
    grp_w = 2 * RENG[0] + ASTK_W + 2 * GX
    centre_w = max(UCIE[1], FRAMES["qkd_ahub"][0]) + 4 * CHAN   # re-cut H engines are 1,953 um: the centre relay channel needs 2 x 259 (was 2 x 130)
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
        band_dy[side] = dy
        for n, mst, x, y, w, h, o, k, dom in rows:
            add(n, mst, x, y, w, h, o, k, 'phy' if k == 'phy' else ('ctrl' if k == 'ctrl' else 'strip'), dom)
    ystack = {'S': MARGIN, 'N': MARGIN + stack_h + GY}
    xc = Wk / 2
    for st in STACKS:
        side, half = st[0], st[1]
        y0 = ystack[half]
        lx = x_land + leaf_shift if side == 'W' else Wk - x_land - leaf_shift - LAND_W
        add(f'land_{st}', 'qkd_land', lx, y0, LAND_W - SHAVE, stack_h - SHAVE, 'MY' if side == 'W' else 'R0',
            'land', 'strip')
        gx = x_grp if side == 'W' else Wk - x_grp - grp_w
        gh = 4 * RENG[1] + 3 * GY
        gy = up(y0 + (stack_h - gh) / 2, GY)
        add(f'astk_{st}', 'qkd_astk', gx + RENG[0] + GX, gy, ASTK_W - SHAVE, gh - SHAVE, 'R0', 'attn_stack', 'attn')
        for e in range(r):
            col = e // 4
            ex = gx if col == 0 else gx + RENG[0] + ASTK_W + 2 * GX
            ey = gy + (e % 4) * (RENG[1] + GY)
            o_up, o_dn = ('R0', 'MX') if col == 0 else ('MY', 'R180')
            for h in range(4):
                add(f'head_{st}_{e}_{h}', 'qkd_rhead', ex, ey + TILE_Y[f'h{h}'], HEAD[0] - SHAVE, HEAD[1] - SHAVE,
                    o_dn if h < 2 else o_up, 'row_engine', 'attn')
            add(f'ectl_{st}_{e}', 'qkd_ectl', ex, ey + TILE_Y['c'], ECTL[0] - SHAVE, ECTL[1] - SHAVE,
                o_up, 'row_engine', 'attn')
    # centre column: N edge stack, hub, S edge host
    uy = Hk - MARGIN - UCIE[2]
    add('ucie_rom', UCIE[0], xc - UCIE[1] / 2, uy, UCIE[1] - SHAVE, UCIE[2] - SHAVE, 'MX', 'phy_d2d', 'io')
    dw, dh = FRAMES['qkd_d2d']
    add('d2d_kv', 'qkd_d2d', xc - dw / 2, up(uy - GY - dh, GY), dw - SHAVE, dh - SHAVE, 'R0', 'd2d', 'io')
    sw, sh = FRAMES['qkd_seq']
    sy = up(uy - 2 * GY - dh - sh, GY)
    add('seq', 'qkd_seq', xc - sw / 2, sy, sw - SHAVE, sh - SHAVE, 'R0', 'seq', 'ctl')
    gw_, gh_ = FRAMES['qkd_embgw']
    add('embgw', 'qkd_embgw', xc - gw_ / 2, up(sy - GY - gh_, GY), gw_ - SHAVE, gh_ - SHAVE, 'R0', 'embgw', 'ctl')
    cw_, ch_ = FRAMES['qkd_ckbump']
    add('ckb_kv', 'qkd_ckbump', xc - UCIE[1] / 2 - cw_ - 10 * GX, Hk - MARGIN - ch_, cw_ - SHAVE, ch_ - SHAVE, 'R0', 'bump', 'io')
    pw, ph = FRAMES['qkd_pll']
    add('pll', 'qkd_pll', xc + UCIE[1] / 2 + GX * 10, Hk - MARGIN - ph, pw - SHAVE, ph - SHAVE, 'R0', 'pll', 'io')
    hw, hh = FRAMES['qkd_ahub']
    add('ahub', 'qkd_ahub', xc - hw / 2, up(Hk / 2 - hh / 2, GY), hw - SHAVE, hh - SHAVE, 'R0', 'attn_hub', 'attn')
    add('serdes_host', SERDES[0], xc - SERDES[1] / 2, MARGIN, SERDES[1] - SHAVE, SERDES[2] - SHAVE, 'R0', 'phy_host',
        'io', 'link_serdes')
    tw, th = FRAMES['qkd_host']
    add('host', 'qkd_host', xc - tw / 2, MARGIN + SERDES[2] + GY, tw - SHAVE, th - SHAVE, 'R0', 'host', 'io')
    m['geo'] = dict(x_land=x_land, x_grp=x_grp, grp_w=grp_w, centre_w=centre_w, stack_h=stack_h, band_dy=band_dy,
                    ystack=ystack, r=r, kv_wq_leaves=kv_wq_leaves, leaf_shift=leaf_shift)
    if kv_wq_leaves:
        _write_tiles(m, add)
    _buses(m, T, r)
    if kv_wq_leaves:
        _write_buses(m)
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
        if all(i in names for i, _ in ne):
            B.append((bid, cl, bits, ne))
    add = B.append
    cdcs = {st: [i.name for i in m['insts'] if i.name.startswith(f'cdc_{st}_')] for st in STACKS}
    # clocks (PLL core trunks a stack group + the centre) and resets
    for st in STACKS:
        grp = [(f'land_{st}', 'ck'), (f'astk_{st}', 'ck')] + [(f'ectl_{st}_{e}', 'ck') for e in range(r)] + \
              [(f'head_{st}_{e}_{h}', 'ck') for e in range(r) for h in range(4)] + \
              [(c, 'clk') for c in cdcs[st]]
        add((f'clk_core_{st}', 'clock_trunk', 1, [('pll', f'pll_{st}')] + grp))
        add((f'rst_core_{st}', 'reset', 1, [('pll', f'rso_{st}'), (f'ctrl_{st}', 'rsi')] +
             [(n, 'rst_n') for n, _ in grp if not n.startswith('cdc_')]))   # the CDC core resets come from land.crst (r21c rst_kv)
    cen = ['d2d_kv', 'seq', 'embgw', 'ahub', 'host']
    add(('clk_core_c', 'clock_trunk', 1, [('pll', 'pll_c')] + [(n, 'ck') for n in cen] +
         [('ucie_rom', 'clk'), ('serdes_host', 'clk')]))
    add(('rst_core_c', 'reset', 1, [('pll', 'rso_c')] + [(n, 'rst_n') for n in cen] +
         [('ucie_rom', 'rst_n'), ('serdes_host', 'rst_n')]))
    add(('pll_fwd', 'clock_trunk', 1, [('pll', 'pll_fwd'), ('ckb_kv', 'pll_ck')]))       # to the clock bump pair
    add(('rst_fwd', 'reset', 1, [('pll', 'rso_fwd'), ('ckb_kv', 'rs')]))
    # the link
    add(('d2d_fdi', 'd2d_fdi', FDI_UCIE, [('d2d_kv', 'fdi'), ('ucie_rom', 'fdi')]))
    add(('d2d_dn', 'd2d_face', 4 * (W + 1) + 4, [('d2d_kv', 'rf'), ('seq', 'rf')]))       # CTL Q KVN EMBQ + credits back
    add(('d2d_up', 'd2d_face', 3 * (W + 1) + 3, [('seq', 'tf'), ('d2d_kv', 'tf')]))       # RES EMBD HCTL + credits back
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
            add((f'krq_{st}_{e}', 'spine_local', 16, [(c_, 'rq'), (f'land_{st}', f'rq{e}')]))
            add((f'krs_{st}_{e}', 'spine_local', 1 + 1024, [(f'land_{st}', f'rs{e}'), (c_, 'rs')]))
        add((f'kvn_{st}', 'kvn', 1024 + 2 + 14 + 6 + 1 + 1, [('seq', f'kvn_{st}'), (f'land_{st}', 'kvn')]))
        add((f'emf_{st}', 'kvn', W + 2, [('embgw', f'emf_{st}'), (f'land_{st}', 'emf')]))
        add((f'emr_{st}', 'kvn', W + 2, [(f'land_{st}', 'emr'), ('embgw', f'emr_{st}')]))
        add((f'ing_{st}', 'kvn', W + 2, [('host', f'ing_{st}'), (f'land_{st}', 'ing')]))
    add(('ares', 'spine_local', 1 + 1 + 6 + 512, [('ahub', 'ao'), ('seq', 'ar')]))
    add(('hs', 'spine_local', 1, [('seq', 'hs'), ('ahub', 'hs')]))                  # layer start to the hub
    add(('d2df', 'spine_local', 6, [('d2d_kv', 'flt'), ('seq', 'd2df')]))            # link-end fault + cause
    add(('kst', 'spine_local', 10, [('seq', 'kst'), ('host', 'kst')]))               # KV-die status to the host
    add(('hf', 'spine_local', 1, [('ahub', 'hf'), ('seq', 'hf')]))                  # hub fault
    for st in STACKS:
        add((f'af_{st}', 'spine_local', 1, [(f'astk_{st}', 'af'), ('seq', f'af_{st}')]))
        add((f'mf_{st}', 'spine_local', 1, [(f'land_{st}', 'mf'), ('seq', f'mf_{st}')]))
    add(('gq', 'kvn', W + 2, [('seq', 'gq'), ('embgw', 'gq')]))
    add(('gr', 'kvn', W + 2, [('embgw', 'gr'), ('seq', 'gr')]))
    add(('hc', 'kvn', W + 2, [('host', 'hc'), ('seq', 'hc')]))
    add(('tk', 'kvn', W + 2, [('seq', 'tk'), ('host', 'tk')]))
    add(('host_fdi', 'd2d_fdi', FDI_SERDES, [('host', 'fdi'), ('serdes_host', 'fdi')]))


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
    G = GRID
    nx, ny = int(Wd // G) + 1, int(Hd // G) + 1
    owner = {}
    for it in m['insts']:
        for gx in range(int(it.x // G), int((it.x + it.w) // G) + 1):
            for gy in range(int(it.y // G), int((it.y + it.h) // G) + 1):
                owner.setdefault((gx, gy), set()).add(it.name)
    occ = [(i.x, i.y, i.x + i.w, i.y + i.h) for i in m['insts']]
    rocc = {}

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

    def route(a, b):
        src, dst = ring(by[a]), set(ring(by[b]))
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
                if q not in prev and 0 <= q[0] < nx and 0 <= q[1] < ny and not owner.get(q):
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
    for bid, cl, bits, eps in m['buses']:
        if cl in ABUT or cl in ('clock_trunk', 'reset', 'constant') or len(eps) != 2:
            nb.append((bid, cl, bits, eps))
            stages[bid] = 0
            continue
        (a, pa), (b, pb) = eps
        path = route(a, b)
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
        prev_r, prev_ep, k, idx0 = rect(by[a]), (a, pa), 0, 0
        offs = [(0, 0)] + [(i * G, j * G) for r_ in (1, 2, 3) for i in range(-r_, r_ + 1) for j in range(-r_, r_ + 1)
                           if max(abs(i), abs(j)) == r_]
        while near_d(prev_r, rect(by[b])) > REACH_TARGET:
            got = None
            # the farthest path point (from the previous chain point) with a free spot within reach
            for idx in range(min(len(path) - 1, idx0 + int(REACH_TARGET // G) + 2), idx0, -1):
                px, py = path[idx]
                for dx_, dy_ in offs:
                    qx, qy = up(px + dx_ - fw / 2, GX), up(py + dy_ - fh / 2, GY)
                    if near_d(prev_r, (qx, qy, qx + fw, qy + fh)) <= REACH_TARGET and free(qx, qy, fw, fh):
                        got = (qx, qy, idx)
                        break
                if got:
                    break
            if got is None:
                raise ValueError(f'kv die relays: no spot for {bid} stage {k} after path index {idx0}')
            nm = f'rly_{bid}_{k}'
            it = F.Inst(nm, mst, got[0], got[1], fw - SHAVE, fh - SHAVE, 'R0', kind='relay', region='relay')
            m['insts'].append(it)
            for gx in range(int(it.x // G), int((it.x + fw) // G) + 1):
                for gy in range(int(it.y // G), int((it.y + fh) // G) + 1):
                    rocc.setdefault((gx, gy), []).append((it.x, it.y, it.x + fw, it.y + fh))
            nb.append((f'{bid}__r{k}' if k else bid, cl, bits, [prev_ep, (nm, 'a')]))
            prev_ep, prev_r, idx0, k = (nm, 'b'), (it.x, it.y, it.x + fw, it.y + fh), got[2], k + 1
        n = k
        stages[bid] = n
        if n == 0:
            nb.append((bid, cl, bits, eps))
            continue
        nb.append((f'{bid}__r{n}', cl, bits, [prev_ep, (b, pb)]))
    m['buses'] = nb
    m['relay_stages'] = stages
    m['route_um'] = lengths


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
    M = {}
    tmap = dict(qkd_ctrl='qfd_ctrl', qkd_cdc='qfd_cdc', qkd_land='qfd_kvc')
    if m['geo'].get('kv_wq_leaves'):
        tmap['qkd_cdc_wleaf'] = 'qfd_cdc'     # ot_hbm3e_phy: the real LEF (k = 1)
    for name, src in tmap.items():
        t = T['masters'][src]
        if name == 'qkd_land':
            mm = F.Master(name, LAND_W - SHAVE, m['geo']['stack_h'] - SHAVE, 7, 'KV landing (qfd_kvc successor)')
            land = by['land_WS']
            for p in t['order']:
                if p in used.get(name, {}):
                    sp = list(t['ports'][p])
                    mt = __import__('re').fullmatch(r'c(\d+)([io])', p)
                    if mt and sp[0] == 'face':
                        cdc = by[f'cdc_WS_{mt.group(1)}']        # every stack has the same CDC column layout
                        sp[4] = cdc.y + cdc.h / 2 - land.y + (40.0 if mt.group(2) == 'i' else -40.0)
                    if sp[0] == 'face' and sp[1] * 0.096 + 4.0 < (mm.w if sp[2] in 'NS' else mm.h):
                        sp[5] = 2          # 2-track pitch where the face has room (emf[221] DRT-0073 at 1 track)
                    mm.ports[p] = tuple(sp)
                    mm.order.append(p)
        else:
            mm = F.Master(name, t['w'], t['h'], t['obs_top'], t['note'])
            for p in (dict.fromkeys(t['order']) if name == 'qkd_cdc_wleaf' else t['order']):
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
            if mst == 'qkd_ectl':
                # the tile column: si / so to the aggregator (E), the pair-0 copy / returns S, pair-1 N, KV rows W
                face = {'si': 'E', 'so': 'E', 't0': 'S', 'e0': 'S', 'e1': 'S', 's0': 'S', 's1': 'S',
                        't1': 'N', 'e2': 'N', 'e3': 'N', 's2': 'N', 's3': 'N'}.get(p, 'W')
            if mst == 'qkd_rhead':
                face = 'E' if p == 'nb' else 'S'  # the S face faces the control tile (heads 0 / 1 are MX)
            if mst == 'qkd_land' and face in 'NS':
                # the landing is a 172.8 um x 12 mm column: its short faces cannot hold its words (die_kv7: 3,186
                # overlapping pin shapes, PA DRT-0073); every word leaves on the long face toward its peer
                face = 'E' if dxp > 0 else 'W'
            if mst == 'qkd_astk' and p[0] in 'ef' and p[1].isdigit():
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
            mm.face(p, bits, face, layer, 0.0, 2 if (mst in ('qkd_ectl', 'qkd_rhead', 'qkd_astk') or (mst == 'qkd_land' and face in 'NS')) else 1)
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
                if mst == 'qkd_astk' and p[0] in 'ef' and p[1].isdigit():
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
    for mst in list(M):
        if mst not in used and mst not in sizes:
            M.pop(mst)
    return M


_BASE_PORT_WIDTHS = F.port_widths


def port_widths(m, k=1):
    return _BASE_PORT_WIDTHS(m, k)


def write_netlist(m, k, path, top='qkd_die'):
    F.write_netlist(m, k, path, top=top)
    if not m['geo'].get('kv_wq_leaves'):
        return
    if k != 1:
        raise ValueError('per-PC leaves require full-width nets (k=1)')
    # These constants are die-top straps, not muxes or a second CDC writer.
    p = Path(path)
    txt = p.read_text()
    ties = [f"  assign n_{bid} = 3'd{lane};" for bid, lane in m['wq_straps'].items()]
    ties += [f"  assign n_wtail_{st}_{g} = 2'b00;" for st in STACKS for g in range(4)]
    txt = txt.replace('endmodule', '\n'.join(ties) + '\nendmodule', 1)
    p.write_text(txt)
    # Explicit nine OR2-equivalent gates a group; no silent 8-bit/3-bit rename.
    # This module is functional composition RTL only.  The die physical abstract
    # remains UNQUALIFIED until this encoder closes at SS/FF in context.
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
    if m['geo'].get('kv_wq_leaves'):
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
    # so the PG check sees them connected (die_kv2..4: 1,000 PSM-0038 unconnected M4 shapes over x 20.8 - 853.3 um)
    (work / 'pdn.tcl').write_text((work / 'pdn.tcl').read_text() + '''
set phy_cells {}
foreach mst [[ord::get_db] getLibs] { foreach c [$mst getMasters] { if {[string match ot_hbm3e_phy* [$c getName]]} { lappend phy_cells [$c getName] } } }
if {[llength $phy_cells]} {
  define_pdn_grid -macro -cells $phy_cells -halo {0 0 0 0} -voltage_domains {CORE} -name {phy}
  add_pdn_stripe -grid {phy} -layer {M8} -width {0.48} -pitch {10.88} -offset {1.0}
  add_pdn_stripe -grid {phy} -layer {M9} -width {0.48} -pitch {10.88} -offset {1.0}
  add_pdn_connect -grid {phy} -layers {M4 M8}
  add_pdn_connect -grid {phy} -layers {M8 M9}
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
    a = ap.parse_args(argv)
    if a.mode == 'case' and a.kv_wq_leaves:
        ap.error('per-PC leaf candidate is plan-only: encoder and closed-view pin/context gates remain open')
    m = build(a.r, kv_wq_leaves=a.kv_wq_leaves)
    if a.mode == 'case':
        m['buses'] = [(bid, cls, bits, eps) for bid, cls, bits, eps in m['buses']]
        print(json.dumps(case(m, a.out)))
        return 0
    rec = record(m)
    rec['legality'] = check(m)
    M = masters(m, 1)
    rec['masters_abstract'] = {n: dict(w=round(mm.w, 3), h=round(mm.h, 3), ports=len(mm.order)) for n, mm in M.items()}
    rec['strict_ports'] = strict_ports(M)
    if a.kv_wq_leaves:
        rec['kv_wq_candidate'] = dict(adopted=False, leaves=128, control_tiles=4, encoder_tiles=16,
            encoder='3 OR4 per group; matches ot_qkvd_kv_wq_leaves exactly; SS/FF context closure owed',
            gate='BLOCKED_ENCODER_PHYSICAL_CLOSURE', chain_order='PC 8*g+7 through 8*g N-to-S, lane strap PC%8',
            cdc_ci_slices=dict(wi=[0,290], wr=[290,11], cf=[301,1]),
            chain_hop_cycles=dict(feed=2, done=1), relay_cycles=m['relay_stages'],
            controller_group_slices={g: dict(f_v=[g,1], f_d=[256*g,256], f_sec=[24*g,24],
                                             f_lane=[8*g,8], f_tag=[9*g,9], r_v=[g,1], r_bad=[g,1]) for g in range(4)},
            physical_gate='closed leaf/ctl pin shapes and context SS/FF must replace candidate abstracts',
            encoder_sizing=dict(or4_per_group=3, or2_equivalent_total=144,
                                reserved_frame_mm2=round(16*43.2*43.2/1e6,6), measured_cell_area=None))
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'plan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    (a.out / 'insts.json').write_text(json.dumps([i.d() for i in m['insts']]) + '\n')
    write_netlist(m, 1, a.out / 'kv_die.v', top='qkd_die')
    print(json.dumps({k_: rec[k_] for k_ in ('die_um', 'die_mm2', 'instances', 'fill', 'legality')}))
    return 0 if not rec['legality']['overlaps'] and not rec['legality']['outside'] else 1


if __name__ == '__main__':
    sys.exit(main())
