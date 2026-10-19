`timescale 1ns/1ps
// KV-DCAL-BOOTCFG 2026-10-19: boot image target 11 (real qkd_static_kv_boot_dispatch LINKCFG=1, 66 words) -> the KV
// calendar sequencer tile qkd_d2d_cal_seq_pin_bc (bcfg_* in, cfg_* out) -> a real ot_qwen_d2d_cal TX + RX pair (as in
// ot_qwen_d2d_static_end).  Reference: the MU pin tile qkd_d2d_cal_seq_pin (its own init stream loads the MU image) on
// its own TX + RX pair, same reset / epoch strobe.
// Run: boot 1..9, 11, 0; epoch 1 (admission + the full 36-run token programme); epoch 2 (base restore e = 1, 2, admission,
// token run + L1).  Checks, every edge from the first epoch: DUT and reference pairs play identical event streams
// (ev_v/port/kind/beat/running, TX and RX); the DUT's cal_start/cal_seg/layer/tok_start/adm_done equal the reference
// tile's; at every admission start both DUT calendars hold the SEG2 bases, at every token start the SEG1 bases; no
// calendar fault; no tile fault; >= 2 admissions + 2 token runs with events.
// MUT 0 PASS.  Must FAIL: 1 tile MUT=1 (sequencer writes dropped = today's die: the token run replays admission),
// 2 boot image = the production (non-MU) image (stale SEG2 8 vs the tile's 9), 3 a boot write on the sequencer's epoch-2
// base-restore edge (collision), 4 a boot write during the token programme, 5 the boot RX base word masked (admission
// before the boot RX base).
module tb_kv_dcal_bootcfg #(parameter integer MUT = 0);
 `include "d2d_cal_image_mu.svh"
 reg ck = 0; always #5 ck = ~ck;
 reg rst_n = 0;
 reg [142:0] pr = 0; reg [3:0] target = 1; reg ready = 0;
 reg [15:0] epoch = 77; reg [63:0] digest = 0; reg [159:0] applied = 0; reg [2:0] configured = 0;
 wire lw, ww, ow; wire [8:0] la; wire [7:0] wa, ga; wire [1:0] oa; wire [63:0] ld, wd, gd, cd; wire [31:0] od, lwe, fwe;
 wire [127:0] cwe, last; wire [7:0] ca; wire [31:0] flast; wire setup, dfault; wire [7:0] code; wire [15:0] ie; wire [63:0] id;
 wire dwe; wire [7:0] dad; wire [63:0] dda;
 wire ltx, lrx; wire [5:0] laddr; wire [31:0] ldata;
 qkd_static_kv_boot_dispatch #(.MUT(0), .DIECFG(0), .LINKCFG(1)) disp (.ck(ck), .rst_n(rst_n), .boot_pr(pr),
  .boot_image_target(target), .boot_image_ready(ready), .boot_image_fault(1'b0), .boot_image_epoch(epoch),
  .boot_image_digest(digest), .execution_active(1'b0), .sink_applied(applied), .local_configured(configured),
  .sink_fault(1'b0), .diecfg_sealed(1'b0), .diecfg_fault(1'b0),
  .layer_we(lw), .layer_addr(la), .layer_data(ld), .writer_we(ww), .writer_addr(wa), .writer_data(wd), .ownership_we(ow),
  .ownership_addr(oa), .ownership_data(od), .landing_we(lwe), .front_we(fwe), .group_addr(ga), .group_data(gd),
  .controller_we(cwe), .controller_addr(ca), .controller_data(cd), .controller_last(last), .front_last(flast),
  .diecfg_we(dwe), .diecfg_addr(dad), .diecfg_data(dda),
  .link_cfg_tx_we(ltx), .link_cfg_rx_we(lrx), .link_cfg_addr(laddr), .link_cfg_data(ldata),
  .setup_ready(setup), .fault(dfault), .fault_code(code), .installed_epoch(ie), .installed_isa_digest(id));
 // ---- boundary: dispatcher link_cfg_* -> tile bcfg_* (mutants 3/4 inject a write, 5 masks the RX base word)
 reg inj = 0;
 wire btx = ltx || inj, brx = lrx && !(MUT == 5 && laddr == 6'b100000);
 wire [5:0] baddr = inj ? 6'b100000 : laddr;
 wire [31:0] bdata = inj ? D2D_CAL_K_TX_SEG2 : ldata;
 reg epoch_go = 0;
 wire dtx, drx, d_cs, d_seg, d_rdy, d_run, d_adm, d_tok, d_fault; wire [5:0] daddr, d_layer; wire [31:0] ddata;
 qkd_d2d_cal_seq_pin_bc #(.EP_SKEW(3), .MUT(MUT == 1 ? 1 : 0)) dut (.ck(ck), .rst_n(rst_n), .reload(1'b0),
  .epoch_go(epoch_go), .halt(1'b0), .bcfg_tx_we(btx), .bcfg_rx_we(brx), .bcfg_addr(baddr), .bcfg_data(bdata),
  .cfg_tx_we(dtx), .cfg_rx_we(drx), .cfg_addr(daddr), .cfg_data(ddata), .cal_start(d_cs), .cal_seg(d_seg),
  .cal_ready(d_rdy), .running(d_run), .layer(d_layer), .adm_done(d_adm), .tok_start(d_tok), .fault(d_fault));
 wire rtx, rrx, r_cs, r_seg, r_rdy, r_run, r_adm, r_tok, r_fault; wire [5:0] raddr, r_layer; wire [31:0] rdata;
 qkd_d2d_cal_seq_pin #(.EP_SKEW(3)) ref_seq (.ck(ck), .rst_n(rst_n), .reload(1'b0), .epoch_go(epoch_go), .halt(1'b0),
  .cfg_tx_we(rtx), .cfg_rx_we(rrx), .cfg_addr(raddr), .cfg_data(rdata), .cal_start(r_cs), .cal_seg(r_seg),
  .cal_ready(r_rdy), .running(r_run), .layer(r_layer), .adm_done(r_adm), .tok_start(r_tok), .fault(r_fault));
 // ---- two real calendar pairs: A = DUT, B = reference
 wire av_t, av_r, bv_t, bv_r, ar_t, ar_r, br_t, br_r, af_t, af_r, bf_t, bf_r;
 wire [2:0] ap_t, ap_r, bp_t, bp_r; wire [3:0] ak_t, ak_r, bk_t, bk_r; wire [4:0] ab_t, ab_r, bb_t, bb_r;
 ot_qwen_d2d_cal #(.NE(32)) a_tx (.ck(ck), .rst_n(rst_n), .cfg_we(dtx), .cfg_addr(daddr), .cfg_data(ddata), .start(d_cs),
  .start_seg(d_seg), .halt(1'b0), .ev_v(av_t), .ev_port(ap_t), .ev_kind(ak_t), .ev_beat(ab_t), .running(ar_t), .fault(af_t));
 ot_qwen_d2d_cal #(.NE(32)) a_rx (.ck(ck), .rst_n(rst_n), .cfg_we(drx), .cfg_addr(daddr), .cfg_data(ddata), .start(d_cs),
  .start_seg(d_seg), .halt(1'b0), .ev_v(av_r), .ev_port(ap_r), .ev_kind(ak_r), .ev_beat(ab_r), .running(ar_r), .fault(af_r));
 ot_qwen_d2d_cal #(.NE(32)) b_tx (.ck(ck), .rst_n(rst_n), .cfg_we(rtx), .cfg_addr(raddr), .cfg_data(rdata), .start(r_cs),
  .start_seg(r_seg), .halt(1'b0), .ev_v(bv_t), .ev_port(bp_t), .ev_kind(bk_t), .ev_beat(bb_t), .running(br_t), .fault(bf_t));
 ot_qwen_d2d_cal #(.NE(32)) b_rx (.ck(ck), .rst_n(rst_n), .cfg_we(rrx), .cfg_addr(raddr), .cfg_data(rdata), .start(r_cs),
  .start_seg(r_seg), .halt(1'b0), .ev_v(bv_r), .ev_port(bp_r), .ev_kind(bk_r), .ev_beat(bb_r), .running(br_r), .fault(bf_r));
 // ---- checks (from the first epoch strobe on)
 reg chk = 0, d_adm_q = 0, r_adm_q = 0;
 always @(posedge ck) begin d_adm_q <= d_adm; r_adm_q <= r_adm; end
 integer errors = 0, nadm = 0, ntok = 0, nlay = 0, evs = 0, evadm = 0, evtok = 0, ndw = 0, nsw = 0;
 integer phase = 0;          // 1 admission run playing, 2 token run playing (segment 1), 0 other
 always @(posedge ck) begin
  if (dtx || drx) ndw <= ndw + 1;
  if (chk && (dtx || drx)) nsw <= nsw + 1;
  if (chk) begin
   if ({av_t, ap_t, ak_t, ab_t, ar_t, av_r, ap_r, ak_r, ab_r, ar_r} !== {bv_t, bp_t, bk_t, bb_t, br_t, bv_r, bp_r, bk_r, bb_r, br_r}) begin
    if (errors < 8) $display("BAD event stream differs at t=%0t (DUT %b%b vs ref %b%b, phase %0d)", $time, av_t, av_r, bv_t, bv_r, phase);
    errors = errors + 1;
   end
   // adm_done: rising edges compared (its fall at the epoch strobe is one edge later in the tile; unbound on the die)
   if ({d_cs, d_seg, d_layer, d_tok, d_adm && !d_adm_q} !== {r_cs, r_seg, r_layer, r_tok, r_adm && !r_adm_q}) begin
    if (errors < 8) $display("BAD strobe differs at t=%0t: DUT cs%0d seg%0d layer%0d tok%0d adm%0d, ref cs%0d seg%0d layer%0d tok%0d adm%0d",
     $time, d_cs, d_seg, d_layer, d_tok, d_adm, r_cs, r_seg, r_layer, r_tok, r_adm);
    errors = errors + 1;
   end
   evs = evs + av_t + av_r;
   if (phase == 1) evadm = evadm + av_t + av_r;
   if (phase == 2) evtok = evtok + av_t + av_r;
   if (d_cs && d_seg && d_layer == 6'h3f) begin
    nadm = nadm + 1; phase = 1;
    if (a_tx.seg1 !== 5'(D2D_CAL_K_TX_SEG2) || a_rx.seg1 !== 5'(D2D_CAL_K_RX_SEG2)) begin
     $display("BAD admission start %0d: DUT bases TX %0d RX %0d, SEG2 %0d / %0d", nadm, a_tx.seg1, a_rx.seg1, D2D_CAL_K_TX_SEG2, D2D_CAL_K_RX_SEG2);
     errors = errors + 1;
    end
   end else if (d_cs && d_seg) begin
    ntok = ntok + 1; phase = 2;
    if (a_tx.seg1 !== 5'(D2D_CAL_K_TX_SEG1) || a_rx.seg1 !== 5'(D2D_CAL_K_RX_SEG1)) begin
     $display("BAD token start %0d: DUT bases TX %0d RX %0d, SEG1 %0d / %0d (token run would replay segment %0d)", ntok,
      a_tx.seg1, a_rx.seg1, D2D_CAL_K_TX_SEG1, D2D_CAL_K_RX_SEG1, a_tx.seg1);
     errors = errors + 1;
    end
   end else if (d_cs) begin nlay = nlay + 1; phase = 0; end
  end
 end
 reg [63:0] img [0:65];
 integer t, a, n, cyc;
 function automatic [63:0] value(input integer t, input integer a); value = (t == 3) ? 64'(a) : 64'h1234567800000000 ^ (64'(t) << 32) ^ 64'(a); endfunction
 task tick; begin @(negedge ck); end endtask
 task word(input [3:0] tg, input integer a, input [63:0] d); begin target = tg; pr = 0; pr[74] = 1; pr[73:64] = 10'(a); pr[63:0] = d; tick(); pr = 0; end endtask
 task image_done(input [3:0] tg); begin pr = 0; tick(); ready = 1; target = tg; tick(); tick(); ready = 0; tick(); end endtask
 task wait_idle; begin    // the token programme over (35 layer runs started): no sequencer run, every calendar idle
  for (cyc = 0; cyc < 400000 && (nlay < 35 || r_run || ar_t || ar_r || br_t || br_r); cyc = cyc + 1) tick();
 end endtask
 initial begin
  $readmemh("target11.hex", img);
  repeat (3) tick(); rst_n = 1; repeat (80) tick();
  if (ndw != 0) begin $display("BAD tile forwarded %0d init writes (suppressed: boot target 11 is the table producer)", ndw); errors = errors + 1; end
  for (t = 1; t <= 9; t = t + 1) begin
   case (t) 1: n = 327; 2: n = 181; 3: n = 4; 4, 5: n = 192; default: n = 1024; endcase
   for (a = 0; a < n; a = a + 1) word(4'(t), a, value(t, a));
   image_done(4'(t));
  end
  for (a = 0; a < 66; a = a + 1) word(11, a, img[a]);
  image_done(11);
  target = 0; tick(); ready = 1; digest = 64'h0fedcba987654321; configured = 7; applied = {160{1'b1}}; tick(); tick(); tick();
  if (!setup || dfault) begin $display("BAD dispatcher setup_ready %0d fault %0d code %h", setup, dfault, code); errors = errors + 1; end
  if (ndw != 66) begin $display("BAD tile forwarded %0d boot writes (66 expected)", ndw); errors = errors + 1; end
  repeat (8) tick();
  for (a = 0; a < 32; a = a + 1)
   if (a_tx.tbl[a] !== b_tx.tbl[a] || a_rx.tbl[a] !== b_rx.tbl[a]) begin
    if (errors < 8) $display("BAD table entry %0d: boot-loaded TX %h RX %h, reference image TX %h RX %h", a, a_tx.tbl[a], a_rx.tbl[a], b_tx.tbl[a], b_rx.tbl[a]);
    errors = errors + 1;
   end
  // ---- epoch 1: admission + the full token programme
  chk = 1; epoch_go = 1; tick();
  if (MUT == 4) begin
   for (cyc = 0; cyc < 5000 && ntok == 0; cyc = cyc + 1) tick();
   repeat (100) tick(); inj = 1; tick(); inj = 0;
  end
  wait_idle();
  if (ntok != 1 || nlay != 35) begin $display("BAD epoch 1: token starts %0d layer starts %0d (1 / 35 expected)", ntok, nlay); errors = errors + 1; end
  // ---- epoch 2 (recovery epoch): the sequencer restores SEG2 (e = 1, 2), admission, token run + L1
  epoch_go = 0; tick(); tick();
  epoch_go = 1;
  if (MUT == 3) begin
   // the DUT's sequencer issues its e = 1 restore inside the tile; inject a boot word so that it reaches the tile's merge
   // on that same edge (the boot input is pin-registered: present it one edge before the sequencer write is visible)
   for (cyc = 0; cyc < 50 && !(dut.u_seq.u_seq.eact && dut.u_seq.u_seq.e == 32'd1); cyc = cyc + 1) tick();
   inj = 1; tick(); inj = 0;
  end
  for (cyc = 0; cyc < 20000 && nlay < 36; cyc = cyc + 1) tick();
  repeat (2000) tick();
  chk = 0;
  if (nadm != 2 || ntok != 2 || nlay < 36) begin $display("BAD runs: admissions %0d token runs %0d layer runs %0d (2 / 2 / >= 36 expected)", nadm, ntok, nlay); errors = errors + 1; end
  if (evadm == 0 || evtok == 0) begin $display("BAD no events: admission %0d token %0d", evadm, evtok); errors = errors + 1; end
  if (nsw != 6 + (MUT == 4)) begin $display("BAD runtime cfg writes forwarded %0d (6 expected: 2 switches to SEG1 + 1 restore to SEG2, 2 words each)", nsw); errors = errors + 1; end
  if (af_t || af_r || bf_t || bf_r) begin $display("BAD calendar fault DUT %0d%0d ref %0d%0d", af_t, af_r, bf_t, bf_r); errors = errors + 1; end
  if (r_fault) begin $display("BAD reference tile fault"); errors = errors + 1; end
  if (d_fault) begin
   $display("BAD tile fault: col %0d run %0d stale %0d early %0d seq %0d", dut.f_col, dut.f_run, dut.f_stale, dut.f_early, dut.s_fault);
   errors = errors + 1;
  end
  if (errors) begin $display("FAIL kv_dcal_bootcfg mut%0d errors%0d", MUT, errors); $fatal(1); end
  $display("PASS kv_dcal_bootcfg mut%0d bootwrites66 admissions%0d tokens%0d layers%0d events%0d adm_ev%0d tok_ev%0d runtime_writes%0d",
   MUT, nadm, ntok, nlay, evs, evadm, evtok, nsw);
  $finish;
 end
endmodule
