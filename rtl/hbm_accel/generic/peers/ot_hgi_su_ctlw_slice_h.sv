`timescale 1ns/1ps
`default_nettype none
module ot_hgi_su_ctlw_slice_h #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 18, parameter integer LQ = 8,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0,
    parameter integer LQSRAM = 0          // 1: each lane's landing FIFO in a 64x16 1R1W SRAM (FWFT), not 64 x LSW flops
) (
    input  wire clk, input wire rst_n,
    input  wire wst_go_i, input wire wdr_go_i,
    input  wire [6*24-1:0] lo_i, input wire [6*24-1:0] hi_i, input wire [6*(LWB+1)-1:0] lb_i, input wire [5:0] rv_i,
    input  wire [6*21-1:0] dsec_i,
    input  wire [2*24-1:0] d_lo_i, input wire [2*24-1:0] d_hi_i, input wire [2*(LWB+1)-1:0] d_lb_i, input wire [1:0] d_rv_i,
    input  wire [2*21-1:0] d_dsec_i, input wire d_os_i,
    // GLUE PLACEMENT (el1011-hbm-sfu 10-11): slice id strap (one hard tile for every slice), the forward link (this
    // slice's descriptor / go pin registers, to the next slice) and the backward done / overflow combine link
    input  wire [1:0] sl_i,
    output wire wst_go_o, output wire wdr_go_o, output wire d_os_o,
    output wire [6*24-1:0] lo_o, output wire [6*24-1:0] hi_o, output wire [6*(LWB+1)-1:0] lb_o, output wire [5:0] rv_o,
    output wire [6*21-1:0] dsec_o, output wire [2*24-1:0] d_lo_o, output wire [2*24-1:0] d_hi_o,
    output wire [2*(LWB+1)-1:0] d_lb_o, output wire [1:0] d_rv_o, output wire [2*21-1:0] d_dsec_o,
    input  wire wst_dn_i, input wire wdr_dn_i, input wire ovf_i,
    output wire  [NL*16-1:0] wrq, input wire [NL-1:0] wrq_cr, input wire [NL*257-1:0] wrr,
    output wire  [NL*280-1:0] wwq, input wire [NL-1:0] wwq_cr, input wire [NL-1:0] wwq_done,
    output wire  [NL-1:0] lsw_v, output wire [NL*(LWB-3)-1:0] lsw_sec, output wire [NL*256-1:0] lsw_d,
    output wire  [NL-1:0] ldc_v, output wire [NL*(LWB-3)-1:0] ldc_sec,
    output wire  [NL-1:0] ldr_v, output wire [NL*(LWB-3)-1:0] ldr_sec,
    input  wire [NL*256-1:0] ldr_d, input wire [NL*8-1:0] ldr_dm, input wire [NL-1:0] ldr_rv,
    output reg  wst_dn, output reg wdr_dn, output reg ovf
);
    localparam integer LSW = LWB - 3, FDW = 561 + 8 * (LWB + 1);
    reg rst_l; always @(posedge clk) rst_l <= rst_n;
    reg [FDW-1:0] f0, f1;
    reg st0, st1, dr0, dr1;
    always @(posedge clk) begin
        f0 <= {d_os_i, lo_i, hi_i, lb_i, rv_i, dsec_i, d_lo_i, d_hi_i, d_lb_i, d_rv_i, d_dsec_i};
        f1 <= f0;
    end
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin st0 <= 0; st1 <= 0; dr0 <= 0; dr1 <= 0; end
        else begin st0 <= wst_go_i; st1 <= st0; dr0 <= wdr_go_i; dr1 <= dr0; end
    assign wst_go_o = st1; assign wdr_go_o = dr1;
    assign {d_os_o, lo_o, hi_o, lb_o, rv_o, dsec_o, d_lo_o, d_hi_o, d_lb_o, d_rv_o, d_dsec_o} = f1;
    wire [3:0] st_done, dr_done, lane_fault;
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_pair
`ifdef OT_HARD_CHILDREN
        ot_hgi_su_ctlw_lane2 u_lane (
`else
        ot_hgi_su_ctlw_lane2 #(.NL(2), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_lane (
`endif
            .clk(clk), .rst_n(rst_n), .sl_i(sl_i), .pair_i(2'(g)),
            .wst_go_i(wst_go_i), .wdr_go_i(wdr_go_i), .lo_i(lo_i), .hi_i(hi_i), .lb_i(lb_i), .rv_i(rv_i), .dsec_i(dsec_i),
            .d_lo_i(d_lo_i), .d_hi_i(d_hi_i), .d_lb_i(d_lb_i), .d_rv_i(d_rv_i), .d_dsec_i(d_dsec_i), .d_os_i(d_os_i),
            .wst_dn_i(wst_dn_i), .wdr_dn_i(wdr_dn_i), .ovf_i(ovf_i),
            .wrq(wrq[g*32 +: 32]), .wrq_cr(wrq_cr[g*2 +: 2]), .wrr(wrr[g*514 +: 514]),
            .wwq(wwq[g*560 +: 560]), .wwq_cr(wwq_cr[g*2 +: 2]), .wwq_done(wwq_done[g*2 +: 2]),
            .lsw_v(lsw_v[g*2 +: 2]), .lsw_sec(lsw_sec[g*2*LSW +: 2*LSW]), .lsw_d(lsw_d[g*512 +: 512]),
            .ldc_v(ldc_v[g*2 +: 2]), .ldc_sec(ldc_sec[g*2*LSW +: 2*LSW]),
            .ldr_v(ldr_v[g*2 +: 2]), .ldr_sec(ldr_sec[g*2*LSW +: 2*LSW]),
            .ldr_d(ldr_d[g*512 +: 512]), .ldr_dm(ldr_dm[g*16 +: 16]), .ldr_rv(ldr_rv[g*2 +: 2]),
            .wst_dn(st_done[g]), .wdr_dn(dr_done[g]), .ovf(lane_fault[g]));
    end endgenerate
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wst_dn <= 1; wdr_dn <= 1; ovf <= 0; end
        else begin wst_dn <= &st_done; wdr_dn <= &dr_done; ovf <= |lane_fault; end
    // synthesis translate_off
    initial if (NL != 8) $fatal(1, "ctlw_slice_h needs four 2-lane children");
    // synthesis translate_on
endmodule
`default_nettype wire
