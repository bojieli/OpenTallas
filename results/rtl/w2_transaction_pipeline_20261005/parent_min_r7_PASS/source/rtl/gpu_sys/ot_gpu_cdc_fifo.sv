`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_cdc_fifo: valid/ready asynchronous clock-domain-crossing FIFO of the
// GPU-organised HBM comparator system (SM <-> crossbar/L2/HBM service, SM <->
// link, host <-> SM).  The storage and Gray-pointer synchronisers are the
// existing link-layer FIFO rtl/link/ot_link_afifo.sv, reused unmodified; this
// wrapper only presents valid/ready on both sides and keeps the overflow
// flag as a sticky fault (a push is never attempted while full, so it stays 0).
//
// Depth 2^AW must cover the synchroniser round trip at the service rate:
// tools/gpu_sys/cdc_sizing.py derives AW from the two clock periods, SYNC and
// the entry rate, and rtl/test/gpu_sys/tb_gpu_cdc_fifo.sv measures it.
// ENABLE = 0 (default): inert, every output 0.
// ---------------------------------------------------------------------------
module ot_gpu_cdc_fifo #(
    parameter integer ENABLE = 0,
    parameter integer W      = 64,
    parameter integer AW     = 3,
    parameter integer SYNC   = 2
) (
    input  wire         wclk,
    input  wire         wrst_n,
    input  wire         in_v,
    output wire         in_rdy,
    input  wire [W-1:0] in_d,
    input  wire         rclk,
    input  wire         rrst_n,
    output wire         out_v,
    input  wire         out_rdy,
    output wire [W-1:0] out_d,
    output wire         ovf_fault
);
    generate if (ENABLE != 0) begin : g_on
        wire wfull, rempty, ovf;
        wire [AW:0] wfreed, rcount;
        ot_link_afifo #(.W(W), .AW(AW), .SYNC(SYNC)) u_fifo (
            .wclk(wclk), .wrst_n(wrst_n), .wr(in_v && !wfull), .wdata(in_d), .wfull(wfull), .wfreed(wfreed),
            .ovf(ovf), .rclk(rclk), .rrst_n(rrst_n), .rd(out_v && out_rdy), .rempty(rempty), .rdata(out_d),
            .rcount(rcount));
        assign in_rdy = !wfull;
        assign out_v = !rempty;
        assign ovf_fault = ovf;
    end else begin : g_off
        assign in_rdy = 1'b0;
        assign out_v = 1'b0;
        assign out_d = {W{1'b0}};
        assign ovf_fault = 1'b0;
    end endgenerate
endmodule
