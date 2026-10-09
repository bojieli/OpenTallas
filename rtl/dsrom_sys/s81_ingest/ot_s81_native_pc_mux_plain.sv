`timescale 1ns/1ps
// Default-off actual dsfd_ctrl_pc rq341/rk/wd/rv endpoint. Four sources hold
// eight initial queue credits each. decode0 has priority; 1hostKV/2RoPE/3Engram
// alternate. One active transaction/PC preserves untagged physical wd identity
// even when the PHY scheduler reorders other requests. No cross-PC serialization.
// Flop queue payload/control has no ECC, parity, TMR or mirrors (confirmed review53).
// PICK=1 (sys-takeover 2026-10-09, opt-in; pcmux_plain_b TT -204 / SS -646 = count -> arbitration -> 340-b 4x8:1 head mux
// -> rq / queue write enable, 23-29 levels): the arbitration result is registered (stage A), the chosen head is
// fetched into a pick register (stage B, may run while the previous transaction is busy), and the launch uses the
// pick register.  +2 edges on an idle-port request, hidden behind a busy transaction otherwise.
module ot_s81_native_pc_mux_plain #(parameter integer ENABLE=0, parameter [339:0] QUEUE_INJECT=0, parameter integer PICK=0,
 // PRE=1 (sys-takeover 2026-10-09, with PICK; pcmux_pick3_b TT -56.7: cho_q -> 4 x 8:1 x 340-b queue mux -> phd 24 lv,
 // ctrl_live -> queue write enable 15 lv): per-source head registers hd_src[i] == queue[i][rp[i]] (re-read every edge,
 // following the pop) so the pick is a 4:1 mux of flops; the queue payload is
 // written on every push from a reset-less block (a push is credit-legal; an illegal one faults anyway).  0 cycles.
 parameter integer PRE=0)(
 input wire ck,rst_n,ctrl_live,
 input wire[4*341-1:0] src_rq,output reg[3:0] src_rk,
 output reg[340:0] rq,input wire rk,wd,
 input wire rv,input wire[255:0] r_data,input wire[16:0] r_tag,input wire[3:0] r_beat,
 output reg[3:0] src_wd,src_rv,src_done,output wire[4*256-1:0] src_rdata,
 output wire[4*17-1:0] src_rtag,output wire[4*4-1:0] src_rbeat,
 output wire pending,output reg ce,fault
);
 generate if(!ENABLE)begin:g_off
  assign pending=0;
  always @(*)begin src_rk=0;rq=0;src_wd=0;src_rv=0;src_done=0;ce=0;fault=0;end
  assign src_rdata=0;assign src_rtag=0;assign src_rbeat=0;
 end else begin:g_on
  // Ordinary flop queue payload; no SRAM macro or ECC claim.
  reg[339:0] queue[0:3][0:7];reg[2:0] wp[0:3],rp[0:3];reg[3:0] count[0:3];
  reg busy,active_we,live_seen;
  reg[1:0] owner,rr;reg[16:0] tag;reg[3:0] len,credits;
  reg[15:0] seen;
  wire[40:0] metadata={busy,active_we,owner,tag,len,seen};
  
  
  integer i,j,chosen;reg[2:0] candidate;
  always @(*)begin
   chosen=-1;
   if(count[0]!=0)chosen=0;
   else for(integer k=3;k>=1;k=k-1)begin
    candidate=1+((rr+k-1)%3);
    if(count[candidate]!=0)chosen=candidate;
   end
  end
  wire ready=!fault&&ctrl_live&&live_seen;
  reg pv,cho_v;reg[1:0] pch,cho_q;reg[339:0] phd;
  wire[1:0] sel=PICK?pch:chosen[1:0];
  wire[339:0] head0=(chosen>=0)?(queue[chosen][rp[chosen]]^QUEUE_INJECT):340'd0;
  wire[339:0] head=PICK?phd:head0;
  wire launch=ready&&!busy&&credits!=0&&(PICK?pv:(chosen>=0));
  reg pok;   // PICK: the picked word's length is non-zero (registered at pick: pcmux_pick2_b phd -> pop -> rq enable 17 lv)
  wire pop=launch&&(PICK?pok:(head[34:31]!=0));
  wire pick=PICK&&ready&&!pv&&cho_v&&count[cho_q]!=0;
  // phd is a pure data register outside the reset block: inside it, synthesis folds rst_n into the 340-bit enable
  // (pcmux_pick_b: rst_n pin -> phd enable, -316 ps)
  // phd / pok track the candidate head every edge until a pick sets pv (enable = !pv only, not the pick logic)
  reg[339:0] hd_src[0:3];
  wire[339:0] cand=PRE?hd_src[cho_q]:queue[cho_q][rp[cho_q]];
  always @(posedge ck) if(!pv) begin phd<=cand^QUEUE_INJECT;pok<=(cand[34:31]^QUEUE_INJECT[34:31])!=0;end
  // PRE: head pre-read and reset-less queue payload writes
  integer pi,pj;
  reg[2:0] pnr;
  always @(posedge ck) begin
   for(pi=0;pi<4;pi=pi+1)begin
    // queue payload (single writer): PRE writes on every push; otherwise only a legal push (the original condition)
    if(PRE!=0 ? src_rq[pi*341] : (ready&&src_rq[pi*341]&&!(count[pi]==8&&(PICK!=0||!(pop&&sel==pi)))))
     queue[pi][wp[pi]]<=src_rq[pi*341+1+:340];
   end
  end
  // hd_src re-reads queue[i][rp after this edge's pop] every edge.  No push bypass is needed: a source is picked at the
  // earliest two edges after the push that made its count non-zero (registered arbitration), by which time hd_src holds
  // the written word (a no-bypass equivalence, checked: the bypass mutant was indistinguishable).
  always @(posedge ck) if(PRE!=0) begin
   for(pj=0;pj<4;pj=pj+1)begin
`ifdef PCMUX_MUT_STALEHEAD
    pnr=rp[pj];                                                  // mutant: the pop's advance is not applied (stale head)
`else
    pnr=rp[pj]+((pop&&sel==pj)?3'd1:3'd0);
`endif
    hd_src[pj]<=queue[pj][pnr];
   end
  end
  // PICK: the read-return data registers load on every rv (their contents are only observed with src_rv); the
  // tag / beat / seen checks gate src_rv alone (pcmux_pick2_b q_r_tag -> check -> 1,024-bit src_rdata enable, 17 lv)
  reg[4*256-1:0] p_rdata;reg[4*17-1:0] p_rtag;reg[4*4-1:0] p_rbeat;
  always @(posedge ck) if(rv)begin p_rdata[owner*256+:256]<=r_data;p_rtag[owner*17+:17]<=r_tag;p_rbeat[owner*4+:4]<=r_beat;end
  reg[4*256-1:0] m_rdata;reg[4*17-1:0] m_rtag;reg[4*4-1:0] m_rbeat;
  assign src_rdata=PICK?p_rdata:m_rdata;assign src_rtag=PICK?p_rtag:m_rtag;assign src_rbeat=PICK?p_rbeat:m_rbeat;
  assign pending=busy||rq[0]||count[0]!=0||count[1]!=0||count[2]!=0||count[3]!=0;
  reg next_busy,next_we;reg[1:0] next_owner,next_rr;reg[16:0] next_tag;reg[3:0] next_len,next_credit;reg[15:0] next_seen;
  reg[2:0] nw,nr;reg[3:0] nc;reg push;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin
    busy<=0;active_we<=0;owner<=0;rr<=0;tag<=0;len<=0;seen<=0;
    credits<=0;live_seen<=0;rq<=0;src_rk<=0;src_wd<=0;src_rv<=0;src_done<=0;
    m_rdata<=0;m_rtag<=0;m_rbeat<=0;ce<=0;fault<=0;
    for(i=0;i<4;i=i+1)begin wp[i]<=0;rp[i]<=0;count[i]<=0;end
    pv<=0;cho_v<=0;cho_q<=0;pch<=0;
   end else begin
    if(PICK)begin
     cho_v<=(chosen>=0);cho_q<=chosen[1:0];
     if(pick)begin pv<=1;pch<=cho_q;end
     if(pop)pv<=0;
    end
    rq[0]<=0;src_rk<=0;src_wd<=0;src_rv<=0;src_done<=0;ce<=0;
    next_busy=busy;next_we=active_we;next_owner=owner;next_tag=tag;next_len=len;next_seen=seen;next_credit=credits;next_rr=rr;
    if(ctrl_live&&!live_seen)begin live_seen<=1;next_credit=8;end
    if(launch&&head[34:31]==0)fault<=1;
    if(ready)begin
     if(rk)begin
      if(credits==8&&!pop)fault<=1;else next_credit=credits+1'b1;
     end
     for(i=0;i<4;i=i+1)begin
      push=src_rq[i*341];nw=wp[i];nr=rp[i];nc=count[i];
      if(push)begin
       if(count[i]==8&&(PICK!=0||!(pop&&sel==i)))fault<=1;   // PICK: credits make a full-queue push illegal
       else begin nw=wp[i]+1'b1;nc=nc+1'b1;end
      end
      if(pop&&sel==i)begin nr=rp[i]+1'b1;nc=nc-1'b1;src_rk[i]<=1;end
      wp[i]<=nw;rp[i]<=nr;count[i]<=nc;
     end
     if(pop)begin
      rq<={head,1'b1};next_busy=1;next_we=head[0];if(PICK)next_owner=sel;else next_owner=chosen[1:0];next_tag=head[51:35];next_len=head[34:31];next_seen=0;
      next_credit=next_credit-1'b1;ce<=0;
      if(sel!=0)next_rr=(sel==3)?0:sel;
     end
     if(wd)begin
      if(!busy||!active_we)fault<=1;
      else begin src_wd[owner]<=1;src_done[owner]<=1;next_busy=0;end
     end
     if(rv)begin
      if(!busy||active_we||r_tag!=tag||r_beat>=len||seen[r_beat])fault<=1;
      else begin
       src_rv[owner]<=1;m_rdata[owner*256+:256]<=r_data;
       m_rtag[owner*17+:17]<=r_tag;m_rbeat[owner*4+:4]<=r_beat;
       next_seen[r_beat]=1;
       if(next_seen==((16'h1<<len)-1))begin src_done[owner]<=1;next_busy=0;end
      end
     end
    end else if(|{src_rq[0],src_rq[341],src_rq[682],src_rq[1023]})fault<=1;
    busy<=next_busy;active_we<=next_we;owner<=next_owner;tag<=next_tag;len<=next_len;seen<=next_seen;credits<=next_credit;rr<=next_rr;
    if(fault)begin rq[0]<=0;src_rk<=0;src_wd<=0;src_rv<=0;src_done<=0;end
   end
  end
 end endgenerate
endmodule
