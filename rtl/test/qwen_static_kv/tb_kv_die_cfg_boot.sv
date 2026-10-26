`timescale 1ns/1ps
// KVJ-F 2026-10-17 (stub audit K-12, coordinator 0da (d)): ECTL cfg and regional reset release delays through the boot
// dispatcher (qkd_static_kv_boot_dispatch DIECFG=1, pre-boot target 10) into qkd_kv_die_cfg, which drives NRST real
// qkd_rst_region roots (each fed by its own registered relay chain of depth d_r from the HOST reset level) and the
// ECTL a/b/c cfg words.  The dispatcher's own reset is region 0's output (it lives in a regional reset domain).
// SCN 0: POR; pass 1 = first release (dly 0: regions release UNALIGNED, measured), target 10 loaded (75 + 1 words),
//        die cfg sealed and every ECTL / dly word read back exact; the HOST re-asserts and releases: every region now
//        releases on the SAME cycle (host release + D + 2); the die cfg survives the functional reset; pass 2 = targets
//        1..9 then ISA 0 -> setup_ready rises (sink applied / configured as in tb_static_boot_dispatch).
// SCN 1: no target-10 pass: the full 1..9 / 0 replay must NOT reach setup_ready (die cfg unsealed).
// SCN 2: target 10 offered after target 1 has started: dispatcher fault (code 3), die cfg never written.
// SCN 3: an ECTL word with a non-zero padding bit: die cfg fault -> dispatcher sink fault, never sealed.
// MUT (qkd_kv_die_cfg): 1 B/C swapped, 3 regions one off (SCN 0 must FAIL); 2 padding unchecked (SCN 3 must FAIL).
// RTL-BUILD-KV/FAULT 10-18 (P8), CAP=1 (die cfg CAP=1 + dispatcher DIECAP=1): the capability word 32+NRST (data[0] = CAPV)
// precedes the seal.  SCN 0 also checks fused_program_capability == 0 after the capability word but BEFORE the seal,
// == CAPV after the seal, and unchanged across the functional re-reset; SCN 4 = capability word with data[1] set:
// die cfg fault, never sealed, capability 0.  MUT 4 (bit taken from data[1]) / MUT 5 (not seal-gated) must FAIL SCN 0.
module tb_kv_die_cfg_boot #(parameter integer SCN = 0, parameter integer MUT = 0, parameter integer NRST = 43,
                            parameter integer CAP = 0, parameter integer CAPV = 1);
 reg ck = 0; always #5 ck = ~ck;
 reg por_n = 0, host_rst = 0;
 reg [142:0] pr = 0; reg [3:0] target = 1; reg ready = 0, source_fault = 0, active = 0;
 reg [15:0] epoch = 123; reg [63:0] digest = 0; reg [159:0] applied = 0; reg [2:0] configured = 0;
 wire lw, ww, ow; wire [8:0] la; wire [7:0] wa, ga; wire [1:0] oa; wire [63:0] ld, wd, gd, cd; wire [31:0] od, lwe, fwe;
 wire [127:0] cwe, last; wire [7:0] ca; wire [31:0] flast; wire setup, dfault; wire [7:0] code; wire [15:0] ie; wire [63:0] id;
 wire dwe; wire [7:0] dad; wire [63:0] dda;
 wire [159:0] ea, eb, ec; wire [NRST*8-1:0] dly; wire sealed, cfault, capb;
 // ---- regional reset roots: chain depth d_r from the HOST level, dly from the die cfg ----
 function automatic integer depth(input integer r); depth = 1 + ((r * 7 + 3) % 19); endfunction
 integer D = 0;
 wire [NRST-1:0] rb;
 genvar r;
 generate for (r = 0; r < NRST; r = r + 1) begin : g_r
  localparam integer DR = 1 + ((r * 7 + 3) % 19);
  reg [DR:1] ch;                        // relays carry no reset (undefined until flushed: start X)
  always @(posedge ck) ch[1] <= host_rst;
  genvar j;
  for (j = 2; j <= DR; j = j + 1) begin : g_ch always @(posedge ck) ch[j] <= ch[j-1]; end
  qkd_rst_region #(.IGNORE(64), .HOLD(16)) u (.ck(ck), .por_n(por_n), .a(ch[DR]), .dly(dly[8*r +: 8]), .b(rb[r]));
 end endgenerate
 qkd_static_kv_boot_dispatch #(.MUT(0), .DIECFG(1), .NRST(NRST), .DIECAP(CAP)) disp (.ck(ck), .rst_n(rb[0]), .boot_pr(pr),
  .boot_image_target(target), .boot_image_ready(ready), .boot_image_fault(source_fault), .boot_image_epoch(epoch),
  .boot_image_digest(digest), .execution_active(active), .sink_applied(applied), .local_configured(configured),
  .sink_fault(1'b0), .diecfg_sealed(sealed), .diecfg_fault(cfault),
  .layer_we(lw), .layer_addr(la), .layer_data(ld), .writer_we(ww), .writer_addr(wa), .writer_data(wd), .ownership_we(ow),
  .ownership_addr(oa), .ownership_data(od), .landing_we(lwe), .front_we(fwe), .group_addr(ga), .group_data(gd),
  .controller_we(cwe), .controller_addr(ca), .controller_data(cd), .controller_last(last), .front_last(flast),
  .diecfg_we(dwe), .diecfg_addr(dad), .diecfg_data(dda),
  .setup_ready(setup), .fault(dfault), .fault_code(code), .installed_epoch(ie), .installed_isa_digest(id));
 qkd_kv_die_cfg #(.NRST(NRST), .CAP(CAP), .MUT(MUT)) dcfg (.ck(ck), .por_n(por_n), .cfg_we(dwe), .cfg_addr(dad), .cfg_data(dda),
  .ectl_a_cfg(ea), .ectl_b_cfg(eb), .ectl_c_cfg(ec), .rst_dly(dly), .fused_program_capability(capb), .sealed(sealed),
  .fault(cfault));
 integer errors = 0, cyc = 0, t, a, n, rel_host;
 integer relc[0:NRST-1];
 always @(posedge ck) cyc <= cyc + 1;
 always @(posedge ck) for (integer k = 0; k < NRST; k = k + 1) if (rb[k] === 1'b1 && relc[k] < 0) relc[k] = cyc;
 function automatic [14:0] ectl_word(input integer i); ectl_word = {5'(i ^ 5'h0a), 5'(i ^ 5'h15), 5'(i)}; endfunction
 function automatic [7:0] dly_of(input integer r); dly_of = 8'(D - depth(r)); endfunction
 function automatic [63:0] value(input integer t, input integer a); value = (t == 3) ? 64'(a) : 64'h1234567800000000 ^ (64'(t) << 32) ^ 64'(a); endfunction
 task tick; begin @(negedge ck); end endtask
 task word(input [3:0] tg, input integer a, input [63:0] d); begin target = tg; pr = 0; pr[74] = 1; pr[73:64] = 10'(a); pr[63:0] = d; tick(); pr = 0; end endtask
 task image_done(input [3:0] tg); begin pr = 0; tick(); ready = 1; target = tg; tick(); tick(); ready = 0; tick(); end endtask
 task release_all(output integer at); begin
  for (integer k = 0; k < NRST; k = k + 1) relc[k] = -1;
  host_rst = 1; at = cyc; repeat (D + 40) tick();
 end endtask
 task load_diecfg(input integer pad_bad); begin
  for (a = 0; a < 32; a = a + 1) word(10, a, {49'((pad_bad && a == 5) ? 1 : 0), ectl_word(a)});
  for (a = 0; a < NRST; a = a + 1) word(10, 32 + a, {56'd0, dly_of(a)});
  if (CAP) begin
   word(10, 32 + NRST, {62'd0, 1'(SCN == 4), 1'(CAPV)});
   repeat (4) tick();
   if (capb !== 1'b0) begin $display("BAD capability %b before the seal", capb); errors++; end
  end
  word(10, 32 + NRST + CAP, 64'h514b5644_43464731);
  image_done(10);
 end endtask
 task full_boot; begin
  for (t = 1; t <= 9; t = t + 1) begin
   case (t) 1: n = 327; 2: n = 181; 3: n = 4; 4, 5: n = 192; default: n = 1024; endcase
   for (a = 0; a < n; a = a + 1) word(4'(t), a, value(t, a));
   image_done(4'(t));
  end
  target = 0; tick(); ready = 1; digest = 64'h123456789abcdef0; configured = 7; applied = {160{1'b1}}; tick(); tick(); tick();
 end endtask
 integer lo, hi, k0;
 initial begin
  for (integer k = 0; k < NRST; k = k + 1) begin relc[k] = -1; if (depth(k) > D) D = depth(k); end
  repeat (4) tick(); por_n = 1; repeat (80) tick();          // past IGNORE: relay chains flushed with the asserted level
  if (SCN != 1) begin
   release_all(rel_host);                                     // pass 1: dly 0 -> unaligned
   lo = 1 << 30; hi = 0; for (integer k = 0; k < NRST; k = k + 1) begin if (relc[k] < lo) lo = relc[k]; if (relc[k] > hi) hi = relc[k]; end
   $display("pass 1 (dly 0): region release spread %0d..%0d cycles after the host (unaligned, D %0d)", lo - rel_host, hi - rel_host, D);
   if (SCN == 2) begin word(1, 0, value(1, 0)); end           // target 1 started before the die cfg image
   load_diecfg(SCN == 3);
   if (SCN == 2) begin
    if (!dfault || !code[3] || sealed) begin $display("BAD late target 10 not refused: fault%0d code%h sealed%0d", dfault, code, sealed); errors++; end
   end else if (SCN == 3 || SCN == 4) begin
    if (!cfault || sealed || !dfault) begin $display("BAD padding not refused: cfg_fault%0d sealed%0d disp_fault%0d", cfault, sealed, dfault); errors++; end
   end else begin
    if (!sealed || cfault || dfault) begin $display("BAD die cfg not sealed: sealed%0d cfault%0d dfault%0d code%h", sealed, cfault, dfault, code); errors++; end
    if (CAP && capb !== 1'(CAPV)) begin $display("BAD capability %b after the seal, image %0d", capb, CAPV); errors++; end
    for (integer i = 0; i < 32; i = i + 1)
     if ({ec[5*i +: 5], eb[5*i +: 5], ea[5*i +: 5]} !== ectl_word(i)) begin if (errors < 8) $display("BAD ECTL cfg group %0d", i); errors++; end
    for (integer k = 0; k < NRST; k = k + 1)
     if (dly[8*k +: 8] !== dly_of(k)) begin if (errors < 8) $display("BAD dly region %0d %0d expected %0d", k, dly[8*k +: 8], dly_of(k)); errors++; end
    // HOST re-asserts the functional resets, then releases: aligned now
    host_rst = 0; repeat (D + 40) tick();
    if (!sealed) begin $display("BAD die cfg lost across the functional reset"); errors++; end
    if (CAP && capb !== 1'(CAPV)) begin $display("BAD capability %b lost across the functional reset", capb); errors++; end
    release_all(rel_host);
    for (integer k = 0; k < NRST; k = k + 1)
     if (relc[k] != relc[0]) begin if (errors < 8) $display("BAD region %0d released at %0d, region 0 at %0d", k, relc[k] - rel_host, relc[0] - rel_host); errors++; end
    $display("pass 2: every region released %0d cycles after the host (D + 2 = %0d)", relc[0] - rel_host, D + 2);
    if (relc[0] - rel_host != D + 2) errors++;
    full_boot();
    if (!setup || dfault) begin $display("BAD setup_ready %0d fault %0d code %h", setup, dfault, code); errors++; end
   end
  end else begin
   release_all(rel_host);
   full_boot();
   if (setup) begin $display("BAD setup_ready without the die cfg image"); errors++; end
  end
  if (SCN == 4 && capb !== 1'b0) begin $display("BAD capability %b from a refused image", capb); errors++; end
  if (errors) begin $display("FAIL kv_die_cfg_boot scn%0d mut%0d errors%0d", SCN, MUT, errors); $fatal(1); end
  $display("PASS kv_die_cfg_boot scn%0d mut%0d cap%0d capv%0d regions%0d D%0d", SCN, MUT, CAP, CAPV, NRST, D);
  $finish;
 end
 initial begin #5000000; $display("FAIL kv_die_cfg_boot timeout"); $fatal(1); end
endmodule
