`timescale 1ns/1ps
// Default-off actual dsfd_ctrl_pc rq341/rk/wd/rv endpoint. Four sources hold
// eight initial queue credits each. decode0 has priority; 1hostKV/2RoPE/3Engram
// alternate. One active transaction/PC preserves untagged physical wd identity
// even when the PHY scheduler reorders other requests. No cross-PC serialization.
// Flop queue payload/control has no ECC, parity, TMR or mirrors (confirmed review53).
module ot_s81_native_pc_mux_plain #(parameter integer ENABLE=0, parameter [339:0] QUEUE_INJECT=0)(
 input wire ck,rst_n,ctrl_live,
 input wire[4*341-1:0] src_rq,output reg[3:0] src_rk,
 output reg[340:0] rq,input wire rk,wd,
 input wire rv,input wire[255:0] r_data,input wire[16:0] r_tag,input wire[3:0] r_beat,
 output reg[3:0] src_wd,src_rv,src_done,output reg[4*256-1:0] src_rdata,
 output reg[4*17-1:0] src_rtag,output reg[4*4-1:0] src_rbeat,
 output wire pending,output reg ce,fault
);
 generate if(!ENABLE)begin:g_off
  assign pending=0;
  always @(*)begin src_rk=0;rq=0;src_wd=0;src_rv=0;src_done=0;src_rdata=0;src_rtag=0;src_rbeat=0;ce=0;fault=0;end
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
  wire launch=ready&&!busy&&credits!=0&&chosen>=0;
  
  wire[339:0] head=(chosen>=0)?(queue[chosen][rp[chosen]]^QUEUE_INJECT):340'd0;
  wire pop=launch&&head[34:31]!=0;
  assign pending=busy||rq[0]||count[0]!=0||count[1]!=0||count[2]!=0||count[3]!=0;
  reg next_busy,next_we;reg[1:0] next_owner,next_rr;reg[16:0] next_tag;reg[3:0] next_len,next_credit;reg[15:0] next_seen;
  reg[2:0] nw,nr;reg[3:0] nc;reg push;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin
    busy<=0;active_we<=0;owner<=0;rr<=0;tag<=0;len<=0;seen<=0;
    credits<=0;live_seen<=0;rq<=0;src_rk<=0;src_wd<=0;src_rv<=0;src_done<=0;
    src_rdata<=0;src_rtag<=0;src_rbeat<=0;ce<=0;fault<=0;
    for(i=0;i<4;i=i+1)begin wp[i]<=0;rp[i]<=0;count[i]<=0;end
   end else begin
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
       if(count[i]==8&&!(pop&&chosen==i))fault<=1;
       else begin queue[i][wp[i]]<=src_rq[i*341+1+:340];nw=wp[i]+1'b1;nc=nc+1'b1;end
      end
      if(pop&&chosen==i)begin nr=rp[i]+1'b1;nc=nc-1'b1;src_rk[i]<=1;end
      wp[i]<=nw;rp[i]<=nr;count[i]<=nc;
     end
     if(pop)begin
      rq<={head,1'b1};next_busy=1;next_we=head[0];next_owner=chosen[1:0];next_tag=head[51:35];next_len=head[34:31];next_seen=0;
      next_credit=next_credit-1'b1;ce<=0;
      if(chosen!=0)next_rr=(chosen==3)?0:chosen;
     end
     if(wd)begin
      if(!busy||!active_we)fault<=1;
      else begin src_wd[owner]<=1;src_done[owner]<=1;next_busy=0;end
     end
     if(rv)begin
      if(!busy||active_we||r_tag!=tag||r_beat>=len||seen[r_beat])fault<=1;
      else begin
       src_rv[owner]<=1;src_rdata[owner*256+:256]<=r_data;
       src_rtag[owner*17+:17]<=r_tag;src_rbeat[owner*4+:4]<=r_beat;
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
