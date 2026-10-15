#!/usr/bin/env python3
"""qwen-split/kvsys v1.2 (2026-10-14, die lead r4; owner 08:05 PT NO STUBS): the KV/system die's strip frames bound to
REAL RTL = wires-only compositions of the CLOSED strip leaves (el1013-qwen-kvstrips), each leaf its own clock entry.

  qkd_land / qkd_land_n -> qkd_land_strip_s : 32 x qkd_land_pc + 8 x qkd_land_grp + qkd_land_emb (all CLOSED, native PASS)
  qkd_astk / qkd_astk_n -> qkd_astk_strip_s : 64 x qkd_astk_pv_tp8 + 32 x qkd_astk_ex + 8 x qkd_astk_ep + 4 x qkd_astk_zn
                                              + qkd_astk_ctl_tp8 (the benched die wiring of ot_qkd_astk_strip,
                                              rtl/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv, KVD_ASTK_TP8)

  qkd_ctrl / qkd_ctrl_n -> qkd_ctrl_strip_s : 32 x qkd_ctrl_pc (np1) + qkd_ctrl_kc (ks2) (all CLOSED): PC k = strap pc k, its
                                              CDC ci / co, its landing es / er and its PHY slice po / pi (the HBM PHY
                                              abstract qkd_hbm3e_phy_pc: per-PC DFI, the controller is OUR RTL); kc chain
                                              kc -> kc leaf -> pc31 .. pc0 (N -> S), fault chain pc0 .. pc31 -> kc.fi, kf out

The die frame ports ARE the strip's ports (per-PC / per-engine die ports = explicit RTL ports, so no slice-order
convention is involved); strip-internal relay stations (the registered stations a 12-mm strip needs on every net that is
not an abutment) are ot_hdc_delay lines on their own clock entry ck_r, exactly as the benched astk composition does.

Land strip die wiring (new, this file is its single source):
  slot s = 4 i + q (i = 0..7 from the S end) hosts physical PC s (CDC s: c<s>i / cf<s>; controller leaf s: es<s> / er<s>)
  and LOGICAL PC {q, G(i)} (lpc = 8 q + G(i), G = kv_die.LAND_GROUP_ORDER); group leaf i (g = G(i)) takes the gw / gc of
  its four slots and the engine G(i)'s rq / rs.
  chains (one flop a leaf, abutted 378 um hops): down dno(emb) -> pc31 .. pc0; up pc0 .. pc31 -> emb.upi; credit
  pc0 .. pc31 -> emb.cri; PC fault kf (controller strip) -> pc0.fi .. pc31.fo -> emb.fi; group fault wf (write-queue
  controller) -> grp0.fi .. grp7.fo -> emb.gfi; emb.mf -> mf.
  KV write words: kvn enters at the strip middle (die port kvn, from the sequencer), one registered station each way,
  leaves on kvo to the write-queue controller (die port kvo; +1 cycle a way on the posted-write path) and fans out as
  kn to the 8 groups (the KV merge's write-then-read fence) on two registered chains (S / N of the middle) with a tap at
  each group: depth ceil(|y_grp - y_mid| / 450 um) = 12 9 6 2 | 2 6 9 12; lt (layer start / T / index, die port lt)
  rides the same chains, so kn and lt reach a group with the same delay.

    python3 tools/qwen_kv_die/kv_strips.py --out rtl/qwen_sys/split_20261014/qkd_strips_s.sv
"""
import argparse
import math
from pathlib import Path

NPC, NGRP, NENG = 32, 8, 8
LAND_GROUP_ORDER = (4, 5, 0, 1, 2, 3, 6, 7)
PC_PITCH = 378.0
HOP_UM = 450.0
W_LI, W_ES, W_ER, W_RQ, W_RS, W_LT, W_KN = 282, 288, 261, 17, 1025, 21, 1047
W_EMF, W_EMR = 289, 521  # compact gateway word + its reverse credit


def land_depths():
    """registered stages from the strip middle to each group's tap (S chain: groups 3..0, N chain: groups 4..7)"""
    ymid = PC_PITCH * NPC / 2
    return [max(1, math.ceil(abs(PC_PITCH * (4 * i + 2) - ymid) / HOP_UM)) for i in range(NGRP)]


def land_ports():
    """{die port: [RTL ports]} of the land frame (qkd_land / qkd_land_n), clock entries apart"""
    p = {}
    for k in range(NPC):
        p[f'c{k}i'] = [f'li{k}', f'lp{k}']
        p[f'cf{k}'] = [f'cf{k}']
        p[f'es{k}'] = [f'es{k}']
        p[f'er{k}'] = [f'er{k}']
    for e in range(NENG):
        p[f'rq{e}'] = [f'rq{e}']
        p[f'rs{e}'] = [f'rs{e}']
    p.update(lt=['lt'], kvn=['kvi', 'kvi_cr'], kvo=['kvo', 'kvo_cr'], emf=['emf', 'emf_cr'], emr=['emr', 'emr_cr'], mf=['mf'],
             wfault=['wf'], kf=['kf'], rst_n=['rst_n'])
    return p


CTRL_CLK = [f'ck_p{k}' for k in range(NPC)] + ['ck_k']
CTRL_HCLK = [f'hk_p{k}' for k in range(NPC)] + ['hk_k']
W_CI, W_CO, W_PO, W_PI = 319, 294, 328, 289
LAND_CLK = [f'ck_p{k}' for k in range(NPC)] + [f'ck_g{i}' for i in range(NGRP)] + ['ck_e', 'ck_r']
ASTK_CLK = ['ck_c'] + [f'ck_z{z}' for z in range(4)] + [f'ck_v{j}' for j in range(64)] + \
           [f'ck_x{j}' for j in range(32)] + [f'ck_e{e}' for e in range(NENG)] + ['ck_r']


def land_binding():
    ports = land_ports()
    ports.update(ck_p0=['ck_p'], ck_g0=['ck_g'], ck_e=['ck_e'], ck_r=['ck_r'])
    return dict(module='qkd_land_strip_s', file='rtl/qwen_sys/split_20261014/qkd_strips_s.sv', ports=ports,
                sliced={**{f'ck_p{k}': 'ck_p0' for k in range(1, NPC)}, **{f'ck_g{i}': 'ck_g0' for i in range(1, NGRP)}},
                classed={'st': 'by_design: die-top strap, the stack index (tie cells)'})


def astk_binding():
    ports = dict(aq=['aq'], am=['am'], ap=['ap'], af=['af'], lt=['lt'], rst_n=['rst_n'],
                 **{f'e{e}i': [f'so{e}'] for e in range(NENG)}, **{f'e{e}o': [f'si{e}'] for e in range(NENG)},
                 **{f'f{e}{h}': [f'nb{e}_{h}'] for e in range(NENG) for h in range(4)},
                 ck_c=['ck_c'], ck_z0=['ck_z'], ck_v0=['ck_v'], ck_x0=['ck_x'], ck_e0=['ck_e'], ck_r=['ck_r'])
    sl = {}
    for base, n in (('ck_z', 4), ('ck_v', 64), ('ck_x', 32), ('ck_e', NENG)):
        sl.update({f'{base}{j}': f'{base}0' for j in range(1, n)})
    return dict(module='qkd_astk_strip_s', file='rtl/qwen_sys/split_20261014/qkd_strips_s.sv', ports=ports, sliced=sl,
                classed={'st': 'by_design: die-top strap, the stack index (tie cells)',
                         'pv_done': 'by_design: the aggregator P.V done pair, not a hub input (the die ap word is 563 b)'})


def ctrl_binding(rev=False):
    ports = {}
    for k in range(NPC):
        ports.update({f'c{k}i': [f'ci{k}'], f'c{k}o': [f'co{k}'], f'es{k}': [f'es{k}'], f'er{k}': [f'er{k}'],
                      f'po{k}': [f'po{k}'], f'pi{k}': [f'pi{k}']})
    ports.update(kc=['kc'], kf=['kf'], hrst=['hrst'], rsi=['rsi'], ck_p0=['ck_p'], ck_k=['ck_k'], hk_p0=['hk_p'],
                 hk_k=['hk_k'])
    return dict(module='qkd_ctrl_strip_sr' if rev else 'qkd_ctrl_strip_s', file='rtl/qwen_sys/split_20261014/qkd_strips_s.sv', ports=ports,
                sliced={**{f'ck_p{k}': 'ck_p0' for k in range(1, NPC)}, **{f'hk_p{k}': 'hk_p0' for k in range(1, NPC)}},
                classed={})


def emit_ctrl(rev=False):
    """rev=False: qkd_ctrl_strip_s (N stacks, qkd_ctrl_n): kc enters the strip's OUTER = N end, kc leaf at the N end,
    command chain kc -> pc31 .. pc0 (N -> S), fault chain pc0 .. pc31 -> kc.
    rev=True (v1.3): qkd_ctrl_strip_sr (S stacks, qkd_ctrl): kc enters the OUTER = S end (kc_<S stack> die pin on the S
    face), kc leaf at the S end, command chain kc -> pc0 .. pc31 (S -> N), fault chain pc31 .. pc0 -> kc; the die places
    these leaves MX (ki / fo face S), so every chain hop stays an abutted 378-um pitch hop."""
    L = ['// ---- HBM controller strip: wires only (every block a CLOSED leaf) ----------------------------------------------',
         f'module {"qkd_ctrl_strip_sr" if rev else "qkd_ctrl_strip_s"} (', '    input  wire [31:0]   ck_p,', '    input  wire          ck_k,',
         '    input  wire [31:0]   hk_p,', '    input  wire          hk_k,', '    input  wire          hrst,',
         '    input  wire          rsi,', '    input  wire [32:0]   kc,', '    output wire          kf,']
    for k in range(NPC):
        L += [f'    input  wire [{W_CI - 1}:0]  ci{k},', f'    output wire [{W_CO - 1}:0]  co{k},',
              f'    input  wire [{W_ES - 1}:0]  es{k},', f'    output wire [{W_ER - 1}:0]  er{k},',
              f'    output wire [{W_PO - 1}:0]  po{k},', f'    input  wire [{W_PI - 1}:0]  pi{k},']
    L[-1] = L[-1].rstrip(',')
    if not rev:
        L += [');', f'    wire [32:0] kw [0:{NPC}];    // kw[k + 1]: into pc k from the N (kw[NPC] = the kc leaf)',
              f'    wire        fw [0:{NPC}];    // fw[k]: into pc k from the S', "    assign fw[0] = 1'b0;",
              f'    qkd_ctrl_kc u_kc (.ck(ck_k), .rsi(rsi), .pll_hbm(hk_k), .hrst(hrst), .kc(kc), .ko(kw[{NPC}]), .fi(fw[{NPC}]), '
              '.kf(kf));']
        for k in range(NPC):
            L.append(f'    qkd_ctrl_pc u_pc{k} (.pll_hbm(hk_p[{k}]), .hrst(hrst), .ck(ck_p[{k}]), .rsi(rsi), .pc(5\'d{k}), '
                     f'.ci(ci{k}), .co(co{k}), .es(es{k}), .er(er{k}), .po(po{k}), .pi(pi{k}), .ki(kw[{k + 1}]), .ko(kw[{k}]), '
                     f'.fi(fw[{k}]), .fo(fw[{k + 1}]));')
    else:
        L += [');', f'    wire [32:0] kw [0:{NPC}];    // kw[k]: into pc k from the S (kw[0] = the kc leaf)',
              f'    wire        fw [0:{NPC}];    // fw[k + 1]: into pc k from the N (fw[0] = into the kc leaf)',
              f"    assign fw[{NPC}] = 1'b0;",
              '    qkd_ctrl_kc u_kc (.ck(ck_k), .rsi(rsi), .pll_hbm(hk_k), .hrst(hrst), .kc(kc), .ko(kw[0]), .fi(fw[0]), .kf(kf));']
        for k in range(NPC):
            L.append(f'    qkd_ctrl_pc u_pc{k} (.pll_hbm(hk_p[{k}]), .hrst(hrst), .ck(ck_p[{k}]), .rsi(rsi), .pc(5\'d{k}), '
                     f'.ci(ci{k}), .co(co{k}), .es(es{k}), .er(er{k}), .po(po{k}), .pi(pi{k}), .ki(kw[{k}]), .ko(kw[{k + 1}]), '
                     f'.fi(fw[{k + 1}]), .fo(fw[{k}]));')
    L.append('endmodule')
    return '\n'.join(L)


def emit_land():
    d = land_depths()
    L = []
    a = L.append
    a('// ---- KV landing strip: wires + strip relay stations only (every block a CLOSED leaf) ----------------------------')
    hdr = ['    input  wire [31:0]   ck_p,', '    input  wire [7:0]    ck_g,', '    input  wire          ck_e,',
           '    input  wire          ck_r,', '    input  wire          rst_n,', '    input  wire [1:0]    st,']
    for k in range(NPC):
        hdr += [f'    input  wire [{W_LI - 1}:0]  li{k},', f'    output wire          lp{k},', f'    input  wire          cf{k},',
                f'    output wire [{W_ES - 1}:0]  es{k},', f'    input  wire [{W_ER - 1}:0]  er{k},']
    for e in range(NENG):
        hdr += [f'    input  wire [{W_RQ - 1}:0]   rq{e},', f'    output wire [{W_RS - 1}:0] rs{e},']
    hdr += [f'    input  wire [{W_LT - 1}:0]   lt,', f'    input  wire [{W_KN - 1}:0] kvi,', '    output wire          kvi_cr,',
            f'    output wire [{W_KN - 1}:0] kvo,', '    input  wire          kvo_cr,', '    input  wire [287:0]  emf,', '    output wire          emf_cr,',
            '    output wire [519:0]  emr,', '    input  wire          emr_cr,', '    output wire          mf,', '    input  wire          wf,',
            '    input  wire          kf']
    a('module qkd_land_strip_s (')
    L += hdr
    a(');')
    a(f'    // kvn pass station (strip middle): one registered stage each way; kn / lt chains S (groups 3..0) and N (4..7)')
    a(f'    wire [{W_KN - 1}:0] kn_m;')
    a(f'    ot_hdc_delay #(.W({W_KN}), .D(1), .RESET(1)) u_kvd (.clk(ck_r), .rst_n(rst_n), .d(kvi), .q(kn_m));')
    a('    assign kvo = kn_m;')
    a('    ot_hdc_delay #(.W(1), .D(1), .RESET(1)) u_kvc (.clk(ck_r), .rst_n(rst_n), .d(kvo_cr), .q(kvi_cr));')
    W = W_KN + W_LT
    a(f'    wire [{W - 1}:0] tap [0:{NGRP - 1}];')
    for half, grps in (('s', (3, 2, 1, 0)), ('n', (4, 5, 6, 7))):
        prev, at = '{lt, kn_m}', 0
        for g in grps:
            n = d[g] - at
            a(f'    wire [{W - 1}:0] ch_{half}{g};')
            a(f'    ot_hdc_delay #(.W({W}), .D({n}), .RESET(1)) u_{half}{g} (.clk(ck_r), .rst_n(rst_n), .d({prev}), .q(ch_{half}{g}));')
            a(f'    assign tap[{g}] = ch_{half}{g};')
            prev, at = f'ch_{half}{g}', d[g]
    a('    // ---- the leaves --------------------------------------------------------------------------------------------')
    a(f'    wire [272:0] gw [0:{NPC - 1}];')
    a(f'    wire         gc [0:{NPC - 1}];')
    a(f'    wire [297:0] dn [0:{NPC}];      // dn[k]: into pc k from the N (dn[NPC] = the embedding engine)')
    a(f'    wire [261:0] up [0:{NPC}];      // up[k]: into pc k from the S (up[0] = 0)')
    a(f'    wire [31:0]  cr [0:{NPC}];')
    a(f'    wire         pf [0:{NPC}];')
    a(f'    wire         gf [0:{NGRP}];')
    a('    assign up[0] = 262\'d0; assign cr[0] = 32\'d0; assign pf[0] = kf; assign gf[0] = wf;')
    for s in range(NPC):
        i, q = divmod(s, 4)
        lpc = 8 * q + LAND_GROUP_ORDER[i]
        a(f'    qkd_land_pc u_pc{s} (.ck(ck_p[{s}]), .rst_n(rst_n), .lpc(5\'d{lpc}), .li(li{s}), .lp(lp{s}), .cf(cf{s}), '
          f'.gw(gw[{s}]), .gc(gc[{s}]), .es(es{s}), .er(er{s}), .dni(dn[{s + 1}]), .dno(dn[{s}]), .upi(up[{s}]), '
          f'.upo(up[{s + 1}]), .cri(cr[{s}]), .cro(cr[{s + 1}]), .fi(pf[{s}]), .fo(pf[{s + 1}]));')
    for i in range(NGRP):
        g = LAND_GROUP_ORDER[i]
        b = 4 * i
        a(f'    qkd_land_grp_epoch u_g{i} (.ck(ck_g[{i}]), .rst_n(rst_n), .g(3\'d{g}), .s(st), '
          + ' '.join(f'.gw{q}(gw[{b + q}]), .gc{q}(gc[{b + q}]),' for q in range(4))
          + f' .rq(rq{g}), .rs(rs{g}), .lt(tap[{i}][{W - 1}:{W_KN}]), .kn(tap[{i}][{W_KN - 1}:0]), .fi(gf[{i}]), '
          f'.fo(gf[{i + 1}]));')
    a(f'    qkd_land_emb_ifw u_emb (.ck(ck_e), .rst_n(rst_n), .st(st), .emf(emf), .emf_cr(emf_cr), .emr(emr), .emr_cr(emr_cr), .dno(dn[{NPC}]), .upi(up[{NPC}]), '
      f'.cri(cr[{NPC}]), .fi(pf[{NPC}]), .gfi(gf[{NGRP}]), .mf(mf));')
    a('endmodule')
    return '\n'.join(L)


def emit_astk(src):
    """qkd_astk_strip_s from the benched ot_qkd_astk_strip body (TP8 leaves): die ports, per-leaf clocks, lt out"""
    t = Path(src).read_text()
    s = t.index('module ot_qkd_astk_strip')
    e = t.index('endmodule', s) + len('endmodule')
    body = t[s:e]
    body = body[body.index('    localparam integer RL'):]
    hdr = ['module qkd_astk_strip_s #(', '    parameter integer RL = 1', ') (',
           '    input  wire          ck_c,', '    input  wire [3:0]    ck_z,', '    input  wire [63:0]   ck_v,',
           '    input  wire [31:0]   ck_x,', '    input  wire [7:0]    ck_e,', '    input  wire          ck_r,',
           '    input  wire          rst_n,', '    input  wire [1:0]    st,', '    input  wire [539:0]  aq,',
           '    input  wire [35:0]   am,', '    output wire [562:0]  ap,', '    output wire [1:0]    pv_done,',
           '    output wire          af,', '    output wire [20:0]   lt,']
    hdr += [f'    input  wire [424:0]  so{e_},' for e_ in range(NENG)]
    hdr += [f'    output wire [633:0]  si{e_},' for e_ in range(NENG)]
    hdr += [f'    input  wire [1023:0] nb{e_}_{h},' for e_ in range(NENG) for h in range(4)]
    hdr[-1] = hdr[-1].rstrip(',')
    rep = [
        ('    localparam integer RL = `KVD_AKRL;\n', ''),
        ('    wire [564:0] ap;\n', ''),
        ('    wire         cfx, cfy, cfz, af;\n', '    wire         cfx, cfy, cfz;\n'),
        ('    wire [1:0] SS = S;\n', '    wire [1:0] SS = st;\n'
         '    wire [425*8-1:0]  so_f = {' + ', '.join(f'so{x}' for x in range(7, -1, -1)) + '};\n'
         '    wire [634*8-1:0]  si_f;\n'
         + ''.join(f'    assign si{x} = si_f[634*{x} +: 634];\n' for x in range(NENG))
         + '    wire [4096*8-1:0] nb_f = {' + ', '.join(f'nb{x}_{h}' for x in range(7, -1, -1) for h in range(3, -1, -1)) + '};\n'),
        ('`ifdef KVD_ASTK_TP8\n    qkd_astk_ctl_tp8 u_ctl (.ck(clk),   // native TP8 master (bench: ASTK_DEFS adds +define+KVD_ASTK_TP8 with KVD_HEADS=1)\n'
         '`else\n    qkd_astk_ctl u_ctl (.ck(clk),\n`endif .rst_n(rst_n), .st(SS), .aq({q_data, q_beat, q_valid, 6\'d0, T, start}), .lt(),\n'
         '        .am({mi_data, mi_hh, mi_g, mi_valid}), .ap(ap), .af(af),',
         '    wire [564:0] ap_w;\n    qkd_astk_ctl_tp8 u_ctl (.ck(ck_c), .rst_n(rst_n), .st(SS), .aq(aq), .lt(lt),\n'
         '        .am(am), .ap(ap_w), .af(af),'),
        ('    assign so_valid = ap[0]; assign so_type = ap[2:1]; assign so_g = ap[3]; assign so_hh = ap[5:4]; assign so_k = ap[9:6];\n'
         '    assign so_any = ap[10]; assign so_data = ap[42:11]; assign pv_done = ap[44:43]; assign pv_valid = ap[45];\n'
         '    assign pv_g = ap[46]; assign pv_beat = ap[52:47]; assign pv_data = ap[564:53];\n'
         '    assign fault = af;\n',
         '    // die ap word (563 b) = the hub ap_<st> fields {si 43 | pi 520}: ap_w without the P.V done pair [44:43]\n'
         '    assign ap = {ap_w[564:45], ap_w[42:0]}; assign pv_done = ap_w[44:43];\n'),
        ('qkd_astk_ep u_ep (.ck(clk)', 'qkd_astk_ep u_ep (.ck(ck_e[e])'),
        ('qkd_astk_ex u_ex (.ck(clk)', 'qkd_astk_ex u_ex (.ck(ck_x[4*e+xh])'),
        ('`ifdef KVD_ASTK_TP8\n                qkd_astk_pv_tp8 u_a (.ck(clk),\n`else\n                qkd_astk_pv u_a (.ck(clk),\n`endif',
         '                qkd_astk_pv_tp8 u_a (.ck(ck_v[16*r+8*c+2*hp]),'),
        ('`ifdef KVD_ASTK_TP8\n                qkd_astk_pv_tp8 u_b (.ck(clk),\n`else\n                qkd_astk_pv u_b (.ck(clk),\n`endif',
         '                qkd_astk_pv_tp8 u_b (.ck(ck_v[16*r+8*c+2*hp+1]),'),
        ('qkd_astk_zn u_zn (.ck(clk)', 'qkd_astk_zn u_zn (.ck(ck_z[z])'),
        ('ot_qkd_rly', 'qkd_srly'),
        ('(.clk(clk), .rst_n(rst_n)', '(.clk(ck_r), .rst_n(rst_n)'),
    ]
    for a_, b_ in rep:
        if a_ not in body:
            raise SystemExit(f'astk source changed: {a_[:60]!r} not found')
        body = body.replace(a_, b_)
    if 'clk' in body.replace('ck_', '').replace('.clk(', ''):
        pass
    return '\n'.join(hdr) + '\n);\n' + body


SRLY = """// strip relay station: D registered stages (reset, as the benched composition's ot_qkd_rly)
module qkd_srly #(parameter integer W = 1, parameter integer D = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d,
                                                                    output wire [W-1:0] q);
    ot_hdc_delay #(.W(W), .D(D), .RESET(1)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
endmodule"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--astk-src', default='rtl/test/qwen_kv_die/ot_qwen_nearhbm_attn_stack_k.sv')
    a = ap.parse_args()
    head = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_kv_die/kv_strips.py (qwen-split/kvsys v1.2, die lead): do not edit by hand.\n'
            '// KV/system die strip frames = wires-only compositions of CLOSED leaves (see the generator docstring).\n'
            '// Leaf RTL: rtl/qwen_sys/kv_die_20261009/{qkd_land_strip.sv, qkd_astk_leaves.sv, qkd_ctrl_strip.sv}; rtl/hdc/ot_hdc_delay.sv.\n')
    Path(a.out).write_text(head + '\n' + SRLY + '\n\n' + emit_land() + '\n\n' + emit_astk(a.astk_src) + '\n\n' +
                           emit_ctrl() + '\n\n' + emit_ctrl(rev=True) + '\n')
    print('land depths', land_depths())


if __name__ == '__main__':
    main()
