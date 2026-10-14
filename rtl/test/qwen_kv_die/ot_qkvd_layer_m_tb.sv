`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen ROM TP8 track B (one die type) 2026-10-13: end-to-end ATTENTION LAYER STEP through the MERGED-die KV sequencer
// (bench top; the two-die form is ot_qkvd_layer_tb).  The ROM end, the two D2D adapters and the PHY pair are gone:
//   ROM side : the SU / VM faces and the ROM sequencer's raw stage-step pins (harness: h_start / stage / token /
//              position out, s_done / next token in, program + descriptor writes) -> ROM_ST on-die relay stages ->
//              the merged sequencer;  host side: d_start {token, pos, gen} in, the done / result levels out
//   KV side  : merged sequencer -> the near-HBM attention (4 stacks + hub, ot_qwen_nearhbm_attn_die_tb) with the row
//              responses through the KV merge; RES back through the sequencer to the VM face.
// DUT: ot_qkvd_kv_seq_merged (flat), or with KVD_CLUSTER the hardened-leaf cluster qkd_seq (wires-only parent,
// rtl/physical/ot_qwen_kv_centre_slots.sv).  Quadrant copy 0 (WS) feeds the attention and the harness; the four
// copies of aq / kvn / kc are compared every cycle (faults[1]); each copy's row credit returns with its own delay
// (0 / 2 / 5 / 9 cycles after the harness's) through the credit join.
// MUT: 0 base | 2 KV merge off | 5 Q beats 0 / 1 swapped | 7 fence off (with KVL_STALL) | 13 launcher layer + 1 |
//      15 the ROM sequencer's copy of a program write lands one address up
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_layer_m_tb #(
    parameter integer HD     = 128,
    parameter integer R      = 8,
    parameter integer LINK   = 14,
    parameter integer ROM_ST = 24,
    parameter integer QX     = 0,
    parameter integer RX     = 0,
    parameter integer KVL    = 0,
    parameter integer KVL_STALL = 0,
    parameter integer MUT    = 0,
    parameter [31:0]  SCALE  = 32'h3DB504F3,
    parameter integer W      = 528,
    parameter integer DQ     = 32,
    parameter integer MERGE_PD = DQ,
    parameter integer HBMT   = 0,
    parameter integer HBMT_SLOT = 64,
    parameter integer HBMT_PULLIN = 0,
    parameter integer RQ_FAR = 0,
    parameter integer RS_FAR = 0,
    parameter integer E      = 4 * R
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              x3_v,
    input  wire [511:0]      x3_d,
    input  wire [10:0]       x3_tag,
    output wire              x3_cr,
    input  wire [55:0]       sd,
    input  wire [43:0]       kvd,
    output wire              ar_v,
    output wire [518:0]      ar_d,
    input  wire              ar_cr,
    output wire [186:0]      ds,
    output wire [74:0]       pw,
    output wire [E-1:0]      req_valid,
    output wire [E-1:0]      req_v,
    output wire [E-1:0]      req_g,
    output wire [13*E-1:0]   req_t,
    output wire [E-1:0]      hrow_rdy,
    output wire [E-1:0]      hrow_v,
    output wire [E-1:0]      hrow_g,
    output wire [13*E-1:0]   hrow_t,
    output wire [3:0]        hrow_fault,
    input  wire [E-1:0]      rsp_valid,
    input  wire [E*HD*8-1:0] rsp_data,
    output wire              kvw_v,
    output wire [1:0]        kvw_vg,
    output wire [13:0]       kvw_t,
    output wire [5:0]        kvw_layer,
    output wire [HD*8-1:0]   kvw_d,
    input  wire              kvw_cr,
    input  wire [181:0]      hc,
    output wire [92:0]       tk,
    output wire [3:0]        faults,          // {attention, KV sequencer, quadrant copies differ, 0}
    output wire              a_start_o,
    output wire              a_out_valid_o
);
    // ---------------- ROM side: harness faces -> ROM_ST relay stages -> the sequencer ----------------
    wire          x3_v_r, kv_v_r, x3_cr_r, ar_v_r, ar_cr_r;
    wire [522:0]  x3_r;
    wire [55:0]   sd_r;
    wire [42:0]   kv_r;
    wire [518:0]  ar_r;
    wire [186:0]  ds_r;
    wire [74:0]   pw_r;
    ot_hdc_delay #(.W(2), .D(ROM_ST), .RESET(1)) u_r1v (.clk(clk), .rst_n(rst_n), .d({x3_v, kvd[43]}), .q({x3_v_r, kv_v_r}));
    ot_hdc_delay #(.W(523 + 43), .D(ROM_ST)) u_r1d (.clk(clk), .rst_n(rst_n), .d({x3_tag, x3_d, kvd[42:0]}), .q({x3_r, kv_r}));
    ot_hdc_delay #(.W(56), .D(ROM_ST), .RESET(1)) u_r1s (.clk(clk), .rst_n(rst_n), .d(sd), .q(sd_r));
    ot_hdc_delay #(.W(1), .D(ROM_ST), .RESET(1)) u_r1c (.clk(clk), .rst_n(rst_n), .d(x3_cr_r), .q(x3_cr));
    ot_hdc_delay #(.W(1), .D(ROM_ST), .RESET(1)) u_r2v (.clk(clk), .rst_n(rst_n), .d(ar_v_r), .q(ar_v));
    ot_hdc_delay #(.W(519), .D(ROM_ST)) u_r2d (.clk(clk), .rst_n(rst_n), .d(ar_r), .q(ar_d));
    ot_hdc_delay #(.W(187 + 75), .D(ROM_ST), .RESET(1)) u_r2s (.clk(clk), .rst_n(rst_n), .d({ds_r, pw_r}), .q({ds, pw}));
    ot_hdc_delay #(.W(1), .D(ROM_ST), .RESET(1)) u_r2c (.clk(clk), .rst_n(rst_n), .d(ar_cr), .q(ar_cr_r));
    // ---------------- the merged sequencer ----------------
    wire [4*540-1:0]  aq;
    wire [4*(HD*8+23)-1:0] kvn;
    wire [3:0]    kvn_cr;
    wire [4*33-1:0] kc;
    wire          a_ov, a_og, hs, seq_f;
    wire [5:0]    a_ob;
    wire [511:0]  a_od;
    wire [8:0]    seq_fc;
    wire [4:0]    af;
    wire [3:0]    mf;
`ifdef KVD_CLUSTER
    wire [9:0]    kst;
    wire [519:0]  t_ar_w;
    qkd_seq u_seq (.ck(clk), .rst_n(rst_n), .r_x3_d({x3_v_r, x3_r}), .r_x3_cr(x3_cr_r), .r_sd(sd_r),
        .r_kvd({kv_v_r, kv_r}), .t_ar_d(t_ar_w), .t_ar_cr(ar_cr_r), .t_ds(ds_r), .t_pw(pw_r),
        .aq_WS(aq[0 +: 540]), .aq_WN(aq[540 +: 540]), .aq_ES(aq[1080 +: 540]), .aq_EN(aq[1620 +: 540]),
        .kvn_WS_d(kvn[0 +: 1047]), .kvn_WN_d(kvn[1047 +: 1047]), .kvn_ES_d(kvn[2094 +: 1047]), .kvn_EN_d(kvn[3141 +: 1047]),
        .kvn_WS_cr(kvn_cr[0]), .kvn_WN_cr(kvn_cr[1]), .kvn_ES_cr(kvn_cr[2]), .kvn_EN_cr(kvn_cr[3]),
        .kc_WS(kc[0 +: 33]), .kc_WN(kc[33 +: 33]), .kc_ES(kc[66 +: 33]), .kc_EN(kc[99 +: 33]),
        .af_WS(af[0]), .af_WN(af[1]), .af_ES(af[2]), .af_EN(af[3]), .mf_WS(mf[0]), .mf_WN(mf[1]), .mf_ES(mf[2]), .mf_EN(mf[3]),
        .ar({a_ov, a_og, a_ob, a_od}), .hf(af[4]), .hs(hs), .hc(hc), .tk(tk), .kst(kst));
    assign {ar_v_r, ar_r} = t_ar_w;
    assign {seq_f, seq_fc} = kst;
`else
    ot_qkvd_kv_seq_merged #(.HD(HD), .MUT(MUT == 5 ? 2 : (MUT == 13 ? 3 : (MUT == 15 ? 5 : 0)))) u_seq (
        .clk(clk), .rst_n(rst_n), .x3_v(x3_v_r), .x3_tag(x3_r[522:512]), .x3_d(x3_r[511:0]), .x3_cr(x3_cr_r),
        .sd(sd_r), .kvd({kv_v_r, kv_r}), .ar_v(ar_v_r), .ar_d(ar_r), .ar_cr(ar_cr_r), .ds(ds_r), .pw(pw_r),
        .aq(aq), .kvn(kvn), .kvn_cr(kvn_cr), .kc(kc), .af(af[3:0]), .mf(mf), .hs(hs),
        .a_out_valid(a_ov), .a_out_g(a_og), .a_out_beat(a_ob), .a_out_data(a_od), .a_hub_fault(af[4]), .hc(hc), .tk(tk),
        .fault(seq_f), .fault_cause(seq_fc));
`endif
    // quadrant copy 0 -> attention, landings and the harness; the four copies must agree every cycle
    wire          a_start = aq[539], a_qv = aq[518];
    wire [13:0]   a_T = aq[538:525];
    wire [5:0]    a_L = aq[524:519], a_qb = aq[517:512];
    wire [511:0]  a_qd = aq[511:0];
    assign kvw_v = kvn[HD*8+22];
    assign kvw_vg = kvn[HD*8+21 -: 2];
    assign kvw_t = kvn[HD*8+19 -: 14];
    assign kvw_layer = kvn[HD*8+5 -: 6];
    assign kvw_d = kvn[HD*8-1:0];
    reg cp_bad;
    integer c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cp_bad <= 1'b0;
        else for (c = 1; c < 4; c = c + 1) begin
            if (aq[540*c + 539] !== aq[539] || aq[540*c + 518] !== aq[518] || kvn[(HD*8+23)*c + HD*8+22] !== kvn[HD*8+22] ||
                kc[33*c + 32] !== kc[32]) cp_bad <= 1'b1;
            if (aq[539] && aq[540*c + 519 +: 20] !== aq[519 +: 20]) cp_bad <= 1'b1;
            if (aq[518] && aq[540*c +: 518] !== aq[0 +: 518]) cp_bad <= 1'b1;
            if (kvn[HD*8+22] && kvn[(HD*8+23)*c +: HD*8+22] !== kvn[0 +: HD*8+22]) cp_bad <= 1'b1;
            if (kc[32] && kc[33*c +: 32] !== kc[0 +: 32]) cp_bad <= 1'b1;
        end
    // each landing write queue returns its own credit per row (different delays through the join)
    assign kvn_cr[0] = kvw_cr;
    ot_hdc_delay #(.W(1), .D(2), .RESET(1)) u_cr1 (.clk(clk), .rst_n(rst_n), .d(kvw_cr), .q(kvn_cr[1]));
    ot_hdc_delay #(.W(1), .D(5), .RESET(1)) u_cr2 (.clk(clk), .rst_n(rst_n), .d(kvw_cr), .q(kvn_cr[2]));
    ot_hdc_delay #(.W(1), .D(9), .RESET(1)) u_cr3 (.clk(clk), .rst_n(rst_n), .d(kvw_cr), .q(kvn_cr[3]));
    wire [E-1:0]  e_rv;
    wire [E*HD*8-1:0] e_rd;
    wire       kl_v;
    wire [1:0] kl_vg;
    wire [13:0] kl_t;
    wire [HD*8-1:0] kl_d;
    wire [5:0] kl_l;
    ot_hdc_delay #(.W(1), .D(KVL + KVL_STALL), .RESET(1)) u_klv (.clk(clk), .rst_n(rst_n), .d(kvw_v), .q(kl_v));
    ot_hdc_delay #(.W(2 + 14 + 6 + HD*8), .D(KVL + KVL_STALL)) u_kld (.clk(clk), .rst_n(rst_n), .d({kvw_vg, kvw_t, kvw_layer, kvw_d}),
                                                                   .q({kl_vg, kl_t, kl_l, kl_d}));
    wire          x_start, x_qv, h_ov, h_og;
    wire [13:0]   x_T;
    wire [5:0]    x_L;
    wire [E-1:0]  m_rq_v, m_rq_vv, m_rq_g;
    wire [13*E-1:0] m_rq_t;
    wire [5:0]    x_qb, h_ob;
    wire [511:0]  x_qd, h_od;
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_land
        ot_qkvd_kv_merge #(.HD(HD), .E(R), .DQ(DQ), .PD(MERGE_PD), .MUT(MUT == 2 ? 1 : (MUT == 7 ? 2 : 0))) u_merge (.clk(clk), .rst_n(rst_n), .kvw_v(kl_v),
            .kvw_vg(kl_vg), .kvw_t(kl_t), .kvw_layer(kl_l), .kvw_d(kl_d), .lay_start(x_start), .lay_T(x_T), .lay_idx(x_L),
            .e_req_valid(m_rq_v[R*s +: R]), .e_req_v(m_rq_vv[R*s +: R]), .e_req_g(m_rq_g[R*s +: R]),
            .e_req_t(m_rq_t[13*R*s +: 13*R]), .h_req_valid(req_valid[R*s +: R]), .h_req_v(req_v[R*s +: R]),
            .h_req_g(req_g[R*s +: R]), .h_req_t(req_t[13*R*s +: 13*R]), .h_rsp_valid(rsp_valid[R*s +: R]),
            .h_rsp_data(rsp_data[HD*8*R*s +: HD*8*R]), .e_rsp_valid(e_rv[R*s +: R]), .e_rsp_data(e_rd[HD*8*R*s +: HD*8*R]),
            .fault(mf[s]));
    end endgenerate
    ot_hdc_delay #(.W(2), .D(QX), .RESET(1)) u_qxv (.clk(clk), .rst_n(rst_n), .d({a_start, a_qv}), .q({x_start, x_qv}));
    ot_hdc_delay #(.W(14 + 6 + 6 + 512), .D(QX)) u_qxd (.clk(clk), .rst_n(rst_n), .d({a_T, a_L, a_qb, a_qd}), .q({x_T, x_L, x_qb, x_qd}));
    ot_hdc_delay #(.W(1), .D(RX), .RESET(1)) u_rxv (.clk(clk), .rst_n(rst_n), .d(h_ov), .q(a_ov));
    ot_hdc_delay #(.W(1 + 6 + 512), .D(RX)) u_rxd (.clk(clk), .rst_n(rst_n), .d({h_og, h_ob, h_od}), .q({a_og, a_ob, a_od}));
    ot_qwen_nearhbm_attn_die_tb #(.HD(HD), .R(R), .LINK(LINK), .SCALE(SCALE), .DQ(DQ)) u_attn (
        .clk(clk), .rst_n(rst_n), .start(x_start), .T(x_T), .q_valid(x_qv), .q_beat(x_qb), .q_data(x_qd),
        .req_valid(m_rq_v), .req_v(m_rq_vv), .req_g(m_rq_g), .req_t(m_rq_t), .rsp_valid(e_rv), .rsp_data(e_rd),
        .out_valid(h_ov), .out_g(h_og), .out_beat(h_ob), .out_data(h_od), .fault(af), .ev_stack(), .ev_hub());
    assign faults = {|af, seq_f, cp_bad, 1'b0};
    assign a_start_o = a_start;
    assign a_out_valid_o = a_ov;
    genvar hs_i;
    generate if (HBMT) begin : g_hbmt
        for (hs_i = 0; hs_i < 4; hs_i = hs_i + 1) begin : g_s
            ot_qkvd_hbm_timed_stack #(.R(R), .NSLOT(HBMT_SLOT), .PULLIN(HBMT_PULLIN), .RQ_FAR(RQ_FAR), .RS_FAR(RS_FAR)) u_hs (.clk(clk), .rst_n(rst_n),
                .rq_v_i(req_valid[R*hs_i +: R]), .rq_vv_i(req_v[R*hs_i +: R]), .rq_g_i(req_g[R*hs_i +: R]), .rq_t_i(req_t[13*R*hs_i +: 13*R]),
                .row_rdy(hrow_rdy[R*hs_i +: R]), .row_vv(hrow_v[R*hs_i +: R]), .row_g(hrow_g[R*hs_i +: R]),
                .row_t(hrow_t[13*R*hs_i +: 13*R]), .fault(hrow_fault[hs_i]));
        end
    end else begin : g_nohbmt
        assign hrow_rdy = '0; assign hrow_v = '0; assign hrow_g = '0; assign hrow_t = '0; assign hrow_fault = '0;
    end endgenerate
endmodule
