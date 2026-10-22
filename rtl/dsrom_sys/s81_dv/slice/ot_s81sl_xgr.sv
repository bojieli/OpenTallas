`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-ELEM2-XGRING (10-21): ot_s81sl_xgr -- structurally safe successor of the end-slice gather sub-leaf master
// ot_s81sl_xgt_xo (u_xg of the die72 slice parents).  SAME PORTS as ot_s81sl_xg / xg_xo / xgt / xgt_xo (die binding =
// master swap of u_xg, no port or net change).
// Why: the xgt_xo --cts gates (f5f35855d, ep9 PIDs 3256858 / 3256860) placed at -765 ps (MAIN) / -429 ps (FB) TT with
// 6,805 failing register endpoints, every one a single-cycle hop of 17-26 logic levels over 800-1,370 um: ring-stop pin
// decodes and input flops -> AND-OR -> output flops on the far face, and the 24-SRAM read AND-OR -> frame register.
// Structure (every long hop is now a pure-wire relay hop or a bank-local logic hop):
//   u_r  ot_s81sl_rstopr   rstopt_xo + a face register stage on every input (old input flops = mid-tile relays, kept
//                          selects decoded from the face flops)                                            +1 edge
//   is   face register stage on is_v / is_d (the issuer word keeps its relative timing to the gather beats)   +1 edge
//   u_s  ot_s81sl_xs5      xs4 + per-bank registered read partials (+1 read edge) + S/N gather write copies
//   ot_s81sl_xgr2 (below, MAIN kit) = ot_s81sl_xgr + one more register stage on every ring / delivery output (ro_e /
//                          ro_w / vo / nx_wi / nx_ei / dl_*): u_r's output flops become mid-tile relays, the new flops sit
//                          at the pins.  ot_s81sl_xgr itself = the FB kit master.
// Cycle delta vs ot_s81sl_xgt_xo (-> MU.S81.CAL; vs ot_s81sl_xg_xo add xgt_xo's +1 x path):
//   ring line in -> line out, V, NX, dl_* (per stop)       +1 edge (ot_s81sl_xgr, FB kit), +2 edges (ot_s81sl_xgr2, MAIN kit)
//   own / V-assembled beat -> line / V                     same as the ring row
//   head XB egress (s_0N -> ro_w)                          same as the ring row
//   slice x path (issuer word / gather beat -> xw frame)   +2 edges (u_r / is face stage +1, xs5 read partial +1):
//                                                          frame word = production lane word + OFF - 1 (xgt_xo: OFF - 3)
//   fault                                                  +2 edges (status only)
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xgr (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1103:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    output wire            xw_v,  output wire [1100:0] xw_d,
    output wire            fault
);
    wire [2:0] g_v, g_fam; wire [20:0] g_idx; wire [3071:0] g_d; wire f_r, f_s;
    wire [1103:0] r_ro_e, r_ro_w, r_dl_e, r_dl_w; wire [275:0] r_vo, r_dl_vb; wire [172:0] r_nx_wi, r_nx_ei;
    wire r_dl_ev, r_dl_wv, r_dl_vv;
    ot_s81sl_rstopr u_r (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(r_ro_e), .ro_w(r_ro_w),
        .vi(vi), .vo(r_vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(r_nx_wi), .nx_ei(r_nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .dl_ev(r_dl_ev), .dl_e(r_dl_e), .dl_wv(r_dl_wv), .dl_w(r_dl_w),
        .dl_vv(r_dl_vv), .dl_vb(r_dl_vb), .ci_dir(ci_dir), .ci_b(ci_b), .fault(f_r));
    assign ro_e = r_ro_e; assign ro_w = r_ro_w; assign vo = r_vo; assign nx_wi = r_nx_wi; assign nx_ei = r_nx_ei;
    assign dl_ev = r_dl_ev; assign dl_e = r_dl_e; assign dl_wv = r_dl_wv; assign dl_w = r_dl_w; assign dl_vv = r_dl_vv;
    assign dl_vb = r_dl_vb;
    // issuer face stage (pin flops; the xs5 capture flops behind them become the relay)
    reg is_vq; reg [159:0] is_dq;
    always @(posedge clk) begin is_vq <= is_v; is_dq <= is_d; end
    ot_s81sl_xs5 u_s (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d),
        .is_v(is_vq), .is_d(is_dq), .xw_v(xw_v), .xw_d(xw_d), .fault(f_s));
    // fault: rstopr fault (registered) gets one edge so both halves reach the output together (as xgt_xo)
    reg f_rq, flt;
    always @(posedge clk) begin f_rq <= f_r; flt <= f_rq | f_s; end
    assign fault = flt;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81sl_xgr2 (MAIN kit master): ot_s81sl_xgr + an output relay stage on every ring / delivery output.  Ring line,
// V, NX, dl_* and head egress +2 edges per stop vs ot_s81sl_xgt_xo; x path and fault exactly as ot_s81sl_xgr.  Every
// valid bit of the stage follows a reset-cleared u_r valid flop one edge later (no reset of its own).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_xgr2 (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1103:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    output wire            xw_v,  output wire [1100:0] xw_d,
    output wire            fault
);
    wire [1103:0] c_ro_e, c_ro_w, c_dl_e, c_dl_w; wire [275:0] c_vo, c_dl_vb; wire [172:0] c_nx_wi, c_nx_ei;
    wire c_dl_ev, c_dl_wv, c_dl_vv;
    ot_s81sl_xgr u_c (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_w), .ri_e(ri_e), .ro_e(c_ro_e), .ro_w(c_ro_w),
        .vi(vi), .vo(c_vo), .xf_v(xf_v), .xf_s(xf_s), .xf(xf), .nx_wi(c_nx_wi), .nx_ei(c_nx_ei), .nx_eo(nx_eo), .nx_wo(nx_wo),
        .dl_ev(c_dl_ev), .dl_e(c_dl_e), .dl_wv(c_dl_wv), .dl_w(c_dl_w), .dl_vv(c_dl_vv), .dl_vb(c_dl_vb),
        .ci_dir(ci_dir), .ci_b(ci_b), .is_v(is_v), .is_d(is_d), .xw_v(xw_v), .xw_d(xw_d), .fault(fault));
    reg [1103:0] q_ro_e, q_ro_w, q_dl_e, q_dl_w; reg [275:0] q_vo, q_dl_vb; reg [172:0] q_nx_wi, q_nx_ei;
    reg q_dl_ev, q_dl_wv, q_dl_vv;
    always @(posedge clk) begin
        q_ro_e <= c_ro_e; q_ro_w <= c_ro_w; q_vo <= c_vo; q_nx_wi <= c_nx_wi; q_nx_ei <= c_nx_ei;
        q_dl_ev <= c_dl_ev; q_dl_e <= c_dl_e; q_dl_wv <= c_dl_wv; q_dl_w <= c_dl_w; q_dl_vv <= c_dl_vv; q_dl_vb <= c_dl_vb;
    end
    assign ro_e = q_ro_e; assign ro_w = q_ro_w; assign vo = q_vo; assign nx_wi = q_nx_wi; assign nx_ei = q_nx_ei;
    assign dl_ev = q_dl_ev; assign dl_e = q_dl_e; assign dl_wv = q_dl_wv; assign dl_w = q_dl_w; assign dl_vv = q_dl_vv;
    assign dl_vb = q_dl_vb;
endmodule
