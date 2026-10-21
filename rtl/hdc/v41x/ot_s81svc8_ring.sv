`timescale 1ns/1ps
// S81-SVC8 (10-20): fixed-delay SRAM ring, generalisation of ot_s81svc7_skew_sram (Codex SVC7, golden D3..30 PASS)
// to a 32x64 (W <= 63) or 32x128 (W <= 127) macro.  Same timing as ot_hdc_v41x_dly #(W, D): o(c + D) = i(c).
// write at t, read at t + D - 2, registered capture at t + D - 1.  i may be combinational from registers.
// Reset: 2-stage local landing (reset0 -> run); while !run the counters hold 0 and o = 0; after release the first
// D-1 captures read unwritten words and are forced 0 (fill), so no uninitialised SRAM word ever leaves the ring.
// Interface contract (landed-reset standard): the caller issues no live data until the ring has run >= 1 edge.
(* keep_hierarchy *)
module ot_s81svc8_ring #(
    parameter integer W = 21,
    parameter integer D = 5,
    parameter integer M = 64,           // macro word: 64 -> ot_sram_1r1w_32x64_m1, 128 -> ot_sram_1r1w_32x128_m1
`ifdef SVC8_RING_WREG
    parameter integer WREG = 1          // hgrp8r (10-21): registered write port (ot_s81svc8_sram_wreg), delay unchanged
`else
    parameter integer WREG = 0
`endif
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] i,
    output wire [W-1:0] o
);
    (* keep *) reg reset0, run_c, run_q;
    always @(posedge clk) begin
        reset0 <= rst_n;
        run_c <= reset0;
        run_q <= reset0;
    end
    reg [4:0] wc;
    reg [5:0] fill;
    always @(posedge clk) begin
        if (!run_c) begin wc <= 5'd0; fill <= 6'd0; end
        else begin wc <= wc + 5'd1; if (fill < D) fill <= fill + 6'd1; end
    end
`ifdef SVC8_RING_MUT_ADDR
    wire [4:0] r_addr = wc - (D - 3);
`else
    wire [4:0] r_addr = wc - (D - 2);
`endif
    wire [M-1:0] rd;
    generate if (M == 128) begin : g_m128
        ot_sram_1r1w_32x128_m1 u_mem (
            .clk(clk), .r_ce_in(run_c), .r_addr_in(r_addr), .rd_out(rd),
            .w_ce_in(run_c), .w_addr_in(wc), .wd_in({{(M-W){1'b0}}, i}), .w_mask_in({M{1'b1}}));
    end else if (WREG != 0) begin : g_m64w
        ot_s81svc8_sram_wreg u_mem (
            .clk(clk), .r_ce_in(run_c), .r_addr_in(r_addr), .rd_out(rd),
            .w_ce_in(run_c), .w_addr_in(wc), .wd_in({{(M-W){1'b0}}, i}), .w_mask_in({M{1'b1}}));
    end else begin : g_m64
        ot_sram_1r1w_32x64_m1 u_mem (
            .clk(clk), .r_ce_in(run_c), .r_addr_in(r_addr), .rd_out(rd),
            .w_ce_in(run_c), .w_addr_in(wc), .wd_in({{(M-W){1'b0}}, i}), .w_mask_in({M{1'b1}}));
    end endgenerate
    reg [W-1:0] q;
    always @(posedge clk) begin
        if (!run_q) q <= {W{1'b0}};
        else if (fill >= D - 1) q <= rd[W-1:0];
        else q <= {W{1'b0}};
    end
    assign o = q;
`ifndef SYNTHESIS
    initial begin
        if (W < 1 || W > M - 1) $fatal(1, "SVC8_RING_W");
        if (D < 3 || D > 31) $fatal(1, "SVC8_RING_D");
        if (M != 64 && M != 128) $fatal(1, "SVC8_RING_M");
        if (WREG != 0 && (M != 64 || D < 4)) $fatal(1, "SVC8_RING_WREG");
    end
`endif
endmodule
