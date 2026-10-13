`timescale 1ns/1ps
`default_nettype none
// Source-explicit GLOBAL WORD command -> legacy LOCAL WORD aperture lease.
// Caller reserves lane/publication resources before installed=1 and owner grant.
module ot_hbm_b2_xload_command #(parameter integer MUT=0)(
 input wire clk,rst_n,installed,
 input wire cmd_v,output wire cmd_r,input wire [191:0] cmd_owner,
 input wire [39:0] cmd_base,input wire [20:0] cmd_n,input wire [3:0] cmd_p,
 input wire [31:0] cmd_stride,input wire [1:0] cmd_space,cmd_fmt,
 input wire [6:0] cmd_xb,input wire [1:0] cluster_sid,
 output wire x_v,input wire x_rdy,output wire [39:0] x_base,
 output wire [20:0] x_n,output wire [3:0] x_p,output wire [31:0] x_stride,
 output wire [1:0] x_space,x_fmt,output wire [6:0] x_xb,
 input wire x_done,input wire traffic_drained,
 output wire lease_v,output wire [191:0] lease_owner,
 output wire [1:0] lease_sid,output wire lease_mirror,
 output reg done,output reg fault
);
 localparam [1:0] IDLE=0,SEND=1,RUN=2,DRAIN=3;
 reg [1:0] state,sid_q;reg mirror_q;
 reg [191:0] owner_q;reg [39:0] base_q;reg [20:0] n_q;
 reg [3:0] p_q;reg [31:0] stride_q;reg [1:0] fmt_q;reg [6:0] xb_q;
 wire mirror=cmd_base>=40'd262144&&cmd_base<40'd294912;
 wire [39:0] aperture_base=mirror?40'd262144:{22'd0,cluster_sid,16'd0};
 wire [39:0] aperture_limit=aperture_base+(mirror?40'd32768:40'd65536);
 wire [44:0] span={5'd0,cmd_base}+45'(cmd_p-4'd1)*45'(cmd_stride)+45'(cmd_n);
 wire [21:0] group_scale=cmd_fmt==1?22'd1024:cmd_fmt==2?22'd2048:22'd512;
 wire [21:0] groups=({1'b0,cmd_n}+group_scale-1'b1)/group_scale;
 wire legal=installed&&cmd_space==1&&cmd_p>0&&cmd_p<=8&&cmd_n>0&&cmd_stride<=65536&&
  cmd_base[2:0]==0&&cmd_stride[2:0]==0&&cmd_base>=aperture_base&&span<=45'(aperture_limit)&&
  (!(cmd_fmt==1||cmd_fmt==2)||cmd_n[4:0]==0)&&22'(cmd_xb)+groups*22'd8<=128;
 assign cmd_r=state==IDLE&&legal&&!fault;
 assign x_v=state==SEND&&!fault;assign x_base=base_q;assign x_n=n_q;assign x_p=p_q;
 assign x_stride=stride_q;assign x_space=2'd1;assign x_fmt=fmt_q;assign x_xb=xb_q;
 assign lease_v=state!=IDLE&&!fault;assign lease_owner=owner_q;
 assign lease_sid=sid_q;assign lease_mirror=mirror_q;
 always @(posedge clk)if(cmd_v&&cmd_r)begin
  base_q<=MUT==1?cmd_base:cmd_base-aperture_base;n_q<=cmd_n;p_q<=cmd_p;stride_q<=cmd_stride;
  fmt_q<=cmd_fmt;xb_q<=cmd_xb;owner_q<=cmd_owner;sid_q<=cluster_sid;mirror_q<=mirror;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;done<=0;fault<=0;end
  else begin
   done<=0;
   if((cmd_v&&state==IDLE&&!legal)||(x_done&&state!=RUN)||(state!=IDLE&&!installed))fault<=1;
   if(!fault)case(state)
    IDLE:if(cmd_v&&cmd_r)state<=SEND;
    SEND:if(x_v&&x_rdy)state<=RUN;
    RUN:if(x_done)state<=DRAIN;
    DRAIN:if(traffic_drained)begin state<=IDLE;done<=1;end
   endcase
  end
 end
endmodule
`default_nettype wire
