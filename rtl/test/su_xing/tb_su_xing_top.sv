// DS-ROM SU crossing bench top (tools/dsrom_1m_su_cdcq.py xing; harness tb_su_xing.cpp).
//
// The crossings a stream-unit node's operands and results take on the DS-ROM die under the adopted clocking
// (results/uarch/rom_die_clocking_decision_20261003.md, option C, "DS RTL" item 4): a field / streamed producer in a
// 1.2 GHz mesochronous field region delivers into the hub region through the closed mesochronous FIFO
// (rtl/common/ot_meso_fifo.sv, W 512 / DEPTH 4 / OFFSET 2), and inside the hub region the 3:4 ratio FIFO
// (rtl/common/ot_ratio_cdc_fifo.sv, W 512 / DEPTH 4, closed f2s_w512_d4) crosses into the 0.9 GHz serial domain of the
// stream unit; results return the reverse way.
//   F2S:  src @ fclk_r -> ot_meso_fifo (fclk_r -> fclk_h) -> ot_ratio_cdc_fifo (fclk_h -> sclk) -> sink @ sclk
//   S2F:  src @ sclk   -> ot_ratio_cdc_fifo (sclk -> fclk_h) -> ot_meso_fifo (fclk_h -> fclk_r) -> sink @ fclk_r
// The two FIFOs of a path are joined ready/valid with no extra register (the meso FIFO's registered output word
// feeds the ratio FIFO's write port directly, and vice versa).
module tb_su_xing_top #(parameter int W = 512) (
    input  logic         fclk_r, fclk_h, sclk,
    input  logic         rst_r_n, rst_h_n, rst_s_n,     // synchronous to their own clock
    // F2S
    input  logic         a_v,  input logic [W-1:0] a_d, output logic a_rdy,
    output logic         z_v,  output logic [W-1:0] z_d, input logic z_rdy,
    // S2F
    input  logic         b_v,  input logic [W-1:0] b_d, output logic b_rdy,
    output logic         y_v,  output logic [W-1:0] y_d, input logic y_rdy,
    output logic         live, output logic fault
);
    logic m1_v, m1_rdy, r1_wl, r1_rl, m1_wl, m1_rl, m1_wf, m1_rf;
    logic [W-1:0] m1_d;
    ot_meso_fifo #(.W(W), .DEPTH(4), .OFFSET(2), .GUARD_LO(0), .GUARD_HI(4), .CREDITS(8), .ENABLE(1)) u_f2s_meso (
        .wclk(fclk_r), .wrst_n(rst_r_n), .w_v(a_v), .w_rdy(a_rdy), .w_d(a_d),
        .rclk(fclk_h), .rrst_n(rst_h_n), .r_v(m1_v), .r_rdy(m1_rdy), .r_d(m1_d),
        .w_live(m1_wl), .r_live(m1_rl), .w_fault(m1_wf), .r_fault(m1_rf));
    ot_ratio_cdc_fifo #(.W(W), .DEPTH(4)) u_f2s_ratio (
        .wclk(fclk_h), .wrst_n(rst_h_n), .w_v(m1_v), .w_rdy(m1_rdy), .w_d(m1_d),
        .rclk(sclk), .rrst_n(rst_s_n), .r_v(z_v), .r_rdy(z_rdy), .r_d(z_d), .w_live(r1_wl), .r_live(r1_rl));

    logic r2_v, r2_rdy, r2_wl, r2_rl, m2_wl, m2_rl, m2_wf, m2_rf;
    logic [W-1:0] r2_d;
    ot_ratio_cdc_fifo #(.W(W), .DEPTH(4)) u_s2f_ratio (
        .wclk(sclk), .wrst_n(rst_s_n), .w_v(b_v), .w_rdy(b_rdy), .w_d(b_d),
        .rclk(fclk_h), .rrst_n(rst_h_n), .r_v(r2_v), .r_rdy(r2_rdy), .r_d(r2_d), .w_live(r2_wl), .r_live(r2_rl));
    ot_meso_fifo #(.W(W), .DEPTH(4), .OFFSET(2), .GUARD_LO(0), .GUARD_HI(4), .CREDITS(8), .ENABLE(1)) u_s2f_meso (
        .wclk(fclk_h), .wrst_n(rst_h_n), .w_v(r2_v), .w_rdy(r2_rdy), .w_d(r2_d),
        .rclk(fclk_r), .rrst_n(rst_r_n), .r_v(y_v), .r_rdy(y_rdy), .r_d(y_d),
        .w_live(m2_wl), .r_live(m2_rl), .w_fault(m2_wf), .r_fault(m2_rf));

    assign live  = m1_wl & m1_rl & r1_wl & r1_rl & r2_wl & r2_rl & m2_wl & m2_rl;
    assign fault = m1_wf | m1_rf | m2_wf | m2_rf;
endmodule
