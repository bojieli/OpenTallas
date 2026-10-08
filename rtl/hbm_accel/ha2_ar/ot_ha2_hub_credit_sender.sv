`timescale 1ns/1ps
// Reservations cover issued rows in the hub delay AND rows in the edge FIFO.
// Readiness is registered; no new row is issued without a reserved queue slot.
// Output valid/data launch together, based on previously observed receiver ready.
module ot_ha2_hub_credit_sender #(
 parameter integer W=544, INJ=2, AW=6, MUTANT=0
)(input wire clk,rst_n,
 input wire [INJ-1:0] issue_v,arrival_v,receiver_ready,
 input wire [INJ*W-1:0] arrival_data,
 output wire [INJ-1:0] issue_ready,
 output reg [INJ-1:0] send_v,
 output reg [INJ*W-1:0] send_data,
 output wire quiet, fault);
 localparam integer DEPTH=1<<AW;
 wire [INJ-1:0] fifo_empty,fifo_overflow,res_fault,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  reg [AW:0] reserved;
  reg ready_q,bad;
  wire [AW:0] count;
  wire [W-1:0] head;
  wire pop=!fifo_empty[i] && (MUTANT==2 || receiver_ready[i]);
  assign issue_ready[i]=(MUTANT==1)?1'b1:ready_q;
  assign res_fault[i]=bad;
  assign idle[i]=(reserved==0)&&fifo_empty[i]&&!send_v[i];
  ot_ha2_fifo #(.W(W),.AW(AW)) u_queue(
    .clk(clk),.rst_n(rst_n),.push(arrival_v[i]),.din(arrival_data[i*W+:W]),
    .pop(pop),.empty(fifo_empty[i]),.dout(head),.ovf(fifo_overflow[i]),.count(count));
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin reserved<=0;ready_q<=1;bad<=0;send_v[i]<=0;end
   else begin:account
    integer next_reserved;
    next_reserved=integer'(reserved)+(issue_v[i]?1:0)-(pop?1:0);
    if((issue_v[i]&&!issue_ready[i]) || next_reserved<0 || next_reserved>DEPTH ||
       (arrival_v[i]&&reserved==0&&!issue_v[i]))bad<=1;
    if(next_reserved>=0 && next_reserved<=DEPTH)reserved<=next_reserved;
    ready_q<=next_reserved>=0 && next_reserved<DEPTH;
    send_v[i]<=pop;
   end
  always @(posedge clk)if(pop)send_data[i*W+:W]<=head;
 end
 assign quiet=&idle;
 assign fault=(|fifo_overflow)||(|res_fault);
endmodule
