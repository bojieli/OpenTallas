`timescale 1ps/1ps
// hbm-system 2026-10-08: SECDED fault bench.  For K in {32, 64, 128, 256}: random words with 0, every single (data and
// check bits) and random double flips; K = 32 also every double flip of 8 words exhaustively.  Expect: 0 flips clean,
// 1 flip corrected (ce, data equal), 2 flips poisoned (ue).  MUT = 1 (wrong encoder column) must fail.
module tb_ot_secded #(parameter integer MUT = 0);
  reg clk = 0, rst_n = 0; always #400 clk = ~clk;
  integer err = 0, nchk = 0;
  task automatic note(input integer bad); begin if (bad) err = err + 1; nchk = nchk + 1; end endtask
  genvar g;
  generate for (g = 0; g < 4; g = g + 1) begin : gk
    localparam integer K = (g == 0) ? 32 : (g == 1) ? 64 : (g == 2) ? 128 : 256;
    localparam integer R = (g == 0) ? 7 : (g == 1) ? 8 : (g == 2) ? 9 : 10;
    reg [K-1:0] din; wire [K+R-1:0] cw; reg [K+R-1:0] flip; reg v = 0;
    wire ov, ce, ue; wire [K-1:0] dout; wire [31:0] nce, nue;
    ot_secded_enc #(.K(K), .R(R), .MUT(MUT)) u_e (.clk(clk), .d(din), .q(cw));
    ot_secded_dec #(.K(K), .R(R)) u_d (.clk(clk), .rst_n(rst_n), .v(v), .w(cw ^ flip), .ov(ov), .d(dout), .ce(ce), .ue(ue),
      .n_ce(nce), .n_ue(nue));
    task automatic one(input [K-1:0] x, input integer a, input integer b);   // a, b: bit to flip or -1
      begin
        @(negedge clk); din = x; flip = 0; v = 0;
        @(negedge clk); if (a >= 0) flip[a] = 1'b1; if (b >= 0) flip[b] = 1'b1; v = 1;
        @(negedge clk); v = 0;
        @(negedge clk);
        if (a < 0) note(!(ov && !ce && !ue && dout == x));
        else if (b < 0) note(!(ov && ce && !ue && dout == x));
        else note(!(ov && ue && !ce));
      end
    endtask
    integer i, j, t;
    reg [K-1:0] x;
    initial begin
      flip = 0; din = 0;
      @(posedge rst_n);
      for (t = 0; t < 6; t = t + 1) begin
        x = {8{$urandom}};
        one(x, -1, -1);
        for (i = 0; i < K + R; i = i + 1) one(x, i, -1);
        for (i = 0; i < 64; i = i + 1) begin j = $urandom % (K + R); one(x, i % (K + R), (i % (K + R) == j) ? (j + 1) % (K + R) : j); end
      end
      if (K == 32) for (t = 0; t < 2; t = t + 1) begin
        x = $urandom;
        for (i = 0; i < K + R; i = i + 1) for (j = i + 1; j < K + R; j = j + 1) one(x, i, j);
      end
      done[g] = 1'b1;
    end
  end endgenerate
  reg [3:0] done = 0;
  initial begin
    repeat (3) @(posedge clk); rst_n = 1;
    wait (done == 4'hf);
    $display("SECDED_BENCH checks=%0d errors=%0d %s", nchk, err, err ? "FAIL" : "PASS");
    $finish;
  end
endmodule
