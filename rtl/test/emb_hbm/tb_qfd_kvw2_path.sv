`timescale 1ns/1ps
// sys-takeover 2026-10-09: KV write ECC path at the die's real write timing (KVW = 2).
//   KV landing (core clk 833 ps) posts writes {sec24, data256, tag} into the real per-PC STREAM4 CDC
//   (ot_qwen_stream4_cdc_pc) -> HCLK (1,024 ps) write-queue head h_wv / h_wsec -> a behavioural scheduler hands it
//   off (h_hand) and issues the WR column 2..6 edges later (h_wcon = col_v && col_we && !col_sr), random gaps;
//   static (embedding boot) writes are interleaved on the same pcport (col_sr) -> CDC completion h_cv / h_cdata one
//   edge after the column -> ot_qfd_emb_pcport KVW 2 kw_v / kw_d -> wd (288 b, side-band encoded) sampled by the
//   behavioural HBM PC two edges after the column -> KV reads return the stored 288-b word through kv_d into
//   ot_qfd_kv_landing_ecc (exact compare); a single-bit upset per word lane is corrected, a double-bit upset is
//   quarantined.  Write-done (h_av) returns the tag; every core write must be acknowledged.
// MUT (pcport) 4 / 5: wrong check column / side-band dropped -> FAIL.  LATE = 1: the bench sends KV data two edges
// after the column (the KVW 1 / KVW 2 contract break) -> the port must fault -> FAIL.
module tb_qfd_kvw2_path;
 parameter integer MUT = 0, LATE = 0, KVWM = 2;   // KVWM 1: the closed KVW 1 port at this timing (must fault)
 reg clk = 0, hclk = 0;
 always #0.416667 clk = ~clk;
 initial begin #0.2; forever #0.512 hclk = ~hclk; end
 reg rst_n = 0;
 // ---- core side (landing) ----
 reg w_v = 0; reg [23:0] w_sec = 0; reg [255:0] w_data = 0; reg [8:0] w_tag = 0;
 wire w_room, wd_v, c_fault; wire [8:0] wd_tag;
 // ---- HCLK side ----
 wire h_wv, h_cv, h_fault; wire [23:0] h_wsec, h_csec; wire [255:0] h_cdata; wire [8:0] h_ctag; wire [2:0] h_cred;
 reg h_hand = 0, h_av = 0; reg [8:0] h_atag = 0;
 reg col_v = 0, col_we = 0, col_sr = 0, sw_v = 0; reg [255:0] sw_d = 0;
 wire h_wcon = col_v && col_we && !col_sr;
 wire l_v; wire [16:0] l_sec; wire [7:0] l_row; wire [255:0] l_data;
 ot_qwen_stream4_cdc_pc #(.TAGW(9)) cdc(.clk(clk), .c_arst_n(rst_n), .l_v(l_v), .l_sec(l_sec), .l_row(l_row), .l_data(l_data),
  .l_pop(1'b0), .w_v(w_v), .w_sec(w_sec), .w_data(w_data), .w_tag(w_tag), .w_room(w_room), .wd_v(wd_v), .wd_tag(wd_tag),
  .c_fault(c_fault), .hclk(hclk), .h_arst_n(rst_n), .h_lv(1'b0), .h_lsec(17'd0), .h_lrow(8'd0), .h_ldata(256'd0),
  .h_cred(h_cred), .h_wv(h_wv), .h_wsec(h_wsec), .h_hand(h_hand), .h_wcon(h_wcon), .h_cv(h_cv), .h_csec(h_csec),
  .h_cdata(h_cdata), .h_ctag(h_ctag), .h_av(h_av), .h_atag(h_atag), .h_fault(h_fault));
 // KV data to the port: the completion entry (LATE: one more edge)
 reg late_v = 0; reg [255:0] late_d = 0;
 always @(posedge hclk) begin late_v <= h_cv; late_d <= h_cdata; end
 wire kw_v = LATE ? late_v : h_cv; wire [255:0] kw_d = LATE ? late_d : h_cdata;
 reg r_v = 0; reg [287:0] r_d = 0;
 wire [287:0] wd, kv_d; wire kv_v, em_v, pfault; wire [257:0] em_d;
 ot_qfd_emb_pcport #(.KVW(KVWM), .MUT(MUT)) port(.clk(hclk), .rst_n(rst_n), .col_v(col_v), .col_we(col_we), .col_sr(col_sr),
  .w_v(sw_v), .w_d(sw_d), .wd(wd), .kw_v(kw_v), .kw_d(kw_d), .r_v(r_v), .r_d(r_d), .kv_v(kv_v), .kv_d(kv_d),
  .em_v(em_v), .em_d(em_d), .fault(pfault));
 wire o_v, ce, ue, lfault; wire [255:0] o_data; wire [16:0] o_sec; wire [7:0] o_row; wire [31:0] ce_count;
 ot_qfd_kv_landing_ecc #(.ENABLE(1)) land(.hclk(hclk), .h_rst_n(rst_n), .i_v(kv_v), .i_code(kv_d), .i_sec(17'd0), .i_row(8'd0),
  .o_v(o_v), .o_data(o_data), .o_sec(o_sec), .o_row(o_row), .ce(ce), .ue(ue), .fault(lfault), .ce_count(ce_count));
 // ---- behavioural HBM PC: 288-b words; the PHY samples wd two edges after each WR column ----
 localparam integer N = 96;               // KV writes (sectors 0..N-1)
 reg [287:0] mem [0:4095];
 reg [255:0] gold [0:N-1];
 reg [287:0] sgold;                       // the static word (embedding boot), sector 4000
 reg [11:0] wa1, wa2; reg wv1 = 0, wv2 = 0;
 reg [11:0] pend_sec [0:63]; integer ph = 0, pt = 0, issued = 0;   // handed-off KV writes awaiting their column
 always @(posedge hclk) begin
  wv2 <= wv1; wa2 <= wa1;
  wv1 <= col_v && col_we; wa1 <= col_sr ? 12'd4000 : pend_sec[ph % 64];
  if (col_v && col_we && !col_sr) begin ph = ph + 1; issued = issued + 1; end
  if (wv2) mem[wa2] <= wd;
 end
 function [255:0] pat(input integer k); integer j; begin for (j = 0; j < 8; j = j + 1) pat[j*32 +: 32] = (32'h9e3779b9 * (k*8 + j + 1)) ^ (k << j); end endfunction
 // ---- core: post N KV writes, back-to-back while w_room ----
 integer sent = 0, acked = 0;
 always @(posedge clk) begin
  w_v <= 1'b0;
  if (rst_n && sent < N && w_room && !w_v && sent - acked < 8) begin
   w_v <= 1'b1; w_sec <= 24'(sent); w_data <= pat(sent); w_tag <= 9'(sent); gold[sent] = pat(sent); sent = sent + 1;
  end
  if (wd_v) acked = acked + 1;
 end
 // ---- HCLK scheduler: hand off the head, issue its WR column 2..6 edges later; static WR interleaved ----
 reg [31:0] rnd = 32'h1234567;
 integer handed = 0, wait_n = 0, nstat = 0;
 reg in_col = 0; reg sched_on = 1;
 always @(negedge hclk) if (rst_n && sched_on) begin
  rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
  h_hand <= 1'b0; col_v <= 1'b0; col_we <= 1'b0; col_sr <= 1'b0; sw_v <= 1'b0; h_av <= 1'b0;
  if (h_cv) begin h_av <= 1'b1; h_atag <= h_ctag; end                  // write done (tag back to the core)
  if (h_wv && !h_hand && handed - issued < 4 && rnd[3:0] != 0) begin  // hand-off (WQ 4)
   h_hand <= 1'b1; pend_sec[handed % 64] = h_wsec[11:0]; handed = handed + 1;
  end
  if (wait_n > 0) wait_n = wait_n - 1;
  else if (handed > issued) begin
   col_v <= 1'b1; col_we <= 1'b1; col_sr <= 1'b0; wait_n = 2 + rnd[6:4] % 5;
  end else if (nstat < 3 && rnd[9:8] == 0) begin                       // a static (embedding) write: data, then its WR
   sw_v <= 1'b1; sw_d <= pat(1000 + nstat); sgold = pat(1000 + nstat); nstat = nstat + 1; wait_n = 1;
   @(negedge hclk); sw_v <= 1'b0; col_v <= 1'b1; col_we <= 1'b1; col_sr <= 1'b1; wait_n = 3;
  end
 end
 // ---- reads ----
 integer got = 0, nce = 0, nue = 0; integer qd [0:1023]; integer qh = 0, qt = 0;
 always @(posedge hclk) begin
  if (o_v) begin
   if (o_data !== gold[qd[qh]]) begin $display("FATAL KV data mismatch sector %0d", qd[qh]); $fatal(1); end
   qh = qh + 1; got = got + 1;
  end
  if (ce) nce = nce + 1;
  if (ue) nue = nue + 1;
 end
 task rd(input integer k, input [287:0] f); begin
  @(negedge hclk); col_v = 1; col_we = 0; col_sr = 0; qd[qt] = k; qt = qt + 1;
  @(negedge hclk); col_v = 0;
  repeat (3) @(negedge hclk);
  r_v = 1; r_d = mem[k] ^ f;
  @(negedge hclk); r_v = 0;
 end endtask
 integer i, w, b, exp_ce;
 initial begin
  repeat (6) @(negedge hclk); rst_n = 1;
  wait (acked == N);
  repeat (12) @(negedge hclk); sched_on = 0; @(negedge hclk); col_v = 0; col_we = 0; col_sr = 0; h_hand = 0; h_av = 0; sw_v = 0;
  if (pfault || c_fault || h_fault) begin $display("FATAL write phase fault port=%0d c=%0d h=%0d", pfault, c_fault, h_fault); $fatal(1); end
  if (mem[4000] !== ot_qfd_emb_pkg::enc256(sgold)) begin $display("FATAL static write word"); $fatal(1); end
  $display("PASS write: %0d KV writes through the STREAM4 CDC (column-then-data), %0d static writes interleaved, all acked", N, nstat);
  for (i = 0; i < N; i = i + 1) rd(i, 288'd0);
  repeat (8) @(negedge hclk);
  if (got != N || nce != 0 || nue != 0) begin $display("FATAL clean read got=%0d ce=%0d ue=%0d", got, nce, nue); $fatal(1); end
  $display("PASS read: %0d KV words read back exact through the landing ECC, 0 CE", N);
  exp_ce = 0;
  for (w = 0; w < 4; w = w + 1) for (b = 0; b < 72; b = b + 12) begin rd((w*7 + b) % N, 288'd1 << (w*72 + b)); exp_ce = exp_ce + 1; end
  rd(9, (288'd1 << 5) | (288'd1 << 60));
  repeat (8) @(negedge hclk);
  if (nce != exp_ce || nue != 1 || !lfault || pfault) begin $display("FATAL CE/UE ce=%0d/%0d ue=%0d lfault=%0d", nce, exp_ce, nue, lfault); $fatal(1); end
  $display("PASS ECC: %0d single-bit upsets corrected, double-bit upset quarantined", exp_ce);
  $display("PASS_ALL qfd_kvw2_path");
  $finish;
 end
 always @(posedge hclk) if (rst_n && pfault && got == 0) begin $display("FATAL pcport fault during writes"); $fatal(1); end
 initial begin #400000; $display("FATAL watchdog sent=%0d handed=%0d issued=%0d acked=%0d h_wv=%0d w_room=%0d faults %0d%0d%0d", sent, handed, issued, acked, h_wv, w_room, pfault, c_fault, h_fault); $fatal(1); end
endmodule
