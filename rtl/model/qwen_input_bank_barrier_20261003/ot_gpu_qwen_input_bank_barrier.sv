`timescale 1ps/1ps
// Physical bank b is NEVER relabelled as the execution actor in tuple239.
// No storage, clocks, initialization, ownership grant or source-release output.
// profile_* MUST be driven by source-qualified immutable census hardware.
module ot_gpu_qwen_input_bank_barrier #(parameter bit ENABLE=0)(
 input wire [63:0] profile_valid,input wire [4095:0] required_banks,
 input wire [15295:0] root_offer_tuple,root_held_tuple,
 input wire [3519:0] root_held_owner,
 input wire [63:0] root_busy,root_fault,root_go_accepted,
 input wire [63:0] root_input_terminal_valid,root_input_reverse_valid,root_frame_retire_valid,
 input wire [15295:0] root_input_terminal_tuple,root_input_reverse_tuple,root_frame_retire_tuple,
 input wire [63:0] bank_bound_valid,bank_live,bank_started,bank_fault,bank_barrier_ready,
 input wire [15295:0] bank_tuple,input wire [447:0] bank_mask,
 input wire [63:0] bank_input_terminal_ready,bank_input_reverse_ready,bank_frame_retire_ready,
 output reg [63:0] root_inputs_bound_valid,root_row_barrier_ready,
 output wire [15295:0] root_inputs_bound_tuple,
 output wire [447:0] root_inputs_bound_mask,
 output reg [63:0] root_input_terminal_ready,root_input_reverse_ready,root_frame_retire_ready,
 output reg [63:0] bank_inputs_bound_ready,bank_go_accepted,
 output wire [15295:0] bank_go_tuple,
 output reg [63:0] bank_input_terminal_valid,bank_input_reverse_valid,bank_frame_retire_valid,
 output wire [15295:0] bank_input_terminal_tuple,bank_input_reverse_tuple,bank_frame_retire_tuple,
 output wire [447:0] bank_input_terminal_mask,bank_input_reverse_mask,
 output reg [63:0] bank_issuer_held_valid,bank_issuer_held_fault,
 output reg [15295:0] bank_issuer_held_tuple,
 output reg [3519:0] bank_issuer_held_owner,bank_frame_retire_owner
);
 // Views of EXISTING coded holders, not new owner/tuple shadow state.
 assign root_inputs_bound_tuple=bank_tuple;
 assign root_inputs_bound_mask=bank_mask;
 assign bank_go_tuple=bank_tuple;
 assign bank_input_terminal_tuple=bank_tuple;
 assign bank_input_reverse_tuple=bank_tuple;
 assign bank_frame_retire_tuple=bank_tuple;
 assign bank_input_terminal_mask=bank_mask;
 assign bank_input_reverse_mask=bank_mask;
 integer a,b,actor;
 reg profile_ok,bind_ok,barrier_ok,held_ok,term_ok,rev_ok,retire_ok;
 reg [238:0] offer,held,bt;
 reg [63:0] needed;
 always @* begin
  root_inputs_bound_valid=0;root_row_barrier_ready=0;
  root_input_terminal_ready=0;root_input_reverse_ready=0;root_frame_retire_ready=0;
  bank_inputs_bound_ready=0;bank_go_accepted=0;
  bank_input_terminal_valid=0;bank_input_reverse_valid=0;bank_frame_retire_valid=0;
  bank_issuer_held_valid=0;bank_issuer_held_fault=0;bank_issuer_held_tuple=0;
  bank_issuer_held_owner=0;bank_frame_retire_owner=0;
  offer=0;held=0;bt=0;needed=0;actor=0;
  profile_ok=0;bind_ok=0;barrier_ok=0;held_ok=0;term_ok=0;rev_ok=0;retire_ok=0;
  for(a=0;a<64;a=a+1)begin
   offer=root_offer_tuple[a*239+:239];held=root_held_tuple[a*239+:239];needed=required_banks[a*64+:64];
   profile_ok=ENABLE && profile_valid[a] && needed[a] && !root_fault[a];
   bind_ok=profile_ok && offer[35:30]==a;
   barrier_ok=bind_ok;
   held_ok=profile_ok && root_busy[a] && held[35:30]==a;
   term_ok=held_ok && root_input_terminal_tuple[a*239+:239]==held;
   rev_ok=held_ok && root_input_reverse_tuple[a*239+:239]==held;
   retire_ok=held_ok && root_frame_retire_tuple[a*239+:239]==held;
   for(b=0;b<64;b=b+1)if(needed[b])begin
    bt=bank_tuple[b*239+:239];
    if(!bank_bound_valid[b] || bank_started[b] || bank_fault[b] || bt!=offer)bind_ok=0;
    if(!bank_barrier_ready[b])barrier_ok=0;
    if(!bank_live[b] || !bank_started[b] || bank_fault[b] || bt!=held)begin term_ok=0;rev_ok=0;retire_ok=0;end
    if(!bank_input_terminal_ready[b])term_ok=0;
    if(!bank_input_reverse_ready[b])rev_ok=0;
    if(!bank_frame_retire_ready[b])retire_ok=0;
   end
   root_inputs_bound_valid[a]=bind_ok;root_row_barrier_ready[a]=barrier_ok && bind_ok;
   root_input_terminal_ready[a]=term_ok;root_input_reverse_ready[a]=rev_ok;root_frame_retire_ready[a]=retire_ok;
  end
  for(b=0;b<64;b=b+1)begin
   bt=bank_tuple[b*239+:239];actor=bt[35:30];needed=required_banks[actor*64+:64];
   if(ENABLE && profile_valid[actor] && needed[b])begin
    // Only a REAL accepted issuer GO can mark a bank binding started.
    if(root_go_accepted[actor] && root_inputs_bound_valid[actor] && root_row_barrier_ready[actor])begin
     bank_inputs_bound_ready[b]=1;bank_go_accepted[b]=1;
    end
    if(bank_live[b] && root_busy[actor] && bt==root_held_tuple[actor*239+:239])begin
     bank_issuer_held_valid[b]=!root_fault[actor];bank_issuer_held_fault[b]=root_fault[actor];
     bank_issuer_held_tuple[b*239+:239]=root_held_tuple[actor*239+:239];
     bank_issuer_held_owner[b*55+:55]=root_held_owner[actor*55+:55];
     bank_frame_retire_owner[b*55+:55]=root_held_owner[actor*55+:55];
     // ALL recipients accept on one edge; partial one-shot consumption is forbidden.
     bank_input_terminal_valid[b]=root_input_terminal_valid[actor] && root_input_terminal_ready[actor];
     bank_input_reverse_valid[b]=root_input_reverse_valid[actor] && root_input_reverse_ready[actor];
     bank_frame_retire_valid[b]=root_frame_retire_valid[actor] && root_frame_retire_ready[actor];
    end
   end
  end
 end
endmodule
