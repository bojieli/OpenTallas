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
 wire [352:0] payload={stage_id,rank_id,tid,user_id,position,token,epoch_id,arrival_deadline,programme_id,t_host,t_kd};
 wire [352:0] saved;
 wire permit=configured&&context_valid&&stage_id<241&&!(require_kit&&(!t_kd[53]||t_kd[52:32]!=token));
 genvar b;
 generate for(b=0;b<24;b=b+1)begin:g_hold
  localparam integer W=(353-15*b<15)?353-15*b:15;
  (* keep_hierarchy="yes" *) dsdv_hostb_return_bank #(.ID(b),.W(W)) u_bank(.ck(ck),.sample(sample_slot),.permit(permit),.d(payload[15*b+:W]),.q(saved[15*b+:W]));
 end endgenerate
 wire [7:0] hs;wire [1:0] hr;wire [15:0] ht;wire [9:0] hu;wire [20:0] hp,hk;wire [31:0] he;wire [47:0] hd;wire [63:0] hg;wire [76:0] hh;wire [53:0] hkd;
 assign {hs,hr,ht,hu,hp,hk,he,hd,hg,hh,hkd}=saved;
 wire sample_good=sample_slot&&permit;
 always @*begin
   held=0;held[31:0]=32'h31454248;held[35:32]=2;held[39:36]=3;
   held[47:40]=hs;held[49:48]=hr;held[65:50]=ht;held[75:66]=131;
   held[87:78]=hu;held[108:88]=hp;held[129:109]=hk;
   held[161:130]=he;held[209:162]=hd;held[273:210]=hg;
   held[350:274]=hh;held[404:351]=hkd;
 end
 always @(posedge ck)begin
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
