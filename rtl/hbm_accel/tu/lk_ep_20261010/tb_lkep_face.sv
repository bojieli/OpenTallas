`timescale 1ns/1ps
// Drive the exact preserved original endpoint wrapper and new hard face with the
// same independently registered core model. Compare the entire external bus,
// including session/reset/status, over randomized traffic and resets.
module ot_hbm_lk_ep #(parameter NS=3, LW=487, TXQ=32, FCR=256)(
 input wire clk,rst_n,input wire[23:0]session,input wire t_v,input wire[544:0]t_flit,
 output reg t_cr,r_v,output reg[544:0]r_flit,input wire r_cr,output reg[LW-1:0]x_tx,
 input wire[LW-1:0]x_rx,output reg fault,locked);
 always @(posedge clk) begin
  r_flit <= t_flit ^ {17{session,8'h91}}; x_tx <= x_rx ^ t_flit[LW-1:0];
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n) begin t_cr<=0;r_v<=0;fault<=0;locked<=0;end
  else begin t_cr<=r_cr;r_v<=t_v;fault<=x_rx[3];locked<=session[0];end
endmodule
module tb_lkep_face;
 parameter integer MUT_FACE=0;
 reg clk=0;always #.5 clk=~clk;reg rst_n=0;
 wire[1119:0] n_bus,g_bus;wire[973:0] n_phy,g_phy;
 reg[547:0] ins=0;reg[23:0] session=0;reg[486:0] rx=0;
 assign n_bus[546:0]=ins[546:0];assign g_bus[546:0]=ins[546:0];
 assign n_bus[1117:1094]=session;assign g_bus[1117:1094]=session;
 assign n_phy[973:487]=rx;assign g_phy[973:487]=rx;
 hfd_lk_ep #(.HARD_CLOCKS(1),.MUT_FACE(MUT_FACE)) n(.clk(clk),.clk_face(clk),.rst_n(rst_n),.f_lk(n_bus),.phy(n_phy));
 hfd_lk_ep_face_golden g(.clk(clk),.rst_n(rst_n),.f_lk(g_bus),.phy(g_phy));
 integer count=0;reg[31:0] prng=32'h34ea0013;
 task automatic step_random;begin
  prng^=prng<<13;prng^=prng>>17;prng^=prng<<5;
 end endtask
 initial begin
  repeat(8) @(negedge clk);rst_n=1;
  for(integer edge_no=0;edge_no<3000;edge_no++) begin
   @(negedge clk);
   if(edge_no>12 && (n_bus!==g_bus || n_phy!==g_phy)) $fatal(1,"LKEP_FACE MUTANT FAIL edge=%0d",edge_no);
   count+=1;
   for(integer bitn=0;bitn<548;bitn+=1) begin step_random;ins[bitn]=prng[0];end
   for(integer bitn=0;bitn<487;bitn+=1) begin step_random;rx[bitn]=prng[0];end
   step_random;session=prng[23:0];rst_n=(edge_no%317!=40 && edge_no%317!=41);
  end
  $display("LKEP_FACE PASS edges=%0d external_bits_checked=%0d",count,count*2094);$finish;
 end
endmodule
