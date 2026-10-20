`timescale 1ns/1ps
// KV-HEALTH 10-19: qkd_hp_or2 -- q == a | b one edge later, every input pair, 4000 random cycles.
// MUT 1 (b dropped) must FAIL: HP_OR2_MISMATCH.
module tb_qkd_hp_or2;
  parameter integer MUT = 0;
  reg ck = 0; always #0.5 ck = ~ck;
  reg a = 0, b = 0, exp_q = 0; reg have = 0;
  wire q;
  qkd_hp_or2 #(.MUT(MUT)) dut (.ck(ck), .a(a), .b(b), .q(q));
  integer i, errs = 0, seen = 0;
  initial begin
    for (i = 0; i < 4000; i = i + 1) begin
      @(negedge ck);
      if (have && q !== exp_q) begin errs = errs + 1; if (errs < 5) $display("HP_OR2_MISMATCH cyc %0d a|b=%b q=%b", i, exp_q, q); end
      a = (i < 4) ? i[0] : $urandom; b = (i < 4) ? i[1] : $urandom; exp_q = a | b; have = 1;
      seen = seen | (1 << {a, b});
    end
    if (seen != 15) begin errs = errs + 1; $display("HP_OR2_COVERAGE %b", seen[3:0]); end
    if (errs) begin $display("HP_OR2_FAIL errors=%0d", errs); $fatal(1); end
    $display("HP_OR2_PASS 4000 cycles all four input pairs");
    $finish;
  end
endmodule
