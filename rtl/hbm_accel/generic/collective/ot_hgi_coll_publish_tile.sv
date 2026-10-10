`timescale 1ns/1ps
`default_nettype none
// Harden one publisher lane then replicate four. Encoded output is a pin flop;
// consumer corrects/captures at its own boundary. CAP127 + this slot =128 total.
module ot_hgi_coll_publish_tile #(parameter integer ENABLE=0,W=544,MUT=0)(
 input wire clk,rst_n,push,pop,input wire[W-1:0]din,
 output wire valid,output wire[((W+31)/32)*39-1:0]encoded,
 output wire fault,output wire[7:0]occupancy
);
 localparam integer NW=(W+31)/32;
 reg[NW*39-1:0]encoded_p;
 wire[NW*39-1:0]coded_head;
 wire iv,ce,core_fault;wire[W-1:0]data;wire[7:0]core_count;
 reg ov,ovi,bad;wire corrupt=(ov^ovi)!=1'b1;
 assign valid=ENABLE!=0&&ov&&!corrupt&&!bad&&!core_fault;
 assign fault=bad||core_fault||corrupt;
 assign occupancy=core_count+8'(ov);
 wire advance=ENABLE!=0&&!fault&&iv&&(!ov||pop);
 ot_hgi_coll_publish_fifo #(.ENABLE(ENABLE),.W(W),.CAP(127),.MUT(MUT))core(
  .clk(clk),.rst_n(rst_n),.push(push),.din(din),.pop(advance),
  .valid(iv),.dout(data),.corrected(ce),.fault(core_fault),.occupancy(core_count),.coded_head(coded_head));
 // Encoded head -> encoded output pin flop; consumer corrects at its capture.
 always @(posedge clk)if(advance)encoded_p<=coded_head;
 assign encoded=MUT==2?coded_head:encoded_p;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ov<=0;ovi<=1;bad<=0;end
  else if(ENABLE!=0)begin
   if(corrupt||(pop&&!valid)||occupancy>128)bad<=1;
   if(!fault)begin
    if(advance)begin ov<=1;ovi<=0;end
    else if(pop)begin ov<=0;ovi<=1;end
   end
  end
 end
endmodule
`default_nettype wire
