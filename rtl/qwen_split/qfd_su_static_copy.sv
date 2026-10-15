`timescale 1ns/1ps
// Compiler-reserved, bit-transparent replay at the actual SU/VM face.
// cp command: start[0], scalar src[24:1], scalar dst[48:25], beats[55:49].
// One contiguous 64-lane A descriptor per edge; no ready, credit or arbitration.
// Native memory samples the registered request and answers after READ_EDGES
// pipeline edges. A separate output register copies every raw bit unchanged.
// cp_done means last output at this face, NOT SRAM commit or XS delivery.
module qfd_su_static_copy #(
 parameter integer READ_EDGES=15, DATA_MUT=0, LATENCY_MUT=0
)(
 input wire ck,rst_n,
 input wire [55:0] cp,
 input wire [2366:0] su_va,
 input wire [6143:0] vq,
 output wire [2366:0] va,
 output wire [2136:0] xsw,
 output wire cp_active,
 output reg cp_done,fault
);
 reg issuing;
 reg [6:0] left;
 reg [23:0] src,dst;
 reg rd_v,rd_last;
 reg [23:0] rd_src,rd_dst;
 reg [READ_EDGES-1:0] valid_pipe,last_pipe;
 reg [23:0] addr_pipe[0:READ_EDGES-1];
 reg wr_v,wr_last;
 reg [23:0] wr_dst;
 reg [2047:0] wr_data;
 wire start=cp[0];
 wire [6:0] beats=cp[55:49];
 wire occupied=issuing||rd_v||(|valid_pipe)||wr_v;
 assign cp_active=occupied;
 wire su_conflict=(|{su_va[149:148],su_va[99:98],su_va[49:48]})||(|su_va[2309:2246])||su_va[2366];
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
 wire [2366:0] copy_va;
 qfd_su_vm_pack u_pack(
 .s_re0({2'd0,rd_v}),.s_re1({2'd0,rd_v}),
 .s_a0({48'd0,rd_src}),.s_a1({48'd0,rd_src+24'd1}),
 .sw_mask({64{wr_v}}),.sw_a0(wr_dst),.sw_a1(wr_dst+24'd1),.sw_data(wr_data),
 .red_we(1'b0),.red_addr(24'd0),.red_data(32'd0),.va(copy_va));
 // Selection follows a compiled reservation, never observed readiness.
 assign va=occupied?copy_va:su_va;
 assign xsw=occupied?{wr_data,{64{wr_v}},wr_dst,wr_v}:
 {su_va[2197:150],su_va[2309:2246],su_va[2221:2198],(|su_va[2309:2246])};
 initial if(READ_EDGES<2 || LATENCY_MUT<0 || LATENCY_MUT>1)$fatal(1,"invalid static copy latency");
endmodule
