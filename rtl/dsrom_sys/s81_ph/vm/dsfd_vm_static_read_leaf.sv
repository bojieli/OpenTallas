`timescale 1ns/1ps
`default_nettype none
// One independently clocked64-bit stripe. R0 bounded4:1, R1 pin register.
// G0/G1 are adjacent: only SU1 needs the registered G1 partial at G0 R1.
module dsfd_vm_static_read_leaf #(
 parameter integer G=0, W=64,
 parameter integer NP=(G==1?9:G==4?2:G>=6?4:8),
 parameter integer NO=(G==1?8:NP)
)(input wire ck,rst_n,input wire[4*W-1:0] i_data,input wire[3:0] i_valid,
 input wire[2*NP-1:0] i_sel,input wire[NP-1:0] i_expected,input wire i_su1_group,
 input wire[W-1:0] i_peer_data,input wire i_peer_valid,
 output wire[W-1:0] o_peer_data,output wire o_peer_valid,
 output reg[NP-1:0] o_partial_valid,output reg[NO*W-1:0] o_data,output reg fault);
 reg[1:0] reset_q;always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 wire rn=reset_q[1];
 reg[NP*W-1:0] partial_data;
 integer p;reg wanted;reg[1:0] s;
 always @(posedge ck)begin
  for(p=0;p<NP;p=p+1)begin
   s=i_sel[2*p+:2];
`ifdef OT_VM_READ_MUT_SELECT
   s=s^2'd1;
`endif
   // Explicit balanced two-level mux. No32slot dynamic index exists in this leaf.
   partial_data[W*p+:W]<=s[1]?(s[0]?i_data[3*W+:W]:i_data[2*W+:W]):(s[0]?i_data[W+:W]:i_data[0+:W]);
  end
  for(p=0;p<NO;p=p+1)begin
`ifdef OT_VM_READ_MUT_EARLY
   o_data[W*p+:W]<=i_data[W*i_sel[2*(p+(G==1?1:0))+:2]+:W];
`else
   if(G==0&&p==1)begin
`ifdef OT_VM_READ_MUT_SU1
    o_data[W*p+:W]<=partial_data[W*p+:W];
`else
    o_data[W*p+:W]<=i_peer_valid?i_peer_data:partial_data[W*p+:W];
`endif
   end else o_data[W*p+:W]<=partial_data[W*(p+(G==1?1:0))+:W];
`endif
  end
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin o_partial_valid<=0;fault<=0;end
  else for(integer q=0;q<NP;q=q+1)begin
   wanted=i_expected[q];
   if((G==0&&q==1)||(G==1&&q==0))wanted=wanted&&(i_su1_group==(G==1));
   o_partial_valid[q]<=wanted&&i_valid[i_sel[2*q+:2]];
   if(wanted&&!i_valid[i_sel[2*q+:2]])fault<=1;
  end
 end
 assign o_peer_data=(G==1)?partial_data[0+:W]:{W{1'b0}};
 assign o_peer_valid=(G==1)?o_partial_valid[0]:1'b0;
endmodule
`default_nettype wire
