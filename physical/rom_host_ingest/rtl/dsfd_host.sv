`timescale 1ns/1ps
// dsfd_host (stream ingest 2026-10-08): die master of the host / KV-ingest block = ot_rom_host_ingest with this die's
// parameters.  DeepSeek-V4.1 S81 layer / head die: ROWS (compressed + window KV rows), IKEY (indexer keys), RAW; QKV and RMW fail closed.
// Clocks: clk_h host link user clock, clk_i ingest core clock (the die clock / 2, its own CTS root, no gating), ck die clock.
module dsfd_host (
    input  wire          rst_n,
    input  wire          clk_h,
    input  wire          h_v,
    input  wire [1:0]    h_cls,
    input  wire [511:0]  h_d,
    output wire [4:0]    h_crn,
    output wire          t_v,
    output wire [63:0]   t_d,
    input  wire          t_cr,
    input  wire          clk_i,
    input  wire          ck,
    output wire          o_v,
    output wire          o_we,
    output wire [31:0]   o_addr,
    output wire [255:0]  o_d,
    input  wire          o_cr,
    input  wire          i_rv,
    input  wire [255:0]  i_rd,
    output wire          fault
);
    ot_rom_host_ingest #(.KVHMAX(1), .HDMAX(16), .QKV_EN(0), .RMW_EN(0)) u_hi (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(i_rv), .i_rd(i_rd), .fault(fault));
endmodule
