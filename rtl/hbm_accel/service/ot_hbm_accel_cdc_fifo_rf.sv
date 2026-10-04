`timescale 1ps/1fs
// HA4 R5a: ot_hbm_accel_cdc_fifo (unchanged, pinned by HA4) with a REGISTERED empty flag for the
// 1.2 GHz landing grant of ot_hbm_accel_expert_fetch_stream_sram.  Identical cycle behaviour: the
// flop holds, at every read edge, exactly the value the original computes combinationally from the
// Gray read pointer and the synchronised write pointer (rgray == wg_r2).  Both candidates (no pop /
// pop) are compared from registers one cycle ahead, and the read enable only selects between them,
// so the reader's empty path starts at a flop.
module ot_hbm_accel_cdc_fifo_rf #(parameter integer W = 32, parameter integer AW = 5) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  reg empty_r;
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  wire pop = re && !empty_r;
  wire [AW:0] wbin_n = wbin + ((we && !full) ? 1'b1 : 1'b0);
  wire [AW:0] rbin_1 = rbin + 1'b1;
  wire [AW:0] rgray_1 = rbin_1 ^ (rbin_1 >> 1);
  wire [AW:0] rbin_n = pop ? rbin_1 : rbin;
  // next edge's (rgray == wg_r2) for either outcome of this cycle's read
  wire e_hold = (rgray == wg_r1), e_pop = (rgray_1 == wg_r1);
  assign full  = (wgray == {~rg_w2[AW:AW-1], rg_w2[AW-2:0]});
  assign empty = empty_r;
  assign rdata = mem[rbin[AW-1:0]];
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; end
    else begin
      if (we && !full) mem[wbin[AW-1:0]] <= wdata;
      wbin <= wbin_n; wgray <= wbin_n ^ (wbin_n >> 1);
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
    end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; empty_r <= 1'b1; end
    else begin
      rbin <= rbin_n; rgray <= pop ? rgray_1 : rgray;
      wg_r1 <= wgray; wg_r2 <= wg_r1;
      empty_r <= pop ? e_pop : e_hold;
    end
endmodule
