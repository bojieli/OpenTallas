`timescale 1ns/1ps
// redesign-hbm 2026-10-09: used by rtl/hbm_accel/tu/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv
// 4-edge SECDED decoder (2026-10-10 registered hit summaries) (same code and rules as rtl/common/ot_secded.sv ot_secded_dec, which stays byte-identical):
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
  reg [K-1:0] fix; reg [3:0] hitpart;
  reg check_hit;
  always @* begin
    fix = 0; hitpart = 0; check_hit = 0;
    for (i = 0; i < K; i = i + 1)
      if (s1[i / (K / 4)] == COLS[16*i +: R]) begin
        fix[i] = 1'b1; hitpart[i / (K / 4)] = 1'b1;
      end
    // A one-hot syndrome identifies a check bit. Constant comparators avoid
    // the old subtract-and-AND serial path through the flag enable.
    for (i = 0; i < R; i = i + 1)
      if (s1[0] == ({{(R-1){1'b0}},1'b1} << i)) check_hit = 1'b1;
  end
  reg [K-1:0] dc;
  reg [3:0] hitreg;
  reg checkreg, nonzero, odd, vc;
  always @(posedge clk) begin
    dc <= db ^ fix;
    hitreg <= hitpart;
    checkreg <= check_hit;
    nonzero <= s1[1] != 0;
    odd <= ^s1[2];
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin vc <= 0; ov <= 0; ce <= 0; ue <= 0; end
    else begin
      vc <= vb;
      ov <= vc;
      ce <= vc && nonzero && odd && ((|hitreg) || checkreg);
      ue <= vc && nonzero && !(odd && ((|hitreg) || checkreg));
    end
  always @(posedge clk) d <= dc;
endmodule
