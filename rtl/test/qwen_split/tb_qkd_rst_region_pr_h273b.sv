`timescale 1ns/1ps
// KV-BIND4 10-19: qkd_rst_region_pr_h273b (dedicated pin register) against qkd_rst_region_pr_h273 (CLOSED, HOLD 273)
// and the CLOSED qkd_rst_region_pr (HOLD 128): (1) identical output to h273 on EVERY cycle of the whole run (POR,
// release, re-assert, hold, re-release) and identical to _pr through the first release (calendar unchanged);
// (2) a one-cycle host re-assert holds the region low >= 273 and <= 277 edges.
// MUT 4 (legacy hold truncation) -> H273B_HOLD_SHORT; MUT 5 (pin twin one edge late) -> H273B_MISMATCH.
module tb_qkd_rst_region_pr_h273b;
  parameter integer MUT = 0;
  reg ck = 0; always #0.5 ck = ~ck;
  reg por_n = 0, host = 0;
  reg [2:0] ch = 3'b111;
  always @(posedge ck) ch <= {ch[1:0], host};
  wire bn, bh, br;
  qkd_rst_region_pr_h273b #(.MUT(MUT)) dut (.ck(ck), .por_n(por_n), .a(ch[2]), .dly(8'd5), .b(bn));
  qkd_rst_region_pr_h273 ref1 (.ck(ck), .por_n(por_n), .a(ch[2]), .dly(8'd5), .b(bh));
  qkd_rst_region_pr #(.IGNORE(255), .HOLD(128)) ref0 (.ck(ck), .por_n(por_n), .a(ch[2]), .dly(8'd5), .b(br));
  integer cyc = 0, errs = 0, mm = 0, fall = -1, rise = -1, phase = 0; reg bq = 0;
  always @(posedge ck) cyc <= cyc + 1;
  always @(negedge ck) begin
    if (bn !== bh) begin mm = mm + 1; if (mm < 5) $display("H273B_MISMATCH cyc %0d h273b %b h273 %b", cyc, bn, bh); end
    if (phase == 0 && bn !== br) begin errs = errs + 1; if (errs < 5) $display("H273B_CALENDAR_MISMATCH cyc %0d %b ref %b", cyc, bn, br); end
    if (phase == 1 && !bn && bq && fall < 0) fall = cyc;
    if (phase == 1 && bn && !bq && fall >= 0 && rise < 0) rise = cyc;
    bq = bn;
  end
  initial begin
    repeat (4) @(negedge ck); por_n = 1;
    repeat (300) @(negedge ck);
    host = 1;
    repeat (40) @(negedge ck);
    if (!bn) begin errs = errs + 1; $display("H273B_NOT_RELEASED"); end
    phase = 1; host = 0; @(negedge ck); host = 1;
    repeat (330) @(negedge ck);
    if (fall < 0 || rise < 0) begin errs = errs + 1; $display("H273B_NO_REASSERT fall %0d rise %0d", fall, rise); end
    else if (rise - fall < 273) begin errs = errs + 1; $display("H273B_HOLD_SHORT held %0d < 273", rise - fall); end
    else if (rise - fall > 277) begin errs = errs + 1; $display("H273B_HOLD_LONG held %0d > 277", rise - fall); end
    errs = errs + mm;
    if (errs) begin $display("H273B_FAIL errors=%0d mismatches=%0d", errs, mm); $fatal(1); end
    $display("H273B_PASS identical to h273 on %0d cycles; calendar = HOLD128 ref to release; re-assert held %0d edges", cyc, rise - fall);
    $finish;
  end
endmodule
