`timescale 1ns/1ps
// MU-KV-PEER 10-19 (Qwen ROM 4 users): drop-in successor of qkd_host_lifecycle_collected (same ports and parameters).
//   MU 0: instantiates the unchanged original (behaviour-identical by construction; original file untouched).
//   MU 1: the die-0 coordinator lifecycle for four users in flight (user = TAG epoch[1:0] = TAG59[44:43]; request
//         user = request position [17:16]).
//   Allocator / cohort: ot_qwen_tp8_token_epoch_allocator_mu #(MU 1) (one allocation per user, epoch {seq14,user2})
//         and ot_qwen_tp8_token_cohort_mu #(MU 1) (one cohort per user, dispatch in begin order).
//   Terminal queue: an engine result or a rank cancel of a user with no terminal / POST pending is captured as that
//         user's terminal and queued in arrival order (4 entries).  The head is presented to the allocator and, when
//         that user's cohort was begun, to the cohort -- only when the allocator accepts it on that edge (all drains,
//         or other users' allocations in flight: the _mu allocator rule), so both pulses coincide.  One idle edge
//         separates consecutive presentations (the allocator / cohort one-shot consume flags re-arm on it).
//   POST queue: an accepted terminal becomes that user's POST-pending identity; POSTs retire in acceptance order and
//         each must name the queue head (else lifecycle_fault).  A user is admitted again only after its POST
//         (request_ready low for that user: the original's host-boundary admission handshake, per user).
//   acknowledged_tag / acknowledged_generation: during the terminal_accepted pulse, the identity being accepted;
//         otherwise the last accepted one (qkd_host_coordinator_services_mu / qkd_host_tp8_coordinator_mu hand it to
//         the POST collector and the class9 codec instead of the latest grant).
//   Cancels: a rank cancel is acknowledged (all drains, as the original) when it names the terminal being accepted,
//         a POST-pending identity, or the user's last retired identity (the token service may cancel a retained
//         request whose step already terminated).  A result or cancel naming a different identity than the user's
//         pending terminal / POST is a sticky lifecycle_fault (fail closed).  Recovery as the original, all queues empty.
//   No new ready/credit/stall: request_ready per user and the existing result/cancel faces only.
module qkd_host_lifecycle_collected_mu #(parameter [15:0] INITIAL_EPOCH = 16'd0, parameter integer MU = 1) (
 input wire clk, por_n, warm_ready,
 input wire request_valid, output wire request_ready,
 input wire [17:0] request_token, request_position,
 input wire [1:0] request_generation,
 output wire grant_valid, input wire grant_ready,
 output wire [15:0] grant_epoch,
 output wire [17:0] grant_token, grant_position,
 output wire [1:0] grant_generation,
 output wire [58:0] grant_tag,
 output wire allocated_valid, allocated_delivered,
 input wire [7:0] participant_valid,
 input wire [471:0] participant_tag,
 input wire [15:0] participant_generation,
 output wire [7:0] participant_accepted,
 input wire engine_admit_ready,
 input wire [7:0] participant_ready,
 output wire dispatch_valid, dispatched,
 output wire [58:0] cohort_tag,
 output wire [1:0] cohort_generation,
 output wire [7:0] accepted_ranks,
 input wire result_valid, result_done, result_fault,
 input wire [58:0] result_tag,
 input wire [1:0] result_generation,
 input wire [7:0] cancel_valid, cancel_done, cancel_fault,
 input wire [471:0] cancel_tag,
 input wire [15:0] cancel_generation,
 output wire [7:0] cancel_accepted,
 input wire [7:0] kv_drained, vm_drained, collective_drained, host_drained,
 input wire post_retired,
 input wire [58:0] post_tag,
 input wire [1:0] post_generation,
 output wire post_pending,
 output wire [58:0] acknowledged_tag,
 output wire [1:0] acknowledged_generation,
 input wire recovery_start,
 input wire [7:0] links_drained, link_reset_seen, retraining_done,
 output wire link_reset_request, retraining_request,
 output wire recovery_complete,
 output wire wrap_locked, identity_fault,
 output wire terminal_accepted,
 output wire lifecycle_fault
);
generate if (MU == 0) begin : g_plain
 qkd_host_lifecycle_collected #(.INITIAL_EPOCH(INITIAL_EPOCH)) u_plain (
  .clk(clk), .por_n(por_n), .warm_ready(warm_ready), .request_valid(request_valid), .request_ready(request_ready),
  .request_token(request_token), .request_position(request_position), .request_generation(request_generation),
  .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token),
  .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag),
  .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered), .participant_valid(participant_valid),
  .participant_tag(participant_tag), .participant_generation(participant_generation), .participant_accepted(participant_accepted),
  .engine_admit_ready(engine_admit_ready), .participant_ready(participant_ready), .dispatch_valid(dispatch_valid),
  .dispatched(dispatched), .cohort_tag(cohort_tag), .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks),
  .result_valid(result_valid), .result_done(result_done), .result_fault(result_fault), .result_tag(result_tag),
  .result_generation(result_generation), .cancel_valid(cancel_valid), .cancel_done(cancel_done), .cancel_fault(cancel_fault),
  .cancel_tag(cancel_tag), .cancel_generation(cancel_generation), .cancel_accepted(cancel_accepted),
  .kv_drained(kv_drained), .vm_drained(vm_drained), .collective_drained(collective_drained), .host_drained(host_drained),
  .post_retired(post_retired), .post_tag(post_tag), .post_generation(post_generation), .post_pending(post_pending),
  .acknowledged_tag(acknowledged_tag), .acknowledged_generation(acknowledged_generation), .recovery_start(recovery_start),
  .links_drained(links_drained), .link_reset_seen(link_reset_seen), .retraining_done(retraining_done),
  .link_reset_request(link_reset_request), .retraining_request(retraining_request), .recovery_complete(recovery_complete),
  .wrap_locked(wrap_locked), .identity_fault(identity_fault), .terminal_accepted(terminal_accepted),
  .lifecycle_fault(lifecycle_fault));
end else begin : g_mu
 reg [7:0] cancel_acknowledged;
 always @(posedge clk or negedge por_n) begin
  if (!por_n) cancel_acknowledged <= 0;
  else cancel_acknowledged <= (cancel_acknowledged | cancel_accepted) & cancel_valid;
 end
 // per-user state
 reg [3:0] ab, coh, tp, t_coh, t_done, t_fault, pp, lt_v;
 reg [58:0] t_tag [0:3]; reg [1:0] t_gen [0:3];
 reg [58:0] ack_tag [0:3]; reg [1:0] ack_gen [0:3];
 reg [1:0] tq [0:3]; reg [1:0] tw, tr; reg [2:0] tn;     // terminal queue (arrival order)
 reg [1:0] pq [0:3]; reg [1:0] pw, pr; reg [2:0] pn;     // POST queue (acceptance order)
 reg gap, lf, rc;
 reg [58:0] last_ack_tag; reg [1:0] last_ack_gen;
 reg recovery_active; reg [7:0] reset_witness, train_witness;
 wire allocator_fault, cohort_fault, cohort_active, cohort_terminal_accepted, cohort_begin_ready, unused_allocator_busy;
 wire alloc_request_ready, alloc_terminal_accepted;
 wire all_drained = (&kv_drained) && (&vm_drained) && (&collective_drained) && (&host_drained);
 wire [1:0] h = tq[tr];
 wire [1:0] uq = request_position[17:16];
 wire [1:0] ub = grant_tag[44:43];
 wire alone_a = (ab & ~(4'd1 << h)) == 4'd0;
 wire present = tn != 0 && !gap && (all_drained || !alone_a);
 assign terminal_accepted = alloc_terminal_accepted;
 assign lifecycle_fault = lf;
 assign recovery_complete = rc;
 assign identity_fault = allocator_fault || cohort_fault || lf;
 assign post_pending = pn != 0;
 assign acknowledged_tag = alloc_terminal_accepted ? t_tag[h] : last_ack_tag;
 assign acknowledged_generation = alloc_terminal_accepted ? t_gen[h] : last_ack_gen;
 wire admission_ready = warm_ready && !recovery_active && !lf && !cohort_fault;
 wire begin_valid = grant_valid && grant_ready;
 assign request_ready = alloc_request_ready && !pp[uq];
 // event capture: one new terminal per edge (the result first, else the lowest cancelling rank)
 reg sel; reg [1:0] su; reg [58:0] stag; reg [1:0] sgen; reg sdone, sfault;
 always @* begin
  sel = 0; su = 0; stag = 0; sgen = 0; sdone = 0; sfault = 0;
  if (result_valid && !tp[result_tag[44:43]] && !pp[result_tag[44:43]]) begin
   sel = 1; su = result_tag[44:43]; stag = result_tag; sgen = result_generation; sdone = result_done; sfault = result_fault;
  end
  for (integer n = 0; n < 8; n = n + 1)
   if (!sel && cancel_valid[n] && !tp[cancel_tag[59*n+43 +: 2]] && !pp[cancel_tag[59*n+43 +: 2]] &&
       !(lt_v[cancel_tag[59*n+43 +: 2]] && cancel_tag[59*n +: 59] == ack_tag[cancel_tag[59*n+43 +: 2]] &&
         cancel_generation[2*n +: 2] == ack_gen[cancel_tag[59*n+43 +: 2]]) &&
       !(result_valid && result_tag[44:43] == cancel_tag[59*n+43 +: 2])) begin
    sel = 1; su = cancel_tag[59*n+43 +: 2]; stag = cancel_tag[59*n +: 59]; sgen = cancel_generation[2*n +: 2];
    sdone = cancel_done[n]; sfault = cancel_fault[n];
   end
 end
 wire recovery_fire = recovery_active && (&links_drained) && (&reset_witness) && (&train_witness) &&
                      all_drained && tn == 0 && pn == 0 && !allocated_valid && !cohort_active && !request_valid &&
                      !(|participant_valid) && !result_valid && !(|cancel_valid);
 assign link_reset_request = recovery_active && (&links_drained);
 assign retraining_request = link_reset_request && (&reset_witness);
 ot_qwen_tp8_token_epoch_allocator_mu #(.INITIAL_EPOCH(INITIAL_EPOCH), .MU(1)) allocator (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .request_valid(request_valid && !pp[uq]), .request_ready(alloc_request_ready), .request_token(request_token),
  .request_position(request_position), .request_generation(request_generation),
  .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token),
  .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag),
  .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered),
  .terminal_valid(present), .terminal_tag(t_tag[h]), .terminal_generation(t_gen[h]),
  .terminal_done(t_done[h]), .terminal_fault(t_fault[h]),
  .terminal_kv_drained(&kv_drained), .terminal_vm_drained(&vm_drained),
  .terminal_collective_drained(&collective_drained), .terminal_host_drained(&host_drained),
  .wrap_fence_valid(recovery_fire && (wrap_locked || allocator_fault)), .wrap_links_drained(&links_drained),
  .wrap_link_reset_seen(&reset_witness), .wrap_retraining_done(&train_witness),
  .busy(unused_allocator_busy), .wrap_locked(wrap_locked), .identity_fault(allocator_fault), .terminal_accepted(alloc_terminal_accepted));
 reg [7:0] pmask;
 always @* for (integer n = 0; n < 8; n = n + 1)
  pmask[n] = !tp[participant_tag[59*n+43 +: 2]] && !pp[participant_tag[59*n+43 +: 2]];
 ot_qwen_tp8_token_cohort_mu #(.MU(1)) cohort (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .begin_valid(begin_valid), .begin_ready(cohort_begin_ready), .begin_tag(grant_tag), .begin_generation(grant_generation),
  .request_valid(participant_valid & pmask), .request_tag(participant_tag), .request_generation(participant_generation),
  .request_credit(participant_accepted), .dispatch_valid(dispatch_valid),
  .dispatch_ready(engine_admit_ready && (&participant_ready)),
  .cohort_tag(cohort_tag), .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks),
  .active(cohort_active), .dispatched(dispatched), .identity_fault(cohort_fault),
  .terminal_valid(present && t_coh[h]), .terminal_tag(t_tag[h]),
  .terminal_generation(t_gen[h]), .terminal_done(t_done[h]), .terminal_fault(t_fault[h]),
  .kv_drained(&kv_drained), .vm_drained(&vm_drained), .collective_drained(&collective_drained), .host_drained(&host_drained),
  .terminal_accepted(cohort_terminal_accepted), .recovery_valid(recovery_fire),
  .links_drained(&links_drained), .link_reset_seen(&reset_witness), .retraining_done(&train_witness));
 genvar r;
 for (r = 0; r < 8; r = r + 1) begin : ack
  wire [1:0] cu = cancel_tag[59*r+43 +: 2];
  assign cancel_accepted[r] = !cancel_acknowledged[r] && cancel_valid[r] && all_drained && (
   (alloc_terminal_accepted && cancel_tag[59*r +: 59] == t_tag[h] && cancel_generation[2*r +: 2] == t_gen[h]) ||
   ((pp[cu] || lt_v[cu]) && cancel_tag[59*r +: 59] == ack_tag[cu] && cancel_generation[2*r +: 2] == ack_gen[cu]));
 end
 integer k;
 always @(posedge clk or negedge por_n) begin
  if (!por_n) begin
   ab <= 0; coh <= 0; tp <= 0; t_coh <= 0; t_done <= 0; t_fault <= 0; pp <= 0; lt_v <= 0;
   tw <= 0; tr <= 0; tn <= 0; pw <= 0; pr <= 0; pn <= 0; gap <= 0; lf <= 0; rc <= 0;
   last_ack_tag <= 0; last_ack_gen <= 0; recovery_active <= 0; reset_witness <= 0; train_witness <= 0;
   for (k = 0; k < 4; k = k + 1) begin t_tag[k] <= 0; t_gen[k] <= 0; ack_tag[k] <= 0; ack_gen[k] <= 0; tq[k] <= 0; pq[k] <= 0; end
  end else begin
   rc <= 0; gap <= 0;
   if (request_valid && request_ready) begin ab[uq] <= 1; lt_v[uq] <= 0; end
   if (begin_valid && !cohort_begin_ready) lf <= 1;
   if (begin_valid && cohort_begin_ready) coh[ub] <= 1;
   // identity checks against the user's pending terminal / POST (fail closed)
   if (result_valid && tp[result_tag[44:43]] &&
       (result_tag != t_tag[result_tag[44:43]] || result_generation != t_gen[result_tag[44:43]])) lf <= 1;
   if (result_valid && pp[result_tag[44:43]] &&
       (result_tag != ack_tag[result_tag[44:43]] || result_generation != ack_gen[result_tag[44:43]])) lf <= 1;
   for (k = 0; k < 8; k = k + 1) if (cancel_valid[k]) begin
    if (tp[cancel_tag[59*k+43 +: 2]] && (cancel_tag[59*k +: 59] != t_tag[cancel_tag[59*k+43 +: 2]] ||
        cancel_generation[2*k +: 2] != t_gen[cancel_tag[59*k+43 +: 2]])) lf <= 1;
    if (pp[cancel_tag[59*k+43 +: 2]] && (cancel_tag[59*k +: 59] != ack_tag[cancel_tag[59*k+43 +: 2]] ||
        cancel_generation[2*k +: 2] != ack_gen[cancel_tag[59*k+43 +: 2]])) lf <= 1;
   end
   if (sel) begin
    if (tn == 3'd4) lf <= 1;
    else begin
     tp[su] <= 1; t_tag[su] <= stag; t_gen[su] <= sgen; t_done[su] <= sdone; t_fault[su] <= sfault;
     t_coh[su] <= coh[su] || (begin_valid && cohort_begin_ready && ub == su); tq[tw] <= su; tw <= tw + 1'b1;
    end
   end
   if (alloc_terminal_accepted) begin
    if (tn == 0 || (t_coh[h] != cohort_terminal_accepted)) lf <= 1;
    tp[h] <= 0; ab[h] <= 0; coh[h] <= 0; pp[h] <= 1; lt_v[h] <= 1;
    ack_tag[h] <= t_tag[h]; ack_gen[h] <= t_gen[h]; last_ack_tag <= t_tag[h]; last_ack_gen <= t_gen[h];
    tr <= tr + 1'b1; gap <= 1;
    if (pn == 3'd4) lf <= 1; else begin pq[pw] <= h; pw <= pw + 1'b1; end
   end else if (cohort_terminal_accepted) lf <= 1;
   tn <= tn + 3'(sel && tn != 3'd4) - 3'(alloc_terminal_accepted && tn != 0);
   if (post_retired) begin
    if (pn == 0 || post_tag != ack_tag[pq[pr]] || post_generation != ack_gen[pq[pr]] || !pp[pq[pr]]) lf <= 1;
    else begin pp[pq[pr]] <= 0; pr <= pr + 1'b1; end
   end
   pn <= pn + 3'(alloc_terminal_accepted && pn != 3'd4) -
         3'(post_retired && !(pn == 0 || post_tag != ack_tag[pq[pr]] || post_generation != ack_gen[pq[pr]] || !pp[pq[pr]]));
   if (recovery_start) begin
    if (recovery_active) lf <= 1;
    else begin recovery_active <= 1; reset_witness <= 0; train_witness <= 0; end
   end
   if (link_reset_request) reset_witness <= reset_witness | link_reset_seen;
   if (retraining_request) train_witness <= train_witness | retraining_done;
   if (recovery_fire) begin recovery_active <= 0; rc <= 1; lf <= 0; lt_v <= 0; end
  end
 end
end endgenerate
endmodule
