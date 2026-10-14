`timescale 1ns/1ps
`default_nettype none
// Physical slice cluster top (el1013-hbm-qdq 10-13): four hard two-lane leaves (ot_hgi_su_ctlw_lane2) stacked S -> N, each
// lane-pair bus its own port (_p0.._p3) so the W (VM lanes) / E (operand memory) pins sit beside their leaf (pure seams
// onto the leaf pin flops, <= ~30 um).  PHYSICAL SPEC: stack ~130 x 605 um, so NOTHING crosses the height unregistered:
//   descriptor / go : S-face pin flops f0 -> mid-height relay fm (feeds the four leaves' S faces, <= ~280 um) -> N-face
//                     forward register f1 (the next slice): 3 edges per hop, leaves see the descriptor 2 edges after the pins
//   done / overflow : next slice's flags pin-flopped at the N face (dn_*_n, <= ~460 um to the leaf N pins, 3 bits), the
//                     leaves' flags AND4 / OR4 into the S-face output registers
//   reset           : pin flop rst_l, leaves take the registered copy (each has its own reset pin flop)
// ot_hgi_su_ctlw_slice_h is the flat-bus shim of this module (wiring only).
module ot_hgi_su_ctlw_slice_hp #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 18, parameter integer LQ = 8,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0, parameter integer LQSRAM = 0
) (
    input  wire clk, input wire rst_n,
    input  wire wst_go_i, input wire wdr_go_i,
    input  wire [6*24-1:0] lo_i, input wire [6*24-1:0] hi_i, input wire [6*(LWB+1)-1:0] lb_i, input wire [5:0] rv_i,
    input  wire [6*21-1:0] dsec_i,
    input  wire [2*24-1:0] d_lo_i, input wire [2*24-1:0] d_hi_i, input wire [2*(LWB+1)-1:0] d_lb_i, input wire [1:0] d_rv_i,
    input  wire [2*21-1:0] d_dsec_i, input wire d_os_i,
    input  wire [1:0] sl_i,
    output wire wst_go_o, output wire wdr_go_o, output wire d_os_o,
    output wire [6*24-1:0] lo_o, output wire [6*24-1:0] hi_o, output wire [6*(LWB+1)-1:0] lb_o, output wire [5:0] rv_o,
    output wire [6*21-1:0] dsec_o, output wire [2*24-1:0] d_lo_o, output wire [2*24-1:0] d_hi_o,
    output wire [2*(LWB+1)-1:0] d_lb_o, output wire [1:0] d_rv_o, output wire [2*21-1:0] d_dsec_o,
    input  wire wst_dn_i, input wire wdr_dn_i, input wire ovf_i,
    output wire [32-1:0] wrq_p0, input wire [2-1:0] wrq_cr_p0, input wire [514-1:0] wrr_p0, output wire [560-1:0] wwq_p0, input wire [2-1:0] wwq_cr_p0, input wire [2-1:0] wwq_done_p0, output wire [2-1:0] lsw_v_p0, output wire [2*(LWB-3)-1:0] lsw_sec_p0, output wire [512-1:0] lsw_d_p0, output wire [2-1:0] ldc_v_p0, output wire [2*(LWB-3)-1:0] ldc_sec_p0, output wire [2-1:0] ldr_v_p0, output wire [2*(LWB-3)-1:0] ldr_sec_p0, input wire [512-1:0] ldr_d_p0, input wire [16-1:0] ldr_dm_p0, input wire [2-1:0] ldr_rv_p0,
    output wire [32-1:0] wrq_p1, input wire [2-1:0] wrq_cr_p1, input wire [514-1:0] wrr_p1, output wire [560-1:0] wwq_p1, input wire [2-1:0] wwq_cr_p1, input wire [2-1:0] wwq_done_p1, output wire [2-1:0] lsw_v_p1, output wire [2*(LWB-3)-1:0] lsw_sec_p1, output wire [512-1:0] lsw_d_p1, output wire [2-1:0] ldc_v_p1, output wire [2*(LWB-3)-1:0] ldc_sec_p1, output wire [2-1:0] ldr_v_p1, output wire [2*(LWB-3)-1:0] ldr_sec_p1, input wire [512-1:0] ldr_d_p1, input wire [16-1:0] ldr_dm_p1, input wire [2-1:0] ldr_rv_p1,
    output wire [32-1:0] wrq_p2, input wire [2-1:0] wrq_cr_p2, input wire [514-1:0] wrr_p2, output wire [560-1:0] wwq_p2, input wire [2-1:0] wwq_cr_p2, input wire [2-1:0] wwq_done_p2, output wire [2-1:0] lsw_v_p2, output wire [2*(LWB-3)-1:0] lsw_sec_p2, output wire [512-1:0] lsw_d_p2, output wire [2-1:0] ldc_v_p2, output wire [2*(LWB-3)-1:0] ldc_sec_p2, output wire [2-1:0] ldr_v_p2, output wire [2*(LWB-3)-1:0] ldr_sec_p2, input wire [512-1:0] ldr_d_p2, input wire [16-1:0] ldr_dm_p2, input wire [2-1:0] ldr_rv_p2,
    output wire [32-1:0] wrq_p3, input wire [2-1:0] wrq_cr_p3, input wire [514-1:0] wrr_p3, output wire [560-1:0] wwq_p3, input wire [2-1:0] wwq_cr_p3, input wire [2-1:0] wwq_done_p3, output wire [2-1:0] lsw_v_p3, output wire [2*(LWB-3)-1:0] lsw_sec_p3, output wire [512-1:0] lsw_d_p3, output wire [2-1:0] ldc_v_p3, output wire [2*(LWB-3)-1:0] ldc_sec_p3, output wire [2-1:0] ldr_v_p3, output wire [2*(LWB-3)-1:0] ldr_sec_p3, input wire [512-1:0] ldr_d_p3, input wire [16-1:0] ldr_dm_p3, input wire [2-1:0] ldr_rv_p3,
    output reg  wst_dn, output reg wdr_dn, output reg ovf
);
    localparam integer FDW = 561 + 8 * (LWB + 1);
    reg rst_l; always @(posedge clk) rst_l <= rst_n;
    reg [FDW-1:0] f0, fm, f1;
    reg st0, stm, st1, dr0, drm, dr1;
    always @(posedge clk) begin
        f0 <= {d_os_i, lo_i, hi_i, lb_i, rv_i, dsec_i, d_lo_i, d_hi_i, d_lb_i, d_rv_i, d_dsec_i};
        fm <= f0; f1 <= fm;
    end
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin st0 <= 0; stm <= 0; st1 <= 0; dr0 <= 0; drm <= 0; dr1 <= 0; end
        else begin st0 <= wst_go_i; stm <= st0; st1 <= stm; dr0 <= wdr_go_i; drm <= dr0; dr1 <= drm; end
    assign wst_go_o = st1; assign wdr_go_o = dr1;
    assign {d_os_o, lo_o, hi_o, lb_o, rv_o, dsec_o, d_lo_o, d_hi_o, d_lb_o, d_rv_o, d_dsec_o} = f1;
    wire m_os; wire [6*24-1:0] m_lo, m_hi; wire [6*(LWB+1)-1:0] m_lb; wire [5:0] m_rv; wire [6*21-1:0] m_dsec;
    wire [2*24-1:0] m_dlo, m_dhi; wire [2*(LWB+1)-1:0] m_dlb; wire [1:0] m_drv; wire [2*21-1:0] m_ddsec;
    assign {m_os, m_lo, m_hi, m_lb, m_rv, m_dsec, m_dlo, m_dhi, m_dlb, m_drv, m_ddsec} = fm;
    reg dn_st_n, dn_dr_n, dn_ov_n;                          // N-face pin flops of the next slice's combined flags
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin dn_st_n <= 1'b1; dn_dr_n <= 1'b1; dn_ov_n <= 1'b0; end
        else begin dn_st_n <= wst_dn_i; dn_dr_n <= wdr_dn_i; dn_ov_n <= ovf_i; end
    wire [3:0] st_done, dr_done, lane_fault;
`ifdef OT_HARD_CHILDREN
    ot_hgi_su_ctlw_lane2 u_lane0 (
`else
    ot_hgi_su_ctlw_lane2 #(.NL(2), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_lane0 (
`endif
        .clk(clk), .rst_n(rst_l), .sl_i(sl_i), .pair_i(2'd0),
        .wst_go_i(stm), .wdr_go_i(drm), .lo_i(m_lo), .hi_i(m_hi), .lb_i(m_lb), .rv_i(m_rv), .dsec_i(m_dsec),
        .d_lo_i(m_dlo), .d_hi_i(m_dhi), .d_lb_i(m_dlb), .d_rv_i(m_drv), .d_dsec_i(m_ddsec), .d_os_i(m_os),
        .wst_go_o(), .wdr_go_o(), .d_os_o(), .lo_o(), .hi_o(), .lb_o(), .rv_o(), .dsec_o(),
        .d_lo_o(), .d_hi_o(), .d_lb_o(), .d_rv_o(), .d_dsec_o(),
        .wst_dn_i(dn_st_n), .wdr_dn_i(dn_dr_n), .ovf_i(dn_ov_n),
        .wrq(wrq_p0), .wrq_cr(wrq_cr_p0), .wrr(wrr_p0), .wwq(wwq_p0), .wwq_cr(wwq_cr_p0), .wwq_done(wwq_done_p0), .lsw_v(lsw_v_p0), .lsw_sec(lsw_sec_p0), .lsw_d(lsw_d_p0), .ldc_v(ldc_v_p0), .ldc_sec(ldc_sec_p0), .ldr_v(ldr_v_p0), .ldr_sec(ldr_sec_p0), .ldr_d(ldr_d_p0), .ldr_dm(ldr_dm_p0), .ldr_rv(ldr_rv_p0),
        .wst_dn(st_done[0]), .wdr_dn(dr_done[0]), .ovf(lane_fault[0]));
`ifdef OT_HARD_CHILDREN
    ot_hgi_su_ctlw_lane2 u_lane1 (
`else
    ot_hgi_su_ctlw_lane2 #(.NL(2), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_lane1 (
`endif
        .clk(clk), .rst_n(rst_l), .sl_i(sl_i), .pair_i(2'd1),
        .wst_go_i(stm), .wdr_go_i(drm), .lo_i(m_lo), .hi_i(m_hi), .lb_i(m_lb), .rv_i(m_rv), .dsec_i(m_dsec),
        .d_lo_i(m_dlo), .d_hi_i(m_dhi), .d_lb_i(m_dlb), .d_rv_i(m_drv), .d_dsec_i(m_ddsec), .d_os_i(m_os),
        .wst_go_o(), .wdr_go_o(), .d_os_o(), .lo_o(), .hi_o(), .lb_o(), .rv_o(), .dsec_o(),
        .d_lo_o(), .d_hi_o(), .d_lb_o(), .d_rv_o(), .d_dsec_o(),
        .wst_dn_i(dn_st_n), .wdr_dn_i(dn_dr_n), .ovf_i(dn_ov_n),
        .wrq(wrq_p1), .wrq_cr(wrq_cr_p1), .wrr(wrr_p1), .wwq(wwq_p1), .wwq_cr(wwq_cr_p1), .wwq_done(wwq_done_p1), .lsw_v(lsw_v_p1), .lsw_sec(lsw_sec_p1), .lsw_d(lsw_d_p1), .ldc_v(ldc_v_p1), .ldc_sec(ldc_sec_p1), .ldr_v(ldr_v_p1), .ldr_sec(ldr_sec_p1), .ldr_d(ldr_d_p1), .ldr_dm(ldr_dm_p1), .ldr_rv(ldr_rv_p1),
        .wst_dn(st_done[1]), .wdr_dn(dr_done[1]), .ovf(lane_fault[1]));
`ifdef OT_HARD_CHILDREN
    ot_hgi_su_ctlw_lane2 u_lane2 (
`else
    ot_hgi_su_ctlw_lane2 #(.NL(2), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_lane2 (
`endif
        .clk(clk), .rst_n(rst_l), .sl_i(sl_i), .pair_i(2'd2),
        .wst_go_i(stm), .wdr_go_i(drm), .lo_i(m_lo), .hi_i(m_hi), .lb_i(m_lb), .rv_i(m_rv), .dsec_i(m_dsec),
        .d_lo_i(m_dlo), .d_hi_i(m_dhi), .d_lb_i(m_dlb), .d_rv_i(m_drv), .d_dsec_i(m_ddsec), .d_os_i(m_os),
        .wst_go_o(), .wdr_go_o(), .d_os_o(), .lo_o(), .hi_o(), .lb_o(), .rv_o(), .dsec_o(),
        .d_lo_o(), .d_hi_o(), .d_lb_o(), .d_rv_o(), .d_dsec_o(),
        .wst_dn_i(dn_st_n), .wdr_dn_i(dn_dr_n), .ovf_i(dn_ov_n),
        .wrq(wrq_p2), .wrq_cr(wrq_cr_p2), .wrr(wrr_p2), .wwq(wwq_p2), .wwq_cr(wwq_cr_p2), .wwq_done(wwq_done_p2), .lsw_v(lsw_v_p2), .lsw_sec(lsw_sec_p2), .lsw_d(lsw_d_p2), .ldc_v(ldc_v_p2), .ldc_sec(ldc_sec_p2), .ldr_v(ldr_v_p2), .ldr_sec(ldr_sec_p2), .ldr_d(ldr_d_p2), .ldr_dm(ldr_dm_p2), .ldr_rv(ldr_rv_p2),
        .wst_dn(st_done[2]), .wdr_dn(dr_done[2]), .ovf(lane_fault[2]));
`ifdef OT_HARD_CHILDREN
    ot_hgi_su_ctlw_lane2 u_lane3 (
`else
    ot_hgi_su_ctlw_lane2 #(.NL(2), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_lane3 (
`endif
        .clk(clk), .rst_n(rst_l), .sl_i(sl_i), .pair_i(2'd3),
        .wst_go_i(stm), .wdr_go_i(drm), .lo_i(m_lo), .hi_i(m_hi), .lb_i(m_lb), .rv_i(m_rv), .dsec_i(m_dsec),
        .d_lo_i(m_dlo), .d_hi_i(m_dhi), .d_lb_i(m_dlb), .d_rv_i(m_drv), .d_dsec_i(m_ddsec), .d_os_i(m_os),
        .wst_go_o(), .wdr_go_o(), .d_os_o(), .lo_o(), .hi_o(), .lb_o(), .rv_o(), .dsec_o(),
        .d_lo_o(), .d_hi_o(), .d_lb_o(), .d_rv_o(), .d_dsec_o(),
        .wst_dn_i(dn_st_n), .wdr_dn_i(dn_dr_n), .ovf_i(dn_ov_n),
        .wrq(wrq_p3), .wrq_cr(wrq_cr_p3), .wrr(wrr_p3), .wwq(wwq_p3), .wwq_cr(wwq_cr_p3), .wwq_done(wwq_done_p3), .lsw_v(lsw_v_p3), .lsw_sec(lsw_sec_p3), .lsw_d(lsw_d_p3), .ldc_v(ldc_v_p3), .ldc_sec(ldc_sec_p3), .ldr_v(ldr_v_p3), .ldr_sec(ldr_sec_p3), .ldr_d(ldr_d_p3), .ldr_dm(ldr_dm_p3), .ldr_rv(ldr_rv_p3),
        .wst_dn(st_done[3]), .wdr_dn(dr_done[3]), .ovf(lane_fault[3]));
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wst_dn <= 1; wdr_dn <= 1; ovf <= 0; end
        else begin wst_dn <= &st_done; wdr_dn <= &dr_done; ovf <= |lane_fault; end
    // synthesis translate_off
    initial if (NL != 8) $fatal(1, "ctlw_slice_hp needs four 2-lane children");
    // synthesis translate_on
endmodule
`default_nettype wire
