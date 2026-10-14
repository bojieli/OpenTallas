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
    output wire wst_dn, output wire wdr_dn, output wire ovf
);
    // flat-bus shim (wiring only) of the physical cluster top ot_hgi_su_ctlw_slice_hp (per-pair ports, relayed forward)
`ifdef OT_HARD_CTLW_SLICE
    ot_hgi_su_ctlw_slice_hp u_hp (
`else
    ot_hgi_su_ctlw_slice_hp #(.SL(SL), .NL(NL), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(LQSRAM)) u_hp (
`endif
        .clk(clk), .rst_n(rst_n), .wst_go_i(wst_go_i), .wdr_go_i(wdr_go_i), .lo_i(lo_i), .hi_i(hi_i), .lb_i(lb_i), .rv_i(rv_i), .dsec_i(dsec_i), .d_lo_i(d_lo_i), .d_hi_i(d_hi_i), .d_lb_i(d_lb_i), .d_rv_i(d_rv_i), .d_dsec_i(d_dsec_i), .d_os_i(d_os_i), .sl_i(sl_i), .wst_go_o(wst_go_o), .wdr_go_o(wdr_go_o), .d_os_o(d_os_o), .lo_o(lo_o), .hi_o(hi_o), .lb_o(lb_o), .rv_o(rv_o), .dsec_o(dsec_o), .d_lo_o(d_lo_o), .d_hi_o(d_hi_o), .d_lb_o(d_lb_o), .d_rv_o(d_rv_o), .d_dsec_o(d_dsec_o), .wst_dn_i(wst_dn_i), .wdr_dn_i(wdr_dn_i), .ovf_i(ovf_i), .wst_dn(wst_dn), .wdr_dn(wdr_dn), .ovf(ovf),
        .wrq_p0(wrq[0 +: 32]), .wrq_cr_p0(wrq_cr[0 +: 2]), .wrr_p0(wrr[0 +: 514]), .wwq_p0(wwq[0 +: 560]), .wwq_cr_p0(wwq_cr[0 +: 2]), .wwq_done_p0(wwq_done[0 +: 2]), .lsw_v_p0(lsw_v[0 +: 2]), .lsw_sec_p0(lsw_sec[0*2*(LWB-3) +: 2*(LWB-3)]), .lsw_d_p0(lsw_d[0 +: 512]), .ldc_v_p0(ldc_v[0 +: 2]), .ldc_sec_p0(ldc_sec[0*2*(LWB-3) +: 2*(LWB-3)]), .ldr_v_p0(ldr_v[0 +: 2]), .ldr_sec_p0(ldr_sec[0*2*(LWB-3) +: 2*(LWB-3)]), .ldr_d_p0(ldr_d[0 +: 512]), .ldr_dm_p0(ldr_dm[0 +: 16]), .ldr_rv_p0(ldr_rv[0 +: 2]),
        .wrq_p1(wrq[32 +: 32]), .wrq_cr_p1(wrq_cr[2 +: 2]), .wrr_p1(wrr[514 +: 514]), .wwq_p1(wwq[560 +: 560]), .wwq_cr_p1(wwq_cr[2 +: 2]), .wwq_done_p1(wwq_done[2 +: 2]), .lsw_v_p1(lsw_v[2 +: 2]), .lsw_sec_p1(lsw_sec[1*2*(LWB-3) +: 2*(LWB-3)]), .lsw_d_p1(lsw_d[512 +: 512]), .ldc_v_p1(ldc_v[2 +: 2]), .ldc_sec_p1(ldc_sec[1*2*(LWB-3) +: 2*(LWB-3)]), .ldr_v_p1(ldr_v[2 +: 2]), .ldr_sec_p1(ldr_sec[1*2*(LWB-3) +: 2*(LWB-3)]), .ldr_d_p1(ldr_d[512 +: 512]), .ldr_dm_p1(ldr_dm[16 +: 16]), .ldr_rv_p1(ldr_rv[2 +: 2]),
        .wrq_p2(wrq[64 +: 32]), .wrq_cr_p2(wrq_cr[4 +: 2]), .wrr_p2(wrr[1028 +: 514]), .wwq_p2(wwq[1120 +: 560]), .wwq_cr_p2(wwq_cr[4 +: 2]), .wwq_done_p2(wwq_done[4 +: 2]), .lsw_v_p2(lsw_v[4 +: 2]), .lsw_sec_p2(lsw_sec[2*2*(LWB-3) +: 2*(LWB-3)]), .lsw_d_p2(lsw_d[1024 +: 512]), .ldc_v_p2(ldc_v[4 +: 2]), .ldc_sec_p2(ldc_sec[2*2*(LWB-3) +: 2*(LWB-3)]), .ldr_v_p2(ldr_v[4 +: 2]), .ldr_sec_p2(ldr_sec[2*2*(LWB-3) +: 2*(LWB-3)]), .ldr_d_p2(ldr_d[1024 +: 512]), .ldr_dm_p2(ldr_dm[32 +: 16]), .ldr_rv_p2(ldr_rv[4 +: 2]),
        .wrq_p3(wrq[96 +: 32]), .wrq_cr_p3(wrq_cr[6 +: 2]), .wrr_p3(wrr[1542 +: 514]), .wwq_p3(wwq[1680 +: 560]), .wwq_cr_p3(wwq_cr[6 +: 2]), .wwq_done_p3(wwq_done[6 +: 2]), .lsw_v_p3(lsw_v[6 +: 2]), .lsw_sec_p3(lsw_sec[3*2*(LWB-3) +: 2*(LWB-3)]), .lsw_d_p3(lsw_d[1536 +: 512]), .ldc_v_p3(ldc_v[6 +: 2]), .ldc_sec_p3(ldc_sec[3*2*(LWB-3) +: 2*(LWB-3)]), .ldr_v_p3(ldr_v[6 +: 2]), .ldr_sec_p3(ldr_sec[3*2*(LWB-3) +: 2*(LWB-3)]), .ldr_d_p3(ldr_d[1536 +: 512]), .ldr_dm_p3(ldr_dm[48 +: 16]), .ldr_rv_p3(ldr_rv[6 +: 2]));
endmodule
`default_nettype wire
