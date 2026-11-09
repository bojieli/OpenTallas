`timescale 1ns/1ps
`default_nettype none
// Four statically booked landed P.V windows, two halves for each H8 pass.
// No arbitration, credits or ready-driven issue. Each window has 320 records.
module dsdv_pv_half_join_h8(
 input wire clk,rst_n,input wire cfg_v,
 input wire[15:0]local_first,peer_first,local_first1,peer_first1,
 input wire[561:0]local_pv,peer_pv,
 output reg pv_v,output reg[1:0]pv_quarter,output reg[512:0]pv_d,
 output reg fault
);
 reg active;reg[16:0]age,first_[0:3],finish;reg[1:0]lq,pq;
 wire[3:0]sel;
 for(genvar i=0;i<4;i=i+1)assign sel[i]=active && age>=first_[i] && age<first_[i]+17'd320;
 wire le=sel[0]||sel[2], pe=sel[1]||sel[3];
 wire pass_now=sel[2]||sel[3];
 wire[512:0]ld=local_pv[513:1],pd=peer_pv[513:1];
 wire[15:0]fs[0:3];assign fs[0]=local_first;assign fs[1]=peer_first;assign fs[2]=local_first1;assign fs[3]=peer_first1;
 reg cfg_bad;reg[16:0]cfg_finish;
 integer a,b;
 always @* begin
  cfg_bad=active;cfg_finish=0;
  for(integer i=0;i<4;i=i+1)begin
   if(fs[i]<3)cfg_bad=1;
   if({1'b0,fs[i]}+17'd319>cfg_finish)cfg_finish={1'b0,fs[i]}+17'd319;
   for(integer j=i+1;j<4;j=j+1)
    if(!({1'b0,fs[i]}+17'd320<={1'b0,fs[j]} || {1'b0,fs[j]}+17'd320<={1'b0,fs[i]}))cfg_bad=1;
  end
  if(local_first1<=local_first || peer_first1<=peer_first)cfg_bad=1;
 end
 always @(posedge clk)begin
  if(le)begin pv_d<=ld;pv_quarter<=ld[512]?ld[93:92]:lq;end
  else if(pe)begin pv_d<=pd;pv_quarter<=pd[512]?pd[93:92]:pq;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;age<=0;finish<=0;lq<=0;pq<=0;pv_v<=0;fault<=0;for(integer i=0;i<4;i=i+1)first_[i]<=0;end
  else begin
   pv_v<=0;
   if(cfg_v)begin
    if(cfg_bad)fault<=1;
    else begin active<=1;age<=1;finish<=cfg_finish;for(integer i=0;i<4;i=i+1)first_[i]<={1'b0,fs[i]};end
   end else if(active)begin age<=age+1;if(age==finish)active<=0;end
   if(le)begin
    if(!local_pv[0] || |local_pv[561:514] || pe || (ld[512] && ld[32]!=pass_now))fault<=1;
    else begin pv_v<=1;if(ld[512])lq<=ld[93:92];end
   end else if(pe)begin
    if(!peer_pv[0] || |peer_pv[561:514] || (pd[512] && pd[32]!=pass_now))fault<=1;
    else begin pv_v<=1;if(pd[512])pq<=pd[93:92];end
   end
  end
 end
endmodule
`default_nettype wire
