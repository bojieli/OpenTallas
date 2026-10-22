#!/usr/bin/env python3
"""S81 HEAD ctl glue R3 generator (STW-S81c-HEAD-GLUE 10-22).

Structural successor of s81hd_glue_m2/f2 (FAIL textbook.wire_reach: synthesis merged identical-D frame-header flops of
different faces into one flop (htd0_q[4..6] == dtd_q[4][4..6]) and the core sat 850-1000 um from its pins with no
relay; clock_rule one 18,948-sink root, pin-flop spread 89.5/98.5 ps).  Owner release freeze 10-22 00:02: the glue keeps
the FROZEN interface (ot_s81hd_ctl_glue port list/widths, single ck / rst_n), so R3 changes only the inside:

  * zone modules (rtl/dsrom_sys/s81_head/ot_s81hd_glue_rg.sv) placed by function at their pins: WL (lep face: ingest,
    forward, RO, HFWD hold), C (core: x store, stream, tag FIFO, N/S final, rank merge, MU replay), N (seq peer, RESULT,
    draft q/w, grant receivers, spine N), S (spine S), WH0 / WH1 (host lanes, CSR, STATUS, fault vector) and one kept TX
    pin-stage module per mesh / draft lane;
  * every zone-to-zone signal rides kept relay stages (ot_s81hd_rs32 / rs8 / kf data, ot_s81hd_rv1 valid with a
    parallel ot_s81hd_rr1 reset relay), stage count n = max(1, ceil((d + 100) / HOP)) with d the Manhattan distance
    between the zone anchors in the LARGER of the MAIN / FB outlines (one RTL for both kits), equal ages per bus group;
  * an equal-depth reset forest (ot_s81hd_rr1 chains from rst_n to every zone, then ot_rst_relay_tree3 leaves);
  * exact per-bit pin placement (io_tcl) from the H10 die plan link positions (each lane's bits where its die link
    lands: draft 0/1 on W as the die routes them), the proven seq peer windows (peer_pin_plan) on N.

  python3 tools/s81_head/glue_rg_gen.py            # writes RTL top, io_tcl + kit specs for m and f, and the ledger
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / 'results/arch/s81_head_1021'
OUT_RTL = ROOT / 'rtl/dsrom_sys/s81_head/ot_s81hd_ctl_glue_r3.sv'
HOP = 380.0
FW = 553
VAR = {'m': dict(name='s81hd_glue_r3m', W=2160.0, H=3888.0),
       'f': dict(name='s81hd_glue_r3f', W=2592.0, H=4320.0)}
GRID = 0.048
OFF = 0.012


# ---------------------------------------------------------------------------------------------------------------- geometry
def load_links(v):
    return json.loads((ARCH / f'glue_r3/h10{v}_ctl_links.json').read_text())


def lane_of(port):
    """die link port -> (zone, kind)"""
    if port.startswith('ln_'):
        nm = port[3:-2]                      # mesh0 / host1 / draft3
        role = nm.rstrip('0123456789'); k = int(nm[len(role):])
        return {'mesh': f'm{k}', 'host': f'h{k}', 'draft': f'd{k}'}[role], port[-1]
    return port, ''


def anchors(v):
    g = VAR[v]; W, H = g['W'], g['H']
    L = load_links(v)['links']
    by = {}
    for r in L:
        z, _ = lane_of(r['port'])
        by.setdefault(z, []).append(r)
    A = {}
    for z, rs in by.items():
        if z.startswith(('m', 'd', 'h')) and z[1:].isdigit():
            f = rs[0]['face']
            y = sum(r['pos_um'] for r in rs) / len(rs)
            A[{'h0': 'WH0', 'h1': 'WH1'}.get(z, z)] = (150.0 if f == 'W' else W - 150.0, y, f)
    lep = [r['pos_um'] for r in L if r['port'] in ('lep_t', 'lep_r')]
    A['WL'] = (150.0, sum(lep) / len(lep), 'W')
    A['N'] = (W / 2, H - 150.0, 'N')
    A['S'] = (W / 2, 150.0, 'S')
    A['C'] = (0.4 * W + 90.0, H / 2, 'C')
    A['RST'] = (0.0, H / 2, 'W')
    return A


def dist(v, a, b):
    A = anchors(v)
    return abs(A[a][0] - A[b][0]) + abs(A[a][1] - A[b][1])


def stages(a, b):
    d = max(dist(v, a, b) for v in VAR)
    return max(1, math.ceil((d + 100.0) / HOP)), d


# ---------------------------------------------------------------------------------------------------------------- nets
MESH = [f'm{k}' for k in range(6)]
DRAFT = [f'd{k}' for k in range(5)]


def nets():
    """(name, src zone, dst zone, valid fields [(fname, expr)], data fields [(fname, width, expr)], group)"""
    N = []
    a = N.append
    # WL ->
    a(('xs', 'WL', 'C', [('v', 'wl_xs_v')], [('gx', 7, 'wl_xs_gx'), ('d', 1024, 'wl_xs_d'), ('rt', 32, 'wl_xs_rt'),
                                              ('rtv', 3, '{3{wl_xs_rt[31]}}')], None))
    a(('tkf', 'WL', 'N', [('v', 'wl_tk_free')], [], None))
    a(('r', 'WL', 'WH0', [('v', 'wl_r_v')], [('d', 512, 'wl_r_d')], None))
    a(('fwl', 'WL', 'WH1', [('f1', 'wl_f1'), ('f10', 'wl_f10'), ('f13', 'wl_f13'), ('f15a', 'wl_f15a')], [], None))
    a(('lw', 'WL', 'C', [('v', 'lw[0]')], [('u', 10, 'lw[10:1]')], None))
    # C ->
    for dz, nm in (('N', 'stn'), ('S', 'sts')):
        a((nm, 'C', dz, [('go', 'c_st_go'), ('xv', 'c_st_xv')], [('xb', 256, 'c_st_xb'), ('xa', 256, 'c_st_xa')], 'st'))
    for z in MESH:
        a((f'om{z[1:]}', 'C', z, [('v', 'c_ov')], [('rec', 81, 'c_orec')], 'om'))
    a(('mg', 'C', 'N', [('v', 'c_mg_v')], [('d', 80, 'c_mg_d')], None))
    a(('rc', 'C', 'WL', [('v', 'c_rc_v')], [('u', 10, 'c_rc_u')], None))
    a(('fc', 'C', 'WH1', [(f, f'c_{f}') for f in ('f0', 'f2', 'f3', 'f5', 'f6', 'f7', 'f8', 'f15b', 'f16c')], [], None))
    # N ->
    a(('sn', 'N', 'C', [('v', 'sn_i[514]')], [('d', 49, 'sn_i[563:515]')], 'snss'))
    a(('f4n', 'N', 'WH1', [('v', 'sn_i[564]')], [], None))
    for z in DRAFT:
        a((f'dt{z[1:]}', 'N', z, [('v', 'n_dt_v')], [('p', 115, 'n_dt_p')], 'dt'))
    a(('tk', 'N', 'WL', [('v', 'n_tk_v')], [('d', 512, 'n_tk_d')], None))
    a(('acc', 'N', 'WH1', [('v55', 'seq_t_acc[55]'), ('v56', 'seq_t_acc[56]')], [('d', 55, 'seq_t_acc[54:0]')], None))
    a(('fn', 'N', 'WH1', [('f9', 'n_f9'), ('f14', 'n_f14'), ('f16a', 'n_f16a')], [], None))
    # S ->
    a(('ss', 'S', 'C', [('v', 'ss_i[514]')], [('d', 49, 'ss_i[563:515]')], 'snss'))
    a(('f4s', 'S', 'WH1', [('v', 'ss_i[564]')], [], None))
    # lanes ->
    for k, z in enumerate(MESH):
        a((f'mr{k}', z, 'C', [('v', f'mrx_v[{k}]')], [('d', 97, f'mrx_d[{FW*k+96}:{FW*k}]')], 'mr'))
        a((f'mf{k}', z, 'WH1', [(f'b{i}', f'mflt[{4*k+i}]') for i in range(4)], [], None))
    for k, z in enumerate(DRAFT):
        a((f'dr{k}', z, 'N', [('v', f'drx_v[{k}]')], [('d', 50, f'drx_d[{FW*k+49}:{FW*k}]')], 'dr'))
        a((f'df{k}', z, 'WH1', [(f'b{i}', f'dflt[{4*k+i}]') for i in range(4)], [], None))
    # host lanes ->
    a(('hf', 'WH0', 'WL', [('v', 'h0_hf_v')], [('d', 512, 'h0_hf_d')], None))
    a(('f16b', 'WH0', 'WH1', [('v', 'h0_f16b')], [], None))
    for k, z in ((0, 'WH0'), (1, 'WH1')):
        a((f'hfl{k}', z, 'WH1', [(f'b{i}', f'hflt[{4*k+i}]') for i in range(4)], [], None))
    # WH1 -> (CSR, fault flag)
    a(('cwl', 'WH1', 'WL', [('gp', 'h1_ce_gp'), ('cp0', 'h1_ce_cp'), ('cp1', 'h1_ce_cp')], [('d', 32, 'h1_csr_d')], None))
    a(('cc', 'WH1', 'C', [('rb0', 'h1_ce_rb'), ('rb1', 'h1_ce_rb')], [('d', 17, 'h1_csr_d[16:0]')], None))
    a(('cn', 'WH1', 'N', [('pl0', 'h1_ce_pl'), ('pl1', 'h1_ce_pl'), ('gl0', 'h1_ce_gl'), ('gl1', 'h1_ce_gl'), ('hd', 'h1_ce_hd'), ('run', 'h1_ce_run')],
       [('d', 21, 'h1_csr_d[20:0]')], None))
    for z in MESH + DRAFT + ['WH0']:
        a((f'cl_{z}', 'WH1', z, [('rk', 'h1_ce_rk'), ('gp', 'h1_ce_gp')], [('d', 4, 'h1_csr_d[3:0]')], None))
    a(('cfl', 'WH1', 'WL', [('v', 'h1_ctlf')], [], None))
    for dz, nm in (('N', 'cfn'), ('S', 'cfs')):
        a((nm, 'WH1', dz, [('v', 'h1_ctlf')], [], 'cfns'))
    return N


def plan_stages():
    N = nets()
    st = {}
    for nm, s, d, vf, df, grp in N:
        st[nm] = stages(s, d)
    grp_n = {}
    for nm, s, d, vf, df, grp in N:
        if grp:
            grp_n[grp] = max(grp_n.get(grp, 0), st[nm][0])
    return {nm: (grp_n[grp] if grp else st[nm][0], st[nm][1], grp) for nm, s, d, vf, df, grp in N}


# ---------------------------------------------------------------------------------------------------------------- RTL
def chunks(w):
    o = 0
    while o < w:
        r = w - o
        if r >= 32:
            yield o, 32, 'ot_s81hd_rs32'
            o += 32
        elif r >= 8:
            yield o, 8, 'ot_s81hd_rs8'
            o += 8
        else:
            yield o, 1, 'ot_s81hd_kf'
            o += 1


def emit_chain(L, nm, vf, df, n, rleaf):
    dw = sum(w for _, w, _ in df)
    if dw:
        L.append(f'    wire [{dw-1}:0] {nm}_d0 = {{' + ', '.join(e for _, _, e in reversed(df)) + '};')
    for i, (f, e) in enumerate(vf):
        L.append(f'    wire {nm}_v{i}_0 = {e};')
    if vf:
        L.append(f'    wire {nm}_r0 = {rleaf};')
    for j in range(1, n + 1):
        if dw:
            L.append(f'    wire [{dw-1}:0] {nm}_d{j};')
            for o, w, mod in chunks(dw):
                if mod == 'ot_s81hd_kf':
                    L.append(f'    {mod} u_{nm}_{j}_{o} (.ck(ck), .d({nm}_d{j-1}[{o}]), .q({nm}_d{j}[{o}]));')
                else:
                    L.append(f'    {mod} u_{nm}_{j}_{o} (.ck(ck), .d({nm}_d{j-1}[{o+w-1}:{o}]), .q({nm}_d{j}[{o+w-1}:{o}]));')
        if vf:
            L.append(f'    wire {nm}_r{j}; ot_s81hd_rr1 u_{nm}_rr{j} (.ck(ck), .rn({nm}_r{j-1}), .q({nm}_r{j}));')
            for i in range(len(vf)):
                L.append(f'    wire {nm}_v{i}_{j}; ot_s81hd_rv1 u_{nm}_v{i}_{j} (.ck(ck), .rn({nm}_r{j}), .d({nm}_v{i}_{j-1}), .q({nm}_v{i}_{j}));')
    o = 0
    for f, w, _ in df:
        L.append(f'    wire [{w-1}:0] {nm}__{f} = {nm}_d{n}[{o+w-1}:{o}];')
        o += w
    for i, (f, _) in enumerate(vf):
        L.append(f'    wire {nm}__{f} = {nm}_v{i}_{n};')


ZONES = ['WL', 'C', 'N', 'S', 'WH0', 'WH1'] + MESH + DRAFT


def gen_rtl(ST):
    N = nets()
    roots = {z: [] for z in ZONES}
    for nm, s, d, vf, df, grp in N:
        if vf:
            roots[s].append(nm)
    dr = max(stages('RST', z)[0] for z in ZONES)
    L = []
    L.append('// GENERATED by tools/s81_head/glue_rg_gen.py -- do not edit.  S81 HEAD ctl glue R3 (frozen interface:')
    L.append('// exact ot_s81hd_ctl_glue port list of ot_s81hd_ctl_peer.sv eb58f5989); zone modules in ot_s81hd_glue_rg.sv.')
    L.append('`timescale 1ns/1ps')
    L.append('''module ot_s81hd_ctl_glue (
    input  wire              ck,
    input  wire              rst_n,
    input  wire [1103:0]     ri,
    input  wire [31:0]       mu_rt,
    input  wire [10:0]       lw,
    input  wire              lep_f,
    output wire [1103:0]     ro,
    output wire [33:0]       mu_c,
    output wire [10:0]       mu_rc,
    output wire              ctl_f,
    output wire [564:0]      sn_o,
    output wire [564:0]      ss_o,
    input  wire [564:0]      sn_i,
    input  wire [564:0]      ss_i,
    output wire [5:0]        mtx_v,
    output wire [6*553-1:0]  mtx_d,
    input  wire [5:0]        mrx_v,
    input  wire [6*553-1:0]  mrx_d,
    input  wire [23:0]       mflt,
    output wire [1:0]        htx_v,
    output wire [2*553-1:0]  htx_d,
    input  wire [1:0]        hrx_v,
    input  wire [2*553-1:0]  hrx_d,
    input  wire [7:0]        hflt,
    output wire [4:0]        dtx_v,
    output wire [5*553-1:0]  dtx_d,
    input  wire [4:0]        drx_v,
    input  wire [5*553-1:0]  drx_d,
    input  wire [19:0]       dflt
,
    output wire [0:0] seq_rst,
    output wire [41:0] seq_f_cfg,
    output wire [0:0] seq_f_rv,
    output wire [511:0] seq_f_rd,
    input wire [0:0] seq_t_rg,
    input wire [0:0] seq_t_tv,
    input wire [511:0] seq_t_td,
    output wire [0:0] seq_f_tg,
    input wire [0:0] seq_t_sv,
    input wire [76:0] seq_t_sd,
    output wire [0:0] seq_f_sg,
    output wire [0:0] seq_f_wv,
    output wire [9:0] seq_f_wd,
    input wire [0:0] seq_t_wg,
    input wire [0:0] seq_t_hv,
    input wire [33:0] seq_t_hd,
    output wire [0:0] seq_f_hg,
    output wire [0:0] seq_f_qv,
    output wire [33:0] seq_f_qd,
    input wire [0:0] seq_t_qg,
    input wire [56:0] seq_t_acc
);''')
    # ---- reset forest: equal depth to every zone, then a leaf tree for the chain roots of the zone
    L.append(f'    // reset forest: {dr} ot_s81hd_rr1 hops (<= {HOP:g} um) from rst_n to every zone, equal depth')
    for z in ZONES:
        prev = 'rst_n'
        for j in range(1, dr + 1):
            L.append(f'    wire zr_{z}_{j}; ot_s81hd_rr1 u_zr_{z}_{j} (.ck(ck), .rn({prev}), .q(zr_{z}_{j}));')
            prev = f'zr_{z}_{j}'
        L.append(f'    wire zr_{z} = {prev};')
        nl = max(1, len(roots[z]))
        L.append(f'    wire [{nl-1}:0] zl_{z}; ot_rst_relay_tree3 #(.REGIONS({nl})) u_zt_{z} (.clk(ck), .rst_n_in(zr_{z}), .rst_n(zl_{z}));')
    leaf = {}
    for z in ZONES:
        for i, nm in enumerate(roots[z]):
            leaf[nm] = f'zl_{z}[{i}]'
    # ---- zone module outputs (declared before the chains that carry them)
    L.append('''    // zone module outputs
    wire wl_xs_v; wire [6:0] wl_xs_gx; wire [1023:0] wl_xs_d; wire [31:0] wl_xs_rt;
    wire wl_tk_free, wl_r_v; wire [511:0] wl_r_d; wire wl_f1, wl_f10, wl_f13, wl_f15a;
    wire c_st_go, c_st_xv; wire [255:0] c_st_xb, c_st_xa; wire c_ov; wire [80:0] c_orec; wire c_mg_v; wire [79:0] c_mg_d;
    wire c_rc_v; wire [9:0] c_rc_u; wire c_f0, c_f2, c_f3, c_f5, c_f6, c_f7, c_f8, c_f15b, c_f16c;
    wire n_dt_v; wire [114:0] n_dt_p; wire n_tk_v; wire [511:0] n_tk_d; wire n_f9, n_f14, n_f16a;
    wire h0_hf_v; wire [511:0] h0_hf_d; wire h0_f16b;
    wire h1_ce_pl, h1_ce_gl, h1_ce_rk, h1_ce_gp, h1_ce_rb, h1_ce_hd, h1_ce_cp, h1_ce_run; wire [31:0] h1_csr_d; wire h1_ctlf;''')
    # ---- relay chains
    for nm, s, d, vf, df, grp in N:
        n, dd, g = ST[nm]
        L.append(f'    // relay {nm}: {s} -> {d}, {n} stage(s), max anchor distance {dd:.0f} um' + (f', age group {g}' if g else ''))
        emit_chain(L, nm, vf, df, n, leaf.get(nm, "1'b1"))
    # ---- zone modules
    L.append('''    // ---------------------------------------------------------------- zones
    ot_s81hd_g_wl u_wl (.ck(ck), .rn(zr_WL), .ri(ri), .mu_rt(mu_rt), .lep_f(lep_f), .ro(ro), .mu_c(mu_c),
        .cs_gp(cwl__gp), .cs_cp({cwl__cp1, cwl__cp0}), .cs_d(cwl__d),
        .xs_v(wl_xs_v), .xs_gx(wl_xs_gx), .xs_d(wl_xs_d), .xs_rt(wl_xs_rt),
        .tk_v(tk__v), .tk_d(tk__d), .tk_free(wl_tk_free), .r_v(wl_r_v), .r_d(wl_r_d), .hf_v(hf__v), .hf_d(hf__d),
        .f1(wl_f1), .f10(wl_f10), .f13(wl_f13), .f15a(wl_f15a));
    assign mu_rc = {rc__u, rc__v};
    assign ctl_f = cfl__v;
    ot_s81hd_g_core u_core (.ck(ck), .rn(zr_C), .xs_v(xs__v), .xs_gx(xs__gx), .xs_d(xs__d), .xs_rt(xs__rt), .xs_rtv(xs__rtv),
        .lw_v(lw__v), .lw_u(lw__u), .rc_v(c_rc_v), .rc_u(c_rc_u), .cs_rb({cc__rb1, cc__rb0}), .cs_d(cc__d),
        .sn_v(sn__v), .ss_v(ss__v), .sn_d(sn__d), .ss_d(ss__d),
        .m_v({mr5__v, mr4__v, mr3__v, mr2__v, mr1__v, mr0__v}), .m_d({mr5__d, mr4__d, mr3__d, mr2__d, mr1__d, mr0__d}),
        .st_go(c_st_go), .st_xv(c_st_xv), .st_xb(c_st_xb), .st_xa(c_st_xa), .ov(c_ov), .orec(c_orec),
        .mg_v(c_mg_v), .mg_d(c_mg_d),
        .f0(c_f0), .f2(c_f2), .f3(c_f3), .f5(c_f5), .f6(c_f6), .f7(c_f7), .f8(c_f8), .f15b(c_f15b), .f16c(c_f16c));
    ot_s81hd_g_n u_n (.ck(ck), .rn(zr_N), .sn_o(sn_o), .st_go(stn__go), .st_xv(stn__xv), .st_xb(stn__xb), .st_xa(stn__xa),
        .ctlf(cfn__v), .cs_pl({cn__pl1, cn__pl0}), .cs_gl({cn__gl1, cn__gl0}), .cs_hd(cn__hd), .cs_run(cn__run), .cs_d(cn__d),
        .mg_v(mg__v), .mg_d(mg__d),
        .d_v({dr4__v, dr3__v, dr2__v, dr1__v, dr0__v}), .d_d({dr4__d, dr3__d, dr2__d, dr1__d, dr0__d}),
        .dt_v(n_dt_v), .dt_p(n_dt_p), .tk_v(n_tk_v), .tk_d(n_tk_d), .tk_free(tkf__v),
        .seq_rst(seq_rst), .seq_f_cfg(seq_f_cfg), .seq_f_rv(seq_f_rv), .seq_f_rd(seq_f_rd), .seq_t_rg(seq_t_rg),
        .seq_t_tv(seq_t_tv), .seq_t_td(seq_t_td), .seq_f_tg(seq_f_tg), .seq_t_sv(seq_t_sv), .seq_t_sd(seq_t_sd),
        .seq_f_sg(seq_f_sg), .seq_f_wv(seq_f_wv), .seq_f_wd(seq_f_wd), .seq_t_wg(seq_t_wg), .seq_t_hv(seq_t_hv),
        .seq_t_hd(seq_t_hd), .seq_f_hg(seq_f_hg), .seq_f_qv(seq_f_qv), .seq_f_qd(seq_f_qd), .seq_t_qg(seq_t_qg),
        .f9(n_f9), .f14(n_f14), .f16a(n_f16a));
    ot_s81hd_g_s u_s (.ck(ck), .ss_o(ss_o), .st_go(sts__go), .st_xv(sts__xv), .st_xb(sts__xb), .st_xa(sts__xa), .ctlf(cfs__v));
    ot_s81hd_g_h0 u_h0 (.ck(ck), .rn(zr_WH0), .hrx_v(hrx_v[0]), .hrx_d(hrx_d[552:0]), .htx_v(htx_v[0]), .htx_d(htx_d[552:0]),
        .cs_rk(cl_WH0__rk), .cs_gp(cl_WH0__gp), .cs_d(cl_WH0__d), .hf_v(h0_hf_v), .hf_d(h0_hf_d), .r_v(r__v), .r_d(r__d),
        .f16b(h0_f16b));
    ot_s81hd_g_h1 u_h1 (.ck(ck), .rn(zr_WH1), .hrx_v(hrx_v[1]), .hrx_d(hrx_d[1105:553]), .htx_v(htx_v[1]), .htx_d(htx_d[1105:553]),
        .ce_pl(h1_ce_pl), .ce_gl(h1_ce_gl), .ce_rk(h1_ce_rk), .ce_gp(h1_ce_gp), .ce_rb(h1_ce_rb), .ce_hd(h1_ce_hd),
        .ce_cp(h1_ce_cp), .ce_run(h1_ce_run), .csr_d(h1_csr_d),
        .acc({acc__v56, acc__v55, acc__d}),
        .lflt({df4__b3, df4__b2, df4__b1, df4__b0, df3__b3, df3__b2, df3__b1, df3__b0, df2__b3, df2__b2, df2__b1, df2__b0,
               df1__b3, df1__b2, df1__b1, df1__b0, df0__b3, df0__b2, df0__b1, df0__b0,
               hfl1__b3, hfl1__b2, hfl1__b1, hfl1__b0, hfl0__b3, hfl0__b2, hfl0__b1, hfl0__b0,
               mf5__b3, mf5__b2, mf5__b1, mf5__b0, mf4__b3, mf4__b2, mf4__b1, mf4__b0, mf3__b3, mf3__b2, mf3__b1, mf3__b0,
               mf2__b3, mf2__b2, mf2__b1, mf2__b0, mf1__b3, mf1__b2, mf1__b1, mf1__b0, mf0__b3, mf0__b2, mf0__b1, mf0__b0}),
        .f0(fc__f0), .f1(fwl__f1), .f2(fc__f2), .f3(fc__f3), .f4n(f4n__v), .f4s(f4s__v), .f5(fc__f5), .f6(fc__f6),
        .f7(fc__f7), .f8(fc__f8), .f9(fn__f9), .f10(fwl__f10), .f13(fwl__f13), .f14(fn__f14), .f15a(fwl__f15a),
        .f15b(fc__f15b), .f16a(fn__f16a), .f16b(f16b__v), .f16c(fc__f16c), .ctlf(h1_ctlf));''')
    for k in range(6):
        L.append(f'    ot_s81hd_g_mtx u_mtx{k} (.ck(ck), .rn(zr_m{k}), .v(om{k}__v), .rec(om{k}__rec), .cs_rk(cl_m{k}__rk), '
                 f'.cs_gp(cl_m{k}__gp), .cs_d(cl_m{k}__d), .tx_v(mtx_v[{k}]), .tx_d(mtx_d[{FW*k+FW-1}:{FW*k}]));')
    for k in range(5):
        L.append(f'    ot_s81hd_g_dtx u_dtx{k} (.ck(ck), .rn(zr_d{k}), .v(dt{k}__v), .p(dt{k}__p), .cs_rk(cl_d{k}__rk), '
                 f'.cs_gp(cl_d{k}__gp), .cs_d(cl_d{k}__d), .tx_v(dtx_v[{k}]), .tx_d(dtx_d[{FW*k+FW-1}:{FW*k}]));')
    L.append('endmodule')
    OUT_RTL.write_text('\n'.join(L) + '\n')
    return dr


# ---------------------------------------------------------------------------------------------------------------- pins
def pack_bits(port):
    """die link port -> ordered list of RTL pin names it carries (hd_bind pack order)"""
    if port.startswith('ln_'):
        z, tr = lane_of(port)
        c, k = z[0], int(z[1:])
        if tr == 't':
            return [f'{c}tx_v[{k}]'] + [f'{c}tx_d[{FW*k+i}]' for i in range(FW)]
        return [f'{c}rx_v[{k}]'] + [f'{c}rx_d[{FW*k+i}]' for i in range(FW)] + [f'{c}flt[{4*k+i}]' for i in range(4)]
    if port == 'lep_t':
        return ([f'ro[{i}]' for i in range(1104)] + [f'mu_c[{i}]' for i in range(34)] + [f'mu_rc[{i}]' for i in range(11)]
                + ['ctl_f'])
    if port == 'lep_r':
        return ([f'ri[{i}]' for i in range(1104)] + [f'mu_rt[{i}]' for i in range(32)] + [f'lw[{i}]' for i in range(11)]
                + ['lep_f'])
    raise KeyError(port)


def snap(x):
    return round(OFF + round((x - OFF) / GRID) * GRID, 3)


def place_band(names, lo, hi):
    n = len(names)
    pitch = max(2, int((hi - lo) / max(n, 1) / GRID)) * GRID
    pitch = min(pitch, 12 * GRID)
    span = pitch * (n - 1)
    assert span <= hi - lo + 1e-6 or n == 1, (names[0], n, lo, hi, pitch)
    start = (lo + hi) / 2 - span / 2
    return [(nm, snap(start + i * pitch)) for i, nm in enumerate(names)]


def bus_names(port, width):
    return [f'{port}[{i}]' for i in range(width)] if width > 1 else [f'{port}']


SEQ_PORTS = {'rst': 1, 'f_cfg': 42, 'f_rv': 1, 'f_rd': 512, 't_rg': 1, 't_tv': 1, 't_td': 512, 'f_tg': 1, 't_sv': 1, 't_sd': 77,
             'f_sg': 1, 'f_wv': 1, 'f_wd': 10, 't_wg': 1, 't_hv': 1, 't_hd': 34, 'f_hg': 1, 'f_qv': 1, 'f_qd': 34, 't_qg': 1,
             't_acc': 57}


def gen_pins(v):
    g = VAR[v]; W, H = g['W'], g['H']
    L = load_links(v)['links']
    pins = []     # (name, face, coord along face)
    for face, pitch in (('W', None), ('E', None)):
        rs = sorted([r for r in L if r['face'] == face], key=lambda r: r['pos_um'])
        ps = [r['pos_um'] for r in rs]
        for i, r in enumerate(rs):
            gaps = [abs(ps[j] - r['pos_um']) for j in (i - 1, i + 1) if 0 <= j < len(ps) and ps[j] != r['pos_um']]
            half = 0.42 * min(gaps)
            bits = pack_bits(r['port'])
            # 276-bit die lanes: link l<k> of the port carries bits [276k, 276k+276) of the packed list
            k = int(r['link'].rsplit('_l', 1)[1])
            mine = bits[276 * k: 276 * (k + 1)]
            pins += [(nm, face, c) for nm, c in place_band(mine, r['pos_um'] - half, r['pos_um'] + half)]
    c = W / 2
    pp = json.loads((ARCH / f'peer_pin_plan_{v}.json').read_text())
    for row in pp['rows']:
        pins += [(nm, 'N', x) for nm, x in place_band(bus_names('seq_' + row['port'], row['bits']), c + row['lo_um'], c + row['hi_um'])]
    for face, o, i in (('N', 'sn_o', 'sn_i'), ('S', 'ss_o', 'ss_i')):
        pins += [(nm, face, x) for nm, x in place_band(bus_names(o, 565), c - 489.6, c - 149.6)]
        pins += [(nm, face, x) for nm, x in place_band(bus_names(i, 565), c + 117.6, c + 457.6)]
    # ck / rst_n: W face, in the gap nearest H/2 (centre of the register mass; reset forest root)
    used = sorted(x for nm, f, x in pins if f == 'W')
    best = None
    for a, b in zip(used, used[1:]):
        if b - a > 4.0:
            m = (a + b) / 2
            if best is None or abs(m - H / 2) < abs(best - H / 2):
                best = m
    pins += [('ck', 'W', snap(best - 0.48)), ('rst_n', 'W', snap(best + 0.48))]
    names = [p[0] for p in pins]
    assert len(names) == len(set(names)), 'duplicate pin'
    lines = [f'# GENERATED by tools/s81_head/glue_rg_gen.py ({g["name"]}, {W:g} x {H:g} um): exact pin per bit at the H10 die '
             'plan link position of its die link (hd_bind pack order); seq windows = peer_pin_plan; sn/ss beside them.']
    for nm, f, x in pins:
        if f == 'W':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M4 -location {{0.000000 {x:.6f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        elif f == 'E':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M4 -location {{{W:.6f} {x:.6f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
        elif f == 'N':
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.6f} {H:.6f}}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
        else:
            lines.append(f'place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.6f} 0.000000}} -pin_size {{0.024 0.192}} -force_to_die_boundary')
    io = ROOT / f'physical/ref_tile/{g["name"]}/io_pins.tcl'
    io.parent.mkdir(parents=True, exist_ok=True)
    io.write_text('\n'.join(lines) + '\n')
    # face density
    dens = {}
    for f in 'NSWE':
        xs = sorted(x for nm, ff, x in pins if ff == f)
        dens[f] = dict(pins=len(xs), per_um_face=round(len(xs) / (W if f in 'NS' else H), 2))
    base = {}
    for nm, f, x in pins:
        b = nm.split('[')[0]
        base.setdefault(b, set()).add(f)
    return pins, dens, base


# ---------------------------------------------------------------------------------------------------------------- main
def main():
    ST = plan_stages()
    dr = gen_rtl(ST)
    ledger = dict(schema='opentallas.s81hd.glue_r3.relays.v1', hop_um=HOP, reset_forest_hops=dr,
                  rule='n = max(1, ceil((d + 100) / hop)), d = max over MAIN/FB of the Manhattan zone-anchor distance; '
                       'equal n inside an age group', anchors={v: anchors(v) for v in VAR}, relays={})
    for nm, s, d, vf, df, grp in nets():
        n, dd, g = ST[nm]
        ledger['relays'][nm] = dict(src=s, dst=d, stages=n, added_edges=n, max_dist_um=round(dd, 1), group=g,
                                    bits=sum(w for _, w, _ in df) + len(vf), flops=n * (sum(w for _, w, _ in df) + 2 * len(vf) if vf else 0) or n * sum(w for _, w, _ in df))
    ledger['pins'] = {}
    for v in VAR:
        pins, dens, base = gen_pins(v)
        ledger['pins'][v] = dict(count=len(pins), faces=dens, split_ports=sorted(b for b, fs in base.items() if len(fs) > 1))
    (ARCH / 'glue_r3/relay_ledger.json').write_text(json.dumps(ledger, indent=1) + '\n')
    tot = sum(r['flops'] for r in ledger['relays'].values())
    print('GLUE_R3 relays', len(ledger['relays']), 'relay flops ~', tot, 'reset forest', dr,
          {v: ledger['pins'][v]['faces'] for v in VAR})


if __name__ == '__main__':
    main()
