`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// S81-CAPC4 (2026-10-20): ot_s81sl_capc5f = the WIRES-ONLY flat form of the release capture cluster, input to
// tools/landed_parent/lp.py (spec tools/landed_parent/specs/ot_s81sl_capc5.json), which emits the LANDED parent
// ot_s81sl_capc5 (rtl/dsrom_sys/s81_dv/slice/lp/).
//
// Why (CLOCKING STANDARD 10-18 + safe-design item 7): capc2/capc4 ran ONE core_clk root over five hard children whose
// boundary insertions differ by > 150 ps (u_rt 234..298 TT vs u_ed 94..103); the conservative child-boundary envelope
// was TT 109.1 / FF 122.4 ps and 11 parent-compensation variants all failed the dual-corner 80 ps rule (best 83.2 / 80.0,
// results/rtl/codex_s81_capc_audit_1020).  The landed parent puts u_rt in its OWN clock region ("rt") and the trees,
// calendar leaves and face registers in region "core"; the three crossings into u_rt (W word, E word, cfg) are LANDED
// (ot_pl_land 4-slot rings, fixed +E+1 = +3 edges, no backpressure), so each region is judged alone at its child flops.
//
// Contents = ot_s81sl_cap_p1 #(.PINPIPE(1), .EDLY(24), .WL3DLY(16)) data path with the same children, edge for edge:
//   u_fw / u_fe / u_fcv / u_fcd   input face registers (PINPIPE in-stage, +1): rt_w, rt_e, cfg_v, cfg_d
//   u_ld3  ot_s81sl_cap_ld  (D 16, hard)  W lane 3 static delay before the W tree
//   u_tw / u_te  ot_s81sl_cap_tr (hard)   W / E column trees
//   u_ed   ot_s81sl_cap_ed  (D 24, hard)  E word static delay before n6
//   u_rt   ot_s81sl_cap_rt  (hard)        n6 + FIN + DEC + sticky fault
// Output face registers (PINPIPE out-stage) and the 2-stage reset landing are emitted by lp.py (out_regs 1 per output;
// regional reset runs).  The compiler record (<top>_lp_record.json) carries every port offset.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_capc5f (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [279:0]  rt_w,
    input  wire [279:0]  rt_e,
    input  wire          cfg_v,
    input  wire [159:0]  cfg_d,
    output wire [5:0]    cw_s_v,
    output wire [71:0]   cw_s_a,
    output wire [191:0]  cw_s_d,
    output wire [3:0]    cw_n_v,
    output wire [47:0]   cw_n_a,
    output wire [127:0]  cw_n_d,
    output wire          fault
);
    wire [279:0] wq, eq;
    wire         cq_v;
    wire [159:0] cq_d;
    wire [69:0]  wd3;
    wire         w_v, w_e, w_f, x_v, x_e, x_f, e_v, e_e, e_f;
    wire [31:0]  w_t, w_d, x_t, x_d, e_t, e_d;
    ot_pl_pad #(.W(280), .N(1)) u_fw (.ck(clk), .d(rt_w), .q(wq));
    ot_pl_pad #(.W(280), .N(1)) u_fe (.ck(clk), .d(rt_e), .q(eq));
    ot_pl_pad #(.W(1), .N(1)) u_fcv (.ck(clk), .d(cfg_v), .q(cq_v));
    ot_pl_pad #(.W(160), .N(1)) u_fcd (.ck(clk), .d(cfg_d), .q(cq_d));
    ot_s81sl_cap_ld #(.D(16)) u_ld3 (.clk(clk), .rst_n(rst_n), .i_w(wq[279:210]), .o_w(wd3));
    ot_s81sl_cap_tr u_tw (.clk(clk), .rst_n(rst_n), .rt({wd3, wq[209:0]}), .o_v(w_v), .o_t(w_t), .o_d(w_d), .o_e(w_e),
        .fault(w_f));
    ot_s81sl_cap_tr u_te (.clk(clk), .rst_n(rst_n), .rt(eq), .o_v(x_v), .o_t(x_t), .o_d(x_d), .o_e(x_e), .fault(x_f));
    ot_s81sl_cap_ed #(.D(24)) u_ed (.clk(clk), .rst_n(rst_n), .i_v(x_v), .i_t(x_t), .i_d(x_d), .i_e(x_e), .i_f(x_f),
        .o_v(e_v), .o_t(e_t), .o_d(e_d), .o_e(e_e), .o_f(e_f));
    ot_s81sl_cap_rt u_rt (.clk(clk), .rst_n(rst_n),
        .w_v(w_v), .w_t(w_t), .w_d(w_d), .w_e(w_e), .w_f(w_f), .e_v(e_v), .e_t(e_t), .e_d(e_d), .e_e(e_e), .e_f(e_f),
        .cfg_v(cq_v), .cfg_d(cq_d),
        .cw_s_v(cw_s_v), .cw_s_a(cw_s_a), .cw_s_d(cw_s_d), .cw_n_v(cw_n_v), .cw_n_a(cw_n_a), .cw_n_d(cw_n_d),
        .fault(fault));
endmodule
`default_nettype wire
