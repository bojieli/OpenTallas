`timescale 1ps/1fs
`default_nettype none
// hbm-system 2026-10-08 (T3 gap F02): on-die SRAM protection, one SECDED code for every protected SRAM of the HBM die
// (and proposed to ds-control for the DS ROM die's SRAMs; ROM storage itself carries no ECC, AGENTS.md ROM policy).
//
// Hsiao odd-weight-column code: K data bits, R check bits (K 32 -> R 7, 64 -> 8, 128 -> 9, 256 -> 10).  Column of
// data bit i = the i-th R-bit value of odd weight >= 3 in increasing order; check bit r has the unit column.
// Syndrome 0: clean; odd weight equal to a column: single error, corrected; anything else (even weight != 0, or odd
// weight matching no column): uncorrectable -> the word is POISONED (ue), never silently used.
// Pipelining (~700 ps a stage): encoder = one XOR tree + output register; decoder = syndrome register, then correction
// + flags register (2 cycles).  MUT (bench negative control): 1 = the encoder uses the wrong column for data bit 0.
module ot_secded_enc #(parameter integer K = 64, parameter integer R = 8, parameter integer MUT = 0) (
  input wire clk, input wire [K-1:0] d, output reg [K+R-1:0] q            // q = {check, data}
);
  `include "ot_secded_cols.svh"
  localparam [256*16-1:0] COLS = cols_all(K, R);
  reg [R-1:0] c;
  integer i, r;
  always @* begin
    c = 0;
    for (i = 0; i < K; i = i + 1) begin
      if (d[i]) c = c ^ ((MUT == 1 && i == 0) ? COLS[16 +: R] : COLS[16*i +: R]);
    end
  end
  always @(posedge clk) q <= {c, d};
endmodule

module ot_secded_dec #(parameter integer K = 64, parameter integer R = 8) (
  input wire clk, input wire rst_n, input wire v, input wire [K+R-1:0] w,
  output reg ov, output reg [K-1:0] d, output reg ce, output reg ue,
  output reg [31:0] n_ce, output reg [31:0] n_ue
);
  `include "ot_secded_cols.svh"
  localparam [256*16-1:0] COLS = cols_all(K, R);
  // stage 1: syndrome
  reg [R-1:0] syn, s1; reg [K-1:0] d1; reg v1;
  integer i;
  always @* begin
    syn = w[K +: R];
    for (i = 0; i < K; i = i + 1) if (w[i]) syn = syn ^ COLS[16*i +: R];
  end
  always @(posedge clk or negedge rst_n) if (!rst_n) v1 <= 1'b0; else v1 <= v;
  always @(posedge clk) begin s1 <= syn; d1 <= w[K-1:0]; end
  // stage 2: locate and correct
  reg [K-1:0] fix; reg hit, odd;
  always @* begin
    fix = 0; hit = 1'b0; odd = ^s1;
    for (i = 0; i < K; i = i + 1) if (s1 == COLS[16*i +: R]) begin fix[i] = 1'b1; hit = 1'b1; end
    if (odd && (s1 & (s1 - 1)) == 0) hit = 1'b1;            // a check bit flipped: data is clean
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin ov <= 1'b0; ce <= 1'b0; ue <= 1'b0; n_ce <= 0; n_ue <= 0; end
    else begin
      ov <= v1;
      ce <= v1 && (s1 != 0) && odd && hit;
      ue <= v1 && (s1 != 0) && !(odd && hit);
      if (v1 && (s1 != 0) && odd && hit) n_ce <= n_ce + 1;
      if (v1 && (s1 != 0) && !(odd && hit)) n_ue <= n_ue + 1;
    end
  always @(posedge clk) d <= d1 ^ fix;
endmodule
`default_nettype wire
