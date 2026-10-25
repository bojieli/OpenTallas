`timescale 1ns/1ps
`default_nettype none
// HBM-BIND B2 (lane hbm-bind-idx 2026-10-24): ot_hbm_idx_selector_static_sel NL (number of 16-lane lists) bench.
// REF = the UNCHANGED as-built r18h5 master (source d34578d6f, renamed ot_hbm_idx_selector_static_sel_ref, 4 lists).
// DUT = ot_hbm_idx_selector_static_sel #(.NL(NL), .MUT(SMUT)). DUT list j is REF list j+OFF; the REF lists not mapped
// are fed 0 (exactly as the r18h5 die feeds its lists 2, 3; OFF 1 at NL 1 = the as-built position of {NE, NW} = list 1
// with list 0 empty). Checked EVERY edge: DUT selected_v[j] / selected_line list j == REF list j+OFF, fault == fault,
// and no unmapped REF list's selected_line lane valid bit is ever 1 (sanity of the reference; the random phase reads
// never-written SRAM rows, whose X propagates identically in REF and DUT and is not counted as a 1).
// Stimulus: NRUN production op streams (tools/hbm_idx_static_calendar.py shape, as tb_hbm_idx_selector_sel_eq: op1,
// op3, 171 x op2 ingest, op5 31..0, passes 1 / 2 op3 + 171 x op4 + op5, 171 x op6 compact) with random k (odd runs:
// keys from 97 values, so the threshold bin has many equal keys and the tie budget decides), then 4,000
// random legal ops (0..7). PASS needs 0 mismatches and selected beats > 0.
module tb_idx_selector_nl #(parameter integer NL = 1, parameter integer OFF = 0, parameter integer SMUT = 0,
    parameter integer NRUN = 4, parameter integer SEED = 11);
 reg clk = 0, rst_n = 0; always #1 clk = ~clk;
 reg [3:0] op = 0; reg [1:0] pass = 0; reg [7:0] addr = 0; reg [9:0] k = 0;
 reg [NL*592-1:0] in_d = 0; wire [2367:0] in_r;
 genvar g;
 for (g = 0; g < 4; g = g + 1) begin : g_map
  if (g >= OFF && g < OFF + NL) begin : g_on assign in_r[g*592 +: 592] = in_d[(g-OFF)*592 +: 592]; end
  else begin : g_off assign in_r[g*592 +: 592] = 592'd0; end
 end
 wire [3:0] rsv; wire [2367:0] rsl; wire rf; wire [NL-1:0] nsv; wire [NL*592-1:0] nsl; wire nf;
 ot_hbm_idx_selector_static_sel_ref ref_u(.clk_ctl(clk), .clk_q({4{clk}}), .clk_mem({12{clk}}), .rst_n(rst_n), .op(op),
  .pass(pass), .addr(addr), .k(k), .in_line(in_r), .selected_v(rsv), .selected_line(rsl), .fault(rf));
 ot_hbm_idx_selector_static_sel #(.MUT(SMUT), .NL(NL)) dut(.clk_ctl(clk), .clk_q({NL{clk}}), .clk_mem({(3*NL){clk}}),
  .rst_n(rst_n), .op(op), .pass(pass), .addr(addr), .k(k), .in_line(in_d), .selected_v(nsv), .selected_line(nsl), .fault(nf));
 reg lowkey = 0;   // odd production runs draw keys from 97 values: many keys equal the threshold (tie path)
 integer chk = 0, mism = 0, selbeats = 0, chosen = 0, seed = SEED, nflt = 0;
 always @(posedge clk) if (rst_n) begin
  chk = chk + 1;
  for (integer q = 0; q < 4; q = q + 1) begin
   if (q >= OFF && q < OFF + NL) begin
    if (rsv[q] !== nsv[q-OFF] || rsl[q*592 +: 592] !== nsl[(q-OFF)*592 +: 592]) begin
     mism = mism + 1; if (mism < 5) $display("MISMATCH t=%0t list %0d sv %b/%b line_eq %b", $time, q, rsv[q], nsv[q-OFF], rsl[q*592 +: 592] === nsl[(q-OFF)*592 +: 592]);
    end
    for (integer l = 0; l < 16; l = l + 1) if (rsl[q*592 + l*37]) chosen = chosen + 1;
   end else for (integer l = 0; l < 16; l = l + 1) if (rsl[q*592 + l*37] === 1'b1) begin   // (X = an unwritten SRAM row read)
    mism = mism + 1; if (mism < 5) $display("REF_UNMAPPED_LIST_NONZERO t=%0t list %0d", $time, q);
   end
  end
  if (rf !== nf) begin mism = mism + 1; if (mism < 5) $display("MISMATCH t=%0t fault %b/%b", $time, rf, nf); end
  if (rf) nflt = nflt + 1;
  if (|nsv) selbeats = selbeats + 1;
 end
 task automatic tick(input [3:0] o, input [1:0] p, input [7:0] a); begin op <= o; pass <= p; addr <= a; @(posedge clk); end endtask
 task automatic idle(input integer n, input [1:0] p); for (integer i = 0; i < n; i = i + 1) tick(0, p, 0); endtask
 task automatic line(input integer a); begin
  for (integer q = 0; q < NL; q = q + 1) for (integer l = 0; l < 16; l = l + 1)
   in_d[q*592 + l*37 +: 37] = {20'(a*16 + l), lowkey ? 16'($unsigned($random(seed)) % 97) : 16'($random(seed)), 1'($random(seed) % 5 != 0)};
 end endtask
 task automatic production(input [9:0] kk); begin
  k <= kk; tick(1, 0, 0); idle(16, 0); idle(128 + 28 + 100, 0);
  tick(3, 0, 0);
  for (integer i = 0; i < 294; i = i + 1) begin
   if (i >= 123) begin line(i - 123); tick(2, 0, 8'(i - 123)); end else tick(0, 0, 0);
  end
  idle(2, 0); for (integer b = 31; b >= 0; b = b - 1) tick(5, 0, 8'(b)); idle(1, 0);
  for (integer ps = 1; ps <= 2; ps = ps + 1) begin
   tick(3, 2'(ps), 0); for (integer a = 0; a < 171; a = a + 1) tick(4, 2'(ps), 8'(a)); idle(2, 2'(ps));
   for (integer b = (ps == 2 ? 63 : 31); b >= 0; b = b - 1) tick(5, 2'(ps), 8'(b)); idle(1, 0);
  end
  for (integer a = 0; a < 171; a = a + 1) tick(6, 2, 8'(a)); idle(3, 0); idle(1 + 16*8 + 4, 0);
 end endtask
 integer kk;
 initial begin
  idle(4, 0); rst_n = 1; idle(4, 0);
  for (integer r = 0; r < NRUN; r = r + 1) begin
   // k within the lists' capacity (NL*16 lanes x 171 lines, ~80 % valid) so the production stream itself stays legal
   lowkey = r % 2; kk = 1 + ($unsigned($random(seed)) % 512); production(10'(kk));
  end
  lowkey = 0;
  for (integer i = 0; i < 4000; i = i + 1) begin
   line($unsigned($random(seed)) % 256); k <= 10'($unsigned($random(seed)) % 600);
   tick(4'($unsigned($random(seed)) % 8), 2'($unsigned($random(seed)) % 3), 8'($random(seed)));
  end
  idle(8, 0);
  $display("IDX_SELECTOR_NL NL=%0d OFF=%0d SMUT=%0d checks=%0d selected_beats=%0d chosen_records=%0d ref_fault_edges=%0d mismatches=%0d",
   NL, OFF, SMUT, chk, selbeats, chosen, nflt, mism);
  $display("IDX_SELECTOR_NL %s checks=%0d errors=%0d", (mism == 0 && selbeats > 0) ? "PASS" : "FAIL", chk, mism);
  $finish;
 end
endmodule
`default_nettype wire
