`timescale 1ns/1ps
// BUS-GEAR-2 smoke: ot_s81_xc_gear_tx (xw_v framed) -> ot_s81_xlane_gear_rx OGATE 0; every word lands exactly 2 edges
// after it is on xc (beat 0 face capture +1, RX +1), for any start parity and gaps 2..4; MUT 1 = back-to-back -> flt.
module tb;
  localparam integer LW = 276, BL = 139;
  integer MUT = 0, SEED = 1, sd, t, e = 0, errs = 0, ok = 0, words = 0, ph = 0, q;
  reg clk = 0; always #1 clk = ~clk;
  reg rst_n = 0;
  reg [4*LW-1:0] xc = 0, hist0 = 0, hist1 = 0;
  wire [4*BL-1:0] xb; wire flt; reg [4*BL-1:0] xbf = 0;
  wire [4*LW-1:0] xo; wire [3:0] vo;
  ot_s81_xc_gear_tx #(.NG(1), .GEN(1'b1)) u_tx (.ck({4{clk}}), .rst_n(rst_n), .xc(xc), .xb(xb), .flt(flt));
  always @(posedge clk) xbf <= xb;   // the partition face flop
  ot_s81_xlane_gear_rx #(.OGATE(0)) u_rx (.xk({4{clk}}), .rst_n({4{rst_n}}), .xb_i(xbf), .x_o(xo), .v_o(vo));
  function [4*LW-1:0] rnd; input integer d; integer k; reg [4*LW+31:0] r;
    begin r = 0; for (k = 0; k < 4*LW; k = k + 32) r[k +: 32] = $random(sd); rnd = r[4*LW-1:0]; end endfunction
  always @(posedge clk) if (rst_n) begin
    e = e + 1;
    // xo (combinational RX output, sampled at this edge) must equal xc of 2 edges ago when that was a word
    if (hist1[1]) begin if (xo !== hist1) begin errs = errs + 1; if (errs < 4) $display("MISMATCH e=%0d", e); end else ok = ok + 1; end
    else if (xo[1] | xo[567]) begin errs = errs + 1; if (errs < 4) $display("PHANTOM e=%0d", e); end
    hist1 <= hist0; hist0 <= xc;
  end
  initial begin
    if (!$value$plusargs("MUT=%d", MUT)) MUT = 0; if (!$value$plusargs("SEED=%d", SEED)) SEED = 1; sd = SEED;
    repeat (5) @(posedge clk); @(negedge clk); rst_n = 1; t = SEED % 4;
    while (e < 3000) begin
      if (t == 0) begin xc = rnd(0); xc[0] = 1; xc[566] = 1; xc[1] = 1; xc[567] = 1; words = words + 1;
        t = (MUT == 1 && words == 100) ? 0 : 1 + (($random(sd) & 32'h7fffffff) % 3); end
      else begin xc = rnd(1); xc[0] = 1; xc[566] = 1; xc[1] = 0; xc[567] = 0; t = t - 1; end
      @(negedge clk);
    end
    $display("SMOKE %s MUT=%0d SEED=%0d words=%0d ok=%0d errs=%0d flt=%0d", (errs == 0 && !flt && ok > 500) ? "PASS" : "FAIL", MUT, SEED, words, ok, errs, flt);
    $finish;
  end
endmodule
