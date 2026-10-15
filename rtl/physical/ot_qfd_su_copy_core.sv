`timescale 1ns/1ps
// Exact sequential-state cut from c6c44c12c qfd_su_static_copy.
// All clocks/reset/data captures unchanged; parent retains native packaging mux.
module ot_qfd_su_copy_core #(
 parameter integer READ_EDGES=15,DATA_MUT=0,LATENCY_MUT=0
)(
 input wire ck,rst_n,input wire [55:0] cp,
 input wire [511:0] vq0,vq1,vq2,vq3,input wire su_conflict,
 output wire cp_active,output reg cp_done,fault,
 output reg rd_v,output reg [23:0] rd_src,
 output reg wr_v,output reg [23:0] wr_dst,
 output wire [511:0] wr_data0,wr_data1,wr_data2,wr_data3
);
 wire [2047:0] vq={vq3,vq2,vq1,vq0};
 reg [2047:0] wr_data;
 assign {wr_data3,wr_data2,wr_data1,wr_data0}=wr_data;
 reg issuing;
 reg [6:0] left;
 reg [23:0] src,dst;
 reg rd_last;
 reg [23:0] rd_dst;
 reg [READ_EDGES-1:0] valid_pipe,last_pipe;
 reg [23:0] addr_pipe[0:READ_EDGES-1];
 reg wr_last;


 wire start=cp[0];
 wire [6:0] beats=cp[55:49];
 wire occupied=issuing||rd_v||(|valid_pipe)||wr_v;
 assign cp_active=occupied;
 integer i;
 always @(posedge ck or negedge rst_n) begin
  if(!rst_n)begin
   issuing<=0;left<=0;src<=0;dst<=0;rd_v<=0;rd_last<=0;
   valid_pipe<=0;last_pipe<=0;wr_v<=0;wr_last<=0;cp_done<=0;fault<=0;
  end else begin
   cp_done<=wr_v&&wr_last;
   if(start&&occupied)fault<=1;
   if(start&&!occupied)begin
    if(beats==0 || {1'b0,cp[24:1]}+({18'd0,beats}<<6)>25'h1000000 ||
       {1'b0,cp[48:25]}+({18'd0,beats}<<6)>25'h1000000)fault<=1;
    else begin issuing<=1;left<=beats;src<=cp[24:1];dst<=cp[48:25];end
   end
   if(occupied&&su_conflict)fault<=1;
   rd_v<=issuing;
   rd_last<=issuing&&(left==1);
   rd_src<=src;rd_dst<=dst;
   if(issuing)begin
    src<=src+24'd64;dst<=dst+24'd64;left<=left-1'b1;
    if(left==1)issuing<=0;
   end
   valid_pipe<={valid_pipe,rd_v};last_pipe<={last_pipe,rd_last};
   addr_pipe[0]<=rd_dst;
   for(i=1;i<READ_EDGES;i=i+1)addr_pipe[i]<=addr_pipe[i-1];
   wr_v<=valid_pipe[READ_EDGES-1-LATENCY_MUT];
   wr_last<=last_pipe[READ_EDGES-1-LATENCY_MUT];
   wr_dst<=addr_pipe[READ_EDGES-1-LATENCY_MUT];
   wr_data<=vq[2047:0] ^ {{2047{1'b0}},(DATA_MUT!=0)};
  end
 end
 initial if(READ_EDGES<2 || LATENCY_MUT<0 || LATENCY_MUT>1)$fatal(1,"invalid static copy latency");
endmodule
