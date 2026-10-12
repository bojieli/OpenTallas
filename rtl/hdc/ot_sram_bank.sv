`timescale 1ns/1ps
// ot_sram_bank (el1011-s81su-qn, 2026-10-12): a DEPTH x 512 b 1R1W store in ceil(DEPTH / 64) macros
// ot_sram_1r1w_64x512_m1_r2c2 stacked in depth (bit-masked write, registered read).  A read issued at cycle c
// (re, ra) is valid on q in cycle c + 1 (the macro's output register; with several macros, a registered bank select
// picks the word).  A read and a write of the same address in one cycle return the old word.  No reset on the data.
module ot_sram_bank #(
    parameter integer DEPTH = 64,
    parameter integer AW = (DEPTH > 64) ? $clog2(DEPTH) : 6
) (
    input  wire                         clk,
    input  wire                         we,
    input  wire [AW-1:0] wa,
    input  wire [511:0]                 wd,
    input  wire [511:0]                 wm,
    input  wire                         re,
    input  wire [AW-1:0] ra,
    output wire [511:0]                 q
);
    localparam integer NM = (DEPTH + 63) / 64;
    wire [NM*512-1:0] rq;
    genvar m;
    generate
        for (m = 0; m < NM; m = m + 1) begin : g_m
            wire [AW-1:0] wsel = wa >> 6, rsel = ra >> 6;
            ot_sram_1r1w_64x512_m1_r2c2 u_m (.clk(clk), .r_ce_in(re && (NM == 1 || rsel == m)), .r_addr_in(ra[5:0]),
                .rd_out(rq[512 * m +: 512]), .w_ce_in(we && (NM == 1 || wsel == m)), .w_addr_in(wa[5:0]), .wd_in(wd),
                .w_mask_in(wm), .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
        end
        if (NM == 1) begin : g_one
            assign q = rq;
        end else begin : g_mux
            reg [AW-1:0] bs;
            reg [511:0] qm;
            always @(posedge clk) if (re) bs <= ra >> 6;
            always @(*) begin : sel                    // decoded AND-OR select (no runtime part-select)
                integer i;
                qm = 512'd0;
                for (i = 0; i < NM; i = i + 1) if (bs == i) qm = qm | rq[512 * i +: 512];
            end
            assign q = qm;
        end
    endgenerate
endmodule
