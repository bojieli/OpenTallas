`timescale 1ns/1ps
`default_nettype none
// hfd_coll_q3 / hfd_coll_q2 (HBM die contract v14, owner-approved P2P step 1, 2026-10-14): the two DIE MASTERS of the
// quadrant collective engine ot_hfd_coll_q (rtl/hbm_accel/generic/collective/p2p, COLL agent).  Each master is hardened
// once: hfd_coll_q3 = SW (NPT 3, links S0-S2, TKM = 1: the 32-tile TOPK_MERGE array sits INSIDE this master, exact for
// k = 2,048), hfd_coll_q2 = SE / NW / NE (NPT 2, TKM 0).  No logic here: every die port is a slice-for-slice rename of an
// ot_hfd_coll_q port (OWNER NO STUBS: the die netlist binds these modules; tools/hbm_die_port_bind.py checks it).
//
// Die ports (one die net per port, one direction per net; die relays are plain register copies):
//   ck, rst                    quadrant clock (phi - R at the pin) and the staged reset release (active low, = rst_n)
//   qid[1:0]                   die strap (0 SW, 1 SE, 2 NW, 3 NE): identity, not data
//   f_hgi_rec / f_hgi_recx / f_hgi_cfg / t_hgi_ret       command processor (the record reaches all four; only SW's ret is bound)
//   t_inj  = {inj_rd[1:0], inj_idx[31:0]}, t_inj_addr, t_vmaddr, f_inj_d          own SU quarter: inject
//   t_del  = {hgi_del_obase[159:0], del_flit[2179:0], del_valid[3:0]}             own SU quarter: delivery
//   f_rc   = {rc_d[255:0], rc_mode, rc_tag[2:0], rc_v}, t_rr = {rc_rdy, rr_d[255:0], rr_tag[2:0], rr_v}  RED_CARRY
//   llk<k>[1119:0]  one link bundle, bit for bit the hfd_lk_ep f_lk bundle (die class link_flit, endpoint 0 = COLL):
//                   [0] t_v, [545:1] t_flit, [546] r_cr, [1117:1094] session (COLL -> link);
//                   [547] r_v, [1092:548] r_flit, [1093] t_cr, [1119:1118] {locked, fault} (link -> COLL)
//   f_pr_cw / t_pr_cw / f_pr_ccw / t_pr_ccw              2 x 2 peer ring (280 b a direction)
//   q3 only: t_tkw = {tk_w_data, tk_w_mask, tk_w_addr, tk_w_v}, f_tkw_rdy;  RGX lanes t_rgx_xq, f_rgx_xr, t_rgx_vmq,
//            f_rgx_vmr, t_rgx_c = {rgx_c_q, rgx_c_req}, f_rgx_c = {rgx_c_rsp, rgx_c_cr, rgx_c_gnt}, t_rgx_xw, f_rgx_xwa
//   fault, t_stat (status outputs)
// q2 masters carry no TKM / RGX ports: ROW_GATHER, ARGMAX and TOPK run whole on QSOLO = SW (ot_hfd_coll_q), so those
// RTL inputs are dead on q2 by the engine's own contract; they are held idle inside this wrapper (not die tie-offs).
module hfd_coll_q_die #(parameter integer NPT = 3, parameter integer TKM = 0) (
    input  wire                 ck,
    input  wire                 rst,
    input  wire [1:0]           qid,
    input  wire [967:0]         f_hgi_rec,
    input  wire [553:0]         f_hgi_recx,
    input  wire [39:0]          f_hgi_cfg,
    output wire [2:0]           t_hgi_ret,
    output wire [33:0]          t_inj,
    output wire [159:0]         t_inj_addr,
    output wire [79:0]          t_vmaddr,
    input  wire [1023:0]        f_inj_d,
    output wire [2343:0]        t_del,
    input  wire [260:0]         f_rc,
    output wire [260:0]         t_rr,
    inout  wire [NPT*1120-1:0]  llk,
    input  wire [279:0]         f_pr_cw,
    output wire [279:0]         t_pr_cw,
    input  wire [279:0]         f_pr_ccw,
    output wire [279:0]         t_pr_ccw,
    output wire [568:0]         t_tkw,
    input  wire                 f_tkw_rdy,
    output wire [75:0]          t_rgx_xq,
    input  wire [513:0]         f_rgx_xr,
    output wire [337:0]         t_rgx_vmq,
    input  wire [273:0]         f_rgx_vmr,
    output wire [8960:0]        t_rgx_c,
    input  wire [64:0]          f_rgx_c,
    output wire [651:0]         t_rgx_xw,
    input  wire [1:0]           f_rgx_xwa,
    output wire                 fault,
    output wire [31:0]          t_stat
);
    wire [NPT-1:0] tx_v, rx_credit, rx_v, sw_cr, lfault, locked;
    wire [NPT*545-1:0] tx_flit, rx_flit;
    wire [NPT*24-1:0] session;
    wire [2*NPT-1:0] status_unused;
    genvar k;
    generate for (k = 0; k < NPT; k = k + 1) begin : g_lk
        assign llk[1120*k +: 547] = {rx_credit[k], tx_flit[545*k +: 545], tx_v[k]};
        assign llk[1120*k + 1094 +: 24] = session[24*k +: 24];
        assign {sw_cr[k], rx_flit[545*k +: 545], rx_v[k]} = llk[1120*k + 547 +: 547];
        assign {locked[k], lfault[k]} = llk[1120*k + 1118 +: 2];
    end endgenerate
    wire [1:0] inj_rd; wire [31:0] inj_idx;
    wire [3:0] del_valid; wire [2179:0] del_flit; wire [159:0] del_obase;
    wire rc_rdy, rr_v; wire [2:0] rr_tag; wire [255:0] rr_d;
    assign t_inj = {inj_rd, inj_idx};
    assign t_del = {del_obase, del_flit, del_valid};
    assign t_rr = {rc_rdy, rr_d, rr_tag, rr_v};
    wire tk_v; wire [39:0] tk_a; wire [15:0] tk_m; wire [511:0] tk_d;
    assign t_tkw = {tk_d, tk_m, tk_a, tk_v};
    wire c_req; wire [32*280-1:0] c_q;
    assign t_rgx_c = {c_q, c_req};
    ot_hfd_coll_q #(.NPT(NPT), .TKM(TKM), .HOME(0), .QSOLO(0)) u_q (
        .clk(ck), .rst_n(rst), .qid(qid),
        .hgi_rec(f_hgi_rec), .hgi_recx(f_hgi_recx), .hgi_ret(t_hgi_ret), .hgi_cfg(f_hgi_cfg),
        .hgi_vmaddr(t_vmaddr), .hgi_inj_addr(t_inj_addr),
        .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_d(f_inj_d),
        .del_valid(del_valid), .del_flit(del_flit), .hgi_del_obase(del_obase),
        .fault(fault), .stat_credit_stall(t_stat),
        .lk_tx_v(tx_v), .lk_tx_flit(tx_flit), .lk_rx_credit(rx_credit), .lk_rx_v(rx_v), .lk_rx_flit(rx_flit),
        .lk_sw_cr(sw_cr), .lk_session(session), .lk_fault(lfault), .lk_locked(locked), .lk_status(status_unused),
        .pr_cw_i(f_pr_cw), .pr_cw_o(t_pr_cw), .pr_ccw_i(f_pr_ccw), .pr_ccw_o(t_pr_ccw),
        .rc_v(f_rc[0]), .rc_rdy(rc_rdy), .rc_tag(f_rc[3:1]), .rc_mode(f_rc[4]), .rc_d(f_rc[260:5]),
        .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
        .tk_w_v(tk_v), .tk_w_addr(tk_a), .tk_w_mask(tk_m), .tk_w_data(tk_d), .tk_w_rdy(f_tkw_rdy),
        .rgx_xq(t_rgx_xq), .rgx_xr(f_rgx_xr), .rgx_vmq(t_rgx_vmq), .rgx_vmr(f_rgx_vmr),
        .rgx_c_req(c_req), .rgx_c_gnt(f_rgx_c[0]), .rgx_c_q(c_q), .rgx_c_cr(f_rgx_c[32:1]), .rgx_c_rsp(f_rgx_c[64:33]),
        .rgx_xw(t_rgx_xw), .rgx_xwa(f_rgx_xwa));
endmodule

// SW: links S0-S2, the TOPK_MERGE array, the RGX lanes, HOME and QSOLO
module hfd_coll_q3 (
    input  wire ck, input wire rst, input wire [1:0] qid,
    input  wire [967:0] f_hgi_rec, input wire [553:0] f_hgi_recx, input wire [39:0] f_hgi_cfg, output wire [2:0] t_hgi_ret,
    output wire [33:0] t_inj, output wire [159:0] t_inj_addr, output wire [79:0] t_vmaddr, input wire [1023:0] f_inj_d,
    output wire [2343:0] t_del, input wire [260:0] f_rc, output wire [260:0] t_rr,
    inout  wire [1119:0] llk0, inout wire [1119:0] llk1, inout wire [1119:0] llk2,
    input  wire [279:0] f_pr_cw, output wire [279:0] t_pr_cw, input wire [279:0] f_pr_ccw, output wire [279:0] t_pr_ccw,
    output wire [568:0] t_tkw, input wire f_tkw_rdy,
    output wire [75:0] t_rgx_xq, input wire [513:0] f_rgx_xr, output wire [337:0] t_rgx_vmq, input wire [273:0] f_rgx_vmr,
    output wire [8960:0] t_rgx_c, input wire [64:0] f_rgx_c, output wire [651:0] t_rgx_xw, input wire [1:0] f_rgx_xwa,
    output wire fault, output wire [31:0] t_stat);
    hfd_coll_q_die #(.NPT(3), .TKM(1)) u (.ck(ck), .rst(rst), .qid(qid), .f_hgi_rec(f_hgi_rec), .f_hgi_recx(f_hgi_recx),
        .f_hgi_cfg(f_hgi_cfg), .t_hgi_ret(t_hgi_ret), .t_inj(t_inj), .t_inj_addr(t_inj_addr), .t_vmaddr(t_vmaddr),
        .f_inj_d(f_inj_d), .t_del(t_del), .f_rc(f_rc), .t_rr(t_rr), .llk({llk2, llk1, llk0}),
        .f_pr_cw(f_pr_cw), .t_pr_cw(t_pr_cw), .f_pr_ccw(f_pr_ccw), .t_pr_ccw(t_pr_ccw),
        .t_tkw(t_tkw), .f_tkw_rdy(f_tkw_rdy), .t_rgx_xq(t_rgx_xq), .f_rgx_xr(f_rgx_xr), .t_rgx_vmq(t_rgx_vmq),
        .f_rgx_vmr(f_rgx_vmr), .t_rgx_c(t_rgx_c), .f_rgx_c(f_rgx_c), .t_rgx_xw(t_rgx_xw), .f_rgx_xwa(f_rgx_xwa),
        .fault(fault), .t_stat(t_stat));
endmodule

// SE / NW / NE: two links each; the TKM / RGX inputs of the engine are idle by contract (QSOLO = SW)
module hfd_coll_q2 (
    input  wire ck, input wire rst, input wire [1:0] qid,
    input  wire [967:0] f_hgi_rec, input wire [553:0] f_hgi_recx, input wire [39:0] f_hgi_cfg, output wire [2:0] t_hgi_ret,
    output wire [33:0] t_inj, output wire [159:0] t_inj_addr, output wire [79:0] t_vmaddr, input wire [1023:0] f_inj_d,
    output wire [2343:0] t_del, input wire [260:0] f_rc, output wire [260:0] t_rr,
    inout  wire [1119:0] llk0, inout wire [1119:0] llk1,
    input  wire [279:0] f_pr_cw, output wire [279:0] t_pr_cw, input wire [279:0] f_pr_ccw, output wire [279:0] t_pr_ccw,
    output wire fault, output wire [31:0] t_stat);
    wire [568:0] idle_tkw; wire [75:0] idle_xq; wire [337:0] idle_vmq; wire [8960:0] idle_c; wire [651:0] idle_xw;
    hfd_coll_q_die #(.NPT(2), .TKM(0)) u (.ck(ck), .rst(rst), .qid(qid), .f_hgi_rec(f_hgi_rec), .f_hgi_recx(f_hgi_recx),
        .f_hgi_cfg(f_hgi_cfg), .t_hgi_ret(t_hgi_ret), .t_inj(t_inj), .t_inj_addr(t_inj_addr), .t_vmaddr(t_vmaddr),
        .f_inj_d(f_inj_d), .t_del(t_del), .f_rc(f_rc), .t_rr(t_rr), .llk({llk1, llk0}),
        .f_pr_cw(f_pr_cw), .t_pr_cw(t_pr_cw), .f_pr_ccw(f_pr_ccw), .t_pr_ccw(t_pr_ccw),
        .t_tkw(idle_tkw), .f_tkw_rdy(1'b1), .t_rgx_xq(idle_xq), .f_rgx_xr(514'd0), .t_rgx_vmq(idle_vmq), .f_rgx_vmr(274'd0),
        .t_rgx_c(idle_c), .f_rgx_c(65'd0), .t_rgx_xw(idle_xw), .f_rgx_xwa(2'd0), .fault(fault), .t_stat(t_stat));
endmodule
`default_nettype wire
