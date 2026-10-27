// YOSYS-CONCAT 10-26 lockstep: original RTL (module *_orig) vs fixed RTL, same stimulus, every output every cycle.
// Stimulus = legal epochs (begin, 3 issues, 256 FP8 seats in random lane order, 4 word slots) + random noise cycles.
// Define NATIVE for ot_qfd_su_kv_native_posted, else ot_qfd_su_kv_static_posted (LOCAL_CTL via -P).
`timescale 1ns/1ps
module tb;
 parameter integer LOCAL_CTL = 0, MUT_TAG_G = 0, MUT_TAG_T = 0, EPOCHS = 40, SEED = 1;
 reg clk = 0, rst_n = 0;
 reg epoch_begin = 0; reg [17:0] epoch_pos = 0;
 reg issue_v = 0; reg [1:0] issue_kind = 0; reg [17:0] issue_nout = 0, issue_nin = 0;
 reg [63:0] kv_we = 0; reg [1535:0] kv_waddr = 0; reg [2047:0] kv_wdata = 0;
 reg word_slot = 0; reg [1:0] word_index = 0; reg word_ready = 1;
 wire g_idle, g_dr, g_wv, g_f, t_idle, t_dr, t_wv, t_f;
 wire [10:0] g_tag, t_tag; wire [511:0] g_data, t_data; wire [7:0] g_fc, t_fc; wire [39:0] g_pub, t_pub;
`ifdef NATIVE
 ot_qfd_su_kv_native_posted_orig #(.ENABLE(1), .HEADS(1), .MUT_TAG(MUT_TAG_G)) g (.clk(clk), .rst_n(rst_n),
  .epoch_begin(epoch_begin), .epoch_pos(epoch_pos), .issue_v(issue_v), .issue_kind(issue_kind), .issue_nout(issue_nout),
  .issue_nin(issue_nin), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .epoch_ready(g_idle), .drained(g_dr),
  .word_v(g_wv), .word_tag(g_tag), .word_data(g_data), .word_ready(word_ready), .fault(g_f), .fault_code(g_fc));
`ifdef NETLIST
 ot_qfd_su_kv_native_posted_ys t (
`else
 ot_qfd_su_kv_native_posted #(.ENABLE(1), .HEADS(1), .MUT_TAG(MUT_TAG_T)) t (
`endif.clk(clk), .rst_n(rst_n),
  .epoch_begin(epoch_begin), .epoch_pos(epoch_pos), .issue_v(issue_v), .issue_kind(issue_kind), .issue_nout(issue_nout),
  .issue_nin(issue_nin), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .epoch_ready(t_idle), .drained(t_dr),
  .word_v(t_wv), .word_tag(t_tag), .word_data(t_data), .word_ready(word_ready), .fault(t_f), .fault_code(t_fc));
 assign g_pub = 0; assign t_pub = 0;
`else
 ot_qfd_su_kv_static_posted_orig #(.ENABLE(1), .HEADS(1), .LOCAL_CTL(LOCAL_CTL), .MUT_TAG(MUT_TAG_G)) g (.clk(clk),
  .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch_pos(epoch_pos), .issue_v(issue_v), .issue_kind(issue_kind),
  .issue_nout(issue_nout), .issue_nin(issue_nin), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
  .epoch_idle(g_idle), .drained(g_dr), .word_v(g_wv), .word_tag(g_tag), .word_data(g_data), .word_slot(word_slot),
  .word_index(word_index), .word_ctl_pub(g_pub), .word_index_pub({8{word_index}}), .epoch_begin_pub({2{epoch_begin}}),
  .word_slot_pub({2{word_slot}}), .fault(g_f), .fault_code(g_fc));
`ifdef NETLIST
 ot_qfd_su_kv_static_posted_ys t (.clk(clk),
`else
 ot_qfd_su_kv_static_posted #(.ENABLE(1), .HEADS(1), .LOCAL_CTL(LOCAL_CTL), .MUT_TAG(MUT_TAG_T)) t (.clk(clk),
`endif
  .rst_n(rst_n), .epoch_begin(epoch_begin), .epoch_pos(epoch_pos), .issue_v(issue_v), .issue_kind(issue_kind),
  .issue_nout(issue_nout), .issue_nin(issue_nin), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
  .epoch_idle(t_idle), .drained(t_dr), .word_v(t_wv), .word_tag(t_tag), .word_data(t_data), .word_slot(word_slot),
  .word_index(word_index), .word_ctl_pub(t_pub), .word_index_pub({8{word_index}}), .epoch_begin_pub({2{epoch_begin}}),
  .word_slot_pub({2{word_slot}}), .fault(t_f), .fault_code(t_fc));
`endif
 integer cyc = 0, mism = 0, words = 0, tag9 = 0, faults = 0, seed, ep, k, n, s, li, pick;
 integer order [0:255];
 always #1 clk = ~clk;
 wire [596:0] go = {g_idle, g_dr, g_wv, g_f, g_tag, g_data, g_fc, g_pub};
 wire [596:0] to = {t_idle, t_dr, t_wv, t_f, t_tag, t_data, t_fc, t_pub};
 always @(negedge clk) if (rst_n) begin
  cyc = cyc + 1;
  if (go !== to) begin
   mism = mism + 1;
   if (mism <= 3) $display("MISMATCH cyc %0d g_tag %h t_tag %h g_wv %b t_wv %b g_f %b t_f %b", cyc, g_tag, t_tag, g_wv, t_wv, g_f, t_f);
  end
  if (g_wv) begin words = words + 1; if (g_tag[9]) tag9 = tag9 + 1; end
 end
 always @(posedge g_f) faults = faults + 1;
 function [31:0] fp8val(input integer r);   // FP32 values the encoder accepts (zero or e 121..134, m[19:0]=0)
  reg [7:0] e; reg [3:0] q;
  begin
   q = r[7:4]; e = 8'd121 + {4'd0, q % 4'd14};
   if (r % 5 == 0) fp8val = 32'd0;
   else fp8val = {r[0], e, r[10:8], 20'd0};
  end
 endfunction
 function [23:0] seat_addr(input integer idx, input [12:0] pos);
  reg [19:0] a; reg [6:0] d;
  begin
   d = idx % 128;
   if (idx < 128) seat_addr = {4'd0, pos[12:4], d, pos[3:0]};
   else begin a = 20'd65536 + {4'd0, pos, d[6:4]}; seat_addr = {a, d[3:0]}; end
  end
 endfunction
 task noise; begin
  epoch_begin <= ($random(seed) % 23) == 0; epoch_pos <= $random(seed);
  issue_v <= ($random(seed) % 7) == 0; issue_kind <= $random(seed); issue_nout <= $random(seed) % 3; issue_nin <= $random(seed) % 130;
  kv_we <= {$random(seed), $random(seed)} & {$random(seed), $random(seed)};
  for (li = 0; li < 64; li = li + 1) begin kv_waddr[24*li +: 24] <= $random(seed); kv_wdata[32*li +: 32] <= fp8val($random(seed)); end
  word_slot <= $random(seed); word_index <= $random(seed); word_ready <= $random(seed);
  @(posedge clk);
 end endtask
 task idle; begin
  epoch_begin <= 0; issue_v <= 0; kv_we <= 0; word_slot <= 0; word_ready <= 1; @(posedge clk);
 end endtask
 reg [12:0] pos;
 initial begin
  seed = SEED;
  repeat (3) @(posedge clk); rst_n <= 1; idle;
  for (ep = 0; ep < EPOCHS; ep = ep + 1) begin
   pos = $random(seed) % 8192;
   if (ep % 4 == 3) repeat (20) noise;
   repeat (4) idle;
   epoch_begin <= 1; epoch_pos <= pos; @(posedge clk); epoch_begin <= 0;
   for (k = 0; k < 3; k = k + 1) begin
    issue_v <= 1; issue_kind <= k; issue_nout <= 1; issue_nin <= (k == 0) ? 128 : 64; @(posedge clk);
   end
   issue_v <= 0;
   for (k = 0; k < 256; k = k + 1) order[k] = k;
   for (k = 255; k > 0; k = k - 1) begin pick = {$random(seed)} % (k + 1); n = order[k]; order[k] = order[pick]; order[pick] = n; end
   for (k = 0; k < 256; k = k + 64) begin
    kv_we <= 0;
    for (li = 0; li < 64; li = li + 1) begin
     kv_we[li] <= ({$random(seed)} % 3) != 0 || 1;
     kv_waddr[24*li +: 24] <= seat_addr(order[k + li], pos); kv_wdata[32*li +: 32] <= fp8val($random(seed));
    end
    @(posedge clk);
   end
   kv_we <= 0;
   repeat (3) idle;
   for (s = 0; s < 4; s = s + 1) begin
    word_slot <= 1; word_index <= s; word_ready <= 1; @(posedge clk); word_slot <= 0; @(posedge clk); @(posedge clk);
   end
   repeat (6) idle;
   if (ep % 8 == 7) begin rst_n <= 0; @(posedge clk); rst_n <= 1; idle; end
  end
  repeat (10) idle;
  $display("LOCKSTEP %s cycles %0d mismatches %0d words %0d tag9 %0d faults %0d", (mism == 0) ? "PASS" : "DIFF", cyc, mism, words, tag9, faults);
  $finish;
 end
endmodule
