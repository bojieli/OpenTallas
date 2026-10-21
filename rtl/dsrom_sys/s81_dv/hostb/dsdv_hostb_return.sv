`timescale 1ns/1ps
`default_nettype none
// require_kit is source-bound only to G8 WALK issuer6c77b4 (valid/token[52:32]);
// future producer schemas need their own source contract, never infer user/pos.
// Actual producer bits sampled at a compiled slot, never manufacture KIT/done.
module dsdv_hostb_return(input wire ck,rst_n,configured,
 input wire sample_slot,send_slot,require_kit,context_valid,
 input wire [7:0] stage_id,input wire [1:0] rank_id,
 input wire [15:0] tid,input wire [9:0] user_id,
 input wire [20:0] position,token,input wire [31:0] epoch_id,
 input wire [47:0] arrival_deadline,input wire [63:0] programme_id,
 input wire [76:0] t_host,input wire [53:0] t_kd,
 output reg [1103:0] return_ring,output reg [3:0] fault);
 wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 reg pending;reg [511:0] held;
 wire sample_good=sample_slot && configured && context_valid && stage_id<241 && !(require_kit&&(!t_kd[53]||t_kd[52:32]!=token));
 reg [511:0] record;
 always @* begin
   record=0;record[31:0]=32'h31454248;record[35:32]=2;record[39:36]=3;
   record[47:40]=stage_id;record[49:48]=rank_id;record[65:50]=tid;record[75:66]=131;
   record[87:78]=user_id;record[108:88]=position;record[129:109]=token;
   record[161:130]=epoch_id;record[209:162]=arrival_deadline;record[273:210]=programme_id;
   record[350:274]=t_host;record[404:351]=t_kd;
 end
 always @(posedge ck)begin
   if(sample_good)held<=record;
   return_ring[1103:1]<={571'd0,held,8'd0,4'd0,5'd1,3'd6};
 end
 always @(posedge ck or negedge rn)begin
   if(!rn)begin pending<=0;return_ring[0]<=0;fault<=0;end
   else begin
     return_ring[0]<=0;
     if(sample_slot)begin
       if(!sample_good)fault[0]<=1;
       else if(pending)fault[1]<=1;
       else pending<=1;
     end
     if(send_slot)begin
       if(!pending || sample_slot)fault[2]<=1;
       else begin return_ring[0]<=fault==0;pending<=0;end
     end
   end
 end
endmodule
`default_nettype wire
