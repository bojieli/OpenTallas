`timescale 1ns/1ps
// Prospective per-SM fullwidth read connector. ENABLE is intentionally off.
// rst_n is a cold, common reset only: operational reset is reset_req/drain.
// Full backend16 comes from actual atomic R14 acceptance, never synthesized here.
module ot_hbm_w5_read_frame #(parameter integer ENABLE=0, parameter [4:0] SM=0)(
 input wire clk,rst_n,
 input wire start_v,output wire start_r,input wire [63:0] native_owner,
 input wire [63:0] native_generation,
 input wire [63:0] frame_byte,input wire [31:0] parent_ref,parent_tag,
 input wire [3:0] producer_gen,input wire [2:0] caller_client,input wire [8:0] rf_slot,
 output wire req_v,input wire req_r,output wire [63:0] req_byte,
 output wire [6:0] req_pc,output wire [45:0] req_owner,
 output wire [91:0] req_meta,output wire [5:0] req_len,output wire req_beat,
 input wire [15:0] accepted_backend16,
 input wire rsp_v,output wire rsp_r,input wire [91:0] rsp_meta,
 input wire [15:0] rsp_backend16,input wire rsp_beat,input wire [255:0] rsp_data,
 output wire stage_ACK_v,input wire stage_ACK_r,output wire [2:0] stage_index,
 output wire rf_v,input wire rf_r,output wire [4095:0] rf_data,
 output wire [54:0] stable_parent,output wire [8:0] rf_dst,
 input wire host_common_ACK,input wire internal_SIMD_ACK,
 output wire visible_v,input wire visible_r,input wire consumer_done,
 output wire reverse_v,input wire reverse_r,output wire [91:0] reverse_meta,
 output wire [15:0] reverse_backend16,
 output wire drain_v,input wire drain_r,input wire [54:0] drained_parent,
 input wire [31:0] drained_ref,input wire [7:0] drained_epoch,
 input wire [8:0] allcopy_zero,input wire reset_req,
 output wire [7:0] reset_epoch,output wire idle,output wire fault,
 output wire [63:0] retained_native_owner,retained_native_generation
);
 generate if(ENABLE!=0) begin:g
 localparam IDLE=0,COLLECT=1,RF=2,ACK=3,VISIBLE=4,CONSUME=5,REVERSE=6,DRAIN=7;
 reg [2:0] state;reg fault_q,reset_pending,wrap_pending;
 reg [63:0] base,native_q,native_gen_q;reg [31:0] ref_q,child_tag;
 reg [3:0] gen_q;reg [2:0] client_q;reg [8:0] slot_q;
 reg [54:0] parent_q;reg [7:0] epoch_q;
 reg [4:0] issued;reg [2:0] fragment;reg [3:0] rev;
 reg [15:0] captured;reg [4095:0] data_q;
 reg [91:0] meta[0:15];reg [15:0] backend[0:15];
 wire [63:0] byte_now=base+({59'b0,issued}<<5);
 wire [63:0] local_byte=((byte_now>>9)<<7)+(byte_now&64'd127);
 wire [63:0] sector=local_byte>>5;
 wire [4:0] pc_local=sector[6:2]^sector[11:7]^sector[16:12];
 wire [6:0] pc_now={byte_now[8:7],pc_local};
 wire [63:0] start_local=(frame_byte>>9)<<7;
 wire [63:0] start_sector=start_local>>5;
 wire [4:0] start_pc=start_sector[6:2]^start_sector[11:7]^start_sector[16:12];
 wire [45:0] owner_now={pc_now,client_q,child_tag,gen_q};
 wire [91:0] meta_now={owner_now,SM,slot_q,ref_q};
 integer i;integer match;integer match_count;
 always @* begin
  match=0;match_count=0;
  for(integer j=0;j<16;j=j+1) begin
   if(j<issued && meta[j]==rsp_meta && backend[j]==rsp_backend16 && !captured[j]) begin
    match=j;match_count=match_count+1;
   end
  end
 end
 assign start_r=rst_n && !fault_q && !reset_req && !reset_pending && state==IDLE && frame_byte[8:0]==0 && frame_byte[63:39]==0 && caller_client<5 && (!wrap_pending || producer_gen==((gen_q+4'd1)&4'hf));
 assign req_v=rst_n && !fault_q && state==COLLECT && issued<16 && issued<({2'b0,fragment}+1)*2;
 assign req_byte=byte_now;assign req_pc=pc_now;assign req_owner=owner_now;assign req_meta=meta_now;
 assign req_len=1;assign req_beat=0;
 assign rsp_r=rst_n && !fault_q && state==COLLECT && match_count==1 && !rsp_beat;
 assign stage_ACK_v=rst_n && !fault_q && state==COLLECT && captured[fragment*2] && captured[fragment*2+1];
 assign stage_index=fragment;
 assign rf_v=rst_n && !fault_q && state==RF;
 assign rf_data=data_q;assign stable_parent=parent_q;assign rf_dst=slot_q;
 assign visible_v=rst_n && !fault_q && state==VISIBLE;
 assign reverse_v=rst_n && !fault_q && state==REVERSE;
 assign reverse_meta=meta[rev];assign reverse_backend16=backend[rev];
 assign drain_v=rst_n && !fault_q && (state==DRAIN || (state==IDLE && reset_pending));
 assign reset_epoch=epoch_q;assign idle=state==IDLE && !fault_q;assign fault=fault_q;
 assign retained_native_owner=native_q;assign retained_native_generation=native_gen_q;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin
   state<=IDLE;fault_q<=0;reset_pending<=0;wrap_pending<=0;base<=0;native_q<=0;native_gen_q<=0;ref_q<=0;
   child_tag<=0;gen_q<=0;client_q<=0;slot_q<=0;parent_q<=0;epoch_q<=0;
   issued<=0;fragment<=0;rev<=0;captured<=0;data_q<=0;
   for(i=0;i<16;i=i+1) begin meta[i]<=0;backend[i]<=0;end
  end else begin
   if(reset_req) reset_pending<=1;
   if(start_v && state==IDLE && !reset_req && !reset_pending && (frame_byte[8:0]!=0 || frame_byte[63:39]!=0 || caller_client>=5)) fault_q<=1;
   if(start_v && start_r) begin
    state<=COLLECT;base<=frame_byte;native_q<=native_owner;native_gen_q<=native_generation;ref_q<=parent_ref;
    // Parent PC is the first sector's actual hashed physical PC.
    parent_q<={frame_byte[8:7],start_pc,caller_client,parent_tag,producer_gen,rf_slot};
    gen_q<=producer_gen;client_q<=caller_client;slot_q<=rf_slot;
    issued<=0;fragment<=0;captured<=0;rev<=0;wrap_pending<=0;
   end
   if(req_v && req_r) begin
    // Atomic acceptance must guarantee no backend16 reuse within this stack
    // until reverse + drain. Detect duplicates already retained in this frame.
    for(i=0;i<16;i=i+1)
     if(i<issued && meta[i][91:90]==meta_now[91:90] && backend[i]==accepted_backend16) fault_q<=1;
    meta[issued[3:0]]<=meta_now;backend[issued[3:0]]<=accepted_backend16;
    issued<=issued+1'b1;child_tag<=child_tag+1'b1;
    if(child_tag==32'hffffffff) wrap_pending<=1;
   end
   if(rsp_v && state==COLLECT && (match_count!=1 || rsp_beat)) fault_q<=1;
   if(rsp_v && rsp_r) begin captured[match]<=1;data_q[match*256+:256]<=rsp_data;end
   // One staging ticket returns ONLY after its two captured sector stores.
   // Child/backend identities remain quarantined; frame credit is independent.
   if(stage_ACK_v && stage_ACK_r) begin
    if(fragment==7) state<=RF;else fragment<=fragment+1'b1;
   end
   if(rf_v && rf_r) state<=ACK;
   if(host_common_ACK && state!=ACK) fault_q<=1;
   if(state==ACK && host_common_ACK) state<=VISIBLE;
   // SIMD ACK is a different origin and cannot satisfy a host write.
   if(state==ACK && internal_SIMD_ACK) fault_q<=1;
   if(visible_v && visible_r) state<=CONSUME;
   if(consumer_done && state==CONSUME) state<=REVERSE;
   if(reverse_v && reverse_r) begin
    if(rev==15) state<=DRAIN;else rev<=rev+1'b1;
   end
   if(state==DRAIN && drain_v && drain_r) begin
    if(drained_parent!=parent_q || drained_ref!=ref_q || drained_epoch!=epoch_q || allcopy_zero!=9'h1ff) fault_q<=1;
    else begin state<=IDLE;if(reset_pending || reset_req) epoch_q<=epoch_q+1'b1;reset_pending<=0;end
   end
   // Empty operational reset still requires an external all-copy drain receipt.
   if(state==IDLE && (reset_pending || reset_req) && drain_r) begin
    if(allcopy_zero!=9'h1ff || drained_epoch!=epoch_q) fault_q<=1;
    else begin epoch_q<=epoch_q+1'b1;reset_pending<=0;end
   end
  end
 end
 end else begin:d
 assign start_r=0;assign req_v=0;assign req_byte=0;assign req_pc=0;assign req_owner=0;assign req_meta=0;assign req_len=0;assign req_beat=0;
 assign rsp_r=0;assign stage_ACK_v=0;assign stage_index=0;assign rf_v=0;assign rf_data=0;assign stable_parent=0;assign rf_dst=0;
 assign visible_v=0;assign reverse_v=0;assign reverse_meta=0;assign reverse_backend16=0;assign drain_v=0;
 assign reset_epoch=0;assign idle=1;assign fault=0;assign retained_native_owner=0;assign retained_native_generation=0;
 end endgenerate
endmodule
