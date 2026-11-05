`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of qkd_host_lifecycle_collected_mu (same ports and per-user rules).
//  Terminal head registers hd_* (loaded from tq[tr] + t_*[user]): first presentation +2 edges, successor +1 edge (the source's
//    one-edge gap is the empty head).  Identity checks are registered inside allocator and cohort from hd_* one edge before
//    presentation (hd_vv); udeliv / disp only rise and a_* / ctag are stable while busy / active, so a registered PASS
//    still holds and a registered FAIL is the verdict of a terminal arriving one edge earlier, a legal timing of the source.
//  A captured terminal holds that user's grant handshake (grant_hold), so t_coh stays exact across the wider window to presentation.
//  acknowledged_tag / generation read hd_*: both consumers sample them only during the terminal_accepted pulse, and hd_* hold
//    through that pulse.  last_ack_* gone.
//  Cancels: per-rank registered qualified valid cv_q and registered compare same_q against the user's retired identity
//    (+1 edge into the terminal queue).  Acceptance is by POST-pending / retired identity only, so a cancel naming the
//    terminal being accepted is accepted 2 edges after that pulse (pp, lt_v, ack_tag cover it from the next edge on).
//    Mismatch faults are unchanged and same-edge.
//  Cancel capture: the lowest cancelling rank is picked one edge ahead (w_*: rank, user, identity, flags), capture checks only
//    the user's tp / pp and the result on that edge (+1 edge; a cancel stays valid until accepted, so none is lost).
//  POST pop: post_tag compare drives only the fault; identity mismatch faults (result, cancel, POST) register once (mis_q, lf +1 edge).
//  Presentation: present_q registers hd_vv with the drain rule (first presentation +1 edge, falls on the source's edge); the allocator accepts
//    on it without re-reading the drains, so allocator and cohort act on one decision.  A drain or alone view one edge old is the source's
//    verdict for a terminal arriving one edge earlier.
//  Cancel candidates register once more (cand_q, +1 edge); capture still checks tp / pp / result live, and a candidate and an acceptance of
//    one rank exclude each other, so a stale candidate cannot capture an accepted cancel.
//  Identity mismatch faults: mis_q is split per source (c_mis_q, r_mis_q, p_mis_q), same edge as before.
//  t_tag, t_gen, ack_tag, ack_gen, hd_*, w_* data: no reset, valid qualified.
module qkd_host_lifecycle_r3 #(parameter [15:0] INITIAL_EPOCH = 16'd0, parameter integer MU = 1) (
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
 function automatic sel4(input[3:0]x,input[1:0]i);sel4=i[1]?(i[0]?x[3]:x[2]):(i[0]?x[1]:x[0]);endfunction
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
 reg lf, rc;
 reg hd_v, hd_vv, hd_done, hd_fault, hd_coh; reg [1:0] hd_u, hd_gen; reg [58:0] hd_tag;
 reg recovery_active; reg [7:0] reset_witness, train_witness;
 reg [7:0] cv_q, same_q;
 reg [7:0] cand_q, c_mis_q; reg r_mis_q, p_mis_q, present_q;
 reg w_v, w_done, w_fault; reg [7:0] w_oh; reg [1:0] w_u, w_gen; reg [58:0] w_tag;
 wire allocator_fault, cohort_fault, cohort_active, cohort_terminal_accepted, cohort_begin_ready, unused_allocator_busy, g_id_ok;
 wire alloc_request_ready, alloc_terminal_accepted;
 wire all_drained = (&kv_drained) && (&vm_drained) && (&collective_drained) && (&host_drained);
 wire [1:0] h = tq[tr];
 wire [1:0] uq = request_position[17:16];
 wire [1:0] ub = grant_tag[44:43];
 wire [1:0] ru = result_tag[44:43];
 wire alone_a = (ab & ~(4'd1 << hd_u)) == 4'd0;
 wire hd_load = tn != 0 && !hd_v;
 wire present_d = hd_vv && !alloc_terminal_accepted && (all_drained || !alone_a);
 wire present = present_q;
 wire mis_q = (|c_mis_q) || r_mis_q || p_mis_q;
 assign terminal_accepted = alloc_terminal_accepted;
 assign lifecycle_fault = lf;
 assign recovery_complete = rc;
 assign identity_fault = allocator_fault || cohort_fault || lf;
 assign post_pending = pn != 0;
 assign acknowledged_tag = hd_tag;
 assign acknowledged_generation = hd_gen;
 wire admission_ready = warm_ready && !recovery_active && !lf && !cohort_fault;
 wire begin_valid = grant_valid && grant_ready;
 wire up_block = sel4(pp, uq);
 assign request_ready = alloc_request_ready;   // up_block is in the allocator's registered request check
 // cancels, one rank each
 wire [7:0] c_cand, c_mis;
 genvar r;
 for (r = 0; r < 8; r = r + 1) begin : ack
  wire [1:0] cu = cancel_tag[59*r+43 +: 2];
  wire [58:0] ct = cancel_tag[59*r +: 59];
  wire [1:0] cg = cancel_generation[2*r +: 2];
  wire c_tp = sel4(tp, cu), c_pp = sel4(pp, cu), c_lt = sel4(lt_v, cu);
  wire c_same = ct == ack_tag[cu] && cg == ack_gen[cu];
  assign c_cand[r] = cv_q[r] && cancel_valid[r] && !c_tp && !c_pp && !(c_lt && same_q[r]);
  assign c_mis[r] = cancel_valid[r] && ((c_tp && (ct != t_tag[cu] || cg != t_gen[cu])) || (c_pp && !c_same));
  assign cancel_accepted[r] = !cancel_acknowledged[r] && cv_q[r] && cancel_valid[r] && all_drained && (c_pp || c_lt) && same_q[r];
  always @(posedge clk or negedge por_n)
   if (!por_n) begin cv_q[r] <= 0; same_q[r] <= 0; end
   else begin cv_q[r] <= cancel_valid[r] && !cancel_accepted[r]; same_q[r] <= c_same; end
 end
 // event capture: one new terminal per edge (the result first, else the lowest cancelling rank)
 wire r_go = result_valid && !sel4(tp, ru) && !sel4(pp, ru);
 // lowest candidate as a one-hot AND-OR: no variable bit read, so RTL and gate name cancel_* the same (LEC)
 wire [7:0] c_oh = cand_q & (~cand_q + 8'd1);
 reg [58:0] c_tag_m; reg [1:0] c_gen_m;
 always @* begin
  c_tag_m = 0; c_gen_m = 0;
  for (integer n = 0; n < 8; n = n + 1) begin
   c_tag_m = c_tag_m | ({59{c_oh[n]}} & cancel_tag[59*n +: 59]);
   c_gen_m = c_gen_m | ({2{c_oh[n]}} & cancel_generation[2*n +: 2]);
  end
 end
 always @(posedge clk) begin
  w_oh <= c_oh; w_u <= c_tag_m[44:43]; w_tag <= c_tag_m; w_gen <= c_gen_m;
  w_done <= |(c_oh & cancel_done); w_fault <= |(c_oh & cancel_fault);
 end
 wire w_go = w_v && (|(w_oh & cancel_valid)) && !sel4(tp, w_u) && !sel4(pp, w_u) && !(result_valid && ru == w_u);
 wire sel = r_go || w_go;
 wire [1:0] su = r_go ? ru : w_u;
 wire [58:0] stag = r_go ? result_tag : w_tag;
 wire [1:0] sgen = r_go ? result_generation : w_gen;
 wire sdone = r_go ? result_done : w_done;
 wire sfault = r_go ? result_fault : w_fault;
 wire post_bad = pn == 0 || post_tag != ack_tag[pq[pr]] || post_generation != ack_gen[pq[pr]] || !sel4(pp, pq[pr]);
 wire recovery_fire = recovery_active && !mis_q && (&links_drained) && (&reset_witness) && (&train_witness) &&
                      all_drained && tn == 0 && pn == 0 && !allocated_valid && !cohort_active && !request_valid &&
                      !(|participant_valid) && !result_valid && !(|cancel_valid);
 assign link_reset_request = recovery_active && (&links_drained);
 assign retraining_request = link_reset_request && (&reset_witness);
 ot_qwen_tp8_token_epoch_allocator_r3 #(.INITIAL_EPOCH(INITIAL_EPOCH), .MU(1)) allocator (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .request_valid(request_valid && !up_block), .request_ready(alloc_request_ready), .request_token(request_token),
  .request_position(request_position), .request_generation(request_generation),
  .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token),
  .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag),
  .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered), .g_id_ok(g_id_ok), .grant_hold(sel4(tp, ub)),
  .terminal_valid(present), .terminal_tag(hd_tag), .terminal_generation(hd_gen),
  .terminal_done(hd_done), .terminal_fault(hd_fault),
  .terminal_kv_drained(&kv_drained), .terminal_vm_drained(&vm_drained),
  .terminal_collective_drained(&collective_drained), .terminal_host_drained(&host_drained),
  .wrap_fence_valid(recovery_fire && (wrap_locked || allocator_fault)), .wrap_links_drained(&links_drained),
  .wrap_link_reset_seen(&reset_witness), .wrap_retraining_done(&train_witness),
  .busy(unused_allocator_busy), .wrap_locked(wrap_locked), .identity_fault(allocator_fault), .terminal_accepted(alloc_terminal_accepted));
 reg [7:0] pmask;
 always @* for (integer n = 0; n < 8; n = n + 1)
  pmask[n] = !sel4(tp, participant_tag[59*n+43 +: 2]) && !sel4(pp, participant_tag[59*n+43 +: 2]);
 ot_qwen_tp8_token_cohort_r3 #(.MU(1)) cohort (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .begin_valid(begin_valid), .begin_ready(cohort_begin_ready), .begin_identity_ok(g_id_ok), .begin_tag(grant_tag), .begin_generation(grant_generation),
  .request_valid(participant_valid & pmask), .request_tag(participant_tag), .request_generation(participant_generation),
  .request_credit(participant_accepted), .dispatch_valid(dispatch_valid),
  .dispatch_ready(engine_admit_ready && (&participant_ready)),
  .cohort_tag(cohort_tag), .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks),
  .active(cohort_active), .dispatched(dispatched), .identity_fault(cohort_fault),
  .terminal_valid(present && hd_coh), .terminal_tag(hd_tag),
  .terminal_generation(hd_gen), .terminal_done(hd_done), .terminal_fault(hd_fault),
  .kv_drained(&kv_drained), .vm_drained(&vm_drained), .collective_drained(&collective_drained), .host_drained(&host_drained),
  .terminal_accepted(cohort_terminal_accepted), .recovery_valid(recovery_fire),
  .links_drained(&links_drained), .link_reset_seen(&reset_witness), .retraining_done(&train_witness));
 integer k;
 // data registers: no reset
 always @(posedge clk) begin
  if (hd_load) begin hd_u <= h; hd_tag <= t_tag[h]; hd_gen <= t_gen[h]; end
  if (sel) begin t_tag[su] <= stag; t_gen[su] <= sgen; end
  if (alloc_terminal_accepted) begin ack_tag[hd_u] <= hd_tag; ack_gen[hd_u] <= hd_gen; end
 end
 always @(posedge clk or negedge por_n) begin
  if (!por_n) begin
   ab <= 0; coh <= 0; tp <= 0; t_coh <= 0; t_done <= 0; t_fault <= 0; pp <= 0; lt_v <= 0;
   tw <= 0; tr <= 0; tn <= 0; pw <= 0; pr <= 0; pn <= 0; lf <= 0; rc <= 0;
   w_v <= 0; cand_q <= 0; c_mis_q <= 0; r_mis_q <= 0; p_mis_q <= 0; present_q <= 0; hd_v <= 0; hd_vv <= 0; hd_done <= 0; hd_fault <= 0; hd_coh <= 0;
   recovery_active <= 0; reset_witness <= 0; train_witness <= 0;
   for (k = 0; k < 4; k = k + 1) begin tq[k] <= 0; pq[k] <= 0; end
  end else begin
   rc <= 0;
   if (request_valid && request_ready) begin ab[uq] <= 1; lt_v[uq] <= 0; end
   if (begin_valid && !cohort_begin_ready) lf <= 1;
   if (begin_valid && cohort_begin_ready) coh[ub] <= 1;
   // identity checks against the user's pending terminal / POST (fail closed)
   cand_q <= c_cand; w_v <= |cand_q; present_q <= present_d;
   r_mis_q <= (result_valid && sel4(tp, ru) && (result_tag != t_tag[ru] || result_generation != t_gen[ru])) ||
              (result_valid && sel4(pp, ru) && (result_tag != ack_tag[ru] || result_generation != ack_gen[ru]));
   c_mis_q <= c_mis; p_mis_q <= post_retired && post_bad;
   if (mis_q) lf <= 1;
   if (sel) begin
    if (tn == 3'd4) lf <= 1;
    else begin
     tp[su] <= 1; t_done[su] <= sdone; t_fault[su] <= sfault;
     t_coh[su] <= sel4(coh, su) || (begin_valid && cohort_begin_ready && ub == su); tq[tw] <= su; tw <= tw + 1'b1;
    end
   end
   if (hd_load) begin hd_v <= 1; hd_done <= sel4(t_done, h); hd_fault <= sel4(t_fault, h); hd_coh <= sel4(t_coh, h); end
   hd_vv <= hd_v;
   if (alloc_terminal_accepted) begin
    if (tn == 0 || (hd_coh != cohort_terminal_accepted)) lf <= 1;
    tp[hd_u] <= 0; ab[hd_u] <= 0; coh[hd_u] <= 0; pp[hd_u] <= 1; lt_v[hd_u] <= 1;
    tr <= tr + 1'b1; hd_v <= 0; hd_vv <= 0;
    if (pn == 3'd4) lf <= 1; else begin pq[pw] <= hd_u; pw <= pw + 1'b1; end
   end else if (cohort_terminal_accepted) lf <= 1;
   tn <= tn + 3'(sel && tn != 3'd4) - 3'(alloc_terminal_accepted && tn != 0);
   if (post_retired) begin
    pp[pq[pr]] <= 0; pr <= pr + 1'b1;
   end
   pn <= pn + 3'(alloc_terminal_accepted && pn != 3'd4) - 3'(post_retired && pn != 0);
   if (recovery_start) begin
    if (recovery_active) lf <= 1;
    else begin recovery_active <= 1; reset_witness <= 0; train_witness <= 0; end
   end
   if (link_reset_request) reset_witness <= reset_witness | link_reset_seen;
   if (retraining_request) train_witness <= train_witness | retraining_done;
   if (recovery_fire) begin recovery_active <= 0; rc <= 1; lf <= 0; lt_v <= 0; end
  end
 end
endmodule
