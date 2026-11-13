`timescale 1ps/1fs
// HA4: asynchronous FIFO (Gray-coded pointers, two-flop synchronisers) for the crossings between the
// 1.2 GHz streaming/SM domain and the HBM controller's CK/2 (976.6 MHz) domain.  One write per wclk
// and one read per rclk at most, so each synchronised pointer moves by one Gray step.  Read data is
// the registered array word at the read pointer (first-word fall-through on the array).
// rd_freed is the number of entries the reader freed, as seen in the write domain after
// synchronisation (0..2 per wclk), for credit return to a producer that counts credits.
module ot_wbq_root_s7_rr_fifo #(parameter integer W = 32, parameter integer AW = 2, parameter integer MUT = 0, parameter integer RSEL = 0, parameter integer RSLICE = 24) (
  input  wire          wclk, wrst_n, input wire we, input wire [W-1:0] wdata, output wire full,
  output wire [2:0]    rd_freed,
  input  wire          rclk, rrst_n, input wire re, output wire [W-1:0] rdata, output wire empty
);
  localparam integer D = 1 << AW;
  reg [W-1:0] mem [0:D-1];
  reg [AW:0] wbin, wgray, rbin, rgray;
  (* async_reg = "true" *) reg [AW:0] rg_w1, rg_w2;   // read pointer in the write domain
  (* async_reg = "true" *) reg [AW:0] wg_r1, wg_r2;   // write pointer in the read domain
  function automatic [AW:0] g2b(input [AW:0] g);
    for (integer i = AW; i >= 0; i = i - 1) g2b[i] = (i == AW) ? g[i] : g2b[i+1] ^ g[i];
  endfunction
  // One ingress record, four local 72-bit controls. Never publish Gray early.
  localparam integer NS=W/72;
  (* keep *) reg [NS-1:0] stage_valid;
  (* keep *) reg [D-1:0] stage_word[0:NS-1];
  reg [W-1:0] stage_data;
  wire ring_full=(wgray == {~rg_w2[AW:AW-1], rg_w2[AW-2:0]});
  wire commit=stage_valid[0]&&!ring_full;
  wire [AW:0] wbin_n=wbin+commit;
  genvar sl,wd;
  generate for(sl=0;sl<NS;sl=sl+1)begin:g_slice
    wire stage_open=!stage_valid[sl]||!ring_full;
    always @(posedge wclk or negedge wrst_n)
      if(!wrst_n)stage_valid[sl]<=0;
      else if(stage_open)stage_valid[sl]<=we&&!full;
    always @(posedge wclk)if(stage_open)begin
      stage_data[sl*72+:72]<=wdata[sl*72+:72];
      stage_word[sl]<=D'(1)<<((MUT==1)?wbin[AW-1:0]:wbin_n[AW-1:0]);
    end
    for(wd=0;wd<D;wd=wd+1)begin:g_word
      always @(posedge wclk)
        if(wrst_n&&stage_valid[sl]&&!ring_full&&stage_word[sl][wd])
          mem[wd][sl*72+:72]<=stage_data[sl*72+:72];
    end
  end endgenerate
  wire [AW:0] rbin_n = rbin + ((re && !empty) ? 1'b1 : 1'b0);
  assign full = stage_valid[0]&&ring_full;
  assign empty = (rgray == wg_r2);
  // RSEL=1 (HBM-CORES-C 11-12, g1 rbin3 setup class): the read-pointer select reaches the W-bit array mux through one registered
  // one-hot copy per RSLICE-bit slice instead of one binary pointer fanning out to every bit.  rsel_oh[s] == onehot(rbin[AW-1:0]) at
  // every clock edge (loaded with the same next state, same reset value), so rdata is cycle-exact equal to RSEL=0: no cycle is added,
  // the credit loop and every other seam signal are unchanged.  Default 0 = the original mux.
  generate if (RSEL != 0) begin : g_rsel
    localparam integer NSL = (W + RSLICE - 1) / RSLICE;
    (* keep *) reg [D-1:0] rsel_oh [0:NSL-1];
    genvar rs, rk;
    for (rs = 0; rs < NSL; rs = rs + 1) begin : g_s
      localparam integer LO = rs * RSLICE;
      localparam integer WS = (LO + RSLICE <= W) ? RSLICE : (W - LO);
      always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) rsel_oh[rs] <= D'(1);
        else rsel_oh[rs] <= D'(1) << rbin_n[AW-1:0];
`ifndef SYNTHESIS
      // invariant (simulation only): the registered one-hot copy equals the decoded read pointer at every rclk edge
      always @(posedge rclk) if (rrst_n && rsel_oh[rs] !== (D'(1) << rbin[AW-1:0])) $display("RSEL_INV_FAIL t=%0t slice=%0d", $time, rs);
`endif
      reg [WS-1:0] sl_data;
      always @* begin
        sl_data = {WS{1'b0}};
        for (integer k = 0; k < D; k = k + 1) sl_data = sl_data | ({WS{rsel_oh[rs][k]}} & mem[k][LO +: WS]);
      end
      assign rdata[LO +: WS] = sl_data;
    end
  end else begin : g_rbin
    assign rdata = mem[rbin[AW-1:0]];
  end endgenerate
  reg [AW:0] rsync_bin_q;
  wire [AW:0] rsync_bin = g2b(rg_w2);
  assign rd_freed = 3'(rsync_bin - rsync_bin_q);
  always @(posedge wclk or negedge wrst_n)
    if (!wrst_n) begin wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; rsync_bin_q <= 0; end
    else begin
      wbin <= wbin_n; wgray <= wbin_n ^ (wbin_n >> 1);
      rg_w1 <= rgray; rg_w2 <= rg_w1; rsync_bin_q <= rsync_bin;
    end
  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) begin rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; end
    else begin
      rbin <= rbin_n; rgray <= rbin_n ^ (rbin_n >> 1);
      wg_r1 <= wgray; wg_r2 <= wg_r1;
    end
endmodule
