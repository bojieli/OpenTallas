`timescale 1ns/1ps
`default_nettype none
// Quartet-local metadata/valid/fault hard leaf: same two-edge age as data.
// IN_REG=1 (READ_PIPE 2, claude S81 VM F5 2026-10-15): i_expected/i_slot are registered at their pins (one edge,
// matching the data leaves' pin registers, so o_valid keeps the data age), and every stripe valid / peer / fault
// input that feeds the sticky fault reduction is first captured by its own pin register: the 64->1 fault OR tree
// runs register-to-register one edge later (native capture audit: v0 i_partial_valid 276 ps through the fault
// tree).  The o_valid completeness AND stays one level behind its pins; o_valid timing is unchanged in edges.
// r2 (routed audit of r1-pinreg: v0_p capture 239.5, the cross-stripe AND i_partial_valid->o_valid): with IN_REG=1
// completeness is recomputed from the memory group's own slot-valid bits (i_slot_valid, the same bits the data
// leaves select; pin-registered): stage A wanted && valid[slot] per stripe pair, stage B AND over the pairs ->
// o_valid, both register-to-register, same o_valid age.  i_partial_valid / i_peer_valid only feed the registered
// fault checks (unchanged: q partial valid != expectation, SU1 both-present), so a missing or wrong data-leaf valid
// still raises the sticky fault.
module dsfd_vm_static_read_valid #(
 parameter integer G=0, STRIPES=8, IN_REG=0,
 parameter integer NP=(G==1?9:G==4?2:G>=6?4:8),
 parameter integer NV=(G==1?8:G==5?5:NP),
 parameter integer NK=STRIPES/2, SV=(G<=1?8:4), SB=(G<=1?0:4*G)
)(input wire ck,rst_n,input wire[NP-1:0] i_expected,input wire[NP*5-1:0] i_slot,
 input wire[NK*SV-1:0] i_slot_valid,
 input wire[STRIPES*NP-1:0] i_partial_valid,input wire[STRIPES-1:0] i_peer_valid,
 input wire[STRIPES-1:0] i_fault,output reg[NV-1:0] o_valid,output reg fault);
 reg[1:0] reset_q;always @(posedge ck or negedge rst_n)if(!rst_n)reset_q<=0;else reset_q<={reset_q[0],1'b1};
 wire rn=reset_q[1];reg[NP-1:0] exp_q;reg bad_q;
 wire[NP-1:0] d_expected;wire[NP*5-1:0] d_slot;
 // fault-observation copies (IN_REG): pin registers of the checked inputs and the expectation they are checked against
 reg[STRIPES*NP-1:0] f_pv;reg[STRIPES-1:0] f_peer,f_fault;reg[NP-1:0] f_exp;reg f_bad;
 wire[NK*SV-1:0] d_sv;reg[NK*NP-1:0] pvr;
 generate if(IN_REG)begin:ri
  reg[NP-1:0] q_expected;reg[NP*5-1:0] q_slot;reg[NK*SV-1:0] q_sv;
  always @(posedge ck)q_slot<=i_slot;
  always @(posedge ck or negedge rn)if(!rn)begin q_expected<=0;q_sv<=0;end else begin q_expected<=i_expected;q_sv<=i_slot_valid;end
  assign d_expected=q_expected;assign d_slot=q_slot;
`ifdef OT_VM_READ_MUT_SVIGNORE
  assign d_sv={NK*SV{1'b1}};
`else
  assign d_sv=q_sv;
`endif
 end else begin:rn0
  assign d_expected=i_expected;assign d_slot=i_slot;assign d_sv=0;
 end endgenerate
 always @(posedge ck or negedge rn)if(!rn)begin f_pv<=0;f_peer<=0;f_fault<=0;f_exp<=0;f_bad<=0;end
  else begin f_pv<=i_partial_valid;f_peer<=i_peer_valid;f_fault<=i_fault;f_exp<=exp_q;f_bad<=bad_q;end
 integer p,b,k;reg legal,wanted,bad,want_v;reg[4:0] slot;reg[NP-1:0] complete;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin exp_q<=0;bad_q<=0;o_valid<=0;fault<=0;pvr<=0;end
  else begin
   bad=0;
   for(p=0;p<NP;p=p+1)begin
    slot=d_slot[5*p+:5];legal=(slot[4:2]==G);
    if(G==0&&p==0)legal=slot<4;
    if((G==0&&p==1)||(G==1&&p==0))legal=slot<8;
    if(G==0&&(p==2||p==3))legal=slot==p;
    if(G==1&&p>=1&&p<=4)legal=slot==p+3;
    if((G==2||G==3)&&p<4)legal=slot==4*G+p;
    if(G==4)legal=slot>=16&&slot<20;
    if(G==5&&p<4)legal=slot==20+p;
    if(G>=6)legal=slot==4*G+p;
    wanted=d_expected[p];
    if(wanted&&!legal)bad=1;
    // stage A (IN_REG): the slot's own valid bit in each stripe pair; G0 SU1 takes either quartet's slot
    want_v=(G==1&&p==0)?(wanted&&slot[2]):wanted;
    for(k=0;k<NK;k=k+1)pvr[NP*k+p]<=want_v&&(slot>=SB)&&(slot<SB+SV)&&d_sv[SV*k+((slot-SB)%SV)];
    if((G==0&&p==1)||(G==1&&p==0))wanted=wanted&&(slot[2]==(G==1));
    exp_q[p]<=wanted;
   end
   bad_q<=bad;
   complete=IN_REG?{NP{1'b1}}:exp_q;
   // stage B (IN_REG): AND of the registered per-pair valids
   if(IN_REG)for(p=0;p<NP;p=p+1)for(k=0;k<NK;k=k+1)complete[p]=complete[p]&&pvr[NP*k+p];
   for(p=0;p<NP;p=p+1)for(b=0;b<STRIPES;b=b+1)begin
    if(IN_REG?(f_pv[NP*b+p]!=f_exp[p]):(i_partial_valid[NP*b+p]!=exp_q[p]))fault<=1;
    if(!IN_REG)complete[p]=complete[p]&&i_partial_valid[NP*b+p];
   end
   if(G==0)begin
    // The SU1 candidate is present at exactly one of its two neighboring quartets.
    for(b=0;b<STRIPES;b=b+1)begin
     if(IN_REG?(f_peer[b]&&f_pv[NP*b+1]):(i_peer_valid[b]&&i_partial_valid[NP*b+1]))fault<=1;
    end
    if(!IN_REG)begin
     complete[1]=1'b1;
     for(b=0;b<STRIPES;b=b+1)complete[1]=complete[1]&&(i_partial_valid[NP*b+1]||i_peer_valid[b]);
    end
   end
   if(G==5)begin
    o_valid[0]<=&complete[3:0];o_valid[4:1]<=complete[7:4];
   end else for(p=0;p<NV;p=p+1)o_valid[p]<=complete[p+(G==1?1:0)];
   if(IN_REG?(f_bad||(|f_fault)):(bad_q||(|i_fault)))fault<=1;
  end
 end
endmodule
`default_nettype wire
