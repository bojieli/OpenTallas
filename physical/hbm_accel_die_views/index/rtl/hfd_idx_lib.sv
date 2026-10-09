`timescale 1ps/1fs
`default_nettype none
// CLAUDE hbm-indexer 2026-10-08: small primitives of the real HBM indexer die views (hfd_idx_score / hfd_idx_sel).
// Design note: claude-takeover-20261007/review_queue/hbm-indexer.md.

// Synchronous FIFO, registered write, first-word read from the array (no output register: the consumers register).
module hfd_idx_fifo #(parameter integer W = 8, parameter integer AW = 4) (
  input  wire          ck, rst_n,
  input  wire          we, input wire [W-1:0] wd,
  input  wire          re, output wire [W-1:0] rd,
  output wire          ne, output wire [AW:0] cnt
);
  reg [W-1:0] m [0:(1<<AW)-1];
  reg [AW:0] wp, rp;
  assign cnt = wp - rp;
  assign ne = (wp != rp);
  assign rd = m[rp[AW-1:0]];
  always @(posedge ck) if (we) m[wp[AW-1:0]] <= wd;
  always @(posedge ck or negedge rst_n)
    if (!rst_n) begin wp <= 0; rp <= 0; end
    else begin
      if (we) wp <= wp + 1'b1;
      if (re && ne) rp <= rp + 1'b1;
    end
`ifndef SYNTHESIS
  always @(posedge ck) if (rst_n && we && cnt == (1 << AW) && !(re && ne))
    $fatal(1, "hfd_idx_fifo overflow (%m)");
`endif
endmodule

// Valid-qualified register pipe: N stages (valid reset, payload not).  Models a die relay chain in benches and is the
// in-block wire-stage chain of the views.
module hfd_idx_pipe #(parameter integer W = 8, parameter integer N = 1) (
  input  wire ck, rst_n, input wire v, input wire [W-1:0] d, output wire qv, output wire [W-1:0] q
);
  generate if (N == 0) begin : g0
    assign qv = v; assign q = d;
  end else begin : gn
    reg [N-1:0] rv;
    always @(posedge ck or negedge rst_n) if (!rst_n) rv <= {N{1'b0}}; else rv <= N'({rv, v});
    genvar k;
    for (k = 0; k < N; k = k + 1) begin : st
      reg [W-1:0] r;
      if (k == 0) begin : h always @(posedge ck) r <= d; end
      else begin : t always @(posedge ck) r <= gn.st[k-1].r; end
    end
    assign qv = rv[N-1]; assign q = st[N-1].r;
  end endgenerate
endmodule

// 1R1W synchronous line memory (rdata holds the line addressed on the edge where re was high, from the next edge on)
// -- the contract of ot_hdc_v41x_sel / ot_hdc_v41x_sel_cand line memories.
//   MEMV 0: behavioural array (benches);
//   MEMV 1: tools/mem_compiler macros, ceil(W/256) side by side: AW 8 -> ot_sram_1r1w_256x256_m2_r2c2 (TT clk->q 405 ps),
//           AW 10 -> ot_sram_1r1w_1024x256_m2_r2c2 (545 ps); repair ports tied off.  The macro output feeds the
//           selector directly for READLAT=1. READLAT=2 captures raw macro output before selector muxing;
//           the matching selector metadata stage preserves finite in-flight reservations.
module hfd_idx_mem #(parameter integer W = 8, parameter integer AW = 4, parameter integer MEMV = 0, parameter integer READLAT = 1) (
  input wire ck, input wire we, input wire [AW-1:0] wa, input wire [W-1:0] wd,
  input wire re, input wire [AW-1:0] ra, output wire [W-1:0] rd
);
  wire [W-1:0] raw_rd;
  generate if (READLAT == 2) begin : capture
    reg [W-1:0] captured;
    always @(posedge ck) captured <= raw_rd;
    assign rd = captured;
  end else begin : direct
    assign rd = raw_rd;
  end endgenerate
  generate if (MEMV == 0) begin : beh
    reg [W-1:0] m [0:(1<<AW)-1];
    reg [W-1:0] r;
    always @(posedge ck) begin
      if (we) m[wa] <= wd;
      if (re) r <= m[ra];
    end
    assign raw_rd = r;
  end else begin : mac
    localparam integer NM = (W + 255) / 256;
    wire [NM*256-1:0] wdx = {{(NM*256-W){1'b0}}, wd};
    wire [NM*256-1:0] rdx;
    genvar i;
    for (i = 0; i < NM; i = i + 1) begin : m
      if (AW == 8) begin : d256
        ot_sram_1r1w_256x256_m2_r2c2 u (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(rdx[i*256 +: 256]),
          .w_ce_in(we), .w_addr_in(wa), .wd_in(wdx[i*256 +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00),
          .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
      end else begin : d1024
        ot_sram_1r1w_1024x256_m2_r2c2 u (.clk(ck), .r_ce_in(re), .r_addr_in(ra), .rd_out(rdx[i*256 +: 256]),
          .w_ce_in(we), .w_addr_in(wa), .wd_in(wdx[i*256 +: 256]), .w_mask_in({256{1'b1}}), .rr_en(2'b00),
          .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
      end
    end
    assign raw_rd = rdx[W-1:0];
  end endgenerate
endmodule
`default_nettype wire
