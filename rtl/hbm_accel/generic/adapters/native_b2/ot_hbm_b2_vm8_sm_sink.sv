`timescale 1ns/1ps
`default_nettype none
// NEW producer ABI {en, addr7, grp7, data2048}, not inferred from old x bus.
// Explicit owner192 is retained through the actual SM sampling edge.
module ot_hbm_b2_vm8_sm_sink #(parameter integer MUT=0,parameter integer PIPE=0)(
 input wire clk,rst_n,input wire permit,
 input wire [191:0] expected_owner,input wire [7:0] sm_mask,
 input wire tap_v,output wire tap_ready,input wire [2062:0] tap_data,
 input wire [191:0] tap_owner,input wire [15:0] tap_ticket,
 output reg tap_ACK_v,output reg [191:0] tap_ACK_owner,output reg [15:0] tap_ACK_ticket,
 output reg [7:0] xw_en,output wire [8*7-1:0] xw_addr,xw_grp,
 output wire [8*2048-1:0] xw_data,output reg fault,output wire drained
);
 reg pending;reg [191:0] owner_q;reg [15:0] ticket_q;
 reg [6:0] addr_q,grp_q;reg [2047:0] data_q;
 wire legal=permit&&sm_mask!=0&&tap_owner==expected_owner&&tap_data[2062]&&tap_data[2054:2048]<13&&
  (tap_data[2054:2048]!=12||tap_data[2047:640]==0);
 wire take=tap_v&&tap_ready;
 assign tap_ready=permit&&!fault&&(PIPE!=0||(!pending&&!tap_ACK_v));
 assign drained=!pending&&!tap_ACK_v&&xw_en==0;
 for(genvar s=0;s<8;s=s+1)begin:sm
  assign xw_addr[s*7+:7]=addr_q;assign xw_grp[s*7+:7]=grp_q;
  assign xw_data[s*2048+:2048]=MUT==1?{data_q[2047:2],data_q[0],data_q[1]}:data_q;
 end
 always @(posedge clk)begin
  if(take&&legal)begin data_q<=tap_data[2047:0];grp_q<=tap_data[2054:2048];addr_q<=tap_data[2061:2055];owner_q<=tap_owner;ticket_q<=tap_ticket;end
  if(pending)begin tap_ACK_owner<=owner_q;tap_ACK_ticket<=MUT==2?ticket_q^16'd1:ticket_q;end
  if(MUT==3&&take&&legal)begin tap_ACK_owner<=tap_owner;tap_ACK_ticket<=tap_ticket;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin pending<=0;tap_ACK_v<=0;xw_en<=0;fault<=0;end
  else begin
   xw_en<=0;tap_ACK_v<=0;pending<=0;
   if(tap_v&&!legal)fault<=1;
   if(take&&legal)begin xw_en<=sm_mask;pending<=1;if(MUT==3)tap_ACK_v<=1;end
   // Current xw_en is sampled by the native SM on this edge.
   if(pending)begin
    if(!permit||expected_owner!=owner_q)fault<=1;
    else if(MUT!=3)tap_ACK_v<=1;
   end
  end
 end
initial if(PIPE!=0&&PIPE!=1)$fatal(1,"PIPE must be0 or1");
endmodule
`default_nettype wire
