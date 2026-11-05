// HBM-FORM-SPLIT d44v part 27: opstore_b -> 2 x operand group tile + output group tile. Members and parameters verbatim
// from ot_hgi_sfu_split3_opstore_b_core (ot_hgi_sfu_static_operand_store g_operand[2,3].u_group, u_output). Each tile
// carries its own kit face shell, +1 in and +1 out, the same as the uncut core's shell, so every plan pin keeps its date.
`timescale 1ns/1ps
`default_nettype none
module ot_hgi_sfu_opsb_group (
    input  wire          clk, rst_n,
    input  wire [15:0]   rq,
    input  wire [383:0]  ra,
    output wire [511:0]  rd,
    input  wire [7:0]    sw_v,
    input  wire [119:0]  sw_addr,
    input  wire [63:0]   sw_mask,
    input  wire [2047:0] sw_d,
    output wire          flt
);
    ot_hgi_su_lgroup2_lf #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(0),.MACRO(1),.MUT_XBAR(0),.NS(8),.BREG(1)) u_g (  // HBM-REFORM-B9: rd +1 edge
        .clk(clk), .rst_n(rst_n), .rq(rq), .rr(rq), .ra(ra), .rd(rd),
        .sr_v(8'd0), .sr_addr(120'd0), .sr_d(), .sr_rv(),
        .sw_v(sw_v), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_d(sw_d),
        .lw(1'b0), .lwa(24'd0), .lwd(32'd0), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
module ot_hgi_sfu_opsb_output (
    input  wire          clk, rst_n,
    input  wire [1:0]    sr_v,
    input  wire [29:0]   sr_addr,
    output wire [511:0]  sr_d,
    output wire [1:0]    sr_rv,
    input  wire [15:0]   lw,
    input  wire [383:0]  lwa,
    input  wire [511:0]  lwd,
    output wire          flt
);
    ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(15),.AW(24),.NLW(16),.MACRO(1),.MUT_XBAR(0),.NS(2)) u_g (
        .clk(clk), .rst_n(rst_n), .rq(16'd0), .rr(16'd0), .ra(384'd0), .rd(),
        .sr_v(sr_v), .sr_addr(sr_addr), .sr_d(sr_d), .sr_rv(sr_rv),
        .sw_v(2'd0), .sw_addr(30'd0), .sw_mask(16'd0), .sw_d(512'd0),
        .lw(lw), .lwa(lwa), .lwd(lwd), .s1_v(1'b0), .s1_a(15'd0), .s1_d(32'd0), .flt(flt));
endmodule
`default_nettype wire
