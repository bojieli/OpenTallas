`timescale 1ns/1ps
// emb-hbm 2026-10-08: with its static port idle, qfd_ctrl_emb (ot_qwen_ctrl_pc_emb, scheduler ot_hbm_r14_stream_pc_srow
// SROW = 1) must be cycle-identical to the closed qfd_ctrl_ready_hbm master (ot_qwen_ctrl_pc_head, scheduler
// ot_hbm_r14_stream_pc_ready READY_CUT = 1) on KV traffic: descriptors, go, writes, read-credit backpressure.
// Every output is compared every cycle; the ready-cut eligibility invariant is checked on the new scheduler.
// NEG = 1: one write's column is perturbed on the emb side only (the bench must FAIL).
module tb_ctrl_pc_emb_equiv;
 parameter integer PC = 0, NEG = 0, SEED = 7;
 reg clk = 0; always #5 clk = ~clk;
 reg rst_n = 0, cmd_v = 0; reg [31:0] cmd = 0; reg [2:0] read_credit = 0;
 wire a_cr, a_rv, a_cv, a_we, a_busy, a_f; wire [2:0] a_op; wire [4:0] a_rb, a_cb, a_cc; wire [18:0] a_rr;
 wire b_cr, b_rv, b_cv, b_we, b_busy, b_f, b_scr, b_sr; wire [2:0] b_op; wire [4:0] b_rb, b_cb, b_cc; wire [18:0] b_rr;
 reg [31:0] cmd_b;
 always @* cmd_b = (NEG && cmd[31:30] == 2'b10 && cmd[9:5] == 5'd3) ? (cmd ^ 32'h20) : cmd;
 ot_qwen_ctrl_pc_head #(.ENABLE(1), .PC(PC)) A (.clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd(cmd), .read_credit(read_credit),
  .cmd_credit(a_cr), .row_v(a_rv), .row_op(a_op), .row_bank(a_rb), .row_row(a_rr), .col_v(a_cv), .col_bank(a_cb),
  .col_col(a_cc), .col_we(a_we), .busy(a_busy), .fault(a_f));
 ot_qwen_ctrl_pc_emb #(.ENABLE(1), .PC(PC)) B (.clk(clk), .rst_n(rst_n), .cmd_v(cmd_v), .cmd(cmd_b), .read_credit(read_credit),
  .cmd_credit(b_cr), .row_v(b_rv), .row_op(b_op), .row_bank(b_rb), .row_row(b_rr), .col_v(b_cv), .col_bank(b_cb),
  .col_col(b_cc), .col_we(b_we), .busy(b_busy), .fault(b_f), .s_v(1'b0), .s_we(1'b0), .s_bank(5'd0), .s_col(5'd0),
  .s_row(19'd0), .s_cr(b_scr), .col_sr(b_sr));
 integer cycles = 0, reads = 0, writes = 0, rows = 0, sent = 0, acked = 0, pend = 0, ret, bad = 0, seed;
 always @(negedge clk) if (rst_n) begin
  cycles = cycles + 1;
  if (B.core.on.write_ready_bank !== (B.core.on.open & ~B.core.on.stale & B.core.on.rcdw_z & ~B.core.on.blk)) begin
   bad = bad + 1; if (bad < 4) $display("eligibility invariant cycle %0d", cycles); end
  if ({a_cr, a_rv, a_cv, a_busy, a_f} !== {b_cr, b_rv, b_cv, b_busy, b_f} || b_scr || b_sr ||
      (a_rv && {a_op, a_rb, a_rr} !== {b_op, b_rb, b_rr}) || (a_cv && {a_we, a_cb, a_cc} !== {b_we, b_cb, b_cc})) begin
   bad = bad + 1; if (bad < 4) $display("MISMATCH cycle %0d", cycles); end
  if (a_rv) rows = rows + 1;
  if (a_cv) begin if (a_we) writes = writes + 1; else begin reads = reads + 1; pend = pend + 1; end end
  ret = (($random(seed) & 7) == 0) ? ((pend > 7) ? 7 : pend) : 0;
  read_credit = 3'(ret); pend = pend - ret;
  if (a_cr) acked = acked + 1;
 end
 task send(input [31:0] p);
  begin
   @(negedge clk); cmd_v = 0;
   while (sent - acked >= 8) @(negedge clk);
   cmd = p; cmd_v = 1; sent = sent + 1;
   @(negedge clk); cmd_v = 0;
  end
 endtask
 integer x, layer;
 initial begin
  seed = SEED;
  repeat (4) @(negedge clk); rst_n = 1;
  for (layer = 0; layer < 6; layer = layer + 1) begin
   send({2'b00, 11'd1024 - 11'(($random(seed) & 255)), 19'(3 + layer)});
   if (layer % 2) repeat (($random(seed) & 255)) @(negedge clk);
   send({2'b01, 30'd0});
   for (x = 0; x < 12; x = x + 1) begin
    repeat (($random(seed) & 31)) @(negedge clk);
    send({2'b10, 20'd0, 5'($random(seed)), 5'($random(seed))});
   end
   while (a_busy || sent != acked) @(negedge clk);
   repeat (($random(seed) & 511)) @(negedge clk);
  end
  repeat (400) @(negedge clk);
  if (bad == 0 && !a_f && reads > 0 && writes == 72)
   $display("PASS ctrl_pc_emb_equiv PC=%0d cycles=%0d reads=%0d writes=%0d rows=%0d", PC, cycles, reads, writes, rows);
  else $display("FAIL ctrl_pc_emb_equiv PC=%0d mismatches=%0d reads=%0d writes=%0d fault=%0d", PC, bad, reads, writes, a_f);
  $finish;
 end
 initial begin #50000000; $display("FAIL ctrl_pc_emb_equiv watchdog"); $finish; end
endmodule
