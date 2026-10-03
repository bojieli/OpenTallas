`timescale 1ns/1ps
// SIMULATION boundary, not a qualified PHY. Explicit endpoint wire registers
// surround a 130 ns ESTIMATE PHY/FEC service. One flight and its returning
// credit; no guessed infinite buffering. No CDC or refresh is simulated here.
module ot_hbm_accel_link_stage_model #(
 parameter integer PW=551,WIRE=33,PHY=156,SERIAL=4
)(input wire clk,rst_n,input wire in_valid,output wire in_ready,
 input wire [PW-1:0] in_data,output wire out_valid,input wire out_ready,
 output wire [PW-1:0] out_data);
 reg busy;
 reg [WIRE-1:0] a_valid,b_valid;
 reg [PW-1:0] a[0:WIRE-1],b[0:WIRE-1],phy_data;
 integer phy_count,credit_count;
 assign in_ready=!busy;
 assign out_valid=b_valid[WIRE-1];
 assign out_data=b[WIRE-1];
 always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin busy<=0; a_valid<=0; b_valid<=0; phy_count<=0; credit_count<=0; end
 else begin
   a_valid[0]<=in_valid && in_ready;
   if(in_valid && in_ready) begin a[0]<=in_data; busy<=1; end
   for(integer i=1;i<WIRE;i=i+1) begin
     a_valid[i]<=a_valid[i-1]; if(a_valid[i-1]) a[i]<=a[i-1];
   end
   if(a_valid[WIRE-1]) begin phy_data<=a[WIRE-1]; phy_count<=PHY+SERIAL; end
   else if(phy_count>0) phy_count<=phy_count-1;
   b_valid[0]<=phy_count==1;
   if(phy_count==1) b[0]<=phy_data;
   for(integer i=1;i<WIRE;i=i+1) begin
     // one in-flight packet: only tail can stall; no combinational ready chain
     if(i==WIRE-1 && b_valid[i] && !out_ready) b_valid[i]<=1;
     else begin b_valid[i]<=b_valid[i-1]; if(b_valid[i-1]) b[i]<=b[i-1]; end
   end
   if(out_valid && out_ready) credit_count<=2*WIRE+PHY+SERIAL;
   else if(credit_count>0) credit_count<=credit_count-1;
   if(credit_count==1) busy<=0;
 end
 end
endmodule
