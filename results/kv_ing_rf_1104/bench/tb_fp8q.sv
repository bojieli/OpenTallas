`timescale 1ns/1ps
// DIE-KV-70/ING 11-04: split quantiser against ot_hdc_ingest_fp8q: every BF16 pattern, all 2^26 FP32 with mantissa sweeps at each exponent / sign below.
module tb;
  reg [31:0] f; wire [7:0] g, q; wire [11:0] p;
  ot_hdc_ingest_fp8q u_g (.f(f), .q(g));
  ot_hdc_ingest_fp8q_s1 u_1 (.f(f), .p(p));
  ot_hdc_ingest_fp8q_s2 u_2 (.p(p), .q(q));
  integer i, e, j, bad = 0; longint n = 0; reg [22:0] m;
  task chk; begin #1; n = n + 1; if (g !== q) begin bad = bad + 1; if (bad < 10) $display("DIFF f=%h g=%h q=%h", f, g, q); end end endtask
  initial begin
    for (i = 0; i < 65536; i = i + 1) begin f = {i[15:0], 16'd0}; chk; end
    for (e = 0; e < 256; e = e + 1) begin
      for (j = 0; j < 23; j = j + 1) begin f = {1'b0, e[7:0], 23'd1 << j}; chk; f = {1'b1, e[7:0], ~(23'd1 << j)}; chk;
        f = {1'b0, e[7:0], (23'h7fffff << j) & 23'h7fffff}; chk; f = {1'b0, e[7:0], 23'h7fffff >> j}; chk; end
      for (i = 0; i < 40000; i = i + 1) begin m = $random; if (i % 3 == 0) m = m & (23'h7fffff << (i % 23)); f = {i[0], e[7:0], m}; chk; end
    end
    $display("fp8q vectors=%0d diffs=%0d", n, bad);
    if (bad == 0) $display("PASS"); else $display("FAIL");
    $finish;
  end
endmodule
