`timescale 1ps/1fs
// 1.2 GHz successor of ot_hbm_accel_cdc_fifo (left byte-identical: the HA4/R5a/DS records pin it).  Same ports,
// same Gray-pointer / two-flop-synchroniser protocol, cycle-identical on every observed output:
//   * empty and full are REGISTERED: each flag is the next edge's comparison, formed one cycle ahead for both
//     outcomes of this cycle's read (write) and selected by it (the ot_hbm_accel_cdc_fifo_rf construction);
//   * rd_freed is REGISTERED: rd_freed(t) = g2b(rg_w2(t)) - g2b(rg_w2(t-1)) = g2b(rg_w1(t-1)) - g2b(rg_w2(t-1)),
//     so it is formed from the synchroniser flops one cycle ahead;
//   * rdata is REGISTERED: the array word at the NEXT read pointer, re-sampled on every read edge.  Whenever
//     the FIFO is not empty, the entry at the read pointer was written at least two read edges before (its
//     write pointer has passed the two-flop synchroniser) and cannot be overwritten before it is read, so the
//     sampled word equals the r0 combinational mem[rbin]; while empty, rdata is a don't-care (as in r0, the
//     word at an unwritten slot).
//   * the write and read pointers are also held as registered ONE-HOTS (wp_oh, rp_oh, rp1_oh = rbin + 1), so the
//     array write enables and the read mux are AND-OR selects of flops, with no pointer decode on the path;
//     rdata's two candidates (no pop / pop) are both selected and the read enable only picks one.
// The look-ahead flags read the first synchroniser stage (rg_w1 / wg_r1) through one comparator before a flop,
// as ot_hbm_accel_cdc_fifo_rf does; mem -> rdata is an asynchronous-group path held stable by the protocol.
// Every port is a flop output or a flop input (through at most the write/read enable gating): the block can be
// closed with its ports registered on both sides.
module ot_hbm_accel_cdc_fifo_r2 #(parameter integer W = 32, parameter integer AW = 5) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  reg full_r, empty_r; reg [2:0] freed_r; reg [W-1:0] rdata_r;
  reg [D-1:0] wp_oh, rp_oh, rp1_oh;
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  function automatic [AW:0] fullof(input [AW:0] g);   // the write-side Gray value that means "full" against g
    fullof = {~g[AW:AW-1], g[AW-2:0]};
  endfunction
  // write side
  wire push = we && !full_r;
  wire [AW:0] wbin_1 = wbin + 1'b1;
  wire [AW:0] wgray_1 = wbin_1 ^ (wbin_1 >> 1);
  wire f_hold = (wgray == fullof(rg_w1)), f_push = (wgray_1 == fullof(rg_w1));
  assign full = full_r;
  assign rd_freed = freed_r;
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; full_r <= 1'b0; freed_r <= 3'd0; wp_oh <= D'(1); end
    else begin
      if (push) wp_oh <= {wp_oh[D-2:0], wp_oh[D-1]};
      wbin <= push ? wbin_1 : wbin; wgray <= push ? wgray_1 : wgray;
      rg_w1 <= rgray; rg_w2 <= rg_w1;
      full_r <= push ? f_push : f_hold;
      freed_r <= 3'(g2b(rg_w1) - g2b(rg_w2));
    end
  // read side
  wire pop = re && !empty_r;
  wire [AW:0] rbin_1 = rbin + 1'b1;
  wire [AW:0] rgray_1 = rbin_1 ^ (rbin_1 >> 1);
  wire [AW:0] rbin_n = pop ? rbin_1 : rbin;
  wire e_hold = (rgray == wg_r1), e_pop = (rgray_1 == wg_r1);
  assign empty = empty_r;
  assign rdata = rdata_r;
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; empty_r <= 1'b1; end
    else begin
      rbin <= rbin_n; rgray <= pop ? rgray_1 : rgray;
      wg_r1 <= wgray; wg_r2 <= wg_r1;
      empty_r <= pop ? e_pop : e_hold;
    end
  // array: entry i written when push && wp_oh[i] (wp_oh == 1 << wbin[AW-1:0] at every edge)
  for (genvar i = 0; i < D; i = i + 1) begin : g_mem
    always @(posedge wclk) if (push && wp_oh[i]) mem[i] <= wdata;
  end
  reg [W-1:0] q0, q1;
  always @* begin
    q0 = 0; q1 = 0;
    for (integer i = 0; i < D; i = i + 1) begin
      q0 = q0 | ({W{rp_oh[i]}} & mem[i]);
      q1 = q1 | ({W{rp1_oh[i]}} & mem[i]);
    end
  end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rp_oh <= D'(1); rp1_oh <= D'(2); end
    else if (pop) begin rp_oh <= rp1_oh; rp1_oh <= {rp1_oh[D-2:0], rp1_oh[D-1]}; end
  // rdata = mem[rbin_n]: rbin_n is rbin + 1 on a pop, else rbin
  always @(posedge rclk) rdata_r <= pop ? q1 : q0;
endmodule
