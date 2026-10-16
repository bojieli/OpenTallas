`timescale 1ns/1ps
module tb_hbm_su_rf_route;
 parameter integer STAGES=36,MUT=0;
 `include "ot_hbm_su_rf_route_flows_v5.svh"
 // die routes r = 4 src + dst (SW 0, SE 1, NW 2, NE 3), compact660_v5 per-stage relay masters
 localparam [16*72-1:0] ALLF={FLOWS_NE_NE,FLOWS_NE_NW,FLOWS_NE_SE,FLOWS_NE_SW,FLOWS_NW_NE,FLOWS_NW_NW,FLOWS_NW_SE,FLOWS_NW_SW,
                             FLOWS_SE_NE,FLOWS_SE_NW,FLOWS_SE_SE,FLOWS_SE_SW,FLOWS_SW_NE,FLOWS_SW_NW,FLOWS_SW_SE,FLOWS_SW_SW};
 initial if(STAGES!=RF_ROUTE_STAGES_V5)$fatal(1,"STAGES must equal the die RF_RELAY");
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [40:0] stimulus[0:15];
 wire [40:0] result[0:15];
 reg [40:0] expected[0:15][0:STAGES-1];
 integer cycle=0,checks=0,errors=0;
 for(genvar r=0;r<16;r=r+1)begin:g_route
  wire [STAGES-1:0] clocks;
  for(genvar k=0;k<STAGES;k=k+1)begin:g_clock
   assign clocks[k]=(MUT==3&&r==5&&k==STAGES/2&&cycle>=200)?1'b0:clk;
  end
  ot_hbm_su_rf_route #(.STAGES(STAGES),.FLOWS(ALLF[r*72+:72]),.MUT((r==5&&MUT<3)?MUT:0)) dut(
   .stage_clk(clocks),.stage_rst_n({STAGES{rst_n}}),.tuple_in(stimulus[r]),.tuple_out(result[r]));
 end
 always @(posedge clk)begin
  for(integer r=0;r<16;r=r+1)begin
   if(!rst_n)for(integer k=0;k<STAGES;k=k+1)expected[r][k]<=0;
   else begin
    expected[r][0]<=stimulus[r];
    for(integer k=1;k<STAGES;k=k+1)expected[r][k]<=expected[r][k-1];
   end
  end
  #1;
  for(integer r=0;r<16;r=r+1)begin
   checks=checks+1;
   if(result[r][40]!==expected[r][STAGES-1][40] ||
      (expected[r][STAGES-1][40]&&result[r][39:0]!==expected[r][STAGES-1][39:0]))begin
    if(errors<6)$display("RF_ROUTE ERROR cycle=%0d route=%0d got=%h want=%h",cycle,r,result[r],expected[r][STAGES-1]);
    errors=errors+1;
   end
  end
 end
 initial begin
  for(integer r=0;r<16;r=r+1)stimulus[r]=0;
  repeat(4)@(negedge clk);rst_n=1;
  for(integer n=0;n<2048+STAGES;n=n+1)begin
   cycle=n;
   if(n==1000)rst_n=0;else if(n==1003)rst_n=1;
   for(integer r=0;r<16;r=r+1)
    stimulus[r]={(n<2048&&n%7!=0),8'((n*11+r*23)%256),32'((n*32'h10203)^(r*32'h9e3779b9))};
   @(negedge clk);
  end
  if(errors)$fatal(1,"RF_ROUTE FAIL errors=%0d checks=%0d",errors,checks);
  $display("RF_ROUTE PASS routes=16 stages=%0d actual48bitmasters=%0d checks=%0d",STAGES,16*STAGES,checks);
  $finish;
 end
endmodule
