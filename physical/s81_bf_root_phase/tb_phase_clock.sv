`timescale 1ns/1ps
// Minimum mechanism: production phase FF, latch/AND gate, output qualifier.
// The full arithmetic transaction bench and physical qualification remain required.
module phase_vehicle #(parameter ROOT=0)(input clk,rst_n,input [31:0] d,
  output reg [31:0] sampled, output reg [31:0] o,output reg ov,output ph_o);
 wire pcl, negclk, eclk; reg ph;
 generate if(ROOT) begin
   ot_s81_bf_phase_inv u0(clk,negclk);
`ifdef OMIT_PHASE_INVERSION
   assign pcl=negclk;
`else
   ot_s81_bf_phase_inv u1(negclk,pcl);
`endif
 end else assign pcl=clk; endgenerate
 always @(posedge pcl or negedge rst_n) if(!rst_n)ph<=0;else ph<=~ph;
 ot_hdc_cg gate_(clk,ph|!rst_n,eclk);
 always @(posedge eclk) sampled<=d;
 always @(posedge clk or negedge rst_n) if(!rst_n)ov<=0;else ov<=~ph;
 always @(posedge clk) if(!ph)o<=sampled;
 assign ph_o=ph;
endmodule
module tb;
 reg clk=0,rst_n=0; reg [31:0] d=0; wire [31:0] a,b,oa,ob;wire va,vb,pa,pb;
 integer n=0,checked=0;
 phase_vehicle #(.ROOT(0)) ref_(clk,rst_n,d,a,oa,va,pa);
 phase_vehicle #(.ROOT(1)) dut(clk,rst_n,d,b,ob,vb,pb);
 always #0.4165 clk=~clk;
 initial begin
   repeat(4)@(negedge clk);rst_n=1;
   for(n=0;n<4096;n=n+1)begin
     @(negedge clk);d=$random;
     if(n%257==0)rst_n=0;else if(n%257==3)rst_n=1;
     @(posedge clk);#0.01;
`ifdef WRONG_PHASE
     if({a,oa,va,pa}!=={b,ob,vb,~pb})$fatal(1,"EXPECTED phase mismatch");
`else
     if({a,oa,va,pa}!=={b,ob,vb,pb})$fatal(1,"phase/output mismatch at %0d",n);
`endif
     checked=checked+1;
   end
   $display("PASS phase edges/reset/output qualifier checks=%0d",checked);$finish;
 end
endmodule
