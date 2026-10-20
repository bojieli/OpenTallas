`timescale 1ns/1ps
// KV-RETIRE 10-19: counter-width bench for qkd_rst_region at depths beyond the old 8/9-bit counters
// (codex/kv-fault-reset-1019 proposed a 273-edge final-sticky reset depth; the old hold counter wrapped HOLD 273 -> 16,
// and an IGNORE above 511 never went live).  Two roots, HOLD 273, IGNORE 600, DW 9:
//   A: a 580-deep reset-less relay chain with RANDOM power-up contents, strap dly 300 (needs 9 bits):
//      (1) low from POR through the ignore window although the chain holds random ones;
//      (2) releases EXACTLY at host release + 580 + 300 + 2;
//   B: a 2-deep chain, dly 0: after a ONE-cycle host re-assert the root stays low for >= HOLD (273) and releases no later
//      than HOLD + 4 edges after it fell.
// MUT 4 (legacy 8-bit hold / 9-bit ignore truncation) must fail: B low only ~17 edges, A never live.
module tb_qkd_rst_region_wide;
  parameter integer MUT = 0;
  localparam integer HOLD = 273, IGN = 600, DA = 580, DLYA = 300, DB = 2;
  reg ck = 0; always #0.5 ck = ~ck;
  reg por_n = 0, host = 0;
  reg [DA-1:0] cha; reg [DB-1:0] chb;
  wire ra, rb;
  qkd_rst_region #(.IGNORE(IGN), .HOLD(HOLD), .MUT(MUT), .DW(9)) u_a (.ck(ck), .por_n(por_n), .a(cha[DA-1]), .dly(9'(DLYA)), .b(ra));
  qkd_rst_region #(.IGNORE(IGN), .HOLD(HOLD), .MUT(MUT), .DW(9)) u_b (.ck(ck), .por_n(por_n), .a(chb[DB-1]), .dly(9'd0), .b(rb));
  integer i, cyc = 0, errs = 0, t_rel = -1, ra_rise = -1, rb_fall = -1, rb_rise2 = -1, ones = 0;
  initial begin
    for (i = 0; i < DA; i = i + 1) cha[i] = $urandom;
    for (i = 0; i < DA; i = i + 1) ones = ones + cha[i];
    chb = 2'b11;                                    // worst case: an unflushed released value
  end
  always @(posedge ck) begin cha <= {cha[DA-2:0], host}; chb <= {chb[DB-2:0], host}; cyc <= cyc + 1; end
  reg ra_q = 0, rb_q = 0;
  always @(negedge ck) begin
    if (t_rel < 0 && (ra || rb)) begin errs = errs + 1; if (errs < 10) $display("ERR release before host release cyc %0d", cyc); end
    if (ra && !ra_q && ra_rise < 0) ra_rise = cyc;
    if (!rb && rb_q && t_rel >= 0 && rb_fall < 0) rb_fall = cyc;
    if (rb && !rb_q && rb_fall >= 0 && rb_rise2 < 0) rb_rise2 = cyc;
    ra_q = ra; rb_q = rb;
  end
  initial begin
    repeat (5) @(negedge ck); por_n = 1;
    repeat (IGN + 40) @(negedge ck);                // host holds reset past the ignore window
    host = 1; t_rel = cyc;
    repeat (DA + DLYA + 40) @(negedge ck);
    if (ra_rise != t_rel + DA + DLYA + 2) begin
      errs = errs + 1; $display("ERR A release at %0d, calendar %0d", ra_rise, t_rel + DA + DLYA + 2); end
    if (!rb) begin errs = errs + 1; $display("ERR B not released"); end
    host = 0; @(negedge ck); host = 1;               // one-cycle host re-assert
    repeat (HOLD + 60) @(negedge ck);
    if (rb_fall < 0 || rb_rise2 < 0) begin errs = errs + 1; $display("ERR B re-assert fall %0d rise %0d", rb_fall, rb_rise2); end
    else if (rb_rise2 - rb_fall < HOLD || rb_rise2 - rb_fall > HOLD + 4) begin
      errs = errs + 1; $display("ERR B held low %0d edges, HOLD %0d (wrapped counter?)", rb_rise2 - rb_fall, HOLD); end
    if (errs) begin $display("RST_REGION_WIDE_FAIL errors=%0d", errs); $fatal(1); end
    $display("RST_REGION_WIDE_PASS HOLD=%0d held=%0d IGNORE=%0d chain=%0d(random ones %0d) dly=%0d release=+%0d exact",
             HOLD, rb_rise2 - rb_fall, IGN, DA, ones, DLYA, ra_rise - t_rel);
    $finish;
  end
endmodule
