`timescale 1ns/1ps
`ifndef KVD_ERMUT
`define KVD_ERMUT 0
`endif
// Distributed ASTK e-read stage. All inputs captured directly; all outputs flops.
// Request forwarding = 2 edges. Response forwarding = 2 edges. Local EP read
// request = 2 edges, actual EP SRAM path = 3, response = 2, total 7 edges.
// A chain of eight stages with RL inter-stage registers costs 7+7*(2+RL).
// owner_id is a stable die strap, captured like every other input. No ready/credit.
module qkd_astk_er_owner_st #(parameter integer N=4)(
 input wire ck, rst_n,
 input wire [2:0] owner_id,
 input wire [N-1:0] read_v,
 input wire [11*N-1:0] read_addr,
 output reg [N-1:0] next_v,
 output reg [11*N-1:0] next_addr,
 input wire [N-1:0] prev_v,
 input wire [11*N-1:0] prev_addr,
 input wire [64*N-1:0] prev_data,
 input wire prev_fault,
 output reg [N-1:0] response_v,
 output reg [11*N-1:0] response_addr,
 output reg [64*N-1:0] response_data,
 output reg fault,
 input wire eso_v,
 input wire [15:0] com,
 input wire [63:0] esi,
 output reg [12:0] aso
);
 reg [2:0] owner_q;
 reg [N-1:0] dv[0:5];
 reg [11*N-1:0] da[0:5];
 reg [N-1:0] pv_q;
 reg [11*N-1:0] pa_q;
 reg [64*N-1:0] pd_q;
 reg pf_q, eso_q;
 reg [15:0] com_q;
 reg [63:0] esi_q;
 reg [12:0] aso_d;
 reg collide, unseen;
 integer i,j;
 always @* begin
  aso_d=0; collide=0; unseen=0;
  for(integer k=0;k<N;k=k+1) begin
   if(dv[0][k] && da[0][11*k+3+:3]==owner_q)
    aso_d={1'b0,da[0][11*k+:11],1'b1};
   if(dv[2][k] && da[2][11*k+3+:3]==owner_q) begin
    if(!com_q[da[2][11*k+3+:4]]) unseen=1;
    for(integer m=0;m<k;m=m+1)
     if(dv[2][m] && da[2][11*m+3+:3]==owner_q) collide=1;
   end
  end
 end
 always @(posedge ck) begin
  owner_q<=owner_id; da[0]<=read_addr;
  pa_q<=prev_addr; pd_q<=prev_data; com_q<=com; esi_q<=esi;
  next_addr<=da[0];
  for(integer k=1;k<6;k=k+1) da[k]<=da[k-1];
  for(integer k=0;k<N;k=k+1) begin
   if(dv[5][k] && da[5][11*k+3+:3]==owner_q) begin
    response_addr[11*k+:11]<=da[5][11*k+:11];
    response_data[64*k+:64]<= (`KVD_ERMUT==3) ? esi : esi_q;
   end else begin
    response_addr[11*k+:11]<=pa_q[11*k+:11];
    response_data[64*k+:64]<=pd_q[64*k+:64];
   end
  end
 end
 always @(posedge ck or negedge rst_n)
  if(!rst_n) begin
   for(integer k=0;k<6;k=k+1) dv[k]<=0;
   pv_q<=0; pf_q<=0; eso_q<=0; next_v<=0; aso<=0; response_v<=0; fault<=0;
  end else begin
   dv[0]<=read_v; for(integer k=1;k<6;k=k+1) dv[k]<=dv[k-1];
   next_v<=dv[0]; pv_q<=prev_v; pf_q<=prev_fault; eso_q<=eso_v;
   aso<=aso_d;
   for(integer k=0;k<N;k=k+1)
    response_v[k]<=pv_q[k] || (dv[5][k] && da[5][11*k+3+:3]==((`KVD_ERMUT==2)?(owner_q^3'd1):owner_q));
   if(pf_q || collide || (unseen && `KVD_ERMUT!=1) || eso_q) fault<=1;
   // Duplicate ownership means a broken source/static calendar, never arbitration.
   for(integer k=0;k<N;k=k+1)
    if(pv_q[k] && dv[5][k] && da[5][11*k+3+:3]==owner_q) fault<=1;
  end
 initial if(N<1 || N>8) $fatal(1,"owner stage requires 1<=N<=8");
endmodule
