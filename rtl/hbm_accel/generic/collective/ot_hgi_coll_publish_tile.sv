`timescale 1ns/1ps
`default_nettype none
// Harden one publisher lane then replicate four. Encoded output is a pin flop;
// consumer corrects/captures at its own boundary. RawPI1 + CAP126 + codedPO1 =128.
module ot_hgi_coll_publish_tile #(parameter integer ENABLE=0,W=544,MUT=0)(
 input wire clk,rst_n,push,pop,input wire[W-1:0]din,
 output wire valid,output wire[((W+31)/32)*39-1:0]encoded,
 output wire fault,output wire[7:0]occupancy
);
 localparam integer NW=(W+31)/32;
 reg[NW*39-1:0]encoded_p;
 wire[NW*39-1:0]coded_head;
 wire iv,ce,core_fault;wire[W-1:0]data;wire[7:0]core_count;
 reg ov,ovi,bad,badi;wire corrupt=(ov^ovi)!=1'b1||(bad^badi)!=1'b1;
 reg[W-1:0]raw_pi;reg pi,pii;wire pi_bad=(pi^pii)!=1'b1;
 wire core_ready;wire pi_accept=pi&&core_ready&&!pi_bad&&!bad;
 wire pi_room=!pi||pi_accept;
 always @(posedge clk)if(push&&pi_room)raw_pi<=din;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin pi<=0;pii<=1;end
 else if(ENABLE!=0)begin pi<=push||(pi&&!pi_accept);pii<=~(push||(pi&&!pi_accept));end
 assign valid=ENABLE!=0&&ov&&!corrupt&&!pi_bad&&!bad&&!core_fault;
 assign fault=bad||core_fault||corrupt||pi_bad;
 assign occupancy=core_count+8'(ov)+8'(pi);
 wire advance=ENABLE!=0&&!fault&&iv&&(!ov||pop);
 ot_hgi_coll_publish_fifo #(.ENABLE(ENABLE),.W(W),.CAP(126),.MUT(MUT))core(
  .clk(clk),.rst_n(rst_n),.push(pi_accept),.din(raw_pi),.pop(advance),
  .valid(iv),.dout(data),.corrected(ce),.fault(core_fault),.occupancy(core_count),.coded_head(coded_head),.input_ready(core_ready));
 // Encoded head -> encoded output pin flop; consumer corrects at its capture.
 always @(posedge clk)if(advance)encoded_p<=coded_head;
 assign encoded=MUT==2?coded_head:encoded_p;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin ov<=0;ovi<=1;bad<=0;badi<=1;end
  else if(ENABLE!=0)begin
   if(corrupt||pi_bad||(pop&&!valid)||(push&&!pi_room)||occupancy>128)begin bad<=1;badi<=0;end
   if(!fault)begin
    if(advance)begin ov<=1;ovi<=0;end
    else if(pop)begin ov<=0;ovi<=1;end
   end
  end
 end
endmodule
`default_nettype wire
