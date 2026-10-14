`timescale 1ns/1ps
`default_nettype none
// Four actual two-lane roots plus registered parent completion cut.
module ot_hgi_su_ctlw_native_h #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 17, parameter integer LQ = 10,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0,
    parameter integer LQSRAM = 0          // 1: each lane's landing FIFO in a 64x16 1R1W SRAM (FWFT), not 64 x LSW flops
) (
    input wire clk,clk_p0,clk_p1,clk_p2,clk_p3, input wire rst_n,
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
    output reg wst_dn, output reg wdr_dn, output reg ovf
);
wire [3:0] sd,dd,of;
ot_hgi_su_ctlw_native_lane2 #(.NL(2),.LWB(LWB),.LQ(LQ),.LQSRAM(LQSRAM),.MUT_W(MUT_W),.MUT_DIRTY(MUT_DIRTY)) p0(.clk(clk_p0),.rst_n(rst_n),.pair_i(2'd0),.sl_i(sl_i),.wst_go_i(wst_go_i),.wst_go_o(wst_go_o),.wdr_go_i(wdr_go_i),.wdr_go_o(wdr_go_o),.d_os_i(d_os_i),.d_os_o(d_os_o),.lo_i(lo_i),.lo_o(lo_o),.hi_i(hi_i),.hi_o(hi_o),.lb_i(lb_i),.lb_o(lb_o),.rv_i(rv_i),.rv_o(rv_o),.dsec_i(dsec_i),.dsec_o(dsec_o),.d_lo_i(d_lo_i),.d_lo_o(d_lo_o),.d_hi_i(d_hi_i),.d_hi_o(d_hi_o),.d_lb_i(d_lb_i),.d_lb_o(d_lb_o),.d_rv_i(d_rv_i),.d_rv_o(d_rv_o),.d_dsec_i(d_dsec_i),.d_dsec_o(d_dsec_o),.wst_dn_i(wst_dn_i),.wdr_dn_i(wdr_dn_i),.ovf_i(ovf_i),.wst_dn(sd[0]),.wdr_dn(dd[0]),.ovf(of[0]),.wrq(wrq[0*2*16+:2*16]),.wrq_cr(wrq_cr[0*2*1+:2*1]),.wrr(wrr[0*2*257+:2*257]),.wwq(wwq[0*2*280+:2*280]),.wwq_cr(wwq_cr[0*2*1+:2*1]),.wwq_done(wwq_done[0*2*1+:2*1]),.lsw_v(lsw_v[0*2*1+:2*1]),.lsw_sec(lsw_sec[0*2*(LWB-3)+:2*(LWB-3)]),.lsw_d(lsw_d[0*2*256+:2*256]),.ldc_v(ldc_v[0*2*1+:2*1]),.ldc_sec(ldc_sec[0*2*(LWB-3)+:2*(LWB-3)]),.ldr_v(ldr_v[0*2*1+:2*1]),.ldr_sec(ldr_sec[0*2*(LWB-3)+:2*(LWB-3)]),.ldr_d(ldr_d[0*2*256+:2*256]),.ldr_dm(ldr_dm[0*2*8+:2*8]),.ldr_rv(ldr_rv[0*2*1+:2*1]));
ot_hgi_su_ctlw_native_lane2 #(.NL(2),.LWB(LWB),.LQ(LQ),.LQSRAM(LQSRAM),.MUT_W(MUT_W),.MUT_DIRTY(MUT_DIRTY)) p1(.clk(clk_p1),.rst_n(rst_n),.pair_i(2'd1),.sl_i(sl_i),.wst_go_i(wst_go_i),.wst_go_o(),.wdr_go_i(wdr_go_i),.wdr_go_o(),.d_os_i(d_os_i),.d_os_o(),.lo_i(lo_i),.lo_o(),.hi_i(hi_i),.hi_o(),.lb_i(lb_i),.lb_o(),.rv_i(rv_i),.rv_o(),.dsec_i(dsec_i),.dsec_o(),.d_lo_i(d_lo_i),.d_lo_o(),.d_hi_i(d_hi_i),.d_hi_o(),.d_lb_i(d_lb_i),.d_lb_o(),.d_rv_i(d_rv_i),.d_rv_o(),.d_dsec_i(d_dsec_i),.d_dsec_o(),.wst_dn_i(wst_dn_i),.wdr_dn_i(wdr_dn_i),.ovf_i(ovf_i),.wst_dn(sd[1]),.wdr_dn(dd[1]),.ovf(of[1]),.wrq(wrq[1*2*16+:2*16]),.wrq_cr(wrq_cr[1*2*1+:2*1]),.wrr(wrr[1*2*257+:2*257]),.wwq(wwq[1*2*280+:2*280]),.wwq_cr(wwq_cr[1*2*1+:2*1]),.wwq_done(wwq_done[1*2*1+:2*1]),.lsw_v(lsw_v[1*2*1+:2*1]),.lsw_sec(lsw_sec[1*2*(LWB-3)+:2*(LWB-3)]),.lsw_d(lsw_d[1*2*256+:2*256]),.ldc_v(ldc_v[1*2*1+:2*1]),.ldc_sec(ldc_sec[1*2*(LWB-3)+:2*(LWB-3)]),.ldr_v(ldr_v[1*2*1+:2*1]),.ldr_sec(ldr_sec[1*2*(LWB-3)+:2*(LWB-3)]),.ldr_d(ldr_d[1*2*256+:2*256]),.ldr_dm(ldr_dm[1*2*8+:2*8]),.ldr_rv(ldr_rv[1*2*1+:2*1]));
ot_hgi_su_ctlw_native_lane2 #(.NL(2),.LWB(LWB),.LQ(LQ),.LQSRAM(LQSRAM),.MUT_W(MUT_W),.MUT_DIRTY(MUT_DIRTY)) p2(.clk(clk_p2),.rst_n(rst_n),.pair_i(2'd2),.sl_i(sl_i),.wst_go_i(wst_go_i),.wst_go_o(),.wdr_go_i(wdr_go_i),.wdr_go_o(),.d_os_i(d_os_i),.d_os_o(),.lo_i(lo_i),.lo_o(),.hi_i(hi_i),.hi_o(),.lb_i(lb_i),.lb_o(),.rv_i(rv_i),.rv_o(),.dsec_i(dsec_i),.dsec_o(),.d_lo_i(d_lo_i),.d_lo_o(),.d_hi_i(d_hi_i),.d_hi_o(),.d_lb_i(d_lb_i),.d_lb_o(),.d_rv_i(d_rv_i),.d_rv_o(),.d_dsec_i(d_dsec_i),.d_dsec_o(),.wst_dn_i(wst_dn_i),.wdr_dn_i(wdr_dn_i),.ovf_i(ovf_i),.wst_dn(sd[2]),.wdr_dn(dd[2]),.ovf(of[2]),.wrq(wrq[2*2*16+:2*16]),.wrq_cr(wrq_cr[2*2*1+:2*1]),.wrr(wrr[2*2*257+:2*257]),.wwq(wwq[2*2*280+:2*280]),.wwq_cr(wwq_cr[2*2*1+:2*1]),.wwq_done(wwq_done[2*2*1+:2*1]),.lsw_v(lsw_v[2*2*1+:2*1]),.lsw_sec(lsw_sec[2*2*(LWB-3)+:2*(LWB-3)]),.lsw_d(lsw_d[2*2*256+:2*256]),.ldc_v(ldc_v[2*2*1+:2*1]),.ldc_sec(ldc_sec[2*2*(LWB-3)+:2*(LWB-3)]),.ldr_v(ldr_v[2*2*1+:2*1]),.ldr_sec(ldr_sec[2*2*(LWB-3)+:2*(LWB-3)]),.ldr_d(ldr_d[2*2*256+:2*256]),.ldr_dm(ldr_dm[2*2*8+:2*8]),.ldr_rv(ldr_rv[2*2*1+:2*1]));
ot_hgi_su_ctlw_native_lane2 #(.NL(2),.LWB(LWB),.LQ(LQ),.LQSRAM(LQSRAM),.MUT_W(MUT_W),.MUT_DIRTY(MUT_DIRTY)) p3(.clk(clk_p3),.rst_n(rst_n),.pair_i(2'd3),.sl_i(sl_i),.wst_go_i(wst_go_i),.wst_go_o(),.wdr_go_i(wdr_go_i),.wdr_go_o(),.d_os_i(d_os_i),.d_os_o(),.lo_i(lo_i),.lo_o(),.hi_i(hi_i),.hi_o(),.lb_i(lb_i),.lb_o(),.rv_i(rv_i),.rv_o(),.dsec_i(dsec_i),.dsec_o(),.d_lo_i(d_lo_i),.d_lo_o(),.d_hi_i(d_hi_i),.d_hi_o(),.d_lb_i(d_lb_i),.d_lb_o(),.d_rv_i(d_rv_i),.d_rv_o(),.d_dsec_i(d_dsec_i),.d_dsec_o(),.wst_dn_i(wst_dn_i),.wdr_dn_i(wdr_dn_i),.ovf_i(ovf_i),.wst_dn(sd[3]),.wdr_dn(dd[3]),.ovf(of[3]),.wrq(wrq[3*2*16+:2*16]),.wrq_cr(wrq_cr[3*2*1+:2*1]),.wrr(wrr[3*2*257+:2*257]),.wwq(wwq[3*2*280+:2*280]),.wwq_cr(wwq_cr[3*2*1+:2*1]),.wwq_done(wwq_done[3*2*1+:2*1]),.lsw_v(lsw_v[3*2*1+:2*1]),.lsw_sec(lsw_sec[3*2*(LWB-3)+:2*(LWB-3)]),.lsw_d(lsw_d[3*2*256+:2*256]),.ldc_v(ldc_v[3*2*1+:2*1]),.ldc_sec(ldc_sec[3*2*(LWB-3)+:2*(LWB-3)]),.ldr_v(ldr_v[3*2*1+:2*1]),.ldr_sec(ldr_sec[3*2*(LWB-3)+:2*(LWB-3)]),.ldr_d(ldr_d[3*2*256+:2*256]),.ldr_dm(ldr_dm[3*2*8+:2*8]),.ldr_rv(ldr_rv[3*2*1+:2*1]));
always @(posedge clk or negedge rst_n)if(!rst_n)begin wst_dn<=1;wdr_dn<=1;ovf<=0;end else begin wst_dn<=&sd;wdr_dn<=&dd;ovf<=|of;end
endmodule
`default_nettype wire
