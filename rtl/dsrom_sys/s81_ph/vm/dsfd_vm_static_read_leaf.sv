`timescale 1ns/1ps
`default_nettype none
// One independently clocked64-bit stripe. R0 bounded4:1, R1 pin register.
// G0/G1 are adjacent: only SU1 needs the registered G1 partial at G0 R1.
// IN_REG=1 (READ_PIPE 2, claude S81 VM F5 2026-10-15): every functional input is registered at its pin (RI) before
// R0, so no input pin reaches the 4:1 select / valid / fault logic or crosses the leaf combinationally (native
// capture audit: q0 i_sel 316 ps, i_data 230 pins > 190).  Adds exactly one edge to data, partial valid, peer and
// fault.  SU1 at G0 R1 is then selected by the registered su1 group (the G1 peer is valid only when su1==1, and
// G0's own slot-1 candidate only when su1==0), so i_peer_valid feeds only a registered consistency fault; the
// returned word is identical whenever its slot is valid (data of an invalid slot is not defined by the schedule).
module dsfd_vm_static_read_leaf #(
 parameter integer G=0, W=64, IN_REG=0,
 parameter integer NP=(G==1?9:G==4?2:G>=6?4:8),
 parameter integer NO=(G==1?8:NP)
)(input wire ck,rst_n,input wire[4*W-1:0] i_data,input wire[3:0] i_valid,
 input wire[2*NP-1:0] i_sel,input wire[NP-1:0] i_expected,input wire i_su1_group,
 input wire[W-1:0] i_peer_data,input wire i_peer_valid,
 output wire[W-1:0] o_peer_data,output wire o_peer_valid,
 output reg[NP-1:0] o_partial_valid,output reg[NO*W-1:0] o_data,output reg fault);
 reg[1:0] reset_q;always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 wire rn=reset_q[1];
 wire[4*W-1:0] d_data;wire[3:0] d_valid;wire[2*NP-1:0] d_sel;wire[NP-1:0] d_expected;wire d_su1;
 reg su1_p,su1_pp,peer_v_q;
 generate if(IN_REG)begin:ri
  reg[4*W-1:0] q_data;reg[3:0] q_valid;reg[2*NP-1:0] q_sel;reg[NP-1:0] q_expected;reg q_su1;
  always @(posedge ck)begin q_data<=i_data;q_sel<=i_sel;end
  always @(posedge ck or negedge rn)if(!rn)begin q_valid<=0;q_expected<=0;q_su1<=0;end
   else begin q_valid<=i_valid;q_expected<=i_expected;q_su1<=i_su1_group;end
  assign d_data=q_data;assign d_valid=q_valid;assign d_sel=q_sel;assign d_expected=q_expected;assign d_su1=q_su1;
 end else begin:rn0
  assign d_data=i_data;assign d_valid=i_valid;assign d_sel=i_sel;assign d_expected=i_expected;assign d_su1=i_su1_group;
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)begin su1_p<=0;su1_pp<=0;peer_v_q<=0;end
  else begin su1_p<=d_su1;su1_pp<=su1_p;peer_v_q<=i_peer_valid;end
 wire peer_take=IN_REG?su1_p:i_peer_valid;
 reg[NP*W-1:0] partial_data;
 integer p;reg wanted;reg[1:0] s;
 always @(posedge ck)begin
  for(p=0;p<NP;p=p+1)begin
   s=d_sel[2*p+:2];
`ifdef OT_VM_READ_MUT_SELECT
   s=s^2'd1;
`endif
   // Explicit balanced two-level mux. No32slot dynamic index exists in this leaf.
   partial_data[W*p+:W]<=s[1]?(s[0]?d_data[3*W+:W]:d_data[2*W+:W]):(s[0]?d_data[W+:W]:d_data[0+:W]);
  end
  for(p=0;p<NO;p=p+1)begin
`ifdef OT_VM_READ_MUT_EARLY
   o_data[W*p+:W]<=d_data[W*d_sel[2*(p+(G==1?1:0))+:2]+:W];
`else
   if(G==0&&p==1)begin
`ifdef OT_VM_READ_MUT_SU1
    o_data[W*p+:W]<=partial_data[W*p+:W];
`else
    o_data[W*p+:W]<=peer_take?i_peer_data:partial_data[W*p+:W];
`endif
   end else o_data[W*p+:W]<=partial_data[W*(p+(G==1?1:0))+:W];
`endif
  end
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin o_partial_valid<=0;fault<=0;end
  else begin for(integer q=0;q<NP;q=q+1)begin
   wanted=d_expected[q];
   if((G==0&&q==1)||(G==1&&q==0))wanted=wanted&&(d_su1==(G==1));
   o_partial_valid[q]<=wanted&&d_valid[d_sel[2*q+:2]];
   if(wanted&&!d_valid[d_sel[2*q+:2]])fault<=1;
  end
  // IN_REG: a G1 peer word may arrive only for an su1 group (registered at the pin, aligned to su1_pp).
  if(IN_REG&&G==0&&peer_v_q&&!su1_pp)fault<=1;
  end
 end
 assign o_peer_data=(G==1)?partial_data[0+:W]:{W{1'b0}};
 assign o_peer_valid=(G==1)?o_partial_valid[0]:1'b0;
endmodule
`default_nettype wire
