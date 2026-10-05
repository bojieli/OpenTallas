`timescale 1ns/1ps
// Inline actual NC6 selected-client tap; NEVER fabricates a capture or reverse.
// Enclosing mux applies req_permit to BOTH c_req_v/c_req_rdy, capture_permit
// to BOTH c_rsp_rdy/c_wr_done_rdy. No extra W2 or provider side ACK authority.
// command is a real mapped source-state sector transaction (source address
// aligned). For writes OLD must be read under the SAME retained sector grant,
// including full-sector writes. command_new_data is source PATCH bytes at
// sector offsets, with command_byte_mask. Actual OLD supplies all other bytes;
// no precomputed whole NEW sector is needed before its physical OLD read.
// command_write=0 performs a read only; unrelated clients retain their authority.
// physical owner46={PC7,client3,originaltag32,generation4}; rank is separate.
// local_reset NEVER clears accepted debt. por_n is cold power-on only.
module ot_gpu_qwen_kv_state_w2_tap #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable, local_reset, source_bound,
 input wire command_valid, output wire command_ready,
 input wire command_rank, command_write, command_sector_granted,
 input wire [5:0] state_client_mask,
 input wire [63:0] command_identity,
 input wire [33:0] command_source_addr, command_physical_addr,
 input wire [45:0] command_owner, input wire [255:0] command_new_data,
 input wire [31:0] command_byte_mask,
 output wire reply_valid, input wire reply_ready,
 output wire [63:0] reply_identity, output wire [255:0] reply_old_data,
 output wire reply_rank, output wire [45:0] reply_owner,
 output wire [33:0] reply_physical_addr,
 output wire quiescent,
 input wire bus_rank, input wire [6:0] bus_PC,
 input wire [5:0] caller_req_v, caller_req_we, raw_req_rdy,
 input wire [203:0] caller_req_addr,
 input wire [191:0] caller_req_tag, input wire [23:0] caller_req_gen,
 input wire [1535:0] caller_req_data, output wire [5:0] req_permit,
 input wire [5:0] raw_rsp_v, raw_wr_done_v, caller_rsp_rdy, caller_wr_done_rdy,
 input wire [191:0] raw_rsp_tag, raw_wr_done_tag,
 input wire [23:0] raw_rsp_gen, raw_wr_done_gen,
 input wire [1535:0] raw_rsp_data,
 input wire W2_fault, repair_busy, output wire [5:0] capture_permit,
 input wire reverse_valid, output wire reverse_ready,
 input wire reverse_rank, reverse_write,
 input wire [45:0] reverse_owner, input wire [33:0] reverse_physical_addr,
 output wire observe_valid, input wire observe_ready,
 output wire observe_rank, observe_old_captured,
 output wire [33:0] observe_source_addr, observe_physical_addr,
 output wire [45:0] observe_owner,
 output wire [255:0] observe_old_data, observe_new_data,
 output wire ACK_valid, input wire ACK_ready,
 output wire [45:0] ACK_owner, output wire [33:0] ACK_physical_addr,
 output wire ACK_visible, ACK_reverse,
 output reg fault
);
 localparam IDLE=0, OLD_REQ=1, OLD_CAPTURE=2, OLD_REVERSE=3,
            NEW_REQ=4, NEW_CAPTURE=5, NEW_REVERSE=6, REPLY=7;
 reg [3:0] state;
 reg rank, write_command; reg [63:0] identity;
 reg [33:0] source_addr, physical_addr; reg [45:0] owner;
 reg [255:0] old_data, new_data; reg [31:0] byte_mask;
 reg [255:0] expected_new_data; integer b;
 always @* begin
  for(b=0;b<32;b=b+1) expected_new_data[b*8+:8]=byte_mask[b] ? new_data[b*8+:8] : old_data[b*8+:8];
 end
 wire enrolled_mask_ok=state==IDLE || (client_ok && state_client_mask[client]);
 wire active=ENABLE && por_n && run_enable && !local_reset && !fault && !W2_fault && !repair_busy && enrolled_mask_ok && source_bound;
 wire [2:0] client=owner[38:36];
 wire client_ok=client<6;
 wire route_match=client_ok && bus_rank==rank && bus_PC==owner[45:39];
 wire req_match=route_match && caller_req_addr[client*34+:34]==physical_addr &&
      caller_req_tag[client*32+:32]==owner[35:4] && caller_req_gen[client*4+:4]==owner[3:0] &&
      caller_req_we[client]==(state==NEW_REQ) &&
      (state!=NEW_REQ || caller_req_data[client*256+:256]==expected_new_data);
 wire capture_write=state==NEW_CAPTURE;
 wire return_valid=client_ok && (capture_write ? raw_wr_done_v[client] : raw_rsp_v[client]);
 wire return_match=route_match &&
      (capture_write ? raw_wr_done_tag[client*32+:32] : raw_rsp_tag[client*32+:32])==owner[35:4] &&
      (capture_write ? raw_wr_done_gen[client*4+:4] : raw_rsp_gen[client*4+:4])==owner[3:0];
 wire reverse_match=reverse_rank==rank && reverse_owner==owner &&
      reverse_physical_addr==physical_addr && reverse_write==(state==NEW_REVERSE);
 wire request_edge=active && client_ok && caller_req_v[client] && raw_req_rdy[client] && req_permit[client];
 wire capture_edge=active && return_valid && capture_permit[client] &&
      (capture_write ? caller_wr_done_rdy[client] : caller_rsp_rdy[client]);
 assign command_ready=active && source_bound && command_sector_granted && state==IDLE;
 assign reply_valid=active && state==REPLY;
 assign reply_identity=identity; assign reply_old_data=old_data;
 assign reply_rank=rank; assign reply_owner=owner; assign reply_physical_addr=physical_addr;
 assign quiescent=state==IDLE && !fault;
 genvar g;
 generate for(g=0;g<6;g=g+1) begin: guard
  // An inactive tap leaves other CLIENTS to their existing authority. It must
  // not be used as a global clean/fence or permit for unbound state transactions.
  assign req_permit[g]=active && (!state_client_mask[g] || (state!=IDLE && client==g &&
       ((state==OLD_REQ || state==NEW_REQ) && req_match && (state!=NEW_REQ || observe_ready))));
  assign capture_permit[g]=active && (!state_client_mask[g] || (state!=IDLE && client==g &&
       ((state==OLD_CAPTURE || state==NEW_CAPTURE) && return_match && (state!=NEW_CAPTURE || ACK_ready))));
 end endgenerate
 assign observe_valid=active && state==NEW_REQ && req_match && caller_req_v[client] && raw_req_rdy[client];
 assign observe_rank=rank; assign observe_source_addr=source_addr;
 assign observe_physical_addr=physical_addr; assign observe_owner=owner;
 assign observe_old_data=old_data; assign observe_new_data=expected_new_data;
 assign observe_old_captured=state>=NEW_REQ && state<=NEW_REVERSE;
 assign ACK_owner=owner; assign ACK_physical_addr=physical_addr;
 assign ACK_visible=active && state==NEW_CAPTURE && return_valid && return_match && caller_wr_done_rdy[client];
 assign ACK_reverse=active && state==NEW_REVERSE && reverse_valid && reverse_match;
 assign ACK_valid=ACK_visible || ACK_reverse;
 assign reverse_ready=active && reverse_match &&
      (state==OLD_REVERSE || (state==NEW_REVERSE && ACK_ready));
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin state<=IDLE;rank<=0;write_command<=0;identity<=0;
   source_addr<=0;physical_addr<=0;owner<=0;old_data<=0;new_data<=0;byte_mask<=0;fault<=0;end
  else begin
   if(ENABLE && state!=IDLE && (W2_fault || !source_bound || !enrolled_mask_ok)) fault<=1;
   if(active) begin
    if(state!=IDLE && client_ok &&
       ((raw_rsp_v[client] && state!=OLD_CAPTURE) ||
        (raw_wr_done_v[client] && state!=NEW_CAPTURE))) fault<=1;
    if(command_valid && command_ready) begin
     rank<=command_rank;write_command<=command_write;identity<=command_identity;
     source_addr<=command_source_addr;physical_addr<=command_physical_addr;
     owner<=command_owner;new_data<=command_new_data;byte_mask<=command_byte_mask;state<=OLD_REQ;
     if((command_write && command_byte_mask==0) || command_owner[38:36]>=6 || !state_client_mask[command_owner[38:36]] || command_source_addr[4:0]!=0 || command_physical_addr[4:0]!=0) fault<=1;
    end
    if(state==OLD_REQ || state==NEW_REQ) begin
     if(client_ok && caller_req_v[client] && !req_match) fault<=1;
     else if(request_edge) state<=state==OLD_REQ ? OLD_CAPTURE : NEW_CAPTURE;
    end
    if(state==OLD_CAPTURE || state==NEW_CAPTURE) begin
     if(return_valid && !return_match) fault<=1;
     else if(capture_edge) begin
      if(state==OLD_CAPTURE) old_data<=raw_rsp_data[client*256+:256];
      state<=state==OLD_CAPTURE ? OLD_REVERSE : NEW_REVERSE;
     end
    end
    // Only this tap's enrolled sector reverse is routed here; wrong/early
    // reverse is refused and retains original debt, not consumed speculatively.
    if(reverse_valid) begin
     if((state!=OLD_REVERSE && state!=NEW_REVERSE) || !reverse_match) fault<=1;
     else if(reverse_ready) state<=state==OLD_REVERSE && write_command ? NEW_REQ : REPLY;
    end
    if(reply_valid && reply_ready) state<=IDLE;
   end
  end
 end
endmodule
