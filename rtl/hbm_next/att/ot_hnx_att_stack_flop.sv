`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hnx_att_stack_flop: FLOP-STACK stand-in for the PV merge's 64x512 stack macro (HBM-NEXT-ATT4 2026-10-19, risk A1
// fallback variant).  Same port shape and timing as ot_sram_1r1w_64x512_m1_r2c2 (registered read, read-before-write,
// full-word writes), but only the words the merge can address at LV levels are built: word {entry e, level k} exists
// for k < LV (the binary-counter stack) and, when PUB = 1, for k = 7 (the published node) -> 8 x LV (+ 8) words of
// flops (LV 3: 24 words, 32 with publication).  An access to any other word is a sticky FAULT (never silently aliased).
// Mutant MUT 5 (bench negative control): the read returns the word one entry up ({e+1, k}).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_att_stack_flop #(
    parameter integer LV  = 3,
    parameter integer PUB = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         r_ce_in,
    input  wire [5:0]   r_addr_in,
    output reg  [511:0] rd_out,
    input  wire         w_ce_in,
    input  wire [5:0]   w_addr_in,
    input  wire [511:0] wd_in,
    output reg          fault
);
    initial if (LV < 1 || LV > 7) $fatal(1, "ot_hnx_att_stack_flop: 1 <= LV <= 7");
    localparam integer NW = LV + (PUB ? 1 : 0);          // levels kept per entry
    // physical word index of {entry, level}: level k < LV -> k, level 7 -> LV
    function automatic integer pidx(input [5:0] a);
        pidx = (a[2:0] == 3'd7) ? (8 * LV + {29'd0, a[5:3]}) : ({29'd0, a[5:3]} * LV + {29'd0, a[2:0]});
    endfunction
    function automatic bit legal(input [5:0] a);
        legal = (a[2:0] < LV) || (PUB != 0 && a[2:0] == 3'd7);
    endfunction
    reg [511:0] w [0:8*NW-1];
    wire [5:0] ra = (MUT == 5) ? {r_addr_in[5:3] + 3'd1, r_addr_in[2:0]} : r_addr_in;
`ifndef SYNTHESIS
    integer i;
    initial for (i = 0; i < 8 * NW; i = i + 1) w[i] = 512'd0;   // simulation parity with the macro model (zeros)
`endif
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= legal(ra) ? w[pidx(ra)] : 512'd0;
        if (w_ce_in && legal(w_addr_in)) w[pidx(w_addr_in)] <= wd_in;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (w_ce_in && !legal(w_addr_in)) fault <= 1'b1;
endmodule
`default_nettype wire
