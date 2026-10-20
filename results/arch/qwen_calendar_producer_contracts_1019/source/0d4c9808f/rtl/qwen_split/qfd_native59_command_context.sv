`timescale 1ns/1ps
// Real HOST identity and accepted head context bind the native command.
// HOST owns epoch allocation. No local epoch, layer, token or position counter.
// Native descriptor must be the actual source-pinned PC11 production word.
// Template SHA256 95e38d7b62b96e5a0f59290d151152ca33b89c725f70a221e4adf4d910521fd3
module qfd_native59_command_context(
 input wire ck,rst_n,
 input wire host_epoch_valid,host_fused_capability,input wire [15:0] host_epoch,
 input wire [58:0] host_tag,input wire [1:0] host_generation,
 input wire context_v,input wire [5:0] context_stage,
 input wire [17:0] context_token,context_position,
 input wire [379:0] native_cmd,input wire [5:0] command_stage,
 input wire [17:0] command_token,command_position,
 input wire service_active,
 output wire begin_slot,output wire [58:0] begin_tag,
 output wire request_slot,output wire [58:0] request_tag,
 output wire [19:0] result_base_word,output reg fault
);
 localparam [379:0] TEMPLATE=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;
 reg valid,cap;reg [1:0] generation;reg [58:0] context_tag;
 assign begin_slot=context_v;
 assign begin_tag={host_epoch,context_stage,context_token,context_position[12:0],6'd0};
 assign request_slot=native_cmd[0];
 assign request_tag={context_tag[58:43],command_stage,command_token,command_position[12:0],6'd0};
 assign result_base_word=native_cmd[299:280];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin valid<=0;cap<=0;generation<=0;context_tag<=0;fault<=0;end
  else begin
   if(context_v)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||host_tag[36:19]!=context_token||host_tag[18:6]!=context_position||service_active||!host_epoch_valid||!host_fused_capability||(valid&&begin_tag==context_tag)||context_stage<1||context_stage>36||context_token>=151936||context_position>=8192)fault<=1;
    valid<=1;cap<=host_fused_capability;generation<=host_generation;context_tag<=begin_tag;
   end
   if(request_slot)begin
    if(host_tag[58:43]!=host_epoch||host_tag[42:37]!=0||host_tag[5:0]!=0||host_tag[36:19]!=context_tag[36:19]||host_tag[18:6]!=context_tag[18:6]||host_generation!=generation||!valid||context_v||!host_epoch_valid||!cap||!host_fused_capability||host_epoch!=context_tag[58:43]||request_tag!=context_tag||command_position>=8192||native_cmd!=TEMPLATE)fault<=1;
   end
  end
 end
endmodule
