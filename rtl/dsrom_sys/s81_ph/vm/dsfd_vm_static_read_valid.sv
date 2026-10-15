`timescale 1ns/1ps
`default_nettype none
// Quartet-local metadata/valid/fault hard leaf: same two-edge age as data.
module dsfd_vm_static_read_valid #(
 parameter integer G=0, STRIPES=8,
 parameter integer NP=(G==1?9:G==4?2:G>=6?4:8),
 parameter integer NV=(G==1?8:G==5?5:NP)
)(input wire ck,rst_n,input wire[NP-1:0] i_expected,input wire[NP*5-1:0] i_slot,
 input wire[STRIPES*NP-1:0] i_partial_valid,input wire[STRIPES-1:0] i_peer_valid,
 input wire[STRIPES-1:0] i_fault,output reg[NV-1:0] o_valid,output reg fault);
 reg[1:0] reset_q;always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 wire rn=reset_q[1];reg[NP-1:0] exp_q;reg bad_q;
 integer p,b;reg legal,wanted,bad;reg[4:0] slot;reg[NP-1:0] complete;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin exp_q<=0;bad_q<=0;o_valid<=0;fault<=0;end
  else begin
   bad=0;
   for(p=0;p<NP;p=p+1)begin
    slot=i_slot[5*p+:5];legal=(slot[4:2]==G);
    if(G==0&&p==0)legal=slot<4;
    if((G==0&&p==1)||(G==1&&p==0))legal=slot<8;
    if(G==0&&(p==2||p==3))legal=slot==p;
    if(G==1&&p>=1&&p<=4)legal=slot==p+3;
    if((G==2||G==3)&&p<4)legal=slot==4*G+p;
    if(G==4)legal=slot>=16&&slot<20;
    if(G==5&&p<4)legal=slot==20+p;
    if(G>=6)legal=slot==4*G+p;
    wanted=i_expected[p];
    if(wanted&&!legal)bad=1;
    if((G==0&&p==1)||(G==1&&p==0))wanted=wanted&&(slot[2]==(G==1));
    exp_q[p]<=wanted;
   end
   bad_q<=bad;
   complete=exp_q;
   for(p=0;p<NP;p=p+1)for(b=0;b<STRIPES;b=b+1)begin
    if(i_partial_valid[NP*b+p]!=exp_q[p])fault<=1;
    complete[p]=complete[p]&&i_partial_valid[NP*b+p];
   end
   if(G==0)begin
    // The SU1 candidate is present at exactly one of its two neighboring quartets.
    for(b=0;b<STRIPES;b=b+1)begin
     if(i_peer_valid[b]&&i_partial_valid[NP*b+1])fault<=1;
    end
    complete[1]=1'b1;
    for(b=0;b<STRIPES;b=b+1)complete[1]=complete[1]&&(i_partial_valid[NP*b+1]||i_peer_valid[b]);
   end
   if(G==5)begin
    o_valid[0]<=&complete[3:0];o_valid[4:1]<=complete[7:4];
   end else for(p=0;p<NV;p=p+1)o_valid[p]<=complete[p+(G==1?1:0)];
   if(bad_q||(|i_fault))fault<=1;
  end
 end
endmodule
`default_nettype wire
