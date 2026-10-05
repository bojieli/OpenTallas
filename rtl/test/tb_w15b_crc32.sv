`timescale 1ns/1ps
// W15: ot_link_crc32 (parallel masks, and the serial form above MASK_MAX_W) and ot_link_crc32_pipe (partials
// registered, CHUNK 256) against the serial CRC-32 definition on 200 random frames of W bits (frame 0 all zero).
module tb_w15b_crc32 #(parameter integer W = 2300, parameter integer MASK_MAX_W = 8192);
  reg [W-1:0] d; wire [31:0] c, cp;
  reg clk = 0;
  ot_link_crc32 #(.W(W), .MASK_MAX_W(MASK_MAX_W)) u (.d(d), .crc(c));
  ot_link_crc32_pipe #(.W(W), .MASK_MAX_W(MASK_MAX_W)) up (.clk(clk), .en(1'b1), .d(d), .crc(cp));
  function automatic [31:0] ser(input [W-1:0] x);
    integer b; reg [31:0] q;
    begin q = 32'hFFFFFFFF;
      for (b = W - 1; b >= 0; b = b - 1) q = {q[30:0], 1'b0} ^ ((q[31] ^ x[b]) ? 32'h04C11DB7 : 32'h0);
      ser = q; end
  endfunction
  integer k, bad = 0, badp = 0;
  initial begin
    for (k = 0; k < 200; k = k + 1) begin
      for (integer j = 0; j < W; j = j + 32) d[j +: 32] = $random;
      if (k == 0) d = 0;
      #1; if (c !== ser(d)) bad = bad + 1;
      clk = 1; #1; clk = 0; #1;
      if (cp !== ser(d)) badp = badp + 1;
    end
    $display("CRCCHK W=%0d mask_max=%0d frames=200 bad=%0d pipe_bad=%0d %s", W, MASK_MAX_W, bad, badp,
             (bad == 0 && badp == 0) ? "PASS" : "FAIL");
    $finish;
  end
endmodule
