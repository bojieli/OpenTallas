`timescale 1ns/1ps
// qfd_io_host (stream ingest 2026-10-08): die master of the host / KV-ingest block = ot_rom_host_ingest with this die's
// parameters.  Qwen3-8B ROM die (TP4: 2 KV heads x 128 a die): QKV + RAW (embedding boot load into HBM, emb-hbm); WRITE-ONLY (reviewer 2026-10-08: RMW_EN 0, the GPU resends the open
// tile at t_lo = 0; an rmw descriptor fails closed). Host link = the board-SerDes HOST class (no PCIe PHY on the die).
// Clocks: clk_h host link user clock, clk_i ingest core clock (the die clock / 2, its own CTS root, no gating), ck die clock.
module qfd_io_host (
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
    ot_rom_host_ingest #(.KVHMAX(2), .HDMAX(128), .QKV_EN(1), .RMW_EN(0)) u_hi (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(i_rv), .i_rd(i_rd), .fault(fault));
endmodule
