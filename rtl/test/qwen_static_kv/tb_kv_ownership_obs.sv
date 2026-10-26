`timescale 1ns/1ps
// KVJ-F 2026-10-17: the ownership calendar joined to its actual producers (qkd_kv_ownership_obs) exactly as
// tools/qwen_kv_die/kv_static_kvjf_join.py binds them: go <- obs.go (layer programme stage_start of stage 1),
// upstream_quiet <- obs.upstream_quiet (KV write path valids), host_quiet <- obs.host_quiet (HOST root quiet exports,
// synchronised); obs.own_active / own_fault <- the calendar; the D2D KV-local status from obs.
// Every obs output is compared each edge against an independent history model (input values sampled before each edge):
//   go(t)            = stage_start(t-1) && stage(t-1) == 1
//   upstream_quiet(t)= no word_valid / es s_v / es w_v in the samples t-1 .. t-QW (reset counts as activity)
//   host_quiet(t)    = AND of the host quiet levels at sample t-2 (two synchroniser flops + the AND register)
//   kv_active(t)     = own.active(t-1);  kv_drained(t) = all drained & no guard fault & !own.fault at t-1, & quiet(t-1)
//   kv_flush(t)      = own.fault(t-1) | any guard fault(t-1)
// (sample index t-1 = the value present before edge t-1, i.e. through one pin register.)
// Scenarios: SCN 0 = two tokens of 36 stages (one ownership window each, writer traffic inside it, no fault), then a
// drain-guard fault (ownership fault code 5, kv_flush); SCN 1 = an es command 5 edges before the compiled leave (the
// ownership calendar must fault with code 4: the evidence is enforced); SCN 2 = HOST not quiet at the compiled enter
// (code 3).  MUT 1..4 = the obs mutants (must FAIL in SCN 0).
module tb_kv_ownership_obs #(parameter integer SCN = 0, parameter integer MUT = 0, parameter integer QW = 16);
 reg ck = 0; always #5 ck = ~ck;
 reg rst_n = 0;
 reg ss = 0; reg [5:0] stage = 0;
 reg wv = 0; reg [3:0] esv = 0, ewv = 0;
 reg hlq = 1; reg [5:0] huq = 6'h3f;
 reg [31:0] drn = 32'hffffffff, gfl = 0;
 reg cwe = 0; reg [1:0] cad = 0; reg [31:0] cda = 0;
 wire go, uq, hq, kact, kdr, kfl;
 wire mode, valid, reserved, active, done, configured, ofault; wire [31:0] cycle; wire [7:0] code;
 qkd_kv_ownership_obs #(.QUIET_WIN(QW), .MUT(MUT)) obs (
  .ck(ck), .rst_n(rst_n), .stage_start(ss), .stage(stage), .word_valid(wv), .es_sv(esv), .es_wv(ewv),
  .host_launch_quiet(hlq), .host_upstream_quiet(huq), .own_active(active), .own_fault(ofault),
  .group_drained(drn), .group_fault(gfl),
  .go(go), .upstream_quiet(uq), .host_quiet(hq), .kv_active_local(kact), .kv_drained_local(kdr), .kv_flush_local(kfl));
 qkd_static_kv_ownership_calendar #(.MUT(0)) own (
  .ck(ck), .rst_n(rst_n), .cfg_we(cwe), .cfg_addr(cad), .cfg_data(cda), .go(go),
  .host_quiet(hq), .upstream_quiet(uq), .group_drained(drn), .group_fault(gfl),
  .native_mode(mode), .ownership_valid(valid), .native_reserved(reserved), .active(active), .done(done),
  .configured(configured), .cycle(cycle), .fault(ofault), .fault_code(code));
 localparam integer ENTER = 20, LEAVE = 150, DEADLINE = 200;
 // ---- history model ----
 localparam integer H = 40;
 reg [H-1:0] h_any, h_ss, h_s1, h_hq, h_act, h_dr, h_gf, h_of, h_uq;
 integer errors = 0, edges = 0, gos = 0, windows = 0, cmp = 0;
 always @(posedge ck) begin
  // samples present before this edge (DUT outputs are pre-edge here: NBA not yet applied)
  h_any <= {h_any[H-2:0], (!rst_n) | wv | (|esv) | (|ewv)};
  h_ss <= {h_ss[H-2:0], ss}; h_s1 <= {h_s1[H-2:0], stage == 6'd1};
  h_hq <= {h_hq[H-2:0], hlq & (&huq)};
  h_act <= {h_act[H-2:0], active}; h_dr <= {h_dr[H-2:0], &drn}; h_gf <= {h_gf[H-2:0], |gfl}; h_of <= {h_of[H-2:0], ofault};
  h_uq <= {h_uq[H-2:0], uq};
  edges <= edges + 1;
 end
 always @(posedge ck) begin
  #1;
  if (edges > QW + 14) begin
   // h_x[0] = sample before this edge (t), h_x[1] = before t-1, ...
   if (go !== (h_ss[1] & h_s1[1])) begin if (errors < 8) $display("BAD go e%0d", edges); errors++; end
   if (uq !== (h_any[QW:1] == 0)) begin if (errors < 8) $display("BAD upstream_quiet e%0d dut%0d", edges, uq); errors++; end
   if (hq !== h_hq[2]) begin if (errors < 8) $display("BAD host_quiet e%0d", edges); errors++; end
   if (kact !== h_act[1]) begin if (errors < 8) $display("BAD kv_active e%0d", edges); errors++; end
   if (kdr !== (h_dr[1] & !h_gf[1] & h_uq[0] & !h_of[1])) begin if (errors < 8) $display("BAD kv_drained e%0d", edges); errors++; end
   if (kfl !== (h_of[1] | h_gf[1])) begin if (errors < 8) $display("BAD kv_flush e%0d", edges); errors++; end
   cmp++;
   if (go) gos++;
  end
 end
 always @(posedge ck) if (active && cycle == ENTER) windows <= windows + 1;
 task tick; begin @(negedge ck); end endtask
 task boot(input [1:0] a, input [31:0] d); begin cwe = 1; cad = a; cda = d; tick(); cwe = 0; tick(); tick(); end endtask
 // one token: 36 stages of 10 edges; traffic keyed to the calendar's own cycle (its accepted go)
 task token(input integer scn);
  integer s, e, c;
  begin
   for (s = 1; s <= 36; s = s + 1) begin
    ss = 1; stage = s[5:0]; tick(); ss = 0;
    for (e = 1; e < 10; e = e + 1) begin
     c = active ? cycle : -1;
     wv = (c >= 30 && c < 60 && c[1:0] == 0);
     esv = (c >= 40 && c < 100 && c[2:0] == 1) ? 4'b1010 : ((scn == 1 && c == LEAVE - 5) ? 4'b0001 : 4'b0000);
     ewv = (c >= 40 && c < 100 && c[2:0] == 3) ? 4'b0101 : 4'b0000;
     drn = (c >= 60 && c < 120) ? 32'hffff7fff : 32'hffffffff;
     huq = (c >= 50 && c < 60) ? 6'h1f : 6'h3f;
     hlq = !(scn == 2 && c >= 10 && c < 25);
     tick();
    end
   end
   wv = 0; esv = 0; ewv = 0; drn = 32'hffffffff; huq = 6'h3f; hlq = 1;
   repeat (40) tick();
  end
 endtask
 initial begin
  repeat (6) tick(); rst_n = 1; repeat (QW + 8) tick();
  boot(0, ENTER); boot(1, LEAVE); boot(2, DEADLINE); boot(3, 32'h514b564d);
  if (!configured || !valid || ofault) begin $display("FAIL kv_ownership_obs boot did not seal"); $fatal(1); end
  token(SCN);
  if (SCN == 0) begin
   token(0);
   if (ofault || gos != 2 || windows != 2) errors++;
   if (ofault) $display("BAD ownership fault code %h in a clean run", code);
   if (gos != 2 || windows != 2) $display("BAD tokens: go pulses %0d ownership windows %0d (expected 2 / 2)", gos, windows);
   gfl[9] = 1; tick(); gfl[9] = 0; repeat (6) tick();
   if (!ofault || !code[5] || !kfl || valid) begin $display("BAD guard fault not stopped: fault%0d code%h flush%0d", ofault, code, kfl); errors++; end
  end else begin
   if (!ofault || !code[(SCN == 1) ? 4 : 3]) begin $display("BAD scenario %0d not caught: fault%0d code%h", SCN, ofault, code); errors++; end
   if (!kfl) begin $display("BAD kv_flush not raised"); errors++; end
  end
  if (errors) begin $display("FAIL kv_ownership_obs scn%0d mut%0d errors%0d compares%0d", SCN, MUT, errors, cmp); $fatal(1); end
  $display("PASS kv_ownership_obs scn%0d mut%0d compares%0d go%0d windows%0d fault_code%h", SCN, MUT, cmp, gos, windows, code);
  $finish;
 end
endmodule
