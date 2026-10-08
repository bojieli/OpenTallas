`timescale 1ns/1ps
// ot_hdc_v41_fh_adec (2026-10-07): exact subtract-free lane-address decode for head_top OREG>=2.
// Original: d = a - BASE; ok = en && a >= BASE && d[LG-1:0] == GA && (d >> LG) < ROWS; row = 9'(d >> LG).
// Here: ok = en && BASE <= a < BASE + (ROWS << LG) && a[LG-1:0] == (BASE + GA)[LG-1:0]  (two constant compares),
// row from a (LG+9)-bit subtract. Equivalence: tb_fh_adec (random + boundary addresses, 3 bases x 4 lanes).
module ot_hdc_v41_fh_adec #(
    parameter integer AW = 24, LG = 2, ROWS = 505, GA = 0,
    parameter [AW-1:0] BASE = 0
) (
    input  wire          en,
    input  wire [AW-1:0] a,
    output wire          ok,
    output wire [8:0]    row
);
    localparam [AW-1:0] LIM = BASE + (AW'(ROWS) << LG);
    localparam [LG-1:0] LOWB = LG'(BASE + GA);
    assign ok = en && a >= BASE && a < LIM && a[LG-1:0] == LOWB;
    wire [LG+8:0] d = a[LG+8:0] - BASE[LG+8:0];
    assign row = d[LG+8:LG];
`ifndef SYNTHESIS
    initial if (BASE + (ROWS << LG) >= (1 << AW)) $fatal(1, "ot_hdc_v41_fh_adec needs BASE + (ROWS << LG) < 2^AW");
`endif
endmodule
