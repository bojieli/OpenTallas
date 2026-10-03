`timescale 1ns/1ps
// Default-off MAX64-fragment C0 command collector. No partial native64 cast.
// Allocation descriptors are accepted source bindings, NOT guessed tags/homes.
// One data assembler; all8frame/128child records survive its reuse.
module ot_hbm_w5_c0_command #(parameter integer ENABLE=0,parameter [4:0] SM=0)(
 input wire clk,por_n,rst_n,
 input wire context_admitted,input wire [1023:0] context_reservation,
 input wire start_v,output wire start_r,input wire [63:0] native_owner,native_generation,
 input wire [54:0] command_parent,input wire [3:0] frame_count,
 input wire [255:0] frame_refs,input wire [71:0] frame_slots,
 output wire allocation_v,input wire allocation_r,input wire [31:0] allocation_tag,
 input wire [3:0] allocation_gen,input wire [38:0] allocation_byte,
 output wire [6:0] allocation_index,output wire [31:0] allocation_frame_ref,
 output wire [8:0] allocation_RFslot,
 output wire req_v,input wire req_r,output wire [38:0] req_byte,
 output wire [30:0] req_phy_sector31,output wire [4:0] req_phy_len5,output wire [3:0] req_phy_beat4,
 output wire [6:0] req_PC,output wire [45:0] req_owner,output wire [91:0] req_meta,
 input wire [15:0] accepted_backend16,
 input wire rsp_v,output wire rsp_r,input wire [91:0] rsp_meta,
 input wire [15:0] rsp_backend16,input wire [255:0] rsp_data,
 output wire stage_ACK_v,input wire stage_ACK_r,output wire [5:0] stage_fragment,
 output wire rf_v,input wire rf_r,output wire [4095:0] rf_data,
 output wire [8:0] rf_slot,output wire [54:0] stable_parent,
 input wire host_common_ACK,input wire [45:0] host_ack_owner,input wire [8:0] host_ack_slot,
 input wire host_ack_identity_fault,output wire host_ack_ready,output wire [45:0] rf_owner,
 input wire internal_SIMD_ACK,
 output wire visible_v,input wire visible_r,
 input wire consumer_v,input wire [54:0] consumer_identity,output wire consumer_r,
 output wire reverse_v,input wire reverse_r,output wire [91:0] reverse_meta,
 output wire [15:0] reverse_backend16,
 input wire parent_reverse_v,input wire [54:0] parent_reverse_identity,output wire parent_reverse_r,
 input wire reverse_CDC_v,input wire [54:0] reverse_CDC_identity,output wire reverse_CDC_r,
 output wire drain_req_v,output wire [54:0] drain_req_identity,
 output wire drain_req_has_owner,drain_req_reset_scope,input wire drain_req_r,
 input wire drain_rsp_v,input wire [54:0] drain_rsp_identity,
 input wire drain_rsp_has_owner,drain_rsp_reset_scope,input wire [8:0] allcopy_live_zero,
 output wire drain_rsp_r,output wire retire_v,input wire retire_r,
 input wire recovery_v,input wire [63:0] recovery_native_owner,recovery_native_generation,
 input wire [54:0] recovery_parent,output wire recovery_r,
 output wire [63:0] retained_native_owner,retained_native_generation,
 output wire [7:0] retained_children,output wire fault,quarantine
);
 localparam IDLE=0,ALLOCATE=1,ISSUE=2,CAPTURE=3,STAGE=4,RF=5,ACK=6,HOST=7,WAIT=8,REV=9,CHILD=10,RETAIN=11;
 reg [3:0] state;reg local_fault,reset_pending;
 reg [63:0] native_q,native_gen_q;reg [54:0] parent_q;
 reg [1023:0] remaining_context;
 reg [3:0] frames;reg [255:0] refs;reg [71:0] slots;
 reg [7:0] count,reverse_count;reg [2:0] frame;reg [3:0] sector;
 reg [31:0] tag_q;reg [3:0] gen_q;reg [38:0] byte_q;
 reg [4095:0] data_q;reg [15:0] captured;
 reg [91:0] meta[0:127];reg [15:0] backend[0:127];
 wire [38:0] local_byte=((byte_q>>9)<<7)+(byte_q&39'd127);
 wire [33:0] source_sector=local_byte[38:5];
 wire [4:0] pc_local=source_sector[6:2]^source_sector[11:7]^source_sector[16:12];
 wire [6:0] pc={byte_q[8:7],pc_local};
 wire [45:0] child_owner={pc,3'd0,tag_q,gen_q};
 wire [91:0] child_meta={child_owner,SM,slots[frame*9+:9],refs[frame*32+:32]};
 wire enable=ENABLE!=0;
 wire w_req_r,w_ack_r,w_visible_v,w_consumer_r,w_child_r,w_retire_v,w_fault,w_quarantine;
 wire [54:0] w_visible_id,w_retire_id;
 wire live=enable && por_n && rst_n && !local_fault && !w_fault && !reset_pending;
 integer demand_sum;reg demand_legal;
 always @* begin
  demand_sum=0;demand_legal=1;
  for(integer k=0;k<128;k=k+1)begin
   demand_sum=demand_sum+integer'(context_reservation[k*8+:8]);
   if(context_reservation[k*8+:8]>128)demand_legal=0;
  end
 end
 wire legal_descriptor=demand_legal && demand_sum==integer'(frame_count)*16 && frame_count>=1 && frame_count<=8 && command_parent[47:45]==0;
 integer match_index,match_count;
 always @* begin
  match_index=0;match_count=0;
  for(integer j=0;j<128;j=j+1)
   if(j<count && meta[j]==rsp_meta && backend[j]==rsp_backend16 && j/16==integer'(frame) && !captured[j%16]) begin match_index=j;match_count=match_count+1;end
 end
 assign start_r=live && context_admitted && state==IDLE && legal_descriptor && w_req_r;
 assign allocation_v=live && state==ALLOCATE;
 assign allocation_index=count[6:0];assign allocation_frame_ref=refs[frame*32+:32];assign allocation_RFslot=slots[frame*9+:9];
 assign req_phy_sector31=source_sector[30:0];assign req_phy_len5=5'd1;assign req_phy_beat4=4'd0;
 assign req_v=live && state==ISSUE && remaining_context[pc*8+:8]!=0;assign req_byte=byte_q;assign req_PC=pc;assign req_owner=enable?child_owner:46'd0;assign req_meta=enable?child_meta:92'd0;
 assign rsp_r=enable && por_n && !local_fault && !w_fault && state==CAPTURE && match_count==1;
 assign stage_ACK_v=live && state==STAGE;assign stage_fragment={frame,sector[3:1]};
 assign rf_v=live && state==RF;assign rf_data=data_q;assign rf_slot=slots[frame*9+:9];assign stable_parent=parent_q;
 assign rf_owner=parent_q[54:9];
 assign host_ack_ready=live && state==ACK && !host_ack_identity_fault && host_ack_owner==parent_q[54:9] && host_ack_slot==slots[frame*9+:9];
 assign visible_v=w_visible_v;assign consumer_r=w_consumer_r;
 assign reverse_v=live && state==REV;assign reverse_meta=meta[reverse_count[6:0]];assign reverse_backend16=backend[reverse_count[6:0]];
 assign retire_v=w_retire_v;
 assign fault=local_fault || w_fault;assign quarantine=reset_pending || w_quarantine;
 assign retained_native_owner=native_q;assign retained_native_generation=native_gen_q;assign retained_children=count;
 // W6 sees one retained C0 parent, one aggregate ACK and one aggregate child reverse.
 // Host ACK identity comes ONLY from the sole accepted RF write context here.
 ot_gpu_rf_visibility_fence_w6 #(.ENABLE(ENABLE!=0)) fence(
  .clk(clk),.por_n(por_n),.rst_n(rst_n),
  .req_valid(enable && context_admitted && start_v && state==IDLE && legal_descriptor && !reset_pending && !local_fault),.req_identity(command_parent),.req_internal_SIMD(1'b0),.req_ready(w_req_r),
  .host_ack_valid(live && state==HOST),.host_ack_identity(parent_q),.host_ack_ready(w_ack_r),
  .simd_ack_retire_valid(1'b0),.simd_ack_retire_identity(55'd0),.simd_ack_retire_ready(),
  .visible_valid(w_visible_v),.visible_identity(w_visible_id),.visible_ready(visible_r),
  .consumer_valid(live && consumer_v),.consumer_identity(consumer_identity),.consumer_ready(w_consumer_r),
  .child_reverse_valid(live && state==CHILD),.child_reverse_identity(parent_q),.child_reverse_ready(w_child_r),
  .parent_reverse_valid(parent_reverse_v),.parent_reverse_identity(parent_reverse_identity),.parent_reverse_ready(parent_reverse_r),
  .reverse_CDC_valid(reverse_CDC_v),.reverse_CDC_identity(reverse_CDC_identity),.reverse_CDC_ready(reverse_CDC_r),
  .drain_req_valid(drain_req_v),.drain_req_identity(drain_req_identity),.drain_req_has_owner(drain_req_has_owner),.drain_req_reset_scope(drain_req_reset_scope),.drain_req_ready(drain_req_r),
  .drain_rsp_valid(drain_rsp_v),.drain_rsp_identity(drain_rsp_identity),.drain_rsp_has_owner(drain_rsp_has_owner),.drain_rsp_reset_scope(drain_rsp_reset_scope),.alldrain_live(allcopy_live_zero),.drain_rsp_ready(drain_rsp_r),
  .retire_valid(w_retire_v),.retire_identity(w_retire_id),.retire_ready(retire_r),.fault(w_fault),.quarantine(w_quarantine));
 assign recovery_r=enable && por_n && rst_n && reset_pending && !w_quarantine && !w_fault &&
  recovery_native_owner==native_q && recovery_native_generation==native_gen_q && recovery_parent==parent_q && (&allcopy_live_zero);
 integer i;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin
   state<=IDLE;local_fault<=0;reset_pending<=0;native_q<=0;native_gen_q<=0;parent_q<=0;frames<=0;refs<=0;slots<=0;
   remaining_context<=0;count<=0;reverse_count<=0;frame<=0;sector<=0;tag_q<=0;gen_q<=0;byte_q<=0;data_q<=0;captured<=0;
   for(i=0;i<128;i=i+1) begin meta[i]<=0;backend[i]<=0;end
  end else begin
   if(!rst_n && enable) reset_pending<=1; // No operational-reset metadata clear.
   if(live && start_v && state==IDLE && !legal_descriptor) local_fault<=1;
   if(start_v && start_r) begin
    state<=ALLOCATE;native_q<=native_owner;native_gen_q<=native_generation;parent_q<=command_parent;
    remaining_context<=context_reservation;refs<=frame_refs;slots<=frame_slots;frames<=frame_count;count<=0;reverse_count<=0;frame<=0;sector<=0;captured<=0;
    for(i=0;i<8;i=i+1)for(integer j=0;j<i;j=j+1)
     if(i<frame_count && (frame_refs[i*32+:32]==frame_refs[j*32+:32] || frame_slots[i*9+:9]==frame_slots[j*9+:9]))local_fault<=1;
   end
   if(allocation_v && allocation_r) begin
    if(allocation_byte[4:0]!=0 || allocation_byte>=39'd81000000000 || allocation_gen!=parent_q[12:9]) local_fault<=1;
    else begin tag_q<=allocation_tag;gen_q<=allocation_gen;byte_q<=allocation_byte;state<=ISSUE;end
   end
   if(live && state==ISSUE && remaining_context[pc*8+:8]==0)local_fault<=1;
   if(req_v && req_r) begin
    remaining_context[pc*8+:8]<=remaining_context[pc*8+:8]-1'b1;
    for(i=0;i<128;i=i+1) if(i<count) begin
     if(meta[i][91:46]==child_owner) local_fault<=1;
     if(meta[i][91:90]==child_meta[91:90] && backend[i]==accepted_backend16) local_fault<=1;
    end
    meta[count[6:0]]<=child_meta;backend[count[6:0]]<=accepted_backend16;count<=count+1'b1;state<=CAPTURE;
   end
   if(live && rsp_v && (state!=CAPTURE || match_count!=1)) local_fault<=1;
   if(rsp_v && rsp_r) begin
    captured[sector]<=1;data_q[sector*256+:256]<=rsp_data;
    if(sector[0]) state<=STAGE;else begin sector<=sector+1'b1;state<=ALLOCATE;end
   end
   if(stage_ACK_v && stage_ACK_r) begin
    if(sector==15) state<=RF;else begin sector<=sector+1'b1;state<=ALLOCATE;end
   end
   if(rf_v && rf_r) state<=ACK;
   if(live && host_common_ACK && (state!=ACK || !host_ack_ready)) local_fault<=1;
   if(live && state==ACK && internal_SIMD_ACK) local_fault<=1;
   if(host_common_ACK && host_ack_ready) begin
    if({1'b0,frame}+1==frames) state<=HOST;
    else begin frame<=frame+1'b1;sector<=0;captured<=0;state<=ALLOCATE;end
   end
   if(live && state==HOST && w_ack_r) state<=WAIT;
   if(consumer_v && consumer_r) begin reverse_count<=0;state<=REV;end
   if(reverse_v && reverse_r) begin
    if(reverse_count+1==count) state<=CHILD;else reverse_count<=reverse_count+1'b1;
   end
   if(live && state==CHILD && w_child_r) state<=RETAIN;
   if(w_retire_v && retire_r) begin state<=IDLE;count<=0;captured<=0;end
   if(recovery_v && recovery_r) begin state<=IDLE;count<=0;captured<=0;local_fault<=0;reset_pending<=0;end
  end
 end
endmodule
