
// HBM-CORES-B 11-09 H12 (H11+ECO routed TT -76.82 / 119: u_ack wgray -> full compare -> 116 mem write enables, ~550 ps
// of wire): the same Gray FIFO as ot_hbm_accel_cdc_fifo, but full is a REGISTER loaded with next cycle's compare
// (gray(wbin_n) against rg_w1, which is next cycle's rg_w2). Cycle-exact: full_q == (wgray == {~rg_w2[AW:AW-1],
// rg_w2[AW-2:0]}) in every cycle (both are 0 out of reset), so ports, latency and contents are unchanged.
module ot_hbm_accel_cdc_fifo_fq #(parameter integer W = 32, parameter integer AW = 5) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  reg full_q;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  wire [AW:0] wbin_n = wbin + ((we && !full_q) ? 1'b1 : 1'b0);
  wire [AW:0] wgray_n = wbin_n ^ (wbin_n >> 1);
  wire [AW:0] rbin_n = rbin + ((re && !empty) ? 1'b1 : 1'b0);
  assign full  = full_q;
  assign empty = (rgray == wg_r2);
  assign rdata = mem[rbin[AW-1:0]];
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; full_q <= 1'b0; end
    else begin
      if (we && !full_q) mem[wbin[AW-1:0]] <= wdata;
      wbin <= wbin_n; wgray <= wgray_n;
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
      full_q <= (wgray_n == {~rg_w1[AW:AW-1], rg_w1[AW-2:0]});
    end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; end
    else begin
      rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
      wg_r1 <= wgray; wg_r2 <= wg_r1;
    end
endmodule
