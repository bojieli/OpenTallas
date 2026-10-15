`timescale 1ns/1ps
// Coordinator leaf. Admission/retirement are exceptional token boundaries;
// these signals never stretch the compiler's execution cycle schedule.
// Rank-indexed inputs use native rank, not physical HOST ID.
module qkd_host_lifecycle_collected #(parameter [15:0] INITIAL_EPOCH = 16'd0) (
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
 output reg post_pending,
 output reg [58:0] acknowledged_tag,
 output reg [1:0] acknowledged_generation,
 // Explicit exceptional recovery transaction. Witnesses are retained only
 // after recovery_start, then reset is requested after all links drain.
 input wire recovery_start,
 input wire [7:0] links_drained, link_reset_seen, retraining_done,
 output wire link_reset_request, retraining_request,
 output reg recovery_complete,
 output wire wrap_locked, identity_fault,
 output wire terminal_accepted,
 output reg lifecycle_fault
);
 reg terminal_pending, rearm;
 reg[7:0]cancel_acknowledged;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)cancel_acknowledged<=0;
  else cancel_acknowledged<=(cancel_acknowledged|cancel_accepted)&cancel_valid;
 end
 reg [58:0] terminal_tag;
 reg [1:0] terminal_generation;
 reg terminal_done, terminal_fault, terminal_cohort_required;
 wire unused_allocator_busy;
 wire allocator_fault, cohort_fault, cohort_active, cohort_terminal_accepted;
 wire cohort_begin_ready;
 wire all_drained = (&kv_drained) && (&vm_drained) && (&collective_drained) && (&host_drained);
 reg recovery_active;
 reg [7:0] reset_witness, train_witness;
 wire recovery_fire = recovery_active && (&links_drained) && (&reset_witness) && (&train_witness) &&
                      all_drained && !terminal_pending && !rearm && !post_pending && !allocated_valid && !cohort_active && !request_valid && !(|participant_valid) && !selected;
 assign link_reset_request = recovery_active && (&links_drained);
 assign retraining_request = link_reset_request && (&reset_witness);
 assign identity_fault = allocator_fault || cohort_fault || lifecycle_fault;
 wire admission_ready = warm_ready && !post_pending && !recovery_active && !lifecycle_fault && !cohort_fault;
 wire begin_valid = grant_valid && grant_ready;
 ot_qwen_tp8_token_epoch_allocator #(.INITIAL_EPOCH(INITIAL_EPOCH)) allocator (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .request_valid(request_valid), .request_ready(request_ready), .request_token(request_token),
  .request_position(request_position), .request_generation(request_generation),
  .grant_valid(grant_valid), .grant_ready(grant_ready), .grant_epoch(grant_epoch), .grant_token(grant_token),
  .grant_position(grant_position), .grant_generation(grant_generation), .grant_tag(grant_tag),
  .allocated_valid(allocated_valid), .allocated_delivered(allocated_delivered),
  .terminal_valid(terminal_pending), .terminal_tag(terminal_tag), .terminal_generation(terminal_generation),
  .terminal_done(terminal_done), .terminal_fault(terminal_fault),
  .terminal_kv_drained(&kv_drained), .terminal_vm_drained(&vm_drained),
  .terminal_collective_drained(&collective_drained), .terminal_host_drained(&host_drained),
  .wrap_fence_valid(recovery_fire && (wrap_locked || allocator_fault)), .wrap_links_drained(&links_drained),
  .wrap_link_reset_seen(&reset_witness), .wrap_retraining_done(&train_witness),
  .busy(unused_allocator_busy), .wrap_locked(wrap_locked), .identity_fault(allocator_fault), .terminal_accepted(terminal_accepted));
 ot_qwen_tp8_token_cohort cohort (
  .clk(clk), .por_n(por_n), .warm_ready(admission_ready),
  .begin_valid(begin_valid), .begin_ready(cohort_begin_ready), .begin_tag(grant_tag), .begin_generation(grant_generation),
  .request_valid(participant_valid & {8{!terminal_pending&&!post_pending&&!rearm&&!terminal_accepted}}), .request_tag(participant_tag), .request_generation(participant_generation),
  .request_credit(participant_accepted), .dispatch_valid(dispatch_valid),
  .dispatch_ready(engine_admit_ready && (&participant_ready)),
  .cohort_tag(cohort_tag), .cohort_generation(cohort_generation), .accepted_ranks(accepted_ranks),
  .active(cohort_active), .dispatched(dispatched), .identity_fault(cohort_fault),
  .terminal_valid(terminal_pending && cohort_active), .terminal_tag(terminal_tag),
  .terminal_generation(terminal_generation), .terminal_done(terminal_done), .terminal_fault(terminal_fault),
  .kv_drained(&kv_drained), .vm_drained(&vm_drained), .collective_drained(&collective_drained), .host_drained(&host_drained),
  .terminal_accepted(cohort_terminal_accepted), .recovery_valid(recovery_fire),
  .links_drained(&links_drained), .link_reset_seen(&reset_witness), .retraining_done(&train_witness));
 genvar r;
 generate for (r=0;r<8;r=r+1) begin: ack
  assign cancel_accepted[r] = !cancel_acknowledged[r] && cancel_valid[r] && all_drained && (
   (terminal_accepted && cancel_tag[59*r+:59] == terminal_tag && cancel_generation[2*r+:2] == terminal_generation) ||
   (post_pending && cancel_tag[59*r+:59] == acknowledged_tag && cancel_generation[2*r+:2] == acknowledged_generation));
 end endgenerate
 integer rank;
 reg selected;
 reg [58:0] selected_tag;
 reg [1:0] selected_generation;
 reg selected_done, selected_fault;
 always @* begin
  selected=result_valid; selected_tag=result_tag; selected_generation=result_generation;
  selected_done=result_done; selected_fault=result_fault;
  for (integer n=0;n<8;n=n+1) if (!selected && cancel_valid[n]) begin
   selected=1; selected_tag=cancel_tag[59*n+:59]; selected_generation=cancel_generation[2*n+:2];
   selected_done=cancel_done[n]; selected_fault=cancel_fault[n];
  end
 end
 always @(posedge clk or negedge por_n) begin
  if (!por_n) begin
   terminal_pending<=0; rearm<=0; terminal_tag<=0; terminal_generation<=0;
   terminal_done<=0; terminal_fault<=0; terminal_cohort_required<=0; post_pending<=0;
   acknowledged_tag<=0; acknowledged_generation<=0; lifecycle_fault<=0;
   recovery_active<=0; reset_witness<=0; train_witness<=0; recovery_complete<=0;
  end else begin
   recovery_complete<=0;
   if (begin_valid && !cohort_begin_ready) lifecycle_fault<=1;
   if (rearm && !result_valid && !(|cancel_valid) && !terminal_accepted) rearm<=0;
   if (selected && !terminal_pending && !rearm && !post_pending) begin
    terminal_pending<=1; terminal_tag<=selected_tag; terminal_generation<=selected_generation;
    terminal_done<=selected_done; terminal_fault<=selected_fault; terminal_cohort_required<=cohort_active;
   end
   // A diagnosed stale terminal cannot strand a live allocation: an actual
   // replacement terminal must prove the allocator-owned identity and status.
   // Fault state remains sticky until the subsequent physical recovery fence.
   if (terminal_pending && identity_fault && selected && allocated_valid &&
       selected_tag == {grant_tag[58:43],6'd37,grant_tag[36:0]} &&
       selected_generation == grant_generation && (selected_fault || (selected_done && allocated_delivered))) begin
    terminal_tag<=selected_tag; terminal_generation<=selected_generation;
    terminal_done<=selected_done; terminal_fault<=selected_fault;
   end
   // All simultaneously retained cancellation sources must describe the same
   // terminal identity. Flags may differ when cancellation races successful completion.
   if (selected) for (rank=0;rank<8;rank=rank+1)
    if (cancel_valid[rank] && (cancel_tag[59*rank+:59] != selected_tag ||
        cancel_generation[2*rank+:2] != selected_generation)) lifecycle_fault<=1;
   if (selected && post_pending && !rearm && (selected_tag!=acknowledged_tag || selected_generation!=acknowledged_generation)) lifecycle_fault<=1;
   for (rank=0;rank<8;rank=rank+1)
    if (cancel_valid[rank] && (terminal_pending || rearm) &&
        (cancel_tag[59*rank+:59] != terminal_tag || cancel_generation[2*rank+:2] != terminal_generation)) lifecycle_fault<=1;
   if (result_valid && terminal_pending && (result_tag != terminal_tag || result_generation != terminal_generation)) lifecycle_fault<=1;
   if (terminal_accepted && terminal_cohort_required && !cohort_terminal_accepted) lifecycle_fault<=1;
   if (terminal_accepted) begin
    acknowledged_tag<=terminal_tag; acknowledged_generation<=terminal_generation;
    terminal_pending<=0; rearm<=1; post_pending<=1;
   end
   if (post_retired) begin
    if (!post_pending || post_tag!=acknowledged_tag || post_generation!=acknowledged_generation) lifecycle_fault<=1;
    else post_pending<=0;
   end
   if (recovery_start) begin
    if (recovery_active) lifecycle_fault<=1;
    else begin recovery_active<=1; reset_witness<=0; train_witness<=0; end
   end
   if (link_reset_request) reset_witness<=reset_witness | link_reset_seen;
   if (retraining_request) train_witness<=train_witness | retraining_done;
   if (recovery_fire) begin recovery_active<=0; recovery_complete<=1; lifecycle_fault<=0; end
  end
 end
endmodule
