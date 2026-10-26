`timescale 1ns/1ps
`default_nettype none
// Join two already LANDED service P.V faces in statically booked windows.
// Each face supplies320 records. Windows are relative to cfg capture (first=1
// means the following rising edge). No readiness or arbitration affects issue.
// The complete562b plan ABI is {pv_x48,pv_d513,pv_v1}; SO gather traffic outside
// these windows stays on its original route and is never fed back to ingress.
// Output adds one edge; ingress then adds its own input register edge.
module dsdv_pv_half_join(
 input wire clk,rst_n,input wire cfg_v,
 input wire[15:0]local_first,peer_first,
 input wire[561:0]local_pv,peer_pv,
 output reg pv_v,output reg[1:0]pv_quarter,output reg[512:0]pv_d,
 output reg fault
);
 reg active;reg[16:0]age,lf,pf,finish;reg[1:0]lq,pq;
 wire le=active && age>=lf && age<lf+17'd320;
 wire pe=active && age>=pf && age<pf+17'd320;
 wire[512:0]ld=local_pv[513:1],pd=peer_pv[513:1];
 always @(posedge clk)begin
  if(le)begin pv_d<=ld;pv_quarter<=ld[512]?ld[93:92]:lq;end
  else if(pe)begin pv_d<=pd;pv_quarter<=pd[512]?pd[93:92]:pq;end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;age<=0;lf<=0;pf<=0;finish<=0;lq<=0;pq<=0;pv_v<=0;fault<=0;end
  else begin
   pv_v<=0;
   if(cfg_v)begin
    if(active || local_first<3 || peer_first<3 ||
      !({1'b0,local_first}+17'd320<={1'b0,peer_first} || {1'b0,peer_first}+17'd320<={1'b0,local_first}))fault<=1;
    else begin active<=1;age<=1;lf<={1'b0,local_first};pf<={1'b0,peer_first};finish<=(local_first>peer_first?{1'b0,local_first}:{1'b0,peer_first})+17'd319;end
   end else if(active)begin age<=age+1;if(age==finish)active<=0;end
   if(le)begin
    if(!local_pv[0] || |local_pv[561:514] || pe)fault<=1;
    else begin pv_v<=1;if(ld[512])lq<=ld[93:92];end
   end else if(pe)begin
    if(!peer_pv[0] || |peer_pv[561:514])fault<=1;
    else begin pv_v<=1;if(pd[512])pq<=pd[93:92];end
   end
  end
 end
endmodule
`default_nettype wire
