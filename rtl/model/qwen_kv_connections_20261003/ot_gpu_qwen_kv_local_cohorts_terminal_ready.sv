`timescale 1ns/1ps
// Exact accepted execution-root ledger + retained id/key drain receipt.
// root_accept MUST be actual source command acceptance. root_retire is a
// real held terminal offer; root_retire_ready is its matched retirement accept. They are not software lease flags or persistent RF-version frees.
// root_admit gates only NEW roots, never admitted children or their replies.
// The enclosing authority must apply root_admit symmetrically at the caller.
module ot_gpu_qwen_kv_root_cohort_terminal_ready #(parameter ENABLE=0, ROOTS=1, OWNERW=64)(
 input wire clk, por_n, run_enable, local_reset, source_bound,
 input wire [ROOTS-1:0] root_accept, root_retire,
 input wire [ROOTS*OWNERW-1:0] root_owner, root_retire_owner,
 output wire [ROOTS-1:0] root_admit, root_retire_ready,
 input wire request_valid, output wire request_ready,
 input wire [63:0] request_identity, input wire [19:0] request_key,
 input wire receipts_empty,
 output wire response_valid, input wire response_ready,
 output wire [63:0] response_identity, output wire [19:0] response_key,
 output wire response_quiet, quiesce, roots_empty,
 output reg fault
);
 reg [ROOTS-1:0] live;
 reg [ROOTS*OWNERW-1:0] owners;
 reg held, receipt; reg [63:0] identity; reg [19:0] key;
 wire active=ENABLE && por_n && run_enable && !local_reset && !fault && source_bound;
 assign request_ready=active && !held;
 assign quiesce=held || request_valid || local_reset || !source_bound || fault;
 assign roots_empty=!(|live);
 assign root_admit={ROOTS{active && !quiesce}} & ~live;
 assign response_valid=active && held && receipt && roots_empty && receipts_empty &&
      !(|root_accept) && !(|root_retire);
 assign response_quiet=receipt && roots_empty && receipts_empty && !fault;
 assign response_identity=identity; assign response_key=key;
 genvar g;
 generate for(g=0;g<ROOTS;g=g+1) begin: retirement
  assign root_retire_ready[g]=active && live[g] &&
       owners[g*OWNERW+:OWNERW]==root_retire_owner[g*OWNERW+:OWNERW];
 end endgenerate
 integer i;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin live<=0;owners<=0;held<=0;receipt<=0;identity<=0;key<=0;fault<=0;end
  else begin
   if(ENABLE && !source_bound && (held || (|live))) fault<=1;
   if(active) begin
    if(request_valid && request_ready) begin
     held<=1;receipt<=0;identity<=request_identity;key<=request_key;
     if(request_key[19:14]>=36) fault<=1;
    end
    for(i=0;i<ROOTS;i=i+1) begin
     if(root_accept[i]) begin
      if(!root_admit[i]) fault<=1;
      else begin live[i]<=1;owners[i*OWNERW+:OWNERW]<=root_owner[i*OWNERW+:OWNERW];end
     end
     if(root_retire[i]) begin
      if(!live[i] || owners[i*OWNERW+:OWNERW]!=root_retire_owner[i*OWNERW+:OWNERW]) fault<=1;
      else live[i]<=0;
     end
    end
    if(held && !receipt && roots_empty && receipts_empty && !(|root_accept)) receipt<=1;
    if(held && receipt && (!roots_empty || !receipts_empty || (|root_accept))) fault<=1;
    if(response_valid && response_ready && response_quiet) begin held<=0;receipt<=0;end
   end
  end
 end
endmodule

// ONLY local stage cohort0 and metadata cohort3. Euclid owns enclosing mux;
// RF/commonACK4 is Popper's, payload1/2 and reverse7 remain Sagan's sources.
// Native stage roots span all source scratch children. State roots span the
// WHOLE byte RPC, including OLD capture and all sector writes/returns. Using
// individual sector completion for state_root_retire is premature for >1sector.
// External writer_retained remains live until controller payload/metadata fences.
module ot_gpu_qwen_kv_local_cohorts_terminal_ready #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable, local_reset, source_bound,
 input wire [63:0] stage_root_accept, stage_root_retire,
 input wire [3519:0] stage_root_owner, stage_root_retire_owner,
 output wire [63:0] stage_root_admit, stage_root_retire_ready,
 input wire shared_router_drained, writer_retained,
 input wire [63:0] shared_service_ready, shared_service_done,
 input wire state_root_accept, state_root_retire,
 input wire [63:0] state_root_identity, state_root_retire_identity,
 output wire state_root_admit, state_root_retire_ready,
 input wire state_tap_quiescent, state_observer_drained,
 input wire metadata_ACK_held, metadata_reverse_held, metadata_event_held,
 input wire [1:0] request_valid, output wire [1:0] request_ready,
 input wire [63:0] request_identity, input wire [19:0] request_key,
 output wire [1:0] response_valid, input wire [1:0] response_ready,
 output wire [127:0] response_identity, output wire [39:0] response_key,
 output wire [1:0] response_quiet, quiesce, roots_empty,
 output wire fault
);
 wire stage_fault,metadata_fault;
 wire stage_empty=shared_router_drained && !writer_retained &&
      (&shared_service_ready) && !(|shared_service_done);
 wire metadata_empty=state_tap_quiescent && state_observer_drained &&
      !metadata_ACK_held && !metadata_reverse_held && !metadata_event_held;
 ot_gpu_qwen_kv_root_cohort_terminal_ready #(.ENABLE(ENABLE),.ROOTS(64),.OWNERW(55)) stage(
  .clk(clk),.por_n(por_n),.run_enable(run_enable && !fault),.local_reset(local_reset),.source_bound(source_bound),
  .root_accept(stage_root_accept),.root_retire(stage_root_retire),
  .root_owner(stage_root_owner),.root_retire_owner(stage_root_retire_owner),.root_admit(stage_root_admit),.root_retire_ready(stage_root_retire_ready),
  .request_valid(request_valid[0]),.request_ready(request_ready[0]),
  .request_identity(request_identity),.request_key(request_key),.receipts_empty(stage_empty),
  .response_valid(response_valid[0]),.response_ready(response_ready[0]),
  .response_identity(response_identity[0+:64]),.response_key(response_key[0+:20]),
  .response_quiet(response_quiet[0]),.quiesce(quiesce[0]),.roots_empty(roots_empty[0]),.fault(stage_fault));
 ot_gpu_qwen_kv_root_cohort_terminal_ready #(.ENABLE(ENABLE),.ROOTS(1),.OWNERW(64)) metadata(
  .clk(clk),.por_n(por_n),.run_enable(run_enable && !fault),.local_reset(local_reset),.source_bound(source_bound),
  .root_accept(state_root_accept),.root_retire(state_root_retire),
  .root_owner(state_root_identity),.root_retire_owner(state_root_retire_identity),.root_admit(state_root_admit),.root_retire_ready(state_root_retire_ready),
  .request_valid(request_valid[1]),.request_ready(request_ready[1]),
  .request_identity(request_identity),.request_key(request_key),.receipts_empty(metadata_empty),
  .response_valid(response_valid[1]),.response_ready(response_ready[1]),
  .response_identity(response_identity[64+:64]),.response_key(response_key[20+:20]),
  .response_quiet(response_quiet[1]),.quiesce(quiesce[1]),.roots_empty(roots_empty[1]),.fault(metadata_fault));
 assign fault=stage_fault || metadata_fault;
endmodule
