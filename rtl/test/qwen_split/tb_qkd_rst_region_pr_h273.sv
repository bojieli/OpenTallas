`timescale 1ns/1ps
// KV-HEALTH 10-19: qkd_rst_region_pr_h273 (HOLD 273) against the closed qkd_rst_region_pr (HOLD 128) reference.
//  (1) POR + first host release: identical output every cycle (same straps dly 5 / chain depth 3), i.e. the release
//      calendar is unchanged;
//  (2) after a one-cycle host re-assert the h273 root stays low for >= 273 and <= 277 edges (the reference: ~128).
// MUT 4 (legacy 8-bit truncation: HOLD 273 loads 16) must FAIL: H273_HOLD_SHORT.
module tb_qkd_rst_region_pr_h273;
  parameter integer MUT = 0;
  reg ck = 0; always #0.5 ck = ~ck;
  reg por_n = 0, host = 0;
  reg [2:0] ch = 3'b111;                                  // unflushed released value in the reset-less chain
  always @(posedge ck) ch <= {ch[1:0], host};
  wire bh, br;
  qkd_rst_region_pr_h273 #(.MUT(MUT)) dut (.ck(ck), .por_n(por_n), .a(ch[2]), .dly(8'd5), .b(bh));
  qkd_rst_region_pr #(.IGNORE(255), .HOLD(128)) ref0 (.ck(ck), .por_n(por_n), .a(ch[2]), .dly(8'd5), .b(br));
  integer cyc = 0, errs = 0, fall = -1, rise = -1, phase = 0; reg bq = 0;
  always @(posedge ck) cyc <= cyc + 1;
  always @(negedge ck) begin
    if (phase == 0 && bh !== br) begin errs = errs + 1; if (errs < 5) $display("H273_CALENDAR_MISMATCH cyc %0d h273 %b ref %b", cyc, bh, br); end
    if (phase == 1 && !bh && bq && fall < 0) fall = cyc;
    if (phase == 1 && bh && !bq && fall >= 0 && rise < 0) rise = cyc;
    bq = bh;
  end
  initial begin
    repeat (4) @(negedge ck); por_n = 1;
    repeat (300) @(negedge ck);
    host = 1;
    repeat (40) @(negedge ck);
    if (!bh) begin errs = errs + 1; $display("H273_NOT_RELEASED"); end
    phase = 1; host = 0; @(negedge ck); host = 1;
    repeat (330) @(negedge ck);
    if (fall < 0 || rise < 0) begin errs = errs + 1; $display("H273_NO_REASSERT fall %0d rise %0d", fall, rise); end
    else if (rise - fall < 273) begin errs = errs + 1; $display("H273_HOLD_SHORT held %0d < 273", rise - fall); end
    else if (rise - fall > 277) begin errs = errs + 1; $display("H273_HOLD_LONG held %0d > 277", rise - fall); end
    if (errs) begin $display("H273_FAIL errors=%0d", errs); $fatal(1); end
    $display("H273_PASS calendar identical to HOLD128 reference; re-assert held %0d edges (>= 273)", rise - fall);
    $finish;
  end
endmodule
