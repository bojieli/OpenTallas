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
        aggregator: the engine <-> aggregator words are 16.5 k / 16.8 k bits, ot_qwen_nearhbm_row_engine_p ports)

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
up = F.up
TPL_PATH = ROOT / 'tools' / 'qwen_kv_die' / 'r21c_band.json'
MARGIN = 21.6
R = 8                           # row engines a stack (near-HBM gate R = 8: 1,824 cycles at ctx 8192)
RENG = (328.32, 1998.0)         # r17b qfd_reng frame (310 k um2 synthesised row engine at ~0.47)
ASTK_W = 777.6                  # stack aggregator column (q registers, exp, Z / P.V trees): ASSUMED ~3 mm2 cells at 0.5
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
ENG_IN = 1 + 14 + 3 + 1 + 16384 + 32 + 64 + 1          # start, T, cyc8, q_ready, q_bf16, exp_done, er_data, lf_take
ENG_OUT = 1 + 12 + 1 + 12 + 128 + 256 + 2 + 1 + 1 + 4 + 3 + 16384 + 1 + 1 + 1   # er, sc, lmax, lf, k/v_done, fault
ABUT = {'stack_local', 'phy_dfi', 'd2d_fdi', 'hbm_cdc', 'cdc_core'}    # abutted / band buses: no relays
RTL = dict(qkd_ctrl='qfd_ctrl element (rtl/qwen_sys/emb_hbm_20261008/ot_qwen_ctrl_pc_emb.sv + per-PC leaves)',
           qkd_cdc='rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv ot_qwen_stream4_cdc_pc (route r11a)',
           qkd_land='qfd_kvc successor (landing crossbar) + ot_qkvd_kv_seq KV-merge slices + ot_qfd_emb_strip',
           qkd_reng='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv ot_qwen_nearhbm_row_engine_p',
           qkd_astk='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv ot_qwen_nearhbm_attn_stack_p minus its engines',
           qkd_ahub='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv ot_qwen_nearhbm_attn_hub_p',
           qkd_seq='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq.sv ot_qkvd_kv_seq',
           qkd_d2d='rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_end.sv ot_qkvd_kv_end (ot_qkvd_d2d NT 3 / NR 4)',
           qkd_embgw='rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_gw.sv ot_qfd_emb_gw',
           qkd_host='qfd_io_host successor (ingest stream: hing_qfd) + SerDes adapter ot_qfd_link_adapter',
           qkd_pll='vendor PLL abstract + ot_qwen_sys_rst_seq (ASSUMED frame)')


# die port -> RTL ports of the bound module (strict_ports: every RTL port is in exactly one die port or is classed)
BINDINGS = dict(
    qkd_reng=dict(module='ot_qwen_nearhbm_row_engine_p', file='rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv',
                  ports=dict(si=['start_in', 'T_in', 'cyc8_in', 'q_ready', 'q_bf16', 'exp_done', 'er_data', 'lf_take'],
                             so=['er_valid', 'er_addr', 'sc_valid', 'sc_addr', 'sc_data', 'lmax', 'lmax_any', 'lf_valid',
                                 'lf_g', 'lf_gam', 'lf_slot', 'lf_data', 'k_done', 'v_done', 'fault'],
                             rq=['req_valid', 'req_v', 'req_g', 'req_t'], rs=['rsp_valid_in', 'rsp_data_in'],
                             ck=['clk'], rst_n=['rst_n']),
                  classed={'ev_k_first': 'debug', 'ev_v_first': 'debug'}),
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
FRAME_ONLY = dict(qkd_astk='ot_qwen_nearhbm_attn_stack_p minus its engines (re-cut owed: q registers into the engines '
                           'or abutted 16 k-bit faces, see review_queue/kv-die.md)',
                  qkd_land='qfd_kvc crossbar successor + ot_qkvd_kv_merge (rtl/qwen_sys/kv_die_20261009) + ot_qfd_emb_strip',
                  qkd_embgw='ot_qfd_emb_gw + the gateway link side (r21c hub link FIFOs)',
                  qkd_host='qfd_io_host successor (hing_qfd ingest) + ot_qfd_link_adapter', qkd_pll='vendor PLL + '
                  'ot_qwen_sys_rst_seq', qkd_ctrl='qfd_ctrl (r21c element, unchanged)',
                  qkd_ckbump='clock / reset bump pair to the ROM die (pad cell, no logic: by design)')


def strict_ports(M):
    """every RTL port of every bound master is in exactly one die port (or classed debug / by_design) and every die
    port of the master is bound.  -> dict(ok, failures, rows)."""
    import re as _re
    rows, fails = [], []
    for mst, b in BINDINGS.items():
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


def build(r=R):
    T = tpl()
    I = T['insts']
    stack_h = I['ctrl_WS']['h']
    Hk = up(2 * MARGIN + 2 * stack_h + GY, GY)
    # x layout (W half; E mirrors)
    x_land = I['cdc_WS_0']['x'] + I['cdc_WS_0']['w'] + GX
    x_grp = up(x_land + LAND_W + CHAN, GX)
    grp_w = 2 * RENG[0] + ASTK_W + 2 * GX
    centre_w = max(UCIE[1], FRAMES['qkd_ahub'][0]) + 2 * CHAN
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
        lx = x_land if side == 'W' else Wk - x_land - LAND_W
        add(f'land_{st}', 'qkd_land', lx, y0, LAND_W - SHAVE, stack_h - SHAVE, 'MY' if side == 'W' else 'R0',
            'land', 'strip')
        gx = x_grp if side == 'W' else Wk - x_grp - grp_w
        gh = 4 * RENG[1] + 3 * GY
        gy = up(y0 + (stack_h - gh) / 2, GY)
        add(f'astk_{st}', 'qkd_astk', gx + RENG[0] + GX, gy, ASTK_W - SHAVE, gh - SHAVE, 'R0', 'attn_stack', 'attn')
        for e in range(r):
            col = e // 4
            ex = gx if col == 0 else gx + RENG[0] + ASTK_W + 2 * GX
            add(f'reng_{st}_{e}', 'qkd_reng', ex, gy + (e % 4) * (RENG[1] + GY), RENG[0] - SHAVE, RENG[1] - SHAVE,
                'R0' if col == 0 else 'MY', 'row_engine', 'attn')
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
                    ystack=ystack, r=r)
    _buses(m, T, r)
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
        grp = [(f'land_{st}', 'ck'), (f'astk_{st}', 'ck')] + [(f'reng_{st}_{e}', 'ck') for e in range(r)] + \
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
            add((f'eq_{st}_{e}', 'stack_local', ENG_IN, [(f'astk_{st}', f'e{e}o'), (f'reng_{st}_{e}', 'si')]))
            add((f'el_{st}_{e}', 'stack_local', ENG_OUT, [(f'reng_{st}_{e}', 'so'), (f'astk_{st}', f'e{e}i')]))
            add((f'krq_{st}_{e}', 'spine_local', 16, [(f'reng_{st}_{e}', 'rq'), (f'land_{st}', f'rq{e}')]))
            add((f'krs_{st}_{e}', 'spine_local', 1 + 1024, [(f'land_{st}', f'rs{e}'), (f'reng_{st}_{e}', 'rs')]))
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
        if cl in ABUT or cl in ('clock_trunk', 'reset') or len(eps) != 2:
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
    tmap = dict(qkd_ctrl='qfd_ctrl', qkd_cdc='qfd_cdc', qkd_land='qfd_kvc')     # ot_hbm3e_phy: the real LEF (k = 1)
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
                    mm.ports[p] = tuple(sp)
                    mm.order.append(p)
        else:
            mm = F.Master(name, t['w'], t['h'], t['obs_top'], t['note'])
            for p in t['order']:
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
            if mst == 'qkd_reng' and p in ('si', 'so'):
                face = 'E'                       # the long face that abuts the aggregator (MY engines mirror it)
            if mst == 'qkd_astk' and p.startswith('e'):
                face = 'W' if int(p[1:-1]) < 4 else 'E'
            layer = 'M4' if face in ('E', 'W') else 'M5'
            if (mst == 'qkd_reng' and p == 'so') or (mst == 'qkd_astk' and p.startswith('e') and p.endswith('i')):
                layer = 'M6'                     # the 16.8 k-bit leaf word on M6, the 16.5 k-bit q word on M4 (same face)
            L = mm.h if face in ('E', 'W') else mm.w
            fl = face_load.setdefault((mst, face), [])
            mm.face(p, bits, face, layer, 0.0, 1)
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
                if mst == 'qkd_astk' and p.startswith('e'):
                    e = int(p[1:-1])
                    sp[4] = (e % 4) * (RENG[1] + GY) + RENG[1] / 2      # level with its engine (o on M4, i on M6)
                if mst == 'qkd_reng' and p in ('si', 'so'):
                    sp[4] = RENG[1] / 2
                mm.ports[p] = tuple(sp)
                pos += span
    for mst in list(M):
        if mst not in used and mst not in sizes:
            M.pop(mst)
    return M


_BASE_PORT_WIDTHS = F.port_widths


def port_widths(m, k=1):
    return _BASE_PORT_WIDTHS(m, k)


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
                assumed=dict(row_engine_frame='r17b qfd_reng 328.32 x 1,998 (310 k um2 synthesised, ~0.47)',
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
    saved = F.masters, F.port_widths
    F.masters, F.port_widths = masters, port_widths
    try:
        man = F.case_real(m, work)
    finally:
        F.masters, F.port_widths = saved
    run = (work / 'run.tcl').read_text()
    (work / 'run_pdn.tcl').write_text((work / 'run_pa.tcl').read_text())
    man.update(die='qwen_kv', die_um=[m['die']['w'], m['die']['h']], generator='tools/qwen_kv_die/kv_die.py')
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['plan', 'case'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--r', type=int, default=R)
    a = ap.parse_args(argv)
    m = build(a.r)
    if a.mode == 'case':
        m['buses'] = [(bid, cls, bits, eps) for bid, cls, bits, eps in m['buses']]
        print(json.dumps(case(m, a.out)))
        return 0
    rec = record(m)
    rec['legality'] = check(m)
    M = masters(m, 1)
    rec['masters_abstract'] = {n: dict(w=round(mm.w, 3), h=round(mm.h, 3), ports=len(mm.order)) for n, mm in M.items()}
    rec['strict_ports'] = strict_ports(M)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'plan.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    (a.out / 'insts.json').write_text(json.dumps([i.d() for i in m['insts']]) + '\n')
    F.write_netlist(m, 1, a.out / 'kv_die.v', top='qkd_die')
    print(json.dumps({k_: rec[k_] for k_ in ('die_um', 'die_mm2', 'instances', 'fill', 'legality')}))
    return 0 if not rec['legality']['overlaps'] and not rec['legality']['outside'] else 1


if __name__ == '__main__':
    sys.exit(main())
