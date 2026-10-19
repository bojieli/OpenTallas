`timescale 1ns/1ps
// MU-KV-PROG 10-19: 4 users interleaved stage by stage through the KV layer programme (qkd_static_kv_layer_programme_mu)
// into the KV-die consumers that latch its metadata: the writer programme (qkd_kv_native_programme VMAP 1), the
// attention programme (qkd_native_attention_programme LAND 1) with its calendar generator (qkd_attn_cal_gen STRETCH 1,
// the die parameters), and the ownership observer + calendar (qkd_kv_ownership_obs -> qkd_static_kv_ownership_calendar_mu).
// Wiring as in qkd_kvs_ctl / qkd_kvs_attn (tools/qwen_kv_die/kv_static.py template, kv_static_attn_join.cal_gen_join).
// Calendar: kvprog_cal_<good|bad>.hex from kvprog_cal.py (production stage roots, lprg_mu GAP table, owner order).
// Parameters: LMU (lprg_mu MU), OMU / OMUT (ownership _mu MU / MUT).  Plusargs: +CAL=<hex> +USERS=<mask> +ROOTS=0|1
// (ownership roots single-user / MU) +XMUT=0|1|2 (bench negative controls: 1 = consumers see the metadata of the
// PREVIOUS lprg event (previous owner); 2 = the lprg context is chosen by the wrong epoch bits [3:2]) +OWNCHK=1.
// Checks (self, $fatal): every writer slot / expected descriptor and every attention request carries the identity of the
// user that owns the window in the static calendar (epoch {seq14,user2}, stage, token, position, generation); the
// attention service face (RX CMD/Q, RESULT, TX slots) is driven with that user's identity, so a programme that latched
// another user's metadata faults; no programme / calendar / ownership fault; 36 writer windows (4 slots) and 36 attention
// operations (1 request, 32 Q, 33 TX) per started user; OWNCHK: native_mode = 1 at every attention run and
// native_reserved = 1 at every writer slot.  Prints per-user hashes (cycle-stamped records) for the cross-run identity
// checks of run_kvprog.sh (alone == together; user 0 == MU 0).
module tb_kvprog_mu;
 parameter integer LMU = 1, OMU = 1, OMUT = 0;
 localparam integer P = 6836, NS = 36;
 reg ck = 0; always #5 ck = ~ck;
 reg rst_n = 0;
 integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
 // ---- calendar ----
 reg [31:0] cal [0:295];
 integer users = 15, roots = 0, xmut = 0, ownchk = 0;
 reg [1023:0] calf;
 // ---- per-user identity: epoch {seq14, user2}, token, position, generation ----
 function automatic [15:0] E(input integer u); E = {14'h0123, 2'(u)}; endfunction
 function automatic [17:0] TOK(input integer u); TOK = 18'(1000 + 7 * u); endfunction
 function automatic [17:0] POS(input integer u); POS = (u == 0) ? 18'd100 : (u == 1) ? 18'd777 : (u == 2) ? 18'd2049 : 18'd4500; endfunction
 function automatic [1:0] GEN(input integer u); GEN = 2'(u + 1); endfunction
 // ---- lprg ----
 reg l_we = 0; reg [8:0] l_addr = 0; reg [63:0] l_data = 0;
 reg start = 0; reg [15:0] a_epoch = 0; reg [17:0] a_token = 0, a_pos = 0; reg [1:0] a_gen = 0;
 wire ctrl_go, kgo, vgo, a_issue, a_run, w_start, link_start, stage_start, stage_done, quiet;
 wire [5:0] completed_stage, l_stage, l_layer; wire [15:0] l_epoch; wire [17:0] l_token, l_pos; wire [13:0] l_ctx;
 wire [1:0] l_gen; wire l_cfg, l_act, l_done, l_fault; wire [7:0] l_fc; wire [31:0] l_age, l_tc;
 wire [15:0] a_epoch_in = (xmut == 2) ? {a_epoch[15:4], a_epoch[1:0], a_epoch[3:2]} : a_epoch;
 qkd_static_kv_layer_programme_mu #(.MUT(0), .MU(LMU)) u_lprg (.ck(ck), .rst_n(rst_n), .cfg_we(l_we), .cfg_addr(l_addr),
  .cfg_data(l_data), .start(start), .authority_valid(1'b1), .programme_authorized(1'b1), .programme_epoch(16'h00a5),
  .programme_digest(64'hfeed_0123_4567_89ab), .authority_epoch(a_epoch_in), .authority_token(a_token),
  .authority_position(a_pos), .authority_generation(a_gen), .ctrl_go(ctrl_go), .kgo(kgo), .vgo(vgo),
  .attention_issue(a_issue), .attention_run(a_run), .writer_start(w_start), .link_start(link_start),
  .stage_start(stage_start), .stage_done(stage_done), .expected_upstream_quiet(quiet), .completed_stage(completed_stage),
  .stage(l_stage), .layer(l_layer), .epoch(l_epoch), .token(l_token), .position(l_pos), .ctx_t(l_ctx),
  .generation(l_gen), .configured(l_cfg), .active(l_act), .done(l_done), .fault(l_fault), .fault_code(l_fc),
  .age(l_age), .token_cycles(l_tc));
 // ---- XMUT 1 shim: metadata of the previous lprg event (bench negative control) ----
 wire ev = ctrl_go | kgo | vgo | a_issue | a_run | w_start | link_start | stage_start | stage_done;
 reg [73:0] m_last = 0, m_prev = 0;
 wire [73:0] m_live = {l_stage, l_epoch, l_token, l_pos[17:0], l_ctx, l_gen};
 always @(posedge ck) if (ev) begin m_prev <= m_last; m_last <= m_live; end
 wire [73:0] m_use = (xmut == 1) ? m_prev : m_live;
 wire [5:0] c_stage = m_use[73:68]; wire [15:0] c_epoch = m_use[67:52]; wire [17:0] c_token = m_use[51:34];
 wire [17:0] c_pos = m_use[33:16]; wire [13:0] c_ctx = m_use[15:2]; wire [1:0] c_gen = m_use[1:0];
 // ---- writer programme ----
 reg w_we = 0; reg [7:0] w_addr = 0; reg [63:0] w_data = 0;
 wire ws_slot, kvn_slot; wire [1:0] ws_idx, ws_gen, x_gen; wire [58:0] ws_id, x_id; wire w_cfg, w_act, w_done, w_fault;
 wire [31:0] w_cyc; wire [3:0] x_v; wire [19:0] x_pc; wire [1:0] x_st; wire [28:0] x_addr;
 qkd_kv_native_programme #(.MUT(0), .VMAP(1)) u_wprg (.ck(ck), .rst_n(rst_n), .cfg_we(w_we), .cfg_addr(w_addr),
  .cfg_data(w_data), .start(w_start), .stage(c_stage), .epoch(c_epoch), .token(c_token), .position(c_pos[12:0]),
  .generation(c_gen), .compiled_word_slot(ws_slot), .compiled_word_index(ws_idx), .compiled_identity(ws_id),
  .compiled_generation(ws_gen), .kvn_word_slot(kvn_slot), .configured(w_cfg), .active(w_act), .done(w_done),
  .fault(w_fault), .cycle(w_cyc), .expected_valid(x_v), .expected_pc(x_pc), .expected_stack(x_st),
  .expected_identity(x_id), .expected_generation(x_gen), .expected_address(x_addr));
 // ---- attention calendar generator + programme ----
 wire [175:0] cg_cal; wire [15:0] cg_rx, cg_txf, cg_end, cg_ep; wire cg_done, cg_valid, cg_fault;
 qkd_attn_cal_gen #(.G3S2(1), .RX_CMD(2), .STRETCH(1), .D_QK(57), .D_RL(76), .SERVICE_END(1777), .MUT(0)) u_cal (
  .ck(ck), .rst_n(rst_n), .go(stage_start), .ctx_t(c_ctx), .epoch(c_epoch), .cal(cg_cal), .rx_cmd(cg_rx),
  .tx_first(cg_txf), .end_age(cg_end), .cal_epoch(cg_ep), .done(cg_done), .valid(cg_valid), .fault(cg_fault));
 reg rx_event = 0; reg [547:0] rx_payload = 0; reg tx_slot = 0; reg [3:0] tx_kind = 0; reg [4:0] tx_beat = 0;
 reg r_valid = 0, r_done = 0; reg [4:0] r_beat = 0; reg [511:0] r_data = 0; reg [15:0] r_epoch = 0; reg [5:0] r_layer = 0;
 wire t_valid, rq_valid, q_valid, r_res, a_busy, a_fault; wire [547:0] t_payload; wire [15:0] rq_epoch, a_age;
 wire [5:0] rq_layer; wire [17:0] rq_pos; wire [175:0] rq_cal; wire [4:0] q_beat; wire [511:0] q_data; wire [536:0] prg_l;
 qkd_native_attention_programme #(.MUT(0), .LAND(1)) u_attn (.ck(ck), .rst_n(rst_n), .issue(a_issue), .run(a_run),
  .fused_program_capability(1'b1), .authority_valid(l_act), .authority_epoch(c_epoch), .authority_token(c_token),
  .authority_position(c_pos), .authority_stage(c_stage), .compiled_calendar(cg_cal), .compiled_rx_cmd(cg_rx),
  .compiled_tx_first(cg_txf), .compiled_end(cg_end), .rx_event(rx_event), .rx_payload(rx_payload), .tx_slot(tx_slot),
  .tx_slot_kind(tx_kind), .tx_slot_beat(tx_beat), .tx_valid(t_valid), .tx_payload(t_payload),
  .request_valid(rq_valid), .request_ready(1'b1), .request_epoch(rq_epoch), .request_layer(rq_layer),
  .request_position(rq_pos), .request_calendar(rq_cal), .q_valid(q_valid), .q_beat(q_beat), .q_data(q_data),
  .result_valid(r_valid), .result_beat(r_beat), .result_data(r_data), .result_epoch(r_epoch), .result_layer(r_layer),
  .result_done(r_done), .service_fault(1'b0), .result_reserved(r_res), .busy(a_busy), .fault(a_fault), .age(a_age),
  .prg_l(prg_l));
 // ---- ownership observer + calendar ----
 reg o_we = 0; reg [1:0] o_addr = 0; reg [31:0] o_data = 0;
 wire o_go, o_uq, o_hq, kv_act, kv_drn, kv_fl;
 wire own_nm, own_ov, own_nr, own_act, own_done, own_cfg, own_fault; wire [31:0] own_cyc; wire [7:0] own_fc;
 wire [31:0] drained = {32{!a_busy}};               // the PC groups drain only while no attention operation runs
 qkd_kv_ownership_obs #(.QUIET_WIN(16), .MUT(0)) u_oobs (.ck(ck), .rst_n(rst_n), .stage_start(stage_start),
  .stage(l_stage), .word_valid(kvn_slot), .es_sv(4'd0), .es_wv(4'd0), .host_launch_quiet(1'b1),
  .host_upstream_quiet(6'h3f), .own_active(own_act), .own_fault(own_fault), .group_drained(drained),
  .group_fault(32'd0), .go(o_go), .upstream_quiet(o_uq), .host_quiet(o_hq), .kv_active_local(kv_act),
  .kv_drained_local(kv_drn), .kv_flush_local(kv_fl));
 qkd_static_kv_ownership_calendar_mu #(.MUT(OMUT), .MU(OMU)) u_own (.ck(ck), .rst_n(rst_n), .cfg_we(o_we),
  .cfg_addr(o_addr), .cfg_data(o_data), .go(o_go), .host_quiet(o_hq), .upstream_quiet(o_uq), .group_drained(drained),
  .group_fault(32'd0), .native_mode(own_nm), .ownership_valid(own_ov), .native_reserved(own_nr), .active(own_act),
  .done(own_done), .configured(own_cfg), .cycle(own_cyc), .fault(own_fault), .fault_code(own_fc));
 // ---- hashes ----
 reg [63:0] hw [0:3], ha [0:3], hown;
 integer nslot [0:3], nwin [0:3], nreq [0:3], nq [0:3], ntx [0:3], nop [0:3], nx [0:3], fails = 0;
 function automatic [63:0] mix(input [63:0] h, input [63:0] x);
  mix = ((h ^ x) * 64'h0000_0100_0000_01b3) ^ (h >> 29);
 endfunction
 function automatic [63:0] fold(input [575:0] v);
  fold = 0; for (int i = 0; i < 9; i++) fold = fold ^ (v[64*i +: 64] << i) ^ (v[64*i +: 64] >> (64 - i));
 endfunction
 // ---- owner order (static calendar), filtered to the started users ----
 integer ord_u [0:143], ord_s [0:143], nord = 0, wi = 0, ai = 0, wu = -1, ws = 0, au = -1, as_ = 0, wslots = 0;
 task automatic fail(input string m); begin fails = fails + 1; if (fails < 6) $display("FAIL cyc %0d: %s", cyc, m); end endtask
 function automatic [58:0] IDN(input integer u, input integer s); IDN = {E(u), 6'(s), TOK(u), 13'(POS(u)), 6'd0}; endfunction
 // writer windows: start pulse -> next owner in the order
 always @(posedge ck) if (rst_n) begin
  if (w_start) begin
   if (wu >= 0 && wslots != 4) fail($sformatf("writer window u%0d s%0d had %0d slots", wu, ws, wslots));
   if (wi >= nord) fail("writer start beyond the calendar"); else begin wu = ord_u[wi]; ws = ord_s[wi]; wi = wi + 1; end
   wslots = 0; nwin[wu] = nwin[wu] + 1;
  end
  if (ws_slot) begin
   if (wu < 0) fail("writer slot without window");
   else begin
    if (ws_id != IDN(wu, ws) || ws_gen != GEN(wu)) fail($sformatf("writer slot identity %h gen %0d, owner u%0d s%0d wants %h", ws_id, ws_gen, wu, ws, IDN(wu, ws)));
    if (ws_idx != 2'(wslots)) fail("writer slot index order");
    if (ownchk && !own_nr) fail("writer slot while the KV die is not natively reserved");
    hw[wu] = mix(hw[wu], {32'(cyc), 6'(ws), ws_idx, ws_gen, 18'd0}); hw[wu] = mix(hw[wu], 64'(ws_id));
    wslots = wslots + 1; nslot[wu] = nslot[wu] + 1;
   end
  end
  if (x_v != 0 && wu >= 0) begin
   if (x_id != IDN(wu, ws) || x_gen != GEN(wu)) fail("writer expected descriptor identity");
   hw[wu] = mix(hw[wu], {32'(cyc), x_v, x_st, x_gen, 24'd0}); hw[wu] = mix(hw[wu], {x_pc, 15'd0, x_addr});
   nx[wu] = nx[wu] + 1;
  end
 end
 // attention operations: issue -> next owner; the service face is driven with the OWNER's identity
 always @(posedge ck) if (rst_n) begin
  if (a_issue) begin
   if (ai >= nord) fail("attention issue beyond the calendar"); else begin au = ord_u[ai]; as_ = ord_s[ai]; ai = ai + 1; end
   nop[au] = nop[au] + 1;
  end
  if (a_run && ownchk && !own_nm) fail("attention run while the KV die is not in native mode");
  if (rq_valid) begin
   if (rq_epoch != E(au) || rq_layer != 6'(as_ - 1) || rq_pos != {5'd0, 13'(POS(au))})
    fail($sformatf("attention request ep %h layer %0d pos %0d, owner u%0d s%0d", rq_epoch, rq_layer, rq_pos, au, as_));
   ha[au] = mix(ha[au], {32'(cyc), rq_epoch, 6'd0, rq_layer, 4'd0}); ha[au] = mix(ha[au], fold({400'd0, rq_cal}));
   nreq[au] = nreq[au] + 1;
  end
  if (q_valid) begin ha[au] = mix(ha[au], {32'(cyc), 27'd0, q_beat}); ha[au] = mix(ha[au], fold({64'd0, q_data})); nq[au] = nq[au] + 1; end
  if (t_valid) begin ha[au] = mix(ha[au], 64'(cyc)); ha[au] = mix(ha[au], fold({28'd0, t_payload})); ntx[au] = ntx[au] + 1; end
 end
 localparam integer TXF = 2 + 2 + 1777 - 31;       // qkd_attn_cal_gen STRETCH: tx_first = RX_CMD + 2 + SERVICE_END - 31
 always @(negedge ck) begin
  rx_event = 0; tx_slot = 0; r_valid = 0; r_done = 0;
  if (a_busy && au >= 0) begin
   if (a_age >= 2 && a_age <= 34) begin
    rx_event = 1;
    rx_payload = {5'd0, (a_age == 2) ? 4'd1 : 4'd2, 6'(as_ - 1), E(au), (a_age == 2) ? 5'd0 : 5'(a_age - 3),
                  (a_age == 2) ? {493'd0, 5'd0, 13'(POS(au)), 1'b1} : {448'd0, 16'(au), 16'(as_), 16'(a_age), 16'hbeef}};
   end
   if ((a_age >= TXF && a_age < TXF + 32) || a_age == TXF + 33) begin
    tx_slot = 1; tx_kind = (a_age == TXF + 33) ? 4'd4 : 4'd3; tx_beat = (a_age == TXF + 33) ? 5'd0 : 5'(a_age - TXF);
   end
   if (a_age >= TXF && a_age < TXF + 32) begin
    r_valid = 1; r_beat = 5'(a_age - TXF); r_epoch = E(au); r_layer = 6'(as_ - 1);
    r_data = {448'd0, 16'(au), 16'(as_), 16'(r_beat), 16'hc0de};
   end
   if (a_age == TXF + 32) r_done = 1;
  end
 end
 // first attention fault: name its source (diagnostic print)
 reg afd = 0;
 always @(posedge ck) if (a_fault && !afd) begin
  afd <= 1;
  $display("ATTN_FAULT cyc %0d age %0d busy %0d local %0d guard %0d(%b) record %0d slot %0d producer %0d rx_cmd %0d tx_first %0d end %0d",
   cyc, a_age, a_busy, u_attn.ctl.local_fault, u_attn.ctl.guard_fault, u_attn.ctl.guard.fault_cause, u_attn.ctl.record_fault,
   u_attn.ctl.slot_fault_o, u_attn.producer_fault, cg_rx, cg_txf, cg_end);
 end
 // ownership trace hash (every edge)
 always @(posedge ck) if (rst_n) hown = mix(hown, {32'(cyc), own_nm, own_ov, own_nr, own_act, own_done, own_cfg, own_fault, 1'b0, own_fc, 16'd0});
 // ---- boot + starts ----
 integer u, s, k, last_end, t0;
 initial begin
  if (!$value$plusargs("CAL=%s", calf)) calf = "kvprog_cal_good.hex";
  if ($value$plusargs("USERS=%d", users)) begin end
  if ($value$plusargs("ROOTS=%d", roots)) begin end
  if ($value$plusargs("XMUT=%d", xmut)) begin end
  if ($value$plusargs("OWNCHK=%d", ownchk)) begin end
  $readmemh(calf, cal);
  for (k = 0; k < 4; k++) begin hw[k] = 64'h1; ha[k] = 64'h2; nslot[k] = 0; nwin[k] = 0; nreq[k] = 0; nq[k] = 0; ntx[k] = 0; nop[k] = 0; nx[k] = 0; end
  hown = 64'h3;
  for (k = 0; k < 144; k++) if (users[cal[144 + k][9:8]]) begin ord_u[nord] = cal[144 + k][9:8]; ord_s[nord] = cal[144 + k][7:0]; nord++; end
  repeat (4) @(negedge ck); rst_n = 1; repeat (4) @(negedge ck);
  // lprg: rows 0..323, digest 324, epoch 325, (MU) GAP 326..469, seal
  // one boot length for every build (471 edges), so the start edges -- and every hashed cycle -- are build independent
  for (k = 0; k < 471; k++) begin
   l_we = (LMU != 0) || k <= 326; l_addr = 9'(k);
   if (k < 324) begin
    case (k % 9) 0: l_data = 227; 1: l_data = 227; 2: l_data = 1273; 3: l_data = 606; 4: l_data = 610; 5: l_data = 642;
     6: l_data = 3; 7: l_data = 2396; default: l_data = P; endcase
   end else if (k == 324) l_data = 64'hfeed_0123_4567_89ab;
   else if (k == 325) l_data = 64'h00a5;
   else if (LMU && k < 470) l_data = {32'd0, cal[k - 326]};
   else l_data = 64'h514b564c59523336;
   if (k < 181) begin w_we = 1; w_addr = 8'(k); w_data = (k == 180) ? 64'h514b565052473336 : ((k % 5) == 4 ? 64'd12 : 64'(4 + k % 5)); end
   else w_we = 0;
   if (k < 4) begin o_we = 1; o_addr = 2'(k); o_data = (k == 3) ? 32'h514b564d : cal[288 + 3 * roots + k]; end else o_we = 0;
   @(negedge ck);
  end
  l_we = 0; w_we = 0; o_we = 0; repeat (8) @(negedge ck);
  if (!l_cfg || !w_cfg || !own_cfg || l_fault || w_fault || own_fault) $fatal(1, "BOOT cfg %b%b%b fault %b%b%b", l_cfg, w_cfg, own_cfg, l_fault, w_fault, own_fault);
  // starts: user u on consecutive edges (accepted edge A_u = A_0 + u); a user not in USERS leaves its edge idle
  t0 = cyc;
  for (u = 0; u < 4; u++) begin
   start = users[u]; a_epoch = E(u); a_token = TOK(u); a_pos = POS(u); a_gen = GEN(u);
   @(negedge ck);
  end
  start = 0;
  last_end = (users == 1) ? cal[295] : cal[294];
  while (cyc < t0 + last_end + 4000 && !(l_fault || w_fault || a_fault || cg_fault || own_fault) && fails == 0) @(negedge ck);
  repeat (20) @(negedge ck);
  if (l_fault) fail($sformatf("layer programme fault code %h", l_fc));
  if (w_fault) fail("writer programme fault");
  if (a_fault) fail("attention programme fault");
  if (cg_fault) fail("attention calendar generator fault");
  if (own_fault) fail($sformatf("ownership calendar fault code %h", own_fc));
  for (u = 0; u < 4; u++) if (users[u]) begin
   if (nwin[u] != 36 || nslot[u] != 144 || nx[u] != 72 || nop[u] != 36 || nreq[u] != 36 || nq[u] != 36 * 32 || ntx[u] != 36 * 33)
    fail($sformatf("u%0d counts win %0d slots %0d xdesc %0d ops %0d req %0d q %0d tx %0d", u, nwin[u], nslot[u], nx[u], nop[u], nreq[u], nq[u], ntx[u]));
  end
  for (u = 0; u < 4; u++) if (users[u]) $display("HASH u%0d writer %h attention %h", u, hw[u], ha[u]);
  $display("HASH own %h", hown);
  if (fails == 0) $display("PASS KVPROG_MU LMU=%0d OMU=%0d OMUT=%0d users=%0d roots=%0d xmut=%0d cal=%0s end_cycle=%0d", LMU, OMU, OMUT, users, roots, xmut, calf, cyc);
  else $display("FAIL KVPROG_MU fails=%0d LMU=%0d OMU=%0d OMUT=%0d users=%0d xmut=%0d", fails, LMU, OMU, OMUT, users, xmut);
  $finish;
 end
endmodule
