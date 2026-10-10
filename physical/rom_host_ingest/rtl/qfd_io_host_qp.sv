`timescale 1ns/1ps
// qfd_io_host_qp (qwen-1010/c 2026-10-10): qfd_io_host with the engine's QPIPE 1 QKV path (registered beat / FP8 codes /
// granule walk, slot fields decoded into registers, per-lane banks, registered drain into an output FIFO: +2 input and
// +2 drain edges on the prefill-ingest path only, 0 decode-token cycles).  Write-only as qfd_io_host (RMW fails closed).
// The preroute of qfd_io_host (hing_qfd_A/B/C) failed -1.2 .. -2.3 ns on the 512-entry computed-index bank decodes / reads.
module qfd_io_host_qp (
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
    ot_rom_host_ingest #(.KVHMAX(2), .HDMAX(128), .QKV_EN(1), .RMW_EN(0), .QPIPE(1)) u_hi (.rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d), .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr), .i_rv(i_rv), .i_rd(i_rd), .fault(fault));
endmodule
