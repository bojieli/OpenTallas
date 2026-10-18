// DEFAULT_OFF epoch permission profile. All16 entries remain actual storage;
// BEGIN/ND8pendingACK only gates reserved issues after captured allow pin.
`timescale 1ns/1ps
// Original packet ING16 promise has real16word storage ahead of CDC IBUF4.
// Captured514bit input; two parallel8:1 registered read selections and one
// registered2:1 output selection. An issue reserves a CDC slot before entering
// either read pipeline stage. Source credits free local storage only.
// RP_REPL (KVJ-A9, opt-in, default 0 = original structure): 1 replicates the
// read-pointer select bits rp[2:0] once per 64-bit slice of the 514-bit queue
// word (9 kept copies). Every copy resets with rp and advances on the same edge
// as rp (on issue), so both 8:1 read selections are cycle-identical; each copy
// drives only its own slice of r0/r1 (rp drove all 2x514 bits: 8,226/4,115
// loads on rp[1]/rp[0]). rp itself still drives bank and its own increment.
module qkd_host_qm_ingress16_service_debt #(parameter integer MUT=0,ENABLE_SERVICE=0,RP_REPL=0)(
 input wire ck,rst_n,in_v,allow,input wire[1:0]in_cls,input wire[511:0]in_d,
 output reg[4:0]in_crn,output reg out_v,output reg[545:0]out_d,
 input wire out_cr,output reg fault,output reg queue_quiet
);
 always @(posedge ck or negedge rst_n)
  if(!rst_n)queue_quiet<=0;
  else queue_quiet<=count==0&&credits==4&&!in_v&&!vq&&!read_v&&!out_v&&!out_cr&&!cq&&!fault;
 reg vq,cq,allow_q;reg[513:0]dq;
 reg[513:0]q[0:15];reg[3:0]wp,rp;reg[4:0]count;reg[2:0]credits;
 reg read_v,bank;reg[513:0]r0,r1;
 wire issue=!fault&&count!=0&&credits!=0&&(!ENABLE_SERVICE||allow_q||MUT==3);
 wire take=vq&&!fault&&(count<16||issue);
 always @(posedge ck)begin
  dq<={in_cls,in_d};
  if(take)q[wp]<=dq;
  if(RP_REPL==0)begin if(issue)begin r0<=q[{1'b0,rp[2:0]}];r1<=q[{1'b1,rp[2:0]}];end end
  out_d<={32'd0,(bank?r1:r0)^((MUT==1)?514'd1:514'd0)};
 end
 generate if(RP_REPL!=0)begin:g_rpr
  localparam integer NS=9; // ceil(514/64)
  (* keep="true",dont_touch="true" *) reg[3*NS-1:0]rpr;
  genvar s;
  for(s=0;s<NS;s=s+1)begin:g_s
   wire[2:0]a=rpr[3*s+:3];wire[513:0]w0=q[{1'b0,a}],w1=q[{1'b1,a}];
   if(s<8)begin:g_d always @(posedge ck)if(issue)begin r0[s*64+:64]<=w0[s*64+:64];r1[s*64+:64]<=w1[s*64+:64];end end
   else begin:g_c always @(posedge ck)if(issue)begin r0[513:512]<=w0[513:512];r1[513:512]<=w1[513:512];end end
   always @(posedge ck or negedge rst_n)
    if(!rst_n)rpr[3*s+:3]<=0;
`ifdef QKD_RPR_MUTANT
    else if(issue)rpr[3*s+:3]<=(s==4)?rpr[3*s+:3]+3'd2:rpr[3*s+:3]+1'b1;
`else
    else if(issue)rpr[3*s+:3]<=rpr[3*s+:3]+1'b1;
`endif
  end
 end endgenerate
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin vq<=0;cq<=0;allow_q<=0;wp<=0;rp<=0;count<=0;credits<=4;read_v<=0;bank<=0;in_crn<=0;out_v<=0;fault<=0;end
  else begin
   vq<=in_v;cq<=out_cr;allow_q<=allow;read_v<=issue;bank<=rp[3];out_v<=read_v;in_crn<=5'(issue);
   if(vq&&count==16&&!issue)fault<=1;
   if(cq&&credits==4&&!issue)fault<=1;
   else credits<=credits+3'(cq)-3'(issue);
   if(take)wp<=wp+1'b1;
   if(issue)rp<=rp+1'b1;
   case({take,issue})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:;endcase
   if(MUT==2)credits<=4; // ignores downstream reservations during a stall
  end
 end
endmodule
