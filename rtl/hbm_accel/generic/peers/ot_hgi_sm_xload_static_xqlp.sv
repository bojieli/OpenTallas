`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sm_xload_static_xqlp (HBM-XLP10 10-20): ot_hgi_sm_xload_static_xql (XQL quadrant x-load: F20-faced control +
// 2 quantisers + NP pair clusters behind equal-age trees of depth T) with the PIPELINED control ot_hgi_sm_xload_cl2xp_ctlx
// (ot_hgi_sm_xload_static_cl2xp.sv).  Pairs, trees, quantisers and every pair leaf are the xql / cl2 modules unchanged.
module ot_hgi_sm_xload_static_xqlp #(
    parameter integer PMAX   = 8,
    parameter [63:0]  RD_LAT = 64'd6,    // scalar or per-bank vector, passed to the ctl (ot_hgi_sm_xload_cl2_ctl RD_LAT)
    parameter integer MUT    = 0,
    parameter integer NP     = 4,
    parameter integer T      = 2,
    parameter integer XQL_MUT = 0,
    parameter integer CTL_OLD = 0         // unused (interface parity with ot_hgi_sm_xload_static_xql)
) (
    input  wire               clk,
    input  wire               clk_cal,
    input  wire               clk_qlo,
    input  wire               clk_qhi,
    input  wire [NP*4-1:0]    clk_bf,
    input  wire [NP-1:0]      clk_bd,
    input  wire [NP-1:0]      clk_eg,
    input  wire               rst_n,
    input  wire [7:0]         tgt,
    input  wire               cfg_v,
    input  wire [7:0]         cfg_target,
    input  wire [11:0]        cfg_addr,
    input  wire [255:0]       cfg_data,
    input  wire               desc_v,
    input  wire [11:0]        desc_base,
    input  wire [12:0]        desc_limit,
    input  wire [15:0]        desc_loops,
    input  wire               launch_v,
    output wire               configured,
    output wire               fault,
    output wire               active,
    output wire [NP-1:0]      x_done,
    output wire [NP-1:0]      xw_en,
    output wire [NP-1:0]      xw_last,
    output wire [NP*7-1:0]    xw_addr,
    output wire [NP*7-1:0]    xw_grp,
    output wire [NP*2048-1:0] xw_data,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr
);
    localparam integer NBQ2 = 2 * ((PMAX * 3152 + 2047) / 2048);
    wire rn;
    wire [1023:0] c_d; wire [3:0] c_wce; wire c_mhi, c_mlo; wire [6:0] c_wa; wire [7:0] r_ce; wire [6:0] r_a;
    wire [2047:0] l_d; wire qv_lo, qv_hi, qo_lo, qo_hi, qf_lo, qf_hi; wire [255:0] qq_lo, qq_hi; wire signed [9:0] qe_lo, qe_hi;
    wire [15:0] r_wsel; wire zlo, zhi; wire [NBQ2-1:0] bsel; wire [PMAX*8-1:0] lane_en;
    wire [7:0] eg_ed5; wire [16:0] eg_ede; wire eg_bqv, eg_bqlast; wire [6:0] eg_bqaddr, eg_bqb;
    // d4f die master ctlx (HBM-B 10-17) = ctlw EGRESS_SPLIT 1 with the die-connected ports only + kept select replicas
    ot_hgi_sm_xload_cl2xp_ctlx #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT)) u_ctl (
        .clk(clk), .clk_cal(clk_cal), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .fault(fault), .active(active),
        .rq(rq), .rr(rr), .rn_o(rn),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a),
        .l_d_o(l_d), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en),
        .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast), .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
    ot_hbm_xp_aq_tree13 u_aq_lo (.clk(clk_qlo), .rst_n(rn), .v(qv_lo), .fp4(1'b0), .x(l_d[1023:0]), .vo(qo_lo), .q(qq_lo),
                             .e(qe_lo), .y(), .fault(qf_lo));
    ot_hbm_xp_aq_tree13 u_aq_hi (.clk(clk_qhi), .rst_n(rn), .v(qv_hi), .fp4(1'b0), .x(l_d[2047:1024]), .vo(qo_hi), .q(qq_hi),
                             .e(qe_hi), .y(), .fault(qf_hi));
    // the ctl -> pair bundle (one equal-age tree per pair)
    localparam integer BW = 1 + 1024 + 4 + 2 + 7 + 8 + 7 + 16 + 2 + 512 + 20 + NBQ2 + PMAX*8 + 8 + 17 + 2 + 14;
    wire [BW-1:0] bun = {rn, c_d, c_wce, c_mhi, c_mlo, c_wa, r_ce, r_a, r_wsel, zlo, zhi, qq_lo, qq_hi, qe_lo, qe_hi, bsel,
                         lane_en, eg_ed5, eg_ede, eg_bqv, eg_bqlast, eg_bqaddr, eg_bqb};
    genvar gp;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
        localparam integer TP = T + ((XQL_MUT == 2 && gp == 2) ? 1 : 0);
        wire [BW-1:0] b;
        ot_hgi_sm_xload_xq_tree #(.W(BW), .T(TP)) u_tree (.clk(clk), .d(bun), .q(b));
        wire p_rn; wire [1023:0] p_cd; wire [3:0] p_wce; wire p_mhi, p_mlo; wire [6:0] p_wa; wire [7:0] p_rce; wire [6:0] p_ra;
        wire [15:0] p_wsel; wire p_zlo, p_zhi; wire [255:0] p_qlo, p_qhi; wire signed [9:0] p_elo, p_ehi; wire [NBQ2-1:0] p_bsel;
        wire [PMAX*8-1:0] p_len; wire [7:0] p_ed5; wire [16:0] p_ede; wire p_bqv, p_bql; wire [6:0] p_bqa, p_bqb;
        assign {p_rn, p_cd, p_wce, p_mhi, p_mlo, p_wa, p_rce, p_ra, p_wsel, p_zlo, p_zhi, p_qlo, p_qhi, p_elo, p_ehi, p_bsel,
                p_len, p_ed5, p_ede, p_bqv, p_bql, p_bqa, p_bqb} = b;
        ot_hgi_sm_xload_xq_pair #(.PMAX(PMAX), .MAPMUT((XQL_MUT == 3 && gp == 3) ? 1 : 0)) u_pair (
            .clk_bf(clk_bf[gp*4 +: 4]), .clk_bd(clk_bd[gp]), .clk_eg(clk_eg[gp]), .rn(p_rn), .c_d(p_cd),
            .c_wce((XQL_MUT == 1 && gp == 1) ? 4'd0 : p_wce), .c_mhi(p_mhi), .c_mlo(p_mlo), .c_wa(p_wa),
            .r_ce(p_rce), .r_a(p_ra), .r_wsel(p_wsel), .zlo(p_zlo), .zhi(p_zhi), .qq_lo(p_qlo), .qq_hi(p_qhi),
            .qe_lo(p_elo), .qe_hi(p_ehi), .bsel(p_bsel), .lane_en(p_len), .ed5(p_ed5), .ede(p_ede), .bq_v(p_bqv),
            .bq_last(p_bql), .bq_addr(p_bqa), .bq_b(p_bqb), .x_done(x_done[gp]), .xw_en(xw_en[gp]), .xw_last(xw_last[gp]),
            .xw_addr(xw_addr[gp*7 +: 7]), .xw_grp(xw_grp[gp*7 +: 7]), .xw_data(xw_data[gp*2048 +: 2048]));
    end endgenerate
endmodule
`default_nettype wire
