`timescale 1ns/1ps
// KVJ-SMALL 2026-10-17 (KV-INT gap item 12): the static D2D link end's calendar cfg (cfg_tx_we / cfg_rx_we / cfg_addr /
// cfg_data) boot-loaded through qkd_static_kv_boot_dispatch LINKCFG=1, image target 11 (66 words from
// tools/qwen_kv_die/kv_static_programme.link_cfg_words, the same d2d_link_calendar.py --profile program compile as the
// committed d2d_cal_image.svh).
// Reference: the KV calendar sequencer qkd_d2d_cal_seq (constants D2D_CAL_K_*, ADM=1), whose init mode is today's only
// producer of these four ports.  Each source drives a real TX + RX calendar pair (ot_qwen_d2d_cal, NE 32, as inside
// ot_qwen_d2d_static_end).
// SCN 0: targets 1..9, 11, 0: the dispatcher's 66 link cfg writes equal the sequencer's init stream word for word,
//        both calendar pairs hold identical tables and segment-1 bases, an admission run (start, seg 1) and a layer run
//        (seg 0) play identical event streams with no calendar fault, and setup_ready rises.
// SCN 1: no target 11 (1..9 then 0): the ISA image is refused (code 6), never setup_ready.
// SCN 2: a target-11 word with data[63:32] != 0: fault code 5, never setup_ready.
// SCN 3: LINKCFG=0 (the KVJ-F/KVJ-A dispatcher): target 11 after 9 is refused (code 3), no link cfg write.
// MUT (dispatcher): 5 TX/RX swapped, 6 segment-1 bases written into entry 0 (SCN 0 must FAIL).
module tb_kv_link_cfg_boot #(parameter integer SCN = 0, parameter integer MUT = 0);
 localparam integer LINKCFG = (SCN == 3) ? 0 : 1;
 reg ck = 0; always #5 ck = ~ck;
 reg rst_n = 0;
 reg [142:0] pr = 0; reg [3:0] target = 1; reg ready = 0, active = 0;
 reg [15:0] epoch = 77; reg [63:0] digest = 0; reg [159:0] applied = 0; reg [2:0] configured = 0;
 wire lw, ww, ow; wire [8:0] la; wire [7:0] wa, ga; wire [1:0] oa; wire [63:0] ld, wd, gd, cd; wire [31:0] od, lwe, fwe;
 wire [127:0] cwe, last; wire [7:0] ca; wire [31:0] flast; wire setup, dfault; wire [7:0] code; wire [15:0] ie; wire [63:0] id;
 wire dwe; wire [7:0] dad; wire [63:0] dda;
 wire ltx, lrx; wire [5:0] laddr; wire [31:0] ldata;
 qkd_static_kv_boot_dispatch #(.MUT(MUT), .DIECFG(0), .LINKCFG(LINKCFG)) disp (.ck(ck), .rst_n(rst_n), .boot_pr(pr),
  .boot_image_target(target), .boot_image_ready(ready), .boot_image_fault(1'b0), .boot_image_epoch(epoch),
  .boot_image_digest(digest), .execution_active(active), .sink_applied(applied), .local_configured(configured),
  .sink_fault(1'b0), .diecfg_sealed(1'b0), .diecfg_fault(1'b0),
  .layer_we(lw), .layer_addr(la), .layer_data(ld), .writer_we(ww), .writer_addr(wa), .writer_data(wd), .ownership_we(ow),
  .ownership_addr(oa), .ownership_data(od), .landing_we(lwe), .front_we(fwe), .group_addr(ga), .group_data(gd),
  .controller_we(cwe), .controller_addr(ca), .controller_data(cd), .controller_last(last), .front_last(flast),
  .diecfg_we(dwe), .diecfg_addr(dad), .diecfg_data(dda),
  .link_cfg_tx_we(ltx), .link_cfg_rx_we(lrx), .link_cfg_addr(laddr), .link_cfg_data(ldata),
  .setup_ready(setup), .fault(dfault), .fault_code(code), .installed_epoch(ie), .installed_isa_digest(id));
 // ---- reference: the KV calendar sequencer's init stream (epoch never strobed: init only) ----
 wire stx, srx; wire [5:0] saddr; wire [31:0] sdata; wire s_start, s_seg, s_ready, s_run, s_adm, s_tok, s_fault; wire [5:0] s_layer;
 qkd_d2d_cal_seq #(.EP_SKEW(3)) ref_seq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .tok_go(1'b0), .epoch_go(1'b0), .halt(1'b0),
  .cfg_tx_we(stx), .cfg_rx_we(srx), .cfg_addr(saddr), .cfg_data(sdata), .cal_start(s_start), .cal_seg(s_seg),
  .cal_ready(s_ready), .running(s_run), .layer(s_layer), .adm_done(s_adm), .tok_start(s_tok), .fault(s_fault));
 // ---- two real calendar pairs: A from the dispatcher, B from the sequencer ----
 reg start = 0, seg = 0;
 wire av_t, av_r, bv_t, bv_r, ar_t, ar_r, br_t, br_r, af_t, af_r, bf_t, bf_r;
 wire [2:0] ap_t, ap_r, bp_t, bp_r; wire [3:0] ak_t, ak_r, bk_t, bk_r; wire [4:0] ab_t, ab_r, bb_t, bb_r;
 ot_qwen_d2d_cal #(.NE(32)) a_tx (.ck(ck), .rst_n(rst_n), .cfg_we(ltx), .cfg_addr(laddr), .cfg_data(ldata), .start(start),
  .start_seg(seg), .halt(1'b0), .ev_v(av_t), .ev_port(ap_t), .ev_kind(ak_t), .ev_beat(ab_t), .running(ar_t), .fault(af_t));
 ot_qwen_d2d_cal #(.NE(32)) a_rx (.ck(ck), .rst_n(rst_n), .cfg_we(lrx), .cfg_addr(laddr), .cfg_data(ldata), .start(start),
  .start_seg(seg), .halt(1'b0), .ev_v(av_r), .ev_port(ap_r), .ev_kind(ak_r), .ev_beat(ab_r), .running(ar_r), .fault(af_r));
 ot_qwen_d2d_cal #(.NE(32)) b_tx (.ck(ck), .rst_n(rst_n), .cfg_we(stx), .cfg_addr(saddr), .cfg_data(sdata), .start(start),
  .start_seg(seg), .halt(1'b0), .ev_v(bv_t), .ev_port(bp_t), .ev_kind(bk_t), .ev_beat(bb_t), .running(br_t), .fault(bf_t));
 ot_qwen_d2d_cal #(.NE(32)) b_rx (.ck(ck), .rst_n(rst_n), .cfg_we(srx), .cfg_addr(saddr), .cfg_data(sdata), .start(start),
  .start_seg(seg), .halt(1'b0), .ev_v(bv_r), .ev_port(bp_r), .ev_kind(bk_r), .ev_beat(bb_r), .running(br_r), .fault(bf_r));
 // ---- write-stream capture ----
 reg [39:0] dstream [0:127]; reg [39:0] sstream [0:127]; integer nd = 0, ns = 0;
 always @(posedge ck) begin
  if (ltx || lrx) begin dstream[nd] <= {ltx, lrx, laddr, ldata}; nd <= nd + 1; end
  if (stx || srx) begin sstream[ns] <= {stx, srx, saddr, sdata}; ns <= ns + 1; end
 end
 reg [63:0] img [0:65];
 integer errors = 0, t, a, n, evs = 0, cyc;
 function automatic [63:0] value(input integer t, input integer a); value = (t == 3) ? 64'(a) : 64'h1234567800000000 ^ (64'(t) << 32) ^ 64'(a); endfunction
 task tick; begin @(negedge ck); end endtask
 task word(input [3:0] tg, input integer a, input [63:0] d); begin target = tg; pr = 0; pr[74] = 1; pr[73:64] = 10'(a); pr[63:0] = d; tick(); pr = 0; end endtask
 task image_done(input [3:0] tg); begin pr = 0; tick(); ready = 1; target = tg; tick(); tick(); ready = 0; tick(); end endtask
 task run_cmp(input s); begin
  seg = s; start = 1; tick(); start = 0; seg = 0;
  for (cyc = 0; cyc < 4000; cyc = cyc + 1) begin
   if ({av_t, ap_t, ak_t, ab_t, ar_t, av_r, ap_r, ak_r, ab_r, ar_r} !== {bv_t, bp_t, bk_t, bb_t, br_t, bv_r, bp_r, bk_r, bb_r, br_r}) begin
    if (errors < 8) $display("BAD seg%0d run differs at +%0d", s, cyc); errors++; end
   evs = evs + av_t + av_r;
   tick();
   if (!ar_t && !ar_r && !br_t && !br_r && cyc > 4) cyc = 4000;
  end
 end endtask
 initial begin
  $readmemh("target11.hex", img);
  repeat (3) tick(); rst_n = 1; repeat (80) tick();                // sequencer init (66 edges) done long before
  if (!s_ready || ns != 66) begin $display("BAD reference sequencer init: ready %0d writes %0d", s_ready, ns); errors++; end
  for (t = 1; t <= 9; t = t + 1) begin
   case (t) 1: n = 327; 2: n = 181; 3: n = 4; 4, 5: n = 192; default: n = 1024; endcase
   for (a = 0; a < n; a = a + 1) word(4'(t), a, value(t, a));
   image_done(4'(t));
  end
  if (SCN != 1) begin
   for (a = 0; a < 66; a = a + 1) word(11, a, (SCN == 2 && a == 7) ? (img[a] | 64'h1_0000_0000) : img[a]);
   image_done(11);
  end
  target = 0; tick(); ready = 1; digest = 64'h0fedcba987654321; configured = 7; applied = {160{1'b1}}; tick(); tick(); tick();
  case (SCN)
   0: begin
    if (!setup || dfault) begin $display("BAD setup_ready %0d fault %0d code %h", setup, dfault, code); errors++; end
    if (nd != 66) begin $display("BAD dispatcher link cfg writes %0d (66 expected)", nd); errors++; end
    for (a = 0; a < 66 && a < nd; a = a + 1)
     if (dstream[a] !== sstream[a]) begin if (errors < 8) $display("BAD link cfg write %0d %h, sequencer %h", a, dstream[a], sstream[a]); errors++; end
    for (a = 0; a < 32; a = a + 1)
     if (a_tx.tbl[a] !== b_tx.tbl[a] || a_rx.tbl[a] !== b_rx.tbl[a]) begin if (errors < 8) $display("BAD table entry %0d", a); errors++; end
    if (a_tx.seg1 !== b_tx.seg1 || a_rx.seg1 !== b_rx.seg1) begin $display("BAD seg1 %0d/%0d vs %0d/%0d", a_tx.seg1, a_rx.seg1, b_tx.seg1, b_rx.seg1); errors++; end
    repeat (4) tick();
    run_cmp(1);                                                     // admission segment (the KV init base)
    run_cmp(0);                                                     // layer run
    if (af_t || af_r || bf_t || bf_r) begin $display("BAD calendar fault A %0d%0d B %0d%0d", af_t, af_r, bf_t, bf_r); errors++; end
    if (evs == 0) begin $display("BAD no calendar events played"); errors++; end
   end
   1: if (setup || !dfault || !code[6]) begin $display("BAD missing target 11 not refused: setup %0d fault %0d code %h", setup, dfault, code); errors++; end
   2: if (setup || !dfault || !code[5]) begin $display("BAD padding not refused: setup %0d fault %0d code %h", setup, dfault, code); errors++; end
   3: if (setup || !dfault || !code[3] || nd != 0) begin $display("BAD LINKCFG=0 accepted target 11: setup %0d fault %0d code %h writes %0d", setup, dfault, code, nd); errors++; end
  endcase
  if (errors) begin $display("FAIL kv_link_cfg_boot scn%0d mut%0d errors%0d", SCN, MUT, errors); $fatal(1); end
  $display("PASS kv_link_cfg_boot scn%0d mut%0d writes%0d events%0d", SCN, MUT, nd, evs);
  $finish;
 end
 initial begin #50000000; $display("FAIL kv_link_cfg_boot timeout"); $fatal(1); end
endmodule
