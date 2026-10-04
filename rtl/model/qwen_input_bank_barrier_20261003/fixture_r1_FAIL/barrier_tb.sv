`timescale 1ps/1ps
// Fixture holders stand for physical coded B/issuer state. No census/engine proof.
module barrier_tb;
 parameter TB_ENABLE=1;
 reg [63:0] profile_valid=0,root_busy=0,root_fault=0,root_go_accepted=0;
 reg [4095:0] required_banks=0;
 reg [15295:0] root_offer_tuple=0,root_held_tuple=0,bank_tuple=0;
 reg [3519:0] root_held_owner=0;
 reg [447:0] bank_mask=0;
 reg [63:0] bank_bound_valid=0,bank_live=0,bank_started=0,bank_fault=0,bank_barrier_ready=0;
 reg [63:0] root_input_terminal_valid=0,root_input_reverse_valid=0,root_frame_retire_valid=0;
 reg [15295:0] root_input_terminal_tuple=0,root_input_reverse_tuple=0,root_frame_retire_tuple=0;
 reg [63:0] bank_input_terminal_ready=0,bank_input_reverse_ready=0,bank_frame_retire_ready=0;
 wire [63:0] root_inputs_bound_valid,root_row_barrier_ready,root_input_terminal_ready,root_input_reverse_ready,root_frame_retire_ready;
 wire [63:0] bank_inputs_bound_ready,bank_go_accepted,bank_input_terminal_valid,bank_input_reverse_valid,bank_frame_retire_valid,bank_issuer_held_valid,bank_issuer_held_fault;
 wire [15295:0] root_inputs_bound_tuple,bank_go_tuple,bank_input_terminal_tuple,bank_input_reverse_tuple,bank_frame_retire_tuple,bank_issuer_held_tuple;
 wire [447:0] root_inputs_bound_mask,bank_input_terminal_mask,bank_input_reverse_mask;
 wire [3519:0] bank_issuer_held_owner,bank_frame_retire_owner;
 ot_gpu_qwen_input_bank_barrier #(.ENABLE(TB_ENABLE)) dut(.*);
 task need(input cond,input [511:0] msg);begin #1;if(cond!==1'b1)$fatal(1,"%s",msg);end endtask
 reg [238:0] t;integer b;
 initial begin
  // Execution actor0 has remote INPUT holders in actual bank3 and bank63.
  t={64'hdeadbeef12345678,11'd14,64'h8000000000000001,64'hf000000000000002,1'b0,5'd0,11'd523,9'd36,10'd37};
  profile_valid[0]=1;required_banks[0+:64]=64'h8000000000000009;
  root_offer_tuple[0+:239]=t;root_held_tuple[0+:239]=t;root_held_owner[0+:55]=55'hff112233;
  for(b=0;b<64;b=b+1)if(required_banks[b])begin bank_tuple[b*239+:239]=t;bank_bound_valid[b]=1;bank_live[b]=1;bank_barrier_ready[b]=1;bank_mask[b*7+:7]=7'(b+1);end
  need(root_inputs_bound_valid[0]==TB_ENABLE,"all actual bindings");
  if(!TB_ENABLE)begin root_go_accepted=1;root_busy=1;bank_started='1;root_input_terminal_valid=1;bank_input_terminal_ready='1;need(bank_go_accepted==0&&bank_input_terminal_valid==0&&bank_issuer_held_valid==0,"defaultoff positiveevent");$display("PASS_DEFAULT_OFF_BANK_BARRIER");$finish;end
  bank_bound_valid[63]=0;need(!root_inputs_bound_valid[0],"omitted remote bank accepted GO");bank_bound_valid[63]=1;
  bank_tuple[63*239+:239]=t^239'h100000000000000000000000000000000000000000000000000;
  need(!root_inputs_bound_valid[0],"foreign high root identity accepted");bank_tuple[63*239+:239]=t;
  bank_barrier_ready[3]=0;need(!root_row_barrier_ready[0],"remote native frontier bypass");bank_barrier_ready[3]=1;
  root_go_accepted[0]=1;need(bank_go_accepted==64'h8000000000000009,"GO did not fanout all physical banks atomically");
  need(bank_go_tuple[63*239+:239]==t&&bank_go_tuple[3*239+:239]==t,"execution actor relabelled physical bank");root_go_accepted=0;
  bank_started=required_banks[0+:64];root_busy[0]=1;root_input_terminal_tuple[0+:239]=t;root_input_reverse_tuple[0+:239]=t;root_frame_retire_tuple[0+:239]=t;
  root_input_terminal_valid[0]=1;bank_input_terminal_ready=64'h9;
  need(!root_input_terminal_ready[0]&&bank_input_terminal_valid==0,"partial terminal consumed before remote ready");
  bank_input_terminal_ready=64'h8000000000000009;need(bank_input_terminal_valid==64'h8000000000000009,"atomic terminal missing");
  need(bank_input_terminal_mask[63*7+:7]==7'd64&&bank_input_terminal_mask[3*7+:7]==7'd4,"physical bank masks replaced by outputversion");root_input_terminal_valid=0;
  root_input_reverse_valid[0]=1;bank_input_reverse_ready=64'h8000000000000001;
  need(bank_input_reverse_valid==0,"partial reverse consumed");bank_input_reverse_ready=64'h8000000000000009;need(bank_input_reverse_valid==64'h8000000000000009,"atomic reverse missing");root_input_reverse_valid=0;
  root_frame_retire_valid[0]=1;bank_frame_retire_ready=64'h8000000000000001;need(bank_frame_retire_valid==0,"frame cleared before ALLbank ready");
  bank_frame_retire_ready=64'h8000000000000009;need(bank_frame_retire_valid==64'h8000000000000009,"allbank frame handshake absent");
  need(bank_issuer_held_tuple[63*239+:239]==t&&bank_issuer_held_owner[63*55+:55]==55'hff112233,"remote coded issuer root association wrong");
  root_fault[0]=1;need(bank_frame_retire_valid==0&&!bank_issuer_held_valid[63]&&bank_issuer_held_fault[63],"fault grantedframe/ownership");root_fault=0;
  profile_valid=0;need(bank_frame_retire_valid==0&&!root_inputs_bound_valid[0],"missing immutable profile granted");
  $display("PASS_ATOMIC_PHYSICAL_BANK_GO_TERMINAL_REVERSE_FRAME_SCOPE");$finish;
 end
endmodule
