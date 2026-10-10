`timescale 1ns/1ps
// redesign-hbm 2026-10-09: used by rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv
// 3-edge SECDED decoder (same code and rules as rtl/common/ot_secded.sv ot_secded_dec, which stays byte-identical):
// edge A: P partial syndromes over K/P data bits each (check bits folded into partial 0); edge B: syndrome = XOR of the
// P partials, registered with 4 replicas (each feeds K/4 column comparators); edge C: locate, correct, flags.
module ot_secded_dec_dp #(parameter integer K = 256, parameter integer R = 10, parameter integer P = 4) (
  input wire clk, input wire rst_n, input wire v, input wire [K+R-1:0] w,
  output reg ov, output reg [K-1:0] d, output reg ce, output reg ue
);
  `include "ot_secded_cols.svh"
  localparam [256*16-1:0] COLS = cols_all(K, R);
  localparam integer KP = K / P;
  reg [R-1:0] ps [0:P-1]; reg [R-1:0] psq [0:P-1];
  reg [K-1:0] da, db; reg va, vb;
  (* keep *) reg [R-1:0] s1 [0:3];
  integer i, p;
  always @* begin
    for (p = 0; p < P; p = p + 1) begin
      ps[p] = (p == 0) ? w[K +: R] : {R{1'b0}};
      for (i = p * KP; i < (p + 1) * KP; i = i + 1) if (w[i]) ps[p] = ps[p] ^ COLS[16*i +: R];
    end
  end
  reg [R-1:0] syn;
  always @* begin syn = 0; for (p = 0; p < P; p = p + 1) syn = syn ^ psq[p]; end
  always @(posedge clk or negedge rst_n) if (!rst_n) begin va <= 1'b0; vb <= 1'b0; end else begin va <= v; vb <= va; end
  always @(posedge clk) begin
    for (p = 0; p < P; p = p + 1) psq[p] <= ps[p];
    da <= w[K-1:0]; db <= da;
    for (p = 0; p < 4; p = p + 1) s1[p] <= syn;
  end
  reg [K-1:0] fix; reg hit; reg [3:0] odd4; reg [3:0] hitq;
  always @* begin
    fix = 0; hitq = 4'b0;
    for (i = 0; i < K; i = i + 1) if (s1[i / (K / 4)] == COLS[16*i +: R]) begin fix[i] = 1'b1; hitq[i / (K / 4)] = 1'b1; end
    hit = |hitq;
    if ((^s1[0]) && (s1[0] & (s1[0] - 1)) == 0) hit = 1'b1;            // a check bit flipped: data is clean
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin ov <= 1'b0; ce <= 1'b0; ue <= 1'b0; end
    else begin
      ov <= vb;
      ce <= vb && (s1[1] != 0) && (^s1[1]) && hit;
      ue <= vb && (s1[2] != 0) && !((^s1[2]) && hit);
    end
  always @(posedge clk) d <= db ^ fix;
endmodule
