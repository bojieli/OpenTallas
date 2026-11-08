`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// S81-RCK-11 11-08 (COORD RE-FORM ruling, owner two-strikes rule): serdes__t16 conservative form.  The column's
// receive decoder and transmit encoder are regrouped into three single-clock HARD CORES with registered faces; no
// logic changes, ZERO added cycles (every cut falls on an existing register):
//   ot_s81_rck_rxs  RX-SYN core  : the last u_rck_transport4 stage (moved inside, the parent keeps 3) + ot_s81_kp4_dsyn
//                                   (vJ OT_S81_KP4_SYN_LOCAL: every output registered)          clock pma_rck
//   ot_s81_rck_rxb  RX-BACK core : the 11 lpl landings + dly (dmem SRAM) + chn (dchn macro) + out (cmem SRAM) + the
//                                   q / n_corr / n_unc face pads                                 clock pma_rck
//   ot_s81_rck_tx   TX core      : the 3 TX input PIN stages + ot_s81_kp4_enc (= ot_s81_serdes_col_tx_pin N=3)  clock clk
// ot_s81_rck_dec = ot_s81_kp4_dec_native_flat_lp (rtl/dsrom_sys/s81_link/lp, lp.py, not edited) with the same ports;
// the parent glue keeps the PMA face pads, 3 transport stages, the AM face, the region reset pads and lock/n_relock
// pads.  The four region clocks of the landed decoder are all pma_rck in ot_pdie_serdes_col, so RX-BACK has ONE clock
// port 'ck' (ck_dly): equal to the lp decoder whenever ck_syn = ck_dly = ck_chn = ck_out (the only use).
// Requires OT_S81_RCK_RELAY4 + OT_S81_KP4_AM_FACE3 + OT_S81_KP4_SYN_LOCAL (+ OT_S81_SERDES_COL_PIN for the TX core).
// Lock-step proof vs the vJ column: results/s81_rck_11_reform_1108.
// ---------------------------------------------------------------------------------------------------------------
`ifdef OT_S81_RCK_REFORM
`ifndef OT_S81_RCK_RELAY4
`error "OT_S81_RCK_REFORM requires OT_S81_RCK_RELAY4"
`endif
`ifndef OT_S81_KP4_AM_FACE3
`error "OT_S81_RCK_REFORM requires OT_S81_KP4_AM_FACE3"
`endif
`ifndef OT_S81_KP4_SYN_LOCAL
`error "OT_S81_RCK_REFORM requires OT_S81_KP4_SYN_LOCAL (registered k_* faces)"
`endif

module ot_s81_rck_dec #(
    parameter integer MUT = 0
) (
    input wire rst_n,
    input wire p_v,
    input wire [543:0] p_d,
    output wire q_v,
    output wire [511:0] q_d,
    output wire q_first,
    output wire q_unc,
    output wire [4:0] q_nerr,
    output wire [7:0] q_seq,
    output wire lock,
    output wire [31:0] n_corr,
    output wire [31:0] n_unc,
    output wire [31:0] n_relock,
    input wire ck_syn,
    input wire ck_dly,
    input wire ck_chn,
    input wire ck_out
);
    wire [543:0] x_q;
    wire [3:0]   k_v;
    wire [309:0] k_lo;
    wire [4:0]   k_L;
    wire         k_any;
    wire face_p_v; wire [543:0] face_p_d; wire [8:0] face_am_parts;
    wire face_lock; wire [31:0] face_n_relock;
    ot_s81_kp4_am_face3 u_face_am3 (.clk(ck_syn), .p_d(p_d), .parts(face_am_parts));
    ot_pl_pad #(.W(1), .N(1)) u_face_p_v (.ck(ck_syn), .d(p_v), .q(face_p_v));
    ot_pl_pad #(.W(544), .N(1)) u_face_p_d (.ck(ck_syn), .d(p_d), .q(face_p_d));
    // transport: 3 of the 4 relay stages here (they walk from the PMA RX pin row); the 4th is RX-SYN's input face
    wire [543:0] t_d; wire t_v; wire [8:0] t_am; wire t_rst;
    ot_pl_pad #(.W(554), .N(
`ifdef RCKRF_MUT_SHORT
        2
`else
        3
`endif
        )) u_rck_transport3 (.ck(ck_syn), .d({face_am_parts, face_p_v, face_p_d}), .q({t_am, t_v, t_d}));
    // the reset calendar keeps its 4 edges (it is not part of the core face)
    ot_pl_pad #(.W(1), .N(4)) u_rck_reset4 (.ck(ck_syn), .d(rst_n), .q(t_rst));
    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_syn), .d(t_rst), .q(lpr_root));
    wire lpr_syn;  ot_pl_pad #(.W(1), .N(2)) u_lpr_syn (.ck(ck_syn), .d(lpr_root), .q(lpr_syn));
    wire lpr_dly;  ot_pl_pad #(.W(1), .N(2)) u_lpr_dly (.ck(ck_dly), .d(lpr_root), .q(lpr_dly));
    wire lpr_chn;  ot_pl_pad #(.W(1), .N(2)) u_lpr_chn (.ck(ck_chn), .d(lpr_root), .q(lpr_chn));
    wire lpr_out;  ot_pl_pad #(.W(1), .N(2)) u_lpr_out (.ck(ck_out), .d(lpr_root), .q(lpr_out));
    wire lpr_c_u_syn;  ot_pl_pad #(.W(1), .N((MUT == 4) ? 1 : 0)) u_lprc_u_syn (.ck(ck_syn), .d(lpr_syn), .q(lpr_c_u_syn));
    ot_s81_rck_rxs u_rxs (.ck(ck_syn), .rst_n(lpr_c_u_syn), .i_v(t_v), .i_d(t_d), .i_am(t_am),
        .x_q(x_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any), .lock(face_lock), .n_relock(face_n_relock));
    ot_s81_rck_rxb #(.MUT(MUT)) u_rxb (.ck(ck_dly), .lpr_syn(lpr_syn), .lpr_dly(lpr_dly), .lpr_chn(lpr_chn), .lpr_out(lpr_out),
        .x_q(x_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L), .k_any(k_any),
        .q_v(q_v), .q_d(q_d), .q_first(q_first), .q_unc(q_unc), .q_nerr(q_nerr), .q_seq(q_seq), .n_corr(n_corr), .n_unc(n_unc));
    ot_pl_pad #(.W(1), .N(1)) u_face_lock (.ck(ck_syn), .d(face_lock), .q(lock));
    ot_pl_pad #(.W(32), .N(1)) u_face_n_relock (.ck(ck_syn), .d(face_n_relock), .q(n_relock));
endmodule

// RX-SYN hard core: input face = the 4th transport stage (554 b, one flop per pin, no logic), dsyn behind it.
(* keep_hierarchy *)
module ot_s81_rck_rxs (
    input wire ck,
    input wire rst_n,
    input wire i_v,
    input wire [543:0] i_d,
    input wire [8:0] i_am,
    output wire [543:0] x_q,
    output wire [3:0] k_v,
    output wire [309:0] k_lo,
    output wire [4:0] k_L,
    output wire k_any,
    output wire lock,
    output wire [31:0] n_relock
);
    wire [543:0] p_d; wire p_v; wire [8:0] am;
    ot_pl_pad #(.W(554), .N(1)) u_face_in (.ck(ck), .d({i_am, i_v, i_d}), .q({am, p_v, p_d}));
    ot_s81_kp4_dsyn u_syn (.clk(ck), .rst_n(rst_n), .p_v(p_v), .p_d(p_d), .x_q(x_q), .k_v(k_v), .k_lo(k_lo), .k_L(k_L),
        .k_any(k_any), .lock(lock), .n_relock(n_relock), .am_face3(am));
endmodule

// RX-BACK hard core: the landed decoder back end, verbatim from ot_s81_kp4_dec_native_flat_lp with ck_* -> ck.
(* keep_hierarchy *)
module ot_s81_rck_rxb #(
    parameter integer MUT = 0
) (
    input wire ck,
    input wire lpr_syn,
    input wire lpr_dly,
    input wire lpr_chn,
    input wire lpr_out,
    input wire [543:0] x_q,
    input wire [3:0] k_v,
    input wire [309:0] k_lo,
    input wire [4:0] k_L,
    input wire k_any,
    output wire q_v,
    output wire [511:0] q_d,
    output wire q_first,
    output wire q_unc,
    output wire [4:0] q_nerr,
    output wire [7:0] q_seq,
    output wire [31:0] n_corr,
    output wire [31:0] n_unc
);
    wire [543:0] d_q, cw;
    wire [4:0] o_ne; wire o_unc, fs; wire [7:0] apply;
    wire face_q_v; wire [511:0] face_q_d; wire face_q_first, face_q_unc; wire [4:0] face_q_nerr; wire [7:0] face_q_seq;
    wire [31:0] face_n_corr, face_n_unc;
    wire [4*((543) - (0) + 1)-1:0] lpl_0_bank;  wire [11:0] lpl_0_epo;  wire [3:0] lpl_0_vld;  wire [543:0] x_q__l_dly, lpl_0_o;
    ot_pl_land_w #(.W(((543) - (0) + 1)), .D(4)) u_lpl_0_w (.ck(ck), .rsi(lpr_syn), .i(x_q), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld));
    ot_pl_land_r #(.W(((543) - (0) + 1)), .D(4), .K((MUT == 2) ? 3 : 2)) u_lpl_0_r (.ck(ck), .rsi(lpr_dly), .bank(lpl_0_bank), .epo(lpl_0_epo), .vld(lpl_0_vld), .o(lpl_0_o));
    assign x_q__l_dly = (MUT == 1) ? x_q : lpl_0_o;
    wire [4*((3) - (0) + 1)-1:0] lpl_1_bank;  wire [11:0] lpl_1_epo;  wire [3:0] lpl_1_vld;  wire [3:0] k_v__l_chn, lpl_1_o;
    ot_pl_land_w #(.W(((3) - (0) + 1)), .D(4)) u_lpl_1_w (.ck(ck), .rsi(lpr_syn), .i(k_v), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld));
    ot_pl_land_r #(.W(((3) - (0) + 1)), .D(4), .K(2)) u_lpl_1_r (.ck(ck), .rsi(lpr_chn), .bank(lpl_1_bank), .epo(lpl_1_epo), .vld(lpl_1_vld), .o(lpl_1_o));
    assign k_v__l_chn = lpl_1_o;
    wire [4*((309) - (0) + 1)-1:0] lpl_2_bank;  wire [11:0] lpl_2_epo;  wire [3:0] lpl_2_vld;  wire [309:0] k_lo__l_chn, lpl_2_o;
    ot_pl_land_w #(.W(((309) - (0) + 1)), .D(4)) u_lpl_2_w (.ck(ck), .rsi(lpr_syn), .i(k_lo), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld));
    ot_pl_land_r #(.W(((309) - (0) + 1)), .D(4), .K(2)) u_lpl_2_r (.ck(ck), .rsi(lpr_chn), .bank(lpl_2_bank), .epo(lpl_2_epo), .vld(lpl_2_vld), .o(lpl_2_o));
    assign k_lo__l_chn = lpl_2_o;
    wire [4*((4) - (0) + 1)-1:0] lpl_3_bank;  wire [11:0] lpl_3_epo;  wire [3:0] lpl_3_vld;  wire [4:0] k_L__l_chn, lpl_3_o;
    ot_pl_land_w #(.W(((4) - (0) + 1)), .D(4)) u_lpl_3_w (.ck(ck), .rsi(lpr_syn), .i(k_L), .bank(lpl_3_bank), .epo(lpl_3_epo), .vld(lpl_3_vld));
    ot_pl_land_r #(.W(((4) - (0) + 1)), .D(4), .K(2)) u_lpl_3_r (.ck(ck), .rsi(lpr_chn), .bank(lpl_3_bank), .epo(lpl_3_epo), .vld(lpl_3_vld), .o(lpl_3_o));
    assign k_L__l_chn = lpl_3_o;
    wire [4*1-1:0] lpl_4_bank;  wire [11:0] lpl_4_epo;  wire [3:0] lpl_4_vld;  wire  k_any__l_chn, lpl_4_o;
    ot_pl_land_w #(.W(1), .D(4)) u_lpl_4_w (.ck(ck), .rsi(lpr_syn), .i(k_any), .bank(lpl_4_bank), .epo(lpl_4_epo), .vld(lpl_4_vld));
    ot_pl_land_r #(.W(1), .D(4), .K(2)) u_lpl_4_r (.ck(ck), .rsi(lpr_chn), .bank(lpl_4_bank), .epo(lpl_4_epo), .vld(lpl_4_vld), .o(lpl_4_o));
    assign k_any__l_chn = lpl_4_o;
    wire [4*((543) - (0) + 1)-1:0] lpl_5_bank;  wire [11:0] lpl_5_epo;  wire [3:0] lpl_5_vld;  wire [543:0] d_q__l_out, lpl_5_o;
    ot_pl_land_w #(.W(((543) - (0) + 1)), .D(4)) u_lpl_5_w (.ck(ck), .rsi(lpr_dly), .i(d_q), .bank(lpl_5_bank), .epo(lpl_5_epo), .vld(lpl_5_vld));
    ot_pl_land_r #(.W(((543) - (0) + 1)), .D(4), .K(2)) u_lpl_5_r (.ck(ck), .rsi(lpr_out), .bank(lpl_5_bank), .epo(lpl_5_epo), .vld(lpl_5_vld), .o(lpl_5_o));
    assign d_q__l_out = lpl_5_o;
    wire [4*((543) - (0) + 1)-1:0] lpl_6_bank;  wire [11:0] lpl_6_epo;  wire [3:0] lpl_6_vld;  wire [543:0] cw__l_out, lpl_6_o;
    ot_pl_land_w #(.W(((543) - (0) + 1)), .D(4)) u_lpl_6_w (.ck(ck), .rsi(lpr_chn), .i(cw), .bank(lpl_6_bank), .epo(lpl_6_epo), .vld(lpl_6_vld));
    ot_pl_land_r #(.W(((543) - (0) + 1)), .D(4), .K(2)) u_lpl_6_r (.ck(ck), .rsi(lpr_out), .bank(lpl_6_bank), .epo(lpl_6_epo), .vld(lpl_6_vld), .o(lpl_6_o));
    assign cw__l_out = lpl_6_o;
    wire [4*((7) - (0) + 1)-1:0] lpl_7_bank;  wire [11:0] lpl_7_epo;  wire [3:0] lpl_7_vld;  wire [7:0] apply__l_out, lpl_7_o;
    ot_pl_land_w #(.W(((7) - (0) + 1)), .D(4)) u_lpl_7_w (.ck(ck), .rsi(lpr_chn), .i(apply), .bank(lpl_7_bank), .epo(lpl_7_epo), .vld(lpl_7_vld));
    ot_pl_land_r #(.W(((7) - (0) + 1)), .D(4), .K(2)) u_lpl_7_r (.ck(ck), .rsi(lpr_out), .bank(lpl_7_bank), .epo(lpl_7_epo), .vld(lpl_7_vld), .o(lpl_7_o));
    assign apply__l_out = lpl_7_o;
    wire [4*1-1:0] lpl_8_bank;  wire [11:0] lpl_8_epo;  wire [3:0] lpl_8_vld;  wire  o_unc__l_out, lpl_8_o;
    ot_pl_land_w #(.W(1), .D(4)) u_lpl_8_w (.ck(ck), .rsi(lpr_chn), .i(o_unc), .bank(lpl_8_bank), .epo(lpl_8_epo), .vld(lpl_8_vld));
    ot_pl_land_r #(.W(1), .D(4), .K(2)) u_lpl_8_r (.ck(ck), .rsi(lpr_out), .bank(lpl_8_bank), .epo(lpl_8_epo), .vld(lpl_8_vld), .o(lpl_8_o));
    assign o_unc__l_out = lpl_8_o;
    wire [4*((4) - (0) + 1)-1:0] lpl_9_bank;  wire [11:0] lpl_9_epo;  wire [3:0] lpl_9_vld;  wire [4:0] o_ne__l_out, lpl_9_o;
    ot_pl_land_w #(.W(((4) - (0) + 1)), .D(4)) u_lpl_9_w (.ck(ck), .rsi(lpr_chn), .i(o_ne), .bank(lpl_9_bank), .epo(lpl_9_epo), .vld(lpl_9_vld));
    ot_pl_land_r #(.W(((4) - (0) + 1)), .D(4), .K(2)) u_lpl_9_r (.ck(ck), .rsi(lpr_out), .bank(lpl_9_bank), .epo(lpl_9_epo), .vld(lpl_9_vld), .o(lpl_9_o));
    assign o_ne__l_out = lpl_9_o;
    wire [4*1-1:0] lpl_10_bank;  wire [11:0] lpl_10_epo;  wire [3:0] lpl_10_vld;  wire  fs__l_out, lpl_10_o;
    ot_pl_land_w #(.W(1), .D(4)) u_lpl_10_w (.ck(ck), .rsi(lpr_chn), .i(fs), .bank(lpl_10_bank), .epo(lpl_10_epo), .vld(lpl_10_vld));
    ot_pl_land_r #(.W(1), .D(4), .K(2)) u_lpl_10_r (.ck(ck), .rsi(lpr_out), .bank(lpl_10_bank), .epo(lpl_10_epo), .vld(lpl_10_vld), .o(lpl_10_o));
    assign fs__l_out = lpl_10_o;
    wire lpr_c_u_dly;  ot_pl_pad #(.W(1), .N(3)) u_lprc_u_dly (.ck(ck), .d(lpr_dly), .q(lpr_c_u_dly));   // t(u_dly) = 3
    wire lpr_c_u_chn;  ot_pl_pad #(.W(1), .N(3)) u_lprc_u_chn (.ck(ck), .d(lpr_chn), .q(lpr_c_u_chn));   // t(u_chn) = 3
    wire lpr_c_u_out;  ot_pl_pad #(.W(1), .N(6)) u_lprc_u_out (.ck(ck), .d(lpr_out), .q(lpr_c_u_out));   // t(u_out) = 6
    ot_s81_kp4_ddly u_dly (.clk(ck), .rst_n(lpr_c_u_dly), .w_d(x_q__l_dly), .r_d(d_q));   // region dly, t = 3
    ot_s81_kp4_dchn u_chn (.clk(ck), .rst_n(lpr_c_u_chn), .k_v(k_v__l_chn), .k_lo(k_lo__l_chn), .k_L(k_L__l_chn), .k_any(k_any__l_chn), .cw_q(cw), .apply(apply), .o_unc(o_unc), .o_ne(o_ne), .fs(fs), .n_corr(face_n_corr), .n_unc(face_n_unc));   // region chn, t = 3
    ot_s81_kp4_dout u_out (.clk(ck), .rst_n(lpr_c_u_out), .d_q(d_q__l_out), .cw(cw__l_out), .apply(apply__l_out), .o_unc(o_unc__l_out), .o_ne(o_ne__l_out), .fs(fs__l_out), .q_v(face_q_v), .q_d(face_q_d), .q_first(face_q_first), .q_unc(face_q_unc), .q_nerr(face_q_nerr), .q_seq(face_q_seq));   // region out, t = 6
    ot_pl_pad #(.W(1), .N(1)) u_face_q_v (.ck(ck), .d(face_q_v), .q(q_v));   // region out, t = 6
    ot_pl_pad #(.W(((511) - (0) + 1)), .N(1)) u_face_q_d (.ck(ck), .d(face_q_d), .q(q_d));   // region out, t = 6
    ot_pl_pad #(.W(1), .N(1)) u_face_q_first (.ck(ck), .d(face_q_first), .q(q_first));   // region out, t = 6
    ot_pl_pad #(.W(1), .N(1)) u_face_q_unc (.ck(ck), .d(face_q_unc), .q(q_unc));   // region out, t = 6
    ot_pl_pad #(.W(((4) - (0) + 1)), .N(1)) u_face_q_nerr (.ck(ck), .d(face_q_nerr), .q(q_nerr));   // region out, t = 6
    ot_pl_pad #(.W(((7) - (0) + 1)), .N(1)) u_face_q_seq (.ck(ck), .d(face_q_seq), .q(q_seq));   // region out, t = 6
    ot_pl_pad #(.W(((31) - (0) + 1)), .N(1)) u_face_n_corr (.ck(ck), .d(face_n_corr), .q(n_corr));   // region chn, t = 3
    ot_pl_pad #(.W(((31) - (0) + 1)), .N(1)) u_face_n_unc (.ck(ck), .d(face_n_unc), .q(n_unc));   // region chn, t = 3
endmodule

// TX hard core: = ot_s81_serdes_col_tx_pin #(.N(3)) (3 coherent input PIN stages + the FEC encoder), unparameterised.
(* keep_hierarchy *)
module ot_s81_rck_tx (
    input wire clk,
    input wire rst_n,
    input wire tx_v,
    input wire [511:0] tx_d,
    output wire p_v,
    output wire [543:0] p_d,
    output wire fault
);
    (* keep *) reg [511:0] pin_q [0:2];
    reg [2:0] pin_v, pin_rst_n;
    always @(posedge clk) begin
        pin_q[0] <= tx_d; pin_v[0] <= tx_v; pin_rst_n[0] <= rst_n;
        pin_q[1] <= pin_q[0]; pin_v[1] <= pin_v[0]; pin_rst_n[1] <= pin_rst_n[0];
        pin_q[2] <= pin_q[1]; pin_v[2] <= pin_v[1]; pin_rst_n[2] <= pin_rst_n[1];
    end
`ifdef RCKRF_MUT_TXSKEW
    // bench mutant: data one PIN stage short while valid / reset keep 3
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(pin_rst_n[2]), .tx_v(pin_v[2]), .tx_d(pin_q[1]), .p_v(p_v), .p_d(p_d), .fault(fault));
`else
    ot_s81_kp4_enc u_enc (.clk(clk), .rst_n(pin_rst_n[2]), .tx_v(pin_v[2]), .tx_d(pin_q[2]), .p_v(p_v), .p_d(p_d), .fault(fault));
`endif
endmodule
`endif
