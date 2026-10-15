`timescale 1ns/1ps
`default_nettype none
// Production HC projection arithmetic seam. The compiler owns launch, bank
// reads (through the exact HCP address pipeline) and raw_read slots. No ready,
// credit, lease, or grant signal participates in this interface. The two ML2
// memory inputs must be real macro captures in a native composition.
//
// A launch reserves the complete command: ((scale?1:0)+nout)*npos*ceil(K/8/W)
// issue cycles without bubbles, plus the fixed tree/tail latency. raw_read
// consumes the resulting ss/row records in exactly that order. The compiler
// leaves the scalar rsqrt latency between each ss read and its first row read.
// An early/empty read or overlapping launch faults; it never delays execution.
// Weight width remains FP32, residual width BF16, and the original chunk8
// arithmetic/reduction/rsqrt sequence is unchanged. This is projection, not
// the subsequent sigmoid/Sinkhorn HC tail or a complete HC_MIX record engine.
module ot_hgi_hc_projection_static #(
    parameter integer W=32, TL=9, PMAX=8, OMAX=32, AW=16, CW=16,
    // Entire production command fits, independent of downstream availability.
    parameter integer DF=512,
    parameter integer PW=(PMAX>1)?$clog2(PMAX):1,
    parameter integer OXW=(OMAX>1)?$clog2(OMAX):1
)(
    input wire clk,rst_n,
    input wire launch,raw_read,
    input wire [PW:0] npos,
    input wire [OXW:0] nout,
    input wire [CW-1:0] nchunk,
    input wire scale,
    input wire [31:0] nf,eps,
    input wire [AW-1:0] wbase,xbase,
    output wire [7:0] w_re,x_re,
    output wire [8*AW-1:0] w_addr,x_addr,
    input wire [8*W*32-1:0] w_data,
    input wire [8*W*16-1:0] x_data,
    output wire result_v,result_last,
    output wire [PW-1:0] result_pos,
    output wire [OXW-1:0] result_row,
    output wire [31:0] result_data,
    output wire fault
);
    ot_hdc_v41x_hcp #(.W(W),.TL(TL),.PMAX(PMAX),.OMAX(OMAX),
        .AW(AW),.CW(CW),.ML(2),.DF(DF),.STATIC_CALENDAR(1)) u_hcp (
        .clk(clk),.rst_n(rst_n),.calendar_pop(raw_read),
        .cmd_valid(launch),.cmd_ready(),.cmd_npos(npos),.cmd_nout(nout),
        .cmd_nchunk(nchunk),.cmd_scale(scale),.cmd_nf(nf),.cmd_eps(eps),
        .cmd_wbase(wbase),.cmd_xbase(xbase),
        .w_re(w_re),.x_re(x_re),.w_addr(w_addr),.x_addr(x_addr),
        .w_data(w_data),.x_data(x_data),
        .o_valid(result_v),.o_ready(1'b1),.o_pos(result_pos),.o_idx(result_row),
        .o_data(result_data),.o_last(result_last),.fault(fault),.idle(),
        .sd_v(),.sd_ss(),.sd_nv(),.sd_wa(),.sd_xa(),
        .sys_sum({W*32{1'b0}}),.sys_fault(1'b0));
endmodule
`default_nettype wire
