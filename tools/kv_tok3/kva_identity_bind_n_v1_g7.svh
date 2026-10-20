// KV-TOK3 10-19: N-step (NSTEP 1..KMAX) generalisation of the exact G7/u1 adapter. RTL and stimulus are unchanged.
// Per step k the expected identity is {epoch_k, layer_k, T-1, token_k}; the d2d face identity is the unique step whose
// configured (epoch, layer) equals the record header (uniq_ep $fatals on a shared pair), never a fallback.
// Accepted identity fields come from the actual guard's accepted tag.
localparam integer KVA_ID_W=58;
wire [KVA_ID_W-1:0] kva_exp_id [0:KMAX-1];
wire [KMAX*KVA_ID_W-1:0] kva_expected_ids;
for (genvar gi=0; gi<KMAX; gi++) begin : g_kva_exp
 assign kva_exp_id[gi] = {kva_ep[gi],6'(kva_l[gi]),18'(kva_T-1),kva_tok[gi]};
 assign kva_expected_ids[gi*KVA_ID_W +: KVA_ID_W] = kva_exp_id[gi];
end
wire [KVA_ID_W-1:0] kva_source_identity = {dut.kvs_attn.u_attn.ctl.guard.accepted_tag[58:43],
 dut.kvs_attn.u_attn.ctl.guard.accepted_tag[42:37]-6'd1,
 5'd0,dut.kvs_attn.u_attn.ctl.guard.accepted_tag[18:6],dut.kvs_attn.u_attn.ctl.guard.accepted_tag[36:19]};
reg kva_guard_source_known=0;
always @(posedge ck or negedge dut.kvs_attn.u_attn.ctl.guard.rst_n)
 if(dut.kvs_attn.u_attn.ctl.guard.rst_n === 1'b0) kva_guard_source_known <= 1;
`define KVA_AUTH_ADMIT (kva_guard_source_known && dut.kvs_attn.u_attn.ctl.guard.accepted)
`include "authority.svh"
reg kva_sampled_accept=0,kva_sampled_run=0,kva_sampled_run_ok=0,kva_sampled_done=0;
reg [KVA_ID_W-1:0] kva_sampled_identity='0;
integer kva_raw_accept=0,kva_raw_tx=0;
always @(posedge ck) begin
 if(dut.kvs_attn.u_attn.ctl.guard.accepted !== 1'b0) begin
  kva_raw_accept=kva_raw_accept+1;
  $display("KVA_RAW_ACCEPT cyc=%0d known=%b valid=%b id=%h",cyc,kva_guard_source_known,dut.kvs_attn.u_attn.ctl.guard.accepted,kva_source_identity);
 end
 kva_sampled_accept <= kva_guard_source_known ? dut.kvs_attn.u_attn.ctl.guard.accepted : 1'b0;
 kva_sampled_run <= kva_guard_source_known ? dut.kvs_attn.u_attn.ctl.run : 1'b0;
 kva_sampled_run_ok <= dut.kvs_attn.u_attn.ctl.run_ok;
 kva_sampled_done <= kva_guard_source_known ? dut.kvs_attn.u_attn.ctl.result_done : 1'b0;
 kva_sampled_identity <= kva_source_identity;
end
integer kva_face_k;
always @* begin
 kva_face_k = -1;
 for (int fk=0; fk<KMAX; fk++)
  if (fk < kva_n && kva_tp[532:517] === kva_ep[fk] && kva_tp[538:533] === 6'(kva_l[fk])) kva_face_k = fk;
end
// Wire protocol has ep/layer only. Unique configured ep/layer binds to the
// accepted full identity in the ledger; no unknown-header fallback exists.
wire [KVA_ID_W-1:0] kva_face_identity = (kva_face_k >= 0) ? kva_exp_id[kva_face_k[2:0]] : '1;
wire kva_result_v = kva_authority_known[0] && kva_tv && kva_tp[542:539]==4'd3;
wire kva_status_v = kva_tv && kva_tp[542:539]==4'd4;
integer kva_identity_errors,kva_identity_success_count,kva_identity_raw_status;
wire kva_identity_programme_executed,kva_identity_final_pass;
reg kva_identity_final_check=0;
reg kva_identity_has_clock=0;
always @(posedge ck) kva_identity_has_clock <= 1;
kva_identity_scoreboard_n #(.ID_W(KVA_ID_W),.NPROG(KMAX),.RESULT_BEATS(32),.REQUIRE_RETIRE(0)) kva_identity (
 .sample_clk(~ck && kva_identity_has_clock),.n_active(kva_n),.expected_ids(kva_expected_ids),
 .required_monitors_known(&kva_authority_known),
 .accept_v(kva_sampled_accept),.accept_id(kva_sampled_identity),
 .run_v(kva_sampled_run),.run_ok(kva_sampled_run_ok),.run_id(kva_sampled_identity),
 .source_done_v(kva_sampled_done),.source_done_id(kva_sampled_identity),
 .result_v(kva_result_v),.result_id(kva_face_identity),.result_beat({27'd0,kva_tp[516:512]}),
 .status_authoritative(kva_authority_known[0]),.status_v(kva_status_v),.status_id(kva_face_identity),
 .status_payload_ok(kva_tp[511:0] === {507'd0,5'b01001}),.status_success(1'b1),
 .final_check(kva_identity_final_check),.errors(kva_identity_errors),.successful_count(kva_identity_success_count),
 .raw_status_count(kva_identity_raw_status),.programme_executed(kva_identity_programme_executed),.final_pass(kva_identity_final_pass));
initial begin #0.001; if(kva_n < 1 || kva_n > KMAX) $fatal(1,"N-step authority adapter supports NSTEP 1..KMAX"); end
always @(negedge ck) begin
 if(kva_tv !== 1'b0) begin
  kva_raw_tx=kva_raw_tx+1;
  $display("KVA_RAW_TX cyc=%0d known=%b valid=%b kind=%h header=%h",cyc,kva_authority_known[0],kva_tv,kva_tp[542:539],kva_tp[538:517]);
 end
 if(kva_authority_known[0] && $isunknown(kva_tv)) smoke_err("unknown authoritative TX valid");
 for(int ga=0;ga<KVA_NG;ga++) begin
  if(kva_authority_known[2+ga] && $isunknown(kva_kreq[ga][0])) smoke_err("unknown authoritative K request");
  if(kva_authority_known[10+ga] && $isunknown(kva_vreq[ga][0])) smoke_err("unknown authoritative V request");
 end
end
