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

// DPIPE=1 (sys-takeover 2026-10-10, opt-in; default 0 = unchanged): the column match (K compares + OR) is registered
// before the correction / flag stage: +1 edge (collvmpub u_dec.s1 -> ue 13 levels at K 256).
module ot_secded_dec #(parameter integer K = 64, parameter integer R = 8, parameter integer DPIPE = 0) (
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
  // DPIPE: stage 2a registers the match (fix vector, hit, odd, syndrome non-zero) and the data; stage 2b corrects
  reg [K-1:0] fix2, d2; reg hit2, odd2, nz2, v2;
  always @(posedge clk or negedge rst_n) if (!rst_n) v2 <= 1'b0; else v2 <= v1;
  always @(posedge clk) begin fix2 <= fix; d2 <= d1; hit2 <= hit; odd2 <= odd; nz2 <= (s1 != 0); end
  wire        vx   = DPIPE ? v2 : v1;
  wire        nzx  = DPIPE ? nz2 : (s1 != 0);
  wire        oddx = DPIPE ? odd2 : odd;
  wire        hitx = DPIPE ? hit2 : hit;
  wire [K-1:0] dx  = DPIPE ? (d2 ^ fix2) : (d1 ^ fix);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin ov <= 1'b0; ce <= 1'b0; ue <= 1'b0; n_ce <= 0; n_ue <= 0; end
    else begin
      ov <= vx;
      ce <= vx && nzx && oddx && hitx;
      ue <= vx && nzx && !(oddx && hitx);
      if (vx && nzx && oddx && hitx) n_ce <= n_ce + 1;
      if (vx && nzx && !(oddx && hitx)) n_ue <= n_ue + 1;
    end
  always @(posedge clk) d <= dx;
endmodule
`default_nettype wire
