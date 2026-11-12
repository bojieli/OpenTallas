`timescale 1ps/1fs
// BUS-GEAR-1 bench for ot_s81_xlane_gear_tx / _rx: random 1104-b x words at cadence >= 2 (random extra gaps), TX ->
// H relay stations on the 556-b beat lanes -> RX.  On every edge, per lane, the RX word must equal the TX input word
// delayed by exactly LAT = 1 + H + 1 edges when that edge carries a word, and be all-zero otherwise (so the crs4
// in-band markers x[0] / x[566] read 0 = bubble).  Phase 2 drives two words on consecutive edges: fault must rise.
// MUT 1 = beat order reversed (must mismatch), 3 = no spacing fault (must miss the phase-2 fault).
module tb;
  parameter integer H = 3, MUT = 0, NW = 3000;
  localparam integer NL = 4, LW = 276, BL = 139, LAT = 1 + H + 1;
  reg clk = 0; always #416 clk = ~clk;
  reg rst_n = 0, v = 0, chk_on = 1; reg [NL*LW-1:0] x = 0;
  wire [NL*BL-1:0] b0; wire flt;
  ot_s81_xlane_gear_tx #(.MUT(MUT)) u_tx (.clk(clk), .rst_n(rst_n), .v_i(v), .x_i(x), .xb_o(b0), .fault_o(flt));
  reg [NL*BL-1:0] st [0:H];
  integer i, j, e = 0, errs = 0, words = 0, now = 0;
  always @(*) st[0] = b0;
  always @(posedge clk) for (j = H; j >= 1; j = j - 1) st[j] <= st[j-1];
  wire [NL*LW-1:0] xo; wire [NL-1:0] vo;
  ot_s81_xlane_gear_rx #(.MUT(MUT)) u_rx (.xk({NL{clk}}), .rst_n({NL{rst_n}}), .xb_i(st[H]), .x_o(xo), .v_o(vo));
  // reference delay line of (v, x) sampled on each edge
  reg rv [0:63]; reg [NL*LW-1:0] rx [0:63];
  function [NL*LW-1:0] rndw(input integer s);
    integer q; reg [NL*LW+31:0] t; begin t = 0; for (q = 0; q < NL*LW; q = q + 32) t[q +: 32] = $random; rndw = t[NL*LW-1:0]; end
  endfunction
  always @(posedge clk) if (rst_n) begin
    now = now + 1;
    rv[now % 64] = v; rx[now % 64] = x;
  end
  // compare just before the next edge
  always @(negedge clk) if (rst_n && chk_on && now > LAT + 2) begin : cmp
    reg ev; reg [NL*LW-1:0] ex;
    ev = rv[(now - LAT + 1 + 64) % 64]; ex = ev ? rx[(now - LAT + 1 + 64) % 64] : {NL*LW{1'b0}};
    if (xo !== ex || vo !== {NL{ev}}) begin errs = errs + 1; if (errs < 4) $display("XGEAR_MISMATCH edge %0d ev %0d vo %b", now, ev, vo); end
    if (ev) words = words + 1;
  end
  initial begin
    repeat (4) @(posedge clk); @(negedge clk); rst_n = 1;
    for (i = 0; i < NW; i = i + 1) begin
      @(negedge clk); x = rndw(i); x[0] = 1'b1; x[566] = 1'b1; v = 1;     // markers set on real words
      @(negedge clk); v = 0; x = rndw(i);                                  // garbage on non-word edges
      if ($random % 3 == 0) begin @(negedge clk); x = rndw(i); end
    end
    @(negedge clk); v = 0; repeat (LAT + 4) @(negedge clk);
    if (flt) begin errs = errs + 1; $display("XGEAR_FAULT in legal phase"); end
    // phase 2: spacing violation (data not compared)
    chk_on = 0;
    @(negedge clk); v = 1; @(negedge clk); v = 1; @(negedge clk); v = 0; repeat (3) @(negedge clk);
    if (!flt) $display("XGEAR_NO_FAULT on back-to-back words");
    if (errs == 0 && flt && words >= NW - 2) $display("XGEAR PASS H=%0d words=%0d", H, words);
    else $display("XGEAR FAIL H=%0d MUT=%0d errs=%0d words=%0d fault=%0d", H, MUT, errs, words, flt);
    $finish;
  end
endmodule
